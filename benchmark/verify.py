"""The verification gate. A candidate value is shown only if every check here passes.

Checks, in order (spec section 6):
  1. the cached filing still has the bytes we hashed when we downloaded it;
  2. the quote appears verbatim in the filing's normalized text;
  3. the value is the expected number inside that quote (right column);
  4. for tagged values, the inline XBRL element exists with that id and concept and shows that number.
"""
import re
from datetime import datetime
from decimal import Decimal

from . import textnorm
from .cache import Cache
from .config import HEADER_WINDOW
from .records import Candidate

# A number not glued to a letter, %, digit, dot or comma on its left. That skips footnote
# markers like "income1" or "%5" and keeps "(0.54" as a negative. A dash standing alone
# (an em dash after normalization) is how financial tables print zero/nil.
_NUMBER = re.compile(r"(?<![A-Za-z%\d.,])(\()?(\d[\d,]*(?:\.\d+)?)|(?<!\S)(-)(?!\S)")


def parse_numbers(text: str) -> list[Decimal]:
    numbers = []
    for paren, digits, dash in _NUMBER.findall(text):
        if dash:
            numbers.append(Decimal("0"))
            continue
        value = Decimal(digits.rstrip(",").replace(",", ""))
        numbers.append(-value if paren else value)
    return numbers


def numbers_after_label(quote: str, row_label: str | None) -> list[Decimal]:
    """Numbers in a quoted table row, skipping the row label (which may contain digits)."""
    label = textnorm.normalize(row_label or "")
    rest = quote[len(label):] if label and quote.startswith(label) else quote
    return parse_numbers(rest)


def _ixbrl_fact_text(raw: bytes, fact_id: str, concept: str | None) -> str | None:
    pattern = rb'<ix:nonfraction\b[^>]*\bid="' + re.escape(fact_id.encode()) + rb'"[^>]*>(.*?)</ix:nonfraction>'
    match = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    if concept and f'name="{concept}"'.encode() not in match.group(0):
        return None
    return textnorm.normalize(re.sub(rb"<[^>]+>", b"", match.group(1)).decode("utf-8", "ignore"))


_FULL = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                   r"\s+(\d{1,2}),?\s+(\d{4})")
_MD = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                 r"\s+(\d{1,2})")


def _date_from_header(header: str):
    """Re-derive a column's period end from its recorded header text, independently of the extractor."""
    parts = [p.strip() for p in header.split("|")]
    full = _FULL.search(parts[0])
    if full and len(parts) == 1:
        return datetime.strptime(" ".join(full.groups()), "%B %d %Y").date()
    md = _MD.search(parts[0])
    if md and len(parts) == 2 and re.fullmatch(r"\d{4}", parts[1]):
        return datetime.strptime(f"{md.group(1)} {md.group(2)} {parts[1]}", "%B %d %Y").date()
    return None


def _header_present(doc_text: str, offset: int, header: str) -> bool:
    before = doc_text[max(0, offset - HEADER_WINDOW):offset]
    key_parts = [p.strip().removeprefix("Year Ended ").rstrip(",") for p in header.split("|")]
    return all(p and p in before for p in key_parts)


def check(candidate: Candidate, cache: Cache) -> tuple[bool, str]:
    ok, reason = _check(candidate, cache)
    candidate.verified, candidate.verify_reason = ok, reason
    return ok, reason


def _check(candidate: Candidate, cache: Cache) -> tuple[bool, str]:
    cit = candidate.citation
    # 1. Source bytes unchanged since download.
    if not cache.verify_hash(cit.cik, cit.accession, cit.document):
        return False, f"source file {cit.document} missing from cache or hash mismatch"
    path = cache.path(cit.cik, cit.accession, cit.document)
    cit.sha256 = cache.sha256(cit.cik, cit.accession, cit.document)

    # 2. Quote present verbatim.
    quote = textnorm.normalize(cit.quote)
    doc_text = textnorm.document_text(path)
    offset = doc_text.find(quote)
    if offset < 0:
        return False, f"quote not found verbatim in {cit.document}"
    cit.char_offset = offset
    if cit.row_label:
        # So a reviewer can find it: "search for the row label; it's match 2 of 7".
        label = textnorm.normalize(cit.row_label)
        # Counted ignoring case, as a browser's find does (deep-link review: case-sensitive counts misled readers).
        lower_doc, lower_label = doc_text.lower(), label.lower()
        cit.find_match = lower_doc.count(lower_label, 0, offset + len(label))
        cit.find_total = lower_doc.count(lower_label)

    # 3. Value is the expected number in the quote.
    numbers = numbers_after_label(quote, cit.row_label)
    if candidate.column_index is None:
        if candidate.value not in numbers:
            return False, f"value {candidate.value} does not appear in the quote"
    elif candidate.column_index >= len(numbers) or numbers[candidate.column_index] != candidate.value:
        return False, f"value {candidate.value} is not in column {candidate.column_index} of the quoted row"

    # 3b. Tables: the column header just above the row must give this period (spec 6.4).
    if candidate.method == "table" and cit.column_header is not None:
        if _date_from_header(cit.column_header) != candidate.period_end:
            return False, f"column header '{cit.column_header}' does not give period {candidate.period_end}"
        if not _header_present(doc_text, offset, cit.column_header):
            return False, f"column header '{cit.column_header}' not found above the quoted row"

    # 4. Tagged values: the XBRL element itself.
    if candidate.method == "ixbrl":
        if not cit.fact_id:
            return False, "tagged value without an XBRL element id"
        fact_text = _ixbrl_fact_text(path.read_bytes(), cit.fact_id, cit.concept)
        if fact_text is None:
            return False, f"XBRL element {cit.fact_id} ({cit.concept}) not found in {cit.document}"
        if parse_numbers(fact_text) != [abs(candidate.value)]:
            return False, f"XBRL element {cit.fact_id} shows '{fact_text}', not {candidate.value}"

    return True, "verified: hash, verbatim quote, value in quote" + (", XBRL element" if candidate.method == "ixbrl" else "")

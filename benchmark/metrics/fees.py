"""Management and incentive fees: not extracted in v1.

Fee terms sit in narrative text and are the slowest to verify, so v1 shows "Not extracted in v1" and a
citation that lands on the sentence stating the terms: the filing link, the sentence verbatim, and a
find hint. The sentence is located and checked against the cached file like any other quote.
If it can't be located, the cell links the filing and says the terms are in the narrative.

Landing (client, Window 3: "at most two scrolls away"): the link carries a URL text fragment
(#:~:text=...) made only of words that occur once in the document, so the browser scrolls to this
sentence and no other. If no such words exist, it falls back to the nearest element id shortly before
the sentence, and failing that to the plain document URL (the record's reason says which).
The plain document URL is always the part of the link before "#".
"""
import re
from pathlib import Path
from urllib.parse import quote

from .. import textnorm
from ..config import (FEE_ANCHOR_MAX_CHARS, FEE_FRAGMENT_MAX_EXTRA_WORDS, FEE_FRAGMENT_UNSAFE_CHARS,
                      FEE_QUOTE_CHARS, FEE_SECTION, FEES_IN_NARRATIVE, FEES_NOT_EXTRACTED,
                      INCENTIVE_FEE_SECTION, INCENTIVE_TERMS, NO_INCENTIVE_TERMS_NOTE)
from ..records import ValueRecord
from .common import FundData, citation, latest_filing_for, missing

METRICS = ("management_fee", "incentive_fee")

LANDING_NOTE = {
    "text_fragment": "the link scrolls to the fee sentence",
    "anchor": "the link opens at the section just before the fee sentence; search the quoted text",
    "plain": "the link opens the filing at page one (the sentence's words repeat); search the quoted text",
}


def _linked_record(data: FundData, filing, metric: str, note: str = "") -> ValueRecord:
    """A "Not extracted in v1" cell whose citation lands on the fee sentence of `filing`: the incentive-fee
    sentence for the incentive row where one is configured, else the management-fee one."""
    fund = data.fund
    path = data.fetch(filing)
    text = textnorm.document_text(path)
    phrase = FEE_SECTION[fund.ticker]
    incentive = INCENTIVE_FEE_SECTION.get(fund.ticker)
    if metric == "incentive_fee" and incentive and incentive in text:
        phrase = incentive
    offset = text.find(phrase)
    if offset < 0:
        where = citation(fund, filing, "Whole report", "", filing.period)
        reason = f"{FEES_NOT_EXTRACTED}. {FEES_IN_NARRATIVE} ({filing.form} {filing.accession})."
    else:
        quote_text = text[offset:offset + FEE_QUOTE_CHARS]
        where = citation(fund, filing, "Fee terms (narrative)", quote_text, filing.period, row_label=phrase,
                         char_offset=offset, find_match=text.count(phrase, 0, offset + len(phrase)),
                         find_total=text.count(phrase), sha256=data.cache.sha256(fund.cik, filing.accession,
                                                                                 filing.primary_doc))
        where.url, how = landing_url(where.url, path, text, offset, phrase)
        reason = (f"{FEES_NOT_EXTRACTED}: fee terms are at the linked sentence ({filing.form} "
                  f"{filing.accession}); {LANDING_NOTE[how]}.")
    return missing(fund.ticker, metric, "not_extracted", reason, filing.period, citation=where, note=note)


def _annual_without_incentive_terms(data: FundData):
    """The latest annual report, if its text never mentions incentive-fee terms (checked on every run, so the
    note can't go stale). Absence of terms is all we say: never that the fund charges no incentive fee."""
    annuals = [f for f in data.filings if f.form in (data.fund.annual_form, data.fund.annual_form + "/A")]
    if not annuals:
        return None
    annual = max(annuals, key=lambda f: (f.period, f.filing_date))
    text = textnorm.document_text(data.fetch(annual))
    return None if re.search(INCENTIVE_TERMS, text, re.IGNORECASE) else annual


def records(data: FundData) -> dict[str, ValueRecord]:
    fund = data.fund
    latest = max(data.filings, key=lambda f: (f.period, f.filing_date)) if data.filings else None
    if latest is None:
        return {m: missing(fund.ticker, m, "not_extracted", FEES_NOT_EXTRACTED) for m in METRICS}
    filing = latest_filing_for(data, latest.period)
    out = {m: _linked_record(data, filing, m) for m in METRICS}
    annual = _annual_without_incentive_terms(data)
    if annual is not None:  # client, W3: say so, and link the annual report's nearest fee section
        out["incentive_fee"] = _linked_record(data, annual, "incentive_fee", note=NO_INCENTIVE_TERMS_NOTE)
    return out


def landing_url(url: str, path: Path, text: str, offset: int, phrase: str) -> tuple[str, str]:
    """The link for the sentence at `offset`, and how it lands: "text_fragment", "anchor" or "plain"."""
    words = unique_fragment_text(text, offset, phrase)
    if words is not None:
        return fragment_url(url, words), "text_fragment"
    anchor = nearest_anchor_before(path, text, offset)
    if anchor is not None:
        return f"{url}#{anchor}", "anchor"
    return url, "plain"


def unique_fragment_text(text: str, offset: int, phrase: str) -> str | None:
    """The shortest text starting at `offset` (at least `phrase`) that occurs once in `text`.

    Browsers match text fragments ignoring case and jump to the first match, so uniqueness is
    counted ignoring case. Grows one word at a time; None if it never becomes unique, or if it
    would include a character our normalizer may have changed (the page might not match it).
    """
    lower = text.lower()
    end = offset + len(phrase)
    for _ in range(FEE_FRAGMENT_MAX_EXTRA_WORDS + 1):
        candidate = text[offset:end]
        if any(ch in candidate for ch in FEE_FRAGMENT_UNSAFE_CHARS):
            return None
        if lower.count(candidate.lower()) == 1:
            return candidate
        next_space = text.find(" ", end + 1)
        end_next = len(text) if next_space < 0 else next_space
        if end_next <= end:
            return None
        end = end_next
    return None


def encode_fragment_text(words: str) -> str:
    """Percent-encode for a text directive. The spec reserves '-', ',' and '&' there, so they are
    escaped too ('-' is otherwise left alone by URL quoting)."""
    return quote(words, safe="").replace("-", "%2D")


def fragment_url(url: str, words: str) -> str:
    return f"{url}#:~:text={encode_fragment_text(words)}"


def nearest_anchor_before(path: Path, text: str, offset: int) -> str | None:
    """The id of the last element whose text starts at most FEE_ANCHOR_MAX_CHARS before `offset`.

    Each element with an id is placed in the document text by searching for the first words at or
    after it, moving forward in document order. This is approximate (the words could also appear
    earlier), which is why it is only the fallback and the record tells the reader to search.
    """
    best, cursor = None, 0
    for el in textnorm.parse_html(path).iter():
        if not isinstance(el.tag, str) or not el.get("id"):
            continue
        head = (textnorm.element_text(el) or textnorm.normalize(el.tail or ""))[:60]
        position = text.find(head, cursor) if head else -1
        if position < 0:
            continue
        if position > offset:
            break
        best, cursor = (el.get("id"), position), position
    if best is None or offset - best[1] > FEE_ANCHOR_MAX_CHARS:
        return None
    return best[0]

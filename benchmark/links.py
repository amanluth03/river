"""Citation links that land on the cited text, not the top of the filing.

EDGAR HTML has no pages, so the link carries a URL text fragment (#:~:text=..., the same mechanism and
encoding as the fee links in metrics/fees.py). Browsers jump to the FIRST match of a fragment, ignoring
case, and never match across a table cell or paragraph boundary. So a fragment is used only if its words
occur once in the document and sit inside one cell or paragraph ("block"). In order of preference:

  1. the row label (or the first words of a narrative quote), grown word by word inside its own block
     until it occurs once. The link lands on the row; no hint needed.
  2. if that never becomes unique (TAKIX "Net asset value, end of period" is in 7 class tables), the
     first words of the nearest block that occurs once: another cell of the cited row, else the nearest
     block before it, such as a caption or the row above. Never further back than the previous copy of
     the label, so the reader's next match of the label after the landing is the cited row (the earlier
     rule "nearest unique text before" landed on TAKIX Class A's table for a Class I row).
     The hint says what to search: 'search “Net asset value, end of period”: match 2 of 7'.
  3. the nearest HTML element id before the row (fees.nearest_anchor_before), with the same hint;
  4. the plain document URL, and the hint says the link opens at the top.

Left alone: client data, non-https links, and links that already carry a "#" (the fee links decide
their own landing, decision 72).
"""
import html as htmllib
import re
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

from lxml import etree

from . import textnorm
from .cache import Cache
from .config import (BLOCK_TAGS, DEEP_LINK_HEADING_MAX_WORDS, DEEP_LINK_HEADING_WINDOW,
                     DEEP_LINK_QUOTE_START_WORDS, FEE_FRAGMENT_MAX_EXTRA_WORDS, FEE_FRAGMENT_UNSAFE_CHARS)
from .metrics.fees import fragment_url, nearest_anchor_before
from .records import Citation, RunBundle


def deep_link(citation: Citation, path: Path | None) -> tuple[str, str]:
    """The link for `citation` (whose document is cached at `path`) and a find hint for the reader.

    The hint is "" when the link lands on the cited text itself.
    """
    url = citation.url
    if citation.cik == "client" or not url.startswith("https://") or "#" in url:
        return url, ""
    if path is None or not Path(path).exists():
        return url, ""
    text = textnorm.document_text(path)
    offset, phrase = _cited_start(citation, text)
    if phrase is None:  # e.g. a "Whole report" citation: there is no one place to land on
        return url, ""
    lower = text.lower()
    hint = _find_hint(lower, offset, phrase)
    blocks = text_blocks(path)
    if blocks is None:  # could not line up blocks with the document text; don't guess a landing
        return url, f"the link opens at the top of the filing; {hint}"
    starts, texts, exact = blocks
    block = bisect_right(starts, offset) - 1

    # 1. The label (or quote start) itself, inside its own block.
    words = unique_start(text, lower, offset, starts[block] + len(texts[block]), exact[block],
                         len(phrase.split()), len(phrase.split()) + FEE_FRAGMENT_MAX_EXTRA_WORDS)
    if words is not None:
        return fragment_url(url, words), ""

    # 2. The nearest block that occurs once: the rest of the cited row, then back toward the previous label.
    for i in _nearby_blocks(starts, block, offset, len(textnorm.normalize(citation.quote or "")),
                            _search_floor(lower, offset, phrase)):
        words = unique_start(text, lower, starts[i], starts[i] + len(texts[i]), exact[i],
                             1, DEEP_LINK_HEADING_MAX_WORDS, extend=True)
        if words is not None:
            return fragment_url(url, words), hint

    # 3. and 4.
    anchor = nearest_anchor_before(Path(path), text, offset)
    if anchor is not None:
        return f"{url}#{anchor}", f"the link opens at the nearest section marker; {hint}"
    return url, f"no unique text near the value, so the link opens at the top of the filing; {hint}"


def apply_deep_links(bundle: RunBundle, cache: Cache) -> dict[tuple, str]:
    """Set the deep link on every citation in the bundle (table cells, their inputs and candidates, and
    NAV trend points). Returns the find hints, keyed by (accession, char_offset, row_label)."""
    hints = {}
    for citation in _citations(bundle):
        path = None if citation.cik == "client" else cache.path(citation.cik, citation.accession,
                                                                 citation.document)
        citation.url, hint = deep_link(citation, path)
        if hint:
            hints[(citation.accession, citation.char_offset, citation.row_label)] = hint
    return hints


def _citations(bundle: RunBundle):
    for row in bundle.table.values():
        for record in row.values():
            if record.citation is not None:
                yield record.citation
            for item in record.inputs + record.candidates:
                yield item.citation
    for points in bundle.trend.values():
        for point in points:
            if point.citation is not None:
                yield point.citation


def _cited_start(citation: Citation, text: str) -> tuple[int, str | None]:
    """Where the cited text starts in the document, and the words to link from there: the row label
    if the quote starts with it, else the first few words of the quote. (offset, None) if neither."""
    quote = textnorm.normalize(citation.quote or "")
    offset = citation.char_offset
    if offset is None:
        offset = text.find(quote) if quote else -1
    if offset < 0:
        return -1, None
    label = textnorm.normalize(citation.row_label or "")
    if label and text.startswith(label, offset):
        return offset, label
    start = " ".join(quote.split()[:DEEP_LINK_QUOTE_START_WORDS])
    if start and text.startswith(start, offset):
        return offset, start
    return offset, None


def _find_hint(lower: str, offset: int, phrase: str) -> str:
    """'search “label”: match N of M'. Counted ignoring case, because a browser's find does, so this can
    differ from the gate's find_match/find_total (which count exact case)."""
    key = phrase.lower()
    return f"search “{phrase}”: match {lower.count(key, 0, offset + len(key))} of {lower.count(key)}"


def _search_floor(lower: str, offset: int, phrase: str) -> int:
    """How far back step 2 may look: the end of the previous copy of the label, or the window limit."""
    previous = lower.rfind(phrase.lower(), 0, offset)
    floor = previous + len(phrase) if previous >= 0 else 0
    return max(floor, offset - DEEP_LINK_HEADING_WINDOW)


def _nearby_blocks(starts: list[int], block: int, offset: int, quote_length: int, floor: int):
    """Block numbers to try in step 2: the other blocks of the quoted row, then backward to `floor`."""
    i = block + 1
    while i < len(starts) and starts[i] < offset + quote_length:
        yield i
        i += 1
    i = block - 1
    while i >= 0 and starts[i] >= floor:
        yield i
        i -= 1


def unique_start(text: str, lower: str, start: int, end: int, exact: bool, min_words: int,
                 max_words: int, extend: bool = False) -> str | None:
    """The shortest run of whole words from `start` (at least `min_words`, at most `max_words`, never
    past `end`) that has a letter or digit and occurs once in the document, ignoring case.
    With `extend`, that run is then lengthened as far as the same limits allow (still unique, since
    it contains the unique run), so a heading is highlighted whole rather than as "Class I".

    If the block is not `exact` (our normalizer changed a character in it), a run never includes a
    quote or hyphen, which might be a different character on the page (same rule as the fee links).
    """
    words = text[start:end].split(" ")
    for count in range(min_words, min(len(words), max_words) + 1):
        candidate = " ".join(words[:count])
        if not exact and any(ch in candidate for ch in FEE_FRAGMENT_UNSAFE_CHARS):
            return None
        if any(ch.isalnum() for ch in candidate) and _occurs_once(lower, candidate.lower()):
            return _extended(words, count, max_words, exact) if extend else candidate
    return None


def _extended(words: list[str], count: int, max_words: int, exact: bool) -> str:
    while count < min(len(words), max_words):
        if not exact and any(ch in words[count] for ch in FEE_FRAGMENT_UNSAFE_CHARS):
            break
        count += 1
    return " ".join(words[:count])


def _occurs_once(lower: str, key: str) -> bool:
    first = lower.find(key)
    return first >= 0 and lower.find(key, first + 1) < 0


def text_blocks(path: Path) -> tuple[list[int], list[str], list[bool]] | None:
    """The document text split at every cell/paragraph boundary: (start offsets, texts, exact flags).

    This walks the HTML as textnorm.element_text does, but cuts the text where element_text inserts a
    boundary space, so the pieces joined by single spaces are the document text (checked; None if not)
    and each piece is what a browser treats as one block. A piece is "exact" if normalizing changed
    nothing but whitespace, so its quotes and hyphens are the page's own characters.
    """
    stat = Path(path).stat()
    return _text_blocks(str(path), stat.st_size, stat.st_mtime)


@lru_cache(maxsize=8)
def _text_blocks(path_str: str, size: int, mtime: float):
    root = textnorm.parse_html(Path(path_str))
    texts, exact, current = [], [], []

    def close_block():
        raw = "".join(current)
        current.clear()
        piece = textnorm.normalize(raw)
        if piece:
            texts.append(piece)
            exact.append(piece == re.sub(r"\s+", " ", htmllib.unescape(raw)).strip())

    for event, el in etree.iterwalk(root, events=("start", "end")):
        is_tag = isinstance(el.tag, str)
        if is_tag and el.tag.lower() in BLOCK_TAGS:
            close_block()
        if event == "start" and is_tag and el.text:
            current.append(el.text)
        if event == "end" and el is not root and el.tail:
            current.append(el.tail)
    close_block()

    if " ".join(texts) != textnorm.document_text(Path(path_str)):
        return None
    starts, position = [], 0
    for piece in texts:
        starts.append(position)
        position += len(piece) + 1
    return starts, texts, exact

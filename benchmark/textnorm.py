"""One way to turn filing HTML into text, shared by extractors and the verifier.

Extraction and verification must see identical text; otherwise a quote could fail
verification just because of spacing. Everything goes through `normalize`.
"""
import html as htmllib
import re
from functools import lru_cache
from pathlib import Path

from lxml import etree, html

# Tags that end a visual unit. We insert a space there so "$" and "8.32" in two
# table cells become "$ 8.32", not "$8.32".
BLOCK_TAGS = {"td", "th", "tr", "p", "div", "br", "li", "table", "tbody", "thead",
              "h1", "h2", "h3", "h4", "h5", "h6"}

_CHAR_MAP = {
    "\xa0": " ", " ": " ", " ": " ", "​": "", "﻿": "",
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
}
_TRANSLATE = str.maketrans(_CHAR_MAP)


def normalize(text: str) -> str:
    text = htmllib.unescape(text).translate(_TRANSLATE)
    return re.sub(r"\s+", " ", text).strip()


def element_text(element) -> str:
    """Text of an element, with a space at every cell/row/block boundary, normalized."""
    parts = []
    for event, el in etree.iterwalk(element, events=("start", "end")):
        is_tag = isinstance(el.tag, str)
        block = is_tag and el.tag.lower() in BLOCK_TAGS
        if event == "start":
            if block:
                parts.append(" ")
            if is_tag and el.text:
                parts.append(el.text)
        else:
            if block:
                parts.append(" ")
            if el is not element and el.tail:
                parts.append(el.tail)
    return normalize("".join(parts))


@lru_cache(maxsize=3)
def _parse(path_str: str, size: int, mtime: float):
    # Decide the encoding ourselves: many filings declare none, and lxml would then assume
    # Latin-1 and turn UTF-8 non-breaking spaces into "Â ".
    raw = Path(path_str).read_bytes()
    try:
        raw.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        encoding = "windows-1252"
    return html.fromstring(raw, parser=html.HTMLParser(encoding=encoding)).getroottree().getroot()


def parse_html(path: Path):
    """Parsed lxml tree of a filing (memoized while the file is unchanged; filings can be 60 MB)."""
    stat = Path(path).stat()
    return _parse(str(path), stat.st_size, stat.st_mtime)


@lru_cache(maxsize=8)
def _document_text(path_str: str, size: int, mtime: float) -> str:
    return element_text(parse_html(Path(path_str)))


def document_text(path: Path) -> str:
    """Normalized text of a whole filing document (memoized while the file is unchanged)."""
    stat = Path(path).stat()
    return _document_text(str(path), stat.st_size, stat.st_mtime)

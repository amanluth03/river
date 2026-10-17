"""Find a labeled row in a filing's HTML tables and map each number to its column's period.

Used for interval-fund financial highlights (NAV per share, Class I) and KREF's book value table.
It returns nothing rather than guess when the column headers and values don't line up.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .. import textnorm
from ..verify import numbers_after_label, parse_numbers

MONTHS = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
FULL_DATE = re.compile(MONTHS + r"\s+(\d{1,2}),?\s+(\d{4})")
MONTH_DAY = re.compile(MONTHS + r"\s+(\d{1,2})\b,?(?!\s*\d{4})")
CLASS_LABEL = re.compile(r"\b(?:CLASS|Class)\s+([A-Z]{1,2})\b")
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass
class RowHit:
    label: str
    values: list[Decimal]
    column_dates: list[date]
    quote: str  # the whole row's text, verbatim from the normalized document
    share_class: str | None
    heading: str  # text just before the table, for the citation's section
    table: object = field(repr=False)
    path: Path = field(repr=False)


def parse_number(cell_text: str) -> Decimal | None:
    numbers = parse_numbers(textnorm.normalize(cell_text))
    return numbers[0] if numbers else None


def _cells(row) -> list[str]:
    return [t for t in (textnorm.element_text(c) for c in row.xpath("./td|./th")) if t]


def _to_date(month: str, day: str, year: str | int) -> date:
    return datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()


def _is_year(n: Decimal) -> bool:
    return n == n.to_integral_value() and 1990 <= n <= 2100


def _is_header_row(row) -> bool:
    cells = _cells(row)
    if not cells:
        return True
    text = " ".join(cells)
    if re.search(MONTHS, text):
        return True
    numbers = numbers_after_label(text, cells[0])
    return not numbers or all(_is_year(n) for n in numbers)


def _column_dates(header_rows, preceding: str, count: int) -> list[date] | None:
    # Case 1: a header row whose cells each carry a full date (ranges take the end date).
    for row in header_rows:
        dates = []
        for cell in _cells(row):
            found = FULL_DATE.findall(cell)
            if found:
                dates.append(_to_date(*found[-1]))
        if len(dates) == count:
            return dates
    # Case 2: mixed. "Six Months Ended June 30, 2025" columns first, then one "Year Ended December 31,"
    # group over a row of bare years. Accepted only in exactly that order, so dates can't be shuffled.
    years_rows = [[n for n in parse_numbers(" ".join(_cells(r))) if _is_year(n)] for r in header_rows]
    for row in header_rows:
        kinds, fulls, month_day = [], [], None
        for cell in _cells(row):
            found = FULL_DATE.findall(cell)
            if found:
                kinds.append("F")
                fulls.append(_to_date(*found[-1]))
            elif MONTH_DAY.search(cell):
                kinds.append("M")
                month_day = MONTH_DAY.findall(cell)[-1]
        if fulls and kinds == ["F"] * len(fulls) + ["M"]:
            for years in years_rows:
                if len(fulls) + len(years) == count:
                    return fulls + [_to_date(month_day[0], month_day[1], int(y)) for y in years]
    # Case 3: a row of bare years plus a "December 31," somewhere in the header or just above it.
    header_text = " ".join(" ".join(_cells(r)) for r in header_rows)
    month_days = MONTH_DAY.findall(header_text) or MONTH_DAY.findall(preceding)
    if not month_days:
        return None
    month, day = month_days[-1]
    for row in header_rows:
        cells = _cells(row)
        years = [n for n in parse_numbers(" ".join(cells)) if _is_year(n)]
        if len(years) == count:
            return [_to_date(month, day, int(y)) for y in years]
    return None


def _literal_prefix(regex: str) -> str:
    """'^Net asset value, end of (the )?period' -> 'net asset value, end of' (for a fast XPath prefilter)."""
    return re.split(r"[(\[\\?*+|]", regex.lstrip("^"))[0].strip().lower()


def _table_of(row):
    node = row
    while node is not None and node.tag != "table":
        node = node.getparent()
    return node


def _share_class(table, header_rows, preceding: str) -> str | None:
    in_table = CLASS_LABEL.findall(" ".join(" ".join(_cells(r)) for r in header_rows))
    if in_table:
        return in_table[0]
    before = CLASS_LABEL.findall(preceding)
    return before[-1] if before else None


def _hit_for_row(row, table, label_regex, path, doc_text) -> RowHit | None:
    cells = _cells(row)
    if not cells or not re.match(label_regex, cells[0], re.IGNORECASE):
        return None
    quote = textnorm.element_text(row)
    values = numbers_after_label(quote, cells[0])
    if not values:
        return None
    rows = table.xpath(".//tr")
    header_rows = []
    for r in rows:
        if r is row or not _is_header_row(r):
            break
        header_rows.append(r)
    table_text = textnorm.element_text(table)
    pos = doc_text.find(table_text[:300])
    preceding = doc_text[max(0, pos - 400):pos] if pos >= 0 else ""
    dates = _column_dates(header_rows, preceding, len(values))
    if dates is None:
        return None
    return RowHit(label=cells[0], values=values, column_dates=dates, quote=quote,
                  share_class=_share_class(table, header_rows, preceding),
                  heading=preceding[-200:].strip(), table=table, path=Path(path))


def find_row(path: Path, label_regex: str, class_label: str | None) -> list[RowHit]:
    """Every table row in the document whose label matches, restricted to one share class if given."""
    root = textnorm.parse_html(path)
    doc_text = textnorm.document_text(path)
    prefix = _literal_prefix(label_regex)
    rows = root.xpath("//tr[contains(translate(normalize-space(translate(string(.), $nb, ' ')), $up, $lo), $p)]",
                      nb=" ", up=UPPER, lo=UPPER.lower(), p=prefix)
    hits = []
    for row in rows:
        table = _table_of(row)
        if table is None:
            continue
        hit = _hit_for_row(row, table, label_regex, path, doc_text)
        if hit is None:
            continue
        if class_label is not None and hit.share_class != class_label:
            continue
        hits.append(hit)
    return hits


def row_in_same_table(hit: RowHit, label_regex: str) -> RowHit | None:
    """Another row from the same table with the same columns (for reconciliations)."""
    doc_text = textnorm.document_text(hit.path)
    for row in hit.table.xpath(".//tr"):
        other = _hit_for_row(row, hit.table, label_regex, hit.path, doc_text)
        if other is not None and other.column_dates == hit.column_dates:
            return other
    return None

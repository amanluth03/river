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
from ..config import CAPTION_CHARS, PERIOD_LENGTHS
from ..verify import numbers_after_label, parse_numbers

MONTHS = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
FULL_DATE = re.compile(MONTHS + r"\s+(\d{1,2}),?\s+(\d{4})")
# "December 31," with no year after it. The lookahead also skips the comma, so the month-day
# inside a full date like "September 30, 2025" never matches (review finding 1).
MONTH_DAY = re.compile(MONTHS + r"\s+(\d{1,2})\b(?!,?\s*\d{4})")
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
    column_headers: list[str] = field(default_factory=list)  # header text that gave each column its date
    column_titles: list[str] = field(default_factory=list)  # each column's full title (says the period length)


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


def _column_dates(header_rows, preceding: str, count: int) -> tuple[list[date], list[str], list[str]] | None:
    """Period end for each value column, the header text each date came from (kept as evidence), and the
    column's full title (e.g. "For the Six Months Ended September 30, 2025"), which says how long the period is."""
    # Case 1: a header row whose cells each carry a full date (ranges take the end date).
    for row in header_rows:
        dates, texts, titles = [], [], []
        for cell in _cells(row):
            found = FULL_DATE.findall(cell)
            if found:
                dates.append(_to_date(*found[-1]))
                texts.append(" ".join(found[-1][:2]) + ", " + found[-1][2])
                titles.append(cell)
        if len(dates) == count:
            return dates, texts, titles
    # Case 2: mixed. "Six Months Ended June 30, 2025" columns first, then one "Year Ended December 31,"
    # group over a row of bare years. Accepted only in exactly that order, so dates can't be shuffled.
    years_rows = [[n for n in parse_numbers(" ".join(_cells(r))) if _is_year(n)] for r in header_rows]
    for row in header_rows:
        kinds, fulls, texts, titles, month_day, md_cell = [], [], [], [], None, ""
        for cell in _cells(row):
            found = FULL_DATE.findall(cell)
            if found:
                kinds.append("F")
                fulls.append(_to_date(*found[-1]))
                texts.append(" ".join(found[-1][:2]) + ", " + found[-1][2])
                titles.append(cell)
            elif MONTH_DAY.search(cell):
                kinds.append("M")
                month_day, md_cell = MONTH_DAY.findall(cell)[-1], cell
        if fulls and kinds == ["F"] * len(fulls) + ["M"]:
            for years in years_rows:
                if len(fulls) + len(years) == count:
                    md_text = f"{month_day[0]} {month_day[1]},"
                    return (fulls + [_to_date(month_day[0], month_day[1], int(y)) for y in years],
                            texts + [f"Year Ended {md_text} | {int(y)}" for y in years],
                            titles + [md_cell] * len(years))
    # Case 3: a single-period statement whose date is only in its caption, e.g. CCLFX's balance sheet:
    # "Consolidated Statement of Assets and Liabilities September 30, 2025 (Unaudited)" above a table with
    # one value column. Accepted only with one value column and exactly one distinct date in the caption.
    # Header rows are checked one by one: joined, "Year Ended December 31," and a row of years below it
    # would read as the full date "December 31, 2025".
    row_texts = [" ".join(_cells(r)) for r in header_rows]
    header_text = " ".join(row_texts)
    any_full_date = any(FULL_DATE.search(t) for t in row_texts)
    caption_dates = set(FULL_DATE.findall(preceding[-CAPTION_CHARS:]))
    if count == 1 and not any_full_date and len(caption_dates) == 1:
        month, day, year = caption_dates.pop()
        return [_to_date(month, day, year)], [f"{month} {day}, {year}"], [preceding[-CAPTION_CHARS:]]
    # Case 4: a row of bare years plus one "December 31," in the header or just above it.
    # Refused if the header also has a full date or two different month-days: the order would be a guess.
    # Also refused if the header names more than one period ("Three Months Ended ... Year Ended December 31,"):
    # one month-day would then be shared by columns of different lengths.
    if any_full_date or len(re.findall(r"\bEnded\b", header_text, re.IGNORECASE)) > 1:
        return None
    month_days = {md for t in row_texts for md in MONTH_DAY.findall(t)} or set(MONTH_DAY.findall(preceding))
    if len(month_days) != 1:
        return None
    month, day = month_days.pop()
    title = next((t for t in row_texts if MONTH_DAY.search(t)), preceding[-CAPTION_CHARS:])
    for years in years_rows:
        if len(years) == count:
            return ([_to_date(month, day, int(y)) for y in years],
                    [f"Year Ended {month} {day}, | {int(y)}" for y in years], [title] * len(years))
    return None


def _literal_prefix(regex: str) -> str:
    """'^Net asset value, end of (the )?period' -> 'net asset value, end of' (for a fast XPath prefilter)."""
    return re.split(r"[(\[\\?*+|$]", regex.lstrip("^"))[0].strip().lower()


def _table_of(row):
    node = row
    while node is not None and node.tag != "table":
        node = node.getparent()
    return node


def _preceding_text(element, limit: int = 400) -> str:
    """Text just before this element in the document, found by walking back through the tree
    (not by searching for the table's text, which finds the first of several identical tables)."""
    parts, size, node = [], 0, element
    while node is not None and size < limit:
        prev = node.getprevious()
        if prev is None:
            node = node.getparent()
            continue
        text = textnorm.element_text(prev)
        if text:
            parts.append(text)
            size += len(text)
        node = prev
    return " ".join(reversed(parts))[-limit:]


def _share_class(table, header_rows, preceding: str) -> str | None:
    in_table = CLASS_LABEL.findall(" ".join(" ".join(_cells(r)) for r in header_rows))
    if in_table:
        return in_table[0]
    before = CLASS_LABEL.findall(preceding)
    return before[-1] if before else None


def _hit_for_row(row, table, label_regex, path) -> RowHit | None:
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
    preceding = _preceding_text(table)
    columns = _column_dates(header_rows, preceding, len(values))
    if columns is None:
        return None
    dates, headers, titles = columns
    return RowHit(label=cells[0], values=values, column_dates=dates, quote=quote,
                  share_class=_share_class(table, header_rows, preceding),
                  heading=preceding[-200:].strip(), table=table, path=Path(path), column_headers=headers,
                  column_titles=titles)


def find_row(path: Path, label_regex: str, class_label: str | None) -> list[RowHit]:
    """Every table row in the document whose label matches, restricted to one share class if given."""
    root = textnorm.parse_html(path)
    prefix = _literal_prefix(label_regex)
    rows = root.xpath("//tr[contains(translate(normalize-space(translate(string(.), $nb, ' ')), $up, $lo), $p)]",
                      nb=" ", up=UPPER, lo=UPPER.lower(), p=prefix)
    hits = []
    for row in rows:
        table = _table_of(row)
        if table is None:
            continue
        hit = _hit_for_row(row, table, label_regex, path)
        if hit is None:
            continue
        if class_label is not None and hit.share_class != class_label:
            continue
        hits.append(hit)
    return hits


def row_in_same_table(hit: RowHit, label_regex: str) -> RowHit | None:
    """Another row from the same table with the same columns (for reconciliations)."""
    for row in hit.table.xpath(".//tr"):
        other = _hit_for_row(row, hit.table, label_regex, hit.path)
        if other is not None and other.column_dates == hit.column_dates:
            return other
    return None


def period_months(title: str) -> int | None:
    """How many months a column covers, read from its title; None if the title doesn't say or is ambiguous."""
    found = {months for pattern, months in PERIOD_LENGTHS if re.search(pattern, title, re.IGNORECASE)}
    return found.pop() if len(found) == 1 else None


@dataclass
class NamedColumnsRow:
    """A row of a table whose columns are named, not dated (e.g. "1-Year 5-Year Since Inception")."""
    label: str
    quote: str  # the whole row's text, verbatim from the normalized document
    cells: list[str]  # value cells, label first; a lone "%" cell is merged into the number before it
    header: list[str]  # header cells, aligned with `cells`
    caption: str  # where the period came from, e.g. "Average Annual Total Returns through December 31, 2025"
    period: date


def find_named_columns_row(path: Path, row_regex: str, header_regex: str, caption_regex: str) -> list[NamedColumnsRow]:
    """Rows whose first cell matches, in a table with a header row of as many cells (one of them matching
    `header_regex`) and a caption (header text or just above the table) that gives one date.
    Anything else is refused, not guessed."""
    root = textnorm.parse_html(path)
    out = []
    for row in root.xpath("//tr"):
        cells = [c for c in _cells(row) if c != "%"]
        if not cells or not re.match(row_regex, cells[0]):
            continue
        table = _table_of(row)
        header = next((h for h in (_cells(r) for r in table.xpath(".//tr")) if len(h) == len(cells)
                       and any(re.match(header_regex, c) for c in h)), None)
        context = " ".join(_cells(table.xpath(".//tr")[0])) + " " + _preceding_text(table)
        captions = re.findall(caption_regex, context)
        if header is None or len(set(captions)) != 1:
            continue
        found = FULL_DATE.search(captions[0])
        if not found:
            continue
        caption = re.search(caption_regex, context).group(0)
        out.append(NamedColumnsRow(label=cells[0], quote=textnorm.element_text(row), cells=cells, header=header,
                                   caption=caption, period=_to_date(*found.groups())))
    return out

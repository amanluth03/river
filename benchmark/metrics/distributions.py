"""Distribution yield = trailing-12-month distributions per share / period-end NAV per share (decision 16).

Funds report distributions for their own periods (fiscal years, six months, quarters). The trailing
12 months ending on the NAV date P are built only from reported pieces, never estimated:
  a 12-month figure ending at P, if the fund reports one (TAKIX, KREF: fiscal year = calendar year); else
  current k-month piece ending at P + the fiscal year ending k months before P - the same k-month piece
  one year earlier (CCLFX: six months; GBDC: one quarter). Each piece is a verified row or tag.
If no 12-month total can be built, the yield uses the period actually covered, flagged (decision 16).
"""
import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

import re

from .. import textnorm
from ..config import (DISTRIBUTION_CONCEPT, DISTRIBUTION_ROWS, GBDC_QUARTER_NUMBER, GBDC_QUARTERS_LAST_HEADER,
                      GBDC_QUARTERS_YEAR_ROW, GBDC_SPECIALS, GBDC_SPECIALS_QUOTES, GBDC_SPECIALS_SOURCE,
                      PERIOD_DAYS)
from ..verify import numbers_after_label
from ..conflicts import resolve
from ..extract import tables
from ..records import Candidate, ValueRecord
from .common import (FundData, check_all, chosen_candidate, citation, computed, ixbrl_candidates, missing,
                     table_candidate)

METRIC = "distribution_yield"


def months_before(d: date, months: int) -> date:
    """The month-end `months` months before month-end `d` (2025-09-30, 6 -> 2025-03-31)."""
    index = d.year * 12 + d.month - 1 - months
    year, month = divmod(index, 12)
    return date(year, month + 1, calendar.monthrange(year, month + 1)[1])


def _table_pieces(data: FundData, period: date) -> list[tuple[int, Candidate]]:
    regex = DISTRIBUTION_ROWS[data.fund.ticker]
    section = (f"Financial Highlights (Class {data.fund.share_class})" if data.fund.kind == "interval"
               else "Consolidated Statements of Income")
    pieces = []
    for filing in data.filings:
        for hit in tables.find_row(data.fetch(filing), regex, data.fund.share_class):
            for i, end in enumerate(hit.column_dates):
                months = tables.period_months(hit.column_titles[i])
                if months and end <= period:
                    pieces.append((months, table_candidate(data.fund, filing, hit, i, "distributions_per_share",
                                                           "usd", section)))
    return pieces


def _ixbrl_pieces(data: FundData, period: date) -> list[tuple[int, Candidate]]:
    pieces = []
    for filing in data.filings:
        for fact, cand in ixbrl_candidates(data.fund, filing, data.fetch(filing), DISTRIBUTION_CONCEPT,
                                           "distributions_per_share", "usd", f"Inline XBRL {DISTRIBUTION_CONCEPT}"):
            if fact.period_start is None or fact.period_end > period:
                continue
            days = (fact.period_end - fact.period_start).days
            months = next((m for (low, high), m in PERIOD_DAYS if low <= days <= high), None)
            if months:
                pieces.append((months, cand))
    return pieces


def _best(pieces, cache) -> dict[tuple[date, int], ValueRecord]:
    """One resolved record per (period end, length): agreeing filings confirm, conflicts are shown."""
    groups = defaultdict(list)
    for months, cand in pieces:
        groups[(cand.period_end, months)].append(cand)
    out = {}
    for key, cands in groups.items():
        check_all(cands, cache)
        record = resolve(cands)
        if record.status in ("ok", "conflict"):
            out[key] = record
    return out


def _ttm(best, period):
    """[(sign, months, record)] that add up to the 12 months ending at `period`, or the longest piece."""
    if (period, 12) in best:
        return [(1, 12, best[(period, 12)])], 12
    for k in (3, 6, 9):
        now, year, last = (best.get((period, k)), best.get((months_before(period, k), 12)),
                           best.get((months_before(period, 12), k)))
        if now and year and last:
            return [(1, k, now), (1, 12, year), (-1, k, last)], 12
    shorter = [(m, r) for (end, m), r in best.items() if end == period]
    if shorter:
        months, record = max(shorter, key=lambda x: x[0])
        return [(1, months, record)], months
    return None, 0


def _specials_in(data: FundData, start: date, end: date) -> str:
    """GBDC special/supplemental distributions paid in (start, end], if the cited footnotes still say so."""
    cik, accession, document, _ = GBDC_SPECIALS_SOURCE
    path = data.cache.path(cik, accession, document)
    if not path.exists():
        return ""
    text = textnorm.document_text(path)
    if not all(q in text for q in GBDC_SPECIALS_QUOTES):
        return ""
    paid = [(date.fromisoformat(d), Decimal(a), kind) for d, a, kind in GBDC_SPECIALS]
    inside = [(d, a, kind) for d, a, kind in paid if start < d <= end]
    if not inside:
        return ""
    total = sum(a for _, a, _ in inside)
    kinds = " and ".join(sorted({kind for _, _, kind in inside}))
    return (f"${total} of {kinds} distributions noted in the 10-K "
            f"(paid {', '.join(sorted({d.isoformat() for d, _, _ in inside}))})")


def _item5_quarters(data: FundData) -> dict[date, Candidate]:
    """GBDC 10-K Item 5: distributions declared per share for each fiscal quarter, as verified candidates keyed
    by quarter end. The quarter's fiscal year comes from the "Fiscal year ended ..." row above it."""
    out = {}
    for filing in data.filings:
        if filing.form != data.fund.annual_form:
            continue
        path = data.fetch(filing)
        root = textnorm.parse_html(path)
        for row in root.xpath("//tr"):
            first = tables._cells(row)
            if not first or not re.match(GBDC_QUARTERS_YEAR_ROW, first[0]):
                continue
            table = tables._table_of(row)
            header = next((tables._cells(r) for r in table.xpath(".//tr") if tables._cells(r)), [])
            if not header or header[-1] != GBDC_QUARTERS_LAST_HEADER:
                break
            year_end = None
            for r in table.xpath(".//tr"):
                cells = tables._cells(r)
                if not cells:
                    continue
                year = re.match(GBDC_QUARTERS_YEAR_ROW, cells[0])
                if year:
                    year_end = tables._to_date(*tables.FULL_DATE.search(year.group(1)).groups())
                    continue
                label = next((name for name in GBDC_QUARTER_NUMBER if cells[0].startswith(name)), None)
                if year_end is None or label is None:
                    continue
                quote = textnorm.element_text(r)
                numbers = numbers_after_label(quote, cells[0])
                end = months_before(year_end, 3 * (4 - GBDC_QUARTER_NUMBER[label]))
                out.setdefault(end, Candidate(
                    fund=data.fund.ticker, metric="distributions_per_share", value=numbers[-1], unit="usd",
                    period_end=end, method="table", column_index=len(numbers) - 1, is_amendment=filing.amendment,
                    citation=citation(data.fund, filing, f"Item 5, distributions declared per share ({cells[0]}, "
                                      f"fiscal year ended {year_end})", quote, end, cells[0])))
            break
    check_all(list(out.values()), data.cache)
    return {end: c for end, c in out.items() if c.verified}


def _quarterly_route(data: FundData, best, parts, period):
    """If a fiscal-year total in `parts` differs from the sum of that year's Item 5 quarters, rebuild the 12 months
    from the four quarters ending at `period` (Item 5 first, else the 10-Q's tagged quarter). None otherwise."""
    years = [rec for _, length, rec in parts if length == 12]
    if not years:
        return None, ""
    quarters = _item5_quarters(data)
    for year in years:
        ends = [months_before(year.period_end, 3 * i) for i in range(4)]
        if all(e in quarters for e in ends):
            listed = sum(quarters[e].value for e in ends)
            if listed != year.value:
                break
    else:
        return None, ""
    route = []
    for end in [months_before(period, 3 * i) for i in range(4)]:
        cand = quarters.get(end) or (chosen_candidate(best[(end, 3)]) if (end, 3) in best else None)
        if cand is None:
            return None, ""
        route.append((1, 3, resolve([cand])))
    note = (f"Fiscal-year total {year.value} (per weighted-average share, {year.citation.form} "
            f"{year.citation.accession}) differs from its quarters declared per share ({listed}, Item 5); "
            f"the trailing 12 months use quarterly amounts")
    return route, note


def record(data: FundData) -> ValueRecord:
    fund, nav_cell = data.fund, data.nav_cell
    if nav_cell.status != "ok":
        return missing(fund.ticker, METRIC, "not_found", "No verified period-end NAV to divide by.")
    period = nav_cell.period_end
    pieces = _ixbrl_pieces(data, period) if fund.kind == "bdc" else _table_pieces(data, period)
    best = _best(pieces, data.cache)
    parts, months = _ttm(best, period)
    basis_note = ""
    if fund.kind == "bdc" and parts:
        route, basis_note = _quarterly_route(data, best, parts, period)
        parts = route or parts
    if not parts:
        return missing(fund.ticker, METRIC, "not_found",
                       f"No verified distributions per share for a period ending {period} in the filings read.", period)
    conflicted = [rec for _, _, rec in parts if rec.status == "conflict"]
    if conflicted:  # an input's filing contradicts itself: the yield waits for the PM's choice
        return ValueRecord(fund=fund.ticker, metric=METRIC, value=None, unit="pct", status="conflict",
                           reason=f"{conflicted[0].reason} This is an input to the trailing-12-month yield.",
                           period_end=period, citation=conflicted[0].citation, flags=["conflict"],
                           candidates=conflicted[0].candidates, resolution=conflicted[0].resolution)
    nav_input = chosen_candidate(data.nav[period])
    inputs, terms, total, flipped = [], [], Decimal(0), False
    for sign, length, rec in parts:
        cand = chosen_candidate(rec)
        amount = abs(cand.value)
        flipped |= cand.value < 0
        total += sign * amount
        inputs.append(cand)
        terms.append(f"{'+' if sign > 0 else '-'} {amount} ({length} months to {cand.period_end}, "
                     f"{cand.citation.form} {cand.citation.accession})")
    value = (total / nav_input.value * 100).quantize(Decimal("0.01"))
    nav_name = "book value per share" if fund.kind == "mreit" else "NAV per share"
    formula = (f"Trailing {months}-month distributions per share = {' '.join(terms).lstrip('+ ')} = {total}; "
               f"yield = {total} / period-end {nav_name} {nav_input.value} = {value}%")
    if flipped:
        formula += ". Distributions are printed in parentheses (a deduction from NAV) and used as positive amounts"
    if basis_note:
        formula += f". {basis_note}"
    short = months < 12
    out = computed(fund.ticker, METRIC, value, "pct", period, inputs + [nav_input], formula,
                   basis_assumption=(f"filings give only {months} months of distributions ending {period}; "
                                     f"shown for that period, not annualized") if short else "")
    out.note = ("TTM ÷ book value" if fund.kind == "mreit" else "TTM ÷ NAV") if not short else f"{months} months only"
    if fund.kind == "bdc":
        specials = _specials_in(data, months_before(period, 12), period)
        if specials:
            out.note += f"; includes {specials}"
            out.normalizations.append(f"Includes {specials}, as stated in {GBDC_SPECIALS_SOURCE[3]}.")
    if short:
        out.flags.append("under_12_months")
    if any("conflict" in rec.flags or "pm_review" in rec.flags for _, _, rec in parts):
        out.flags.append("conflict")
        out.resolution = "; ".join(rec.resolution for _, _, rec in parts if rec.resolution)
        out.confidence, out.confidence_reason = "low", "An input had conflicting sources; see resolution."
    return out

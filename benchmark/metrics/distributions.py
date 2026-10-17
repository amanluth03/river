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

from ..config import DISTRIBUTION_CONCEPT, DISTRIBUTION_ROWS, PERIOD_DAYS
from ..conflicts import resolve
from ..extract import tables
from ..records import Candidate, ValueRecord
from .common import FundData, check_all, chosen_candidate, computed, ixbrl_candidates, missing, table_candidate

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
        if record.status == "ok":
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


def record(data: FundData) -> ValueRecord:
    fund, nav_cell = data.fund, data.nav_cell
    if nav_cell.status != "ok":
        return missing(fund.ticker, METRIC, "not_found", "No verified period-end NAV to divide by.")
    period = nav_cell.period_end
    pieces = _ixbrl_pieces(data, period) if fund.kind == "bdc" else _table_pieces(data, period)
    parts, months = _ttm(_best(pieces, data.cache), period)
    if not parts:
        return missing(fund.ticker, METRIC, "not_found",
                       f"No verified distributions per share for a period ending {period} in the filings read.", period)
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
    short = months < 12
    out = computed(fund.ticker, METRIC, value, "pct", period, inputs + [nav_input], formula,
                   basis_assumption=(f"filings give only {months} months of distributions ending {period}; "
                                     f"shown for that period, not annualized") if short else "")
    out.note = ("TTM ÷ book value" if fund.kind == "mreit" else "TTM ÷ NAV") if not short else f"{months} months only"
    if short:
        out.flags.append("under_12_months")
    if any("conflict" in rec.flags or "pm_review" in rec.flags for _, _, rec in parts):
        out.flags.append("conflict")
        out.resolution = "; ".join(rec.resolution for _, _, rec in parts if rec.resolution)
        out.confidence, out.confidence_reason = "low", "An input had conflicting sources; see resolution."
    return out

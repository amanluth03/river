"""Net returns, 1Y / 3Y / 5Y, NAV basis, as each fund reports them (decisions 2, 13, 15).

Interval funds: the "Average Annual Total Returns" table in the latest annual report (N-CSR), Class I.
  The 1Y figure is checked against the same fiscal year's total return in the Financial Highlights.
  A horizon the table doesn't have (TAKIX 3Y) is "Not reported by fund", with a link to the table.
GBDC: its reported return on average net assets for the latest fiscal year, labeled as that measure and
  "Not directly comparable"; never compounded into 3Y/5Y (client, W2).
KREF: no NAV-based return exists (a REIT reports book value, not NAV); market-price returns are excluded.
Semi-annual figures are not chained into a trailing year: the latest reported trailing figure is shown
with its lag instead (decision 39).
"""
import re
from decimal import Decimal

from ..config import (DAYS_ONE_YEAR, GBDC_RETURN_CONCEPT, GBDC_RETURN_LABEL, GBDC_RETURN_NOTE,
                      HIGHLIGHTS_RETURN_ROW, NOT_REPORTED_BY_FUND, RETURN_COLUMNS, RETURN_HEADER, RETURN_ROW,
                      RETURN_TABLE_CAPTION, RETURN_TOLERANCE)
from ..conflicts import resolve
from ..extract import tables
from ..records import Candidate, ValueRecord
from ..verify import parse_numbers
from .common import FundData, check_all, citation, ixbrl_candidates, missing

METRICS = list(RETURN_COLUMNS)


def _highlights_check(data: FundData, filing, cand: Candidate) -> None:
    """Second source for the 1Y figure: the fiscal-year total return in the Financial Highlights."""
    for hit in tables.find_row(data.fetch(filing), HIGHLIGHTS_RETURN_ROW[data.fund.ticker], data.fund.share_class):
        for i, end in enumerate(hit.column_dates):
            if end == cand.period_end and tables.period_months(hit.column_titles[i]) == 12:
                other = hit.values[i]
                ok = abs(other - cand.value) <= RETURN_TOLERANCE
                cand.reconciliation = (f"Financial Highlights total return for the year to {end}: {other}% vs "
                                       f"{cand.value}% in the performance table ({'agree' if ok else 'DISAGREE'}). "
                                       f"Highlights row: \"{hit.quote}\"")
                cand.reconciliation_ok = ok
                return


def _interval(data: FundData) -> dict[str, ValueRecord]:
    fund = data.fund
    annuals = sorted((f for f in data.filings if f.form.startswith(fund.annual_form)),
                     key=lambda f: (f.period, f.filing_date), reverse=True)
    for filing in annuals:
        rows = tables.find_named_columns_row(data.fetch(filing), RETURN_ROW[fund.ticker], RETURN_HEADER,
                                             RETURN_TABLE_CAPTION)
        if len(rows) != 1:
            continue
        row = rows[0]
        section = f"Performance: {row.caption} (Class {fund.share_class})"
        where = citation(fund, filing, section, row.quote, row.period, row.label,
                         column_header=tables.FULL_DATE.search(row.caption).group(0))
        out = {}
        for metric, header_regex in RETURN_COLUMNS.items():
            columns = [j for j, h in enumerate(row.header) if re.match(header_regex, h)]
            value = tables.parse_number(row.cells[columns[0]]) if len(columns) == 1 else None
            if value is None:
                shown = ", ".join(h for h in row.header[1:] if re.match(RETURN_HEADER, h) or h.startswith("Since"))
                out[metric] = missing(fund.ticker, metric, "not_reported",
                                      f"{NOT_REPORTED_BY_FUND}: the fund's performance table ({filing.form} "
                                      f"{filing.accession}) shows {shown} only.", row.period, citation=where)
                continue
            j = columns[0]
            index = sum(len(parse_numbers(c)) for c in row.cells[1:j])  # position among the row's numbers
            cand = Candidate(fund=fund.ticker, metric=metric, value=value, unit="pct", period_end=row.period,
                             method="table", column_index=index, is_amendment=filing.amendment,
                             citation=where.model_copy(update={"column_label": row.header[j]}))
            if metric == "net_return_1y":
                _highlights_check(data, filing, cand)
            check_all([cand], data.cache)
            out[metric] = resolve([cand])
            out[metric].note = "Average annual, NAV basis" if metric != "net_return_1y" else "NAV basis"
        return out
    reason = "No average annual total returns table found in the annual reports read."
    return {m: missing(fund.ticker, m, "not_found", reason) for m in METRICS}


def _gbdc(data: FundData) -> dict[str, ValueRecord]:
    fund = data.fund
    annuals = sorted((f for f in data.filings if f.form.startswith(fund.annual_form)),
                     key=lambda f: (f.period, f.filing_date), reverse=True)
    one_year = None
    for filing in annuals:
        cands = [c for fact, c in ixbrl_candidates(fund, filing, data.fetch(filing), GBDC_RETURN_CONCEPT,
                                                   "net_return_1y", "pct", f"Financial Highlights (inline XBRL {GBDC_RETURN_CONCEPT})")
                 if fact.period_end == filing.period and fact.period_start
                 and DAYS_ONE_YEAR[0] <= (fact.period_end - fact.period_start).days <= DAYS_ONE_YEAR[1]]
        if cands:
            check_all(cands, data.cache)
            one_year = resolve(cands, label=GBDC_RETURN_LABEL)
            break
    if one_year is None:
        one_year = missing(fund.ticker, "net_return_1y", "not_found",
                           f"Tagged {GBDC_RETURN_CONCEPT} for a full fiscal year not found in the 10-Ks read.")
    else:
        one_year.note = f"{GBDC_RETURN_NOTE}: fiscal year to {one_year.period_end}; not a NAV total return"
        one_year.flags.append("not_comparable")
    reason = (f"{NOT_REPORTED_BY_FUND}: GBDC reports one fiscal year at a time (return on average net assets); "
              f"compounding years into 3Y/5Y was ruled out by the client (W2).")
    out = {"net_return_1y": one_year}
    for metric in ("net_return_3y", "net_return_5y"):
        out[metric] = missing(fund.ticker, metric, "not_reported", reason, one_year.period_end,
                              citation=one_year.citation, label=GBDC_RETURN_LABEL)
    return out


def records(data: FundData) -> dict[str, ValueRecord]:
    if data.fund.kind == "interval":
        return _interval(data)
    if data.fund.kind == "bdc":
        return _gbdc(data)
    reason = ("Not applicable: KREF reports no NAV-based total return (a REIT reports book value, not NAV); "
              "market-price returns are excluded by the NAV-basis rule.")
    where = data.nav_cell.citation and data.nav_cell.citation.model_copy(update={
        "section": "Whole report: no NAV-based return is reported", "quote": "", "row_label": None,
        "column_header": None, "column_label": None})
    return {m: missing(data.fund.ticker, m, "not_applicable", reason, citation=where) for m in METRICS}

"""NAV per share candidates for one fund: one candidate per (period, filing).

Interval funds: Class I "Net asset value, end of period" in the financial highlights,
  checked with the NAV bridge (beginning NAV + total from operations + total distributions = ending NAV).
KREF: "Book value per share" table (KREF does not report NAV), checked with equity / shares.
GBDC: the inline-XBRL tag us-gaap:NetAssetValuePerShare.
"""
from datetime import date
from decimal import Decimal
from typing import Callable

from ..config import (BOOK_VALUE, COMMON_EQUITY, KREF_BOOK_VALUE_LABEL, NAV_BEGIN, NAV_CONCEPT, NAV_END,
                      PER_SHARE_TOLERANCE as TOLERANCE, SCALE_WORDS, TOTAL_DIST, TOTAL_OPS, TOTAL_SHARES, Fund)
from ..edgar import archive_url
from ..extract import ixbrl, tables
from ..filings import Filing
from ..records import Candidate, Citation

KREF_LABEL = KREF_BOOK_VALUE_LABEL


def _citation(fund: Fund, filing: Filing, section: str, quote: str, row_label: str, period: date, **extra) -> Citation:
    return Citation(cik=fund.cik, form=filing.form, accession=filing.accession, filing_date=filing.filing_date,
                    period_end=period, url=archive_url(fund.cik, filing.accession, filing.primary_doc),
                    document=filing.primary_doc, section=section, quote=quote, row_label=row_label,
                    column_label=period.isoformat(), **extra)


def _bridge(hit, i) -> tuple[str | None, bool | None]:
    begin = tables.row_in_same_table(hit, NAV_BEGIN)
    ops = tables.row_in_same_table(hit, TOTAL_OPS)
    dist = tables.row_in_same_table(hit, TOTAL_DIST)
    if not (begin and ops and dist):
        return None, None
    end = hit.values[i]
    total = begin.values[i] + ops.values[i] + dist.values[i]
    ok = abs(total - end) <= TOLERANCE
    return (f"NAV bridge: {begin.values[i]} + {ops.values[i]} + ({dist.values[i]}) = {total} "
            f"vs reported {end} ({'ok' if ok else 'MISMATCH'})"), ok


def _book_value_check(hit, i) -> tuple[str | None, bool | None]:
    equity = tables.row_in_same_table(hit, COMMON_EQUITY)
    shares = tables.row_in_same_table(hit, TOTAL_SHARES)
    if not (equity and shares) or shares.values[i] == 0:
        return None, None
    # The scale of the equity amount comes from the table's own caption, e.g. KREF's
    # "(amounts in thousands, except share and per share data)". No caption, no check.
    words = [w for w in SCALE_WORDS if w in hit.heading.lower()]
    if len(words) != 1:
        return None, None
    scale = SCALE_WORDS[words[0]]
    computed = (equity.values[i] * scale / shares.values[i]).quantize(TOLERANCE)
    ok = abs(computed - hit.values[i]) <= TOLERANCE
    return (f"Common equity {equity.values[i]:,} ({words[0]}, per the table caption) / {shares.values[i]:,} "
            f"shares = {computed} vs reported {hit.values[i]} ({'ok' if ok else 'MISMATCH'})"), ok


def _from_table(fund, filing, path, window, label_regex, class_label, section, check) -> list[Candidate]:
    cands = []
    # Every matching table becomes a candidate source. Two tables claiming the same class with
    # different values then surface as a same-filing conflict for the PM instead of a silent pick.
    for hit in tables.find_row(path, label_regex, class_label):
        for i, (period, value) in enumerate(zip(hit.column_dates, hit.values)):
            if not window[0] <= period <= window[1]:
                continue
            if value <= 0:  # a dash (no shares outstanding) or a negative is never a NAV
                continue
            note, ok = check(hit, i)
            cands.append(Candidate(
                fund=fund.ticker, metric="nav_per_share", value=value, unit="usd", period_end=period,
                method="table", column_index=i, is_amendment=filing.amendment,
                reconciliation=note, reconciliation_ok=ok,
                citation=_citation(fund, filing, section, hit.quote, hit.label, period,
                                   column_header=hit.column_headers[i])))
    return cands


def _from_ixbrl(fund, filing, path, window) -> list[Candidate]:
    cands, seen = [], set()
    for fact in ixbrl.facts(path, NAV_CONCEPT):
        if fact.dims or not fact.row_quote or not window[0] <= fact.period_end <= window[1]:
            continue
        if fact.period_end in seen:  # the same fact is often tagged twice in one document
            continue
        seen.add(fact.period_end)
        cands.append(Candidate(
            fund=fund.ticker, metric="nav_per_share", value=fact.value, unit="usd", period_end=fact.period_end,
            method="ixbrl", is_amendment=filing.amendment,
            citation=_citation(fund, filing, f"Inline XBRL {NAV_CONCEPT}", fact.row_quote,
                               fact.row_label, fact.period_end, fact_id=fact.fact_id, concept=NAV_CONCEPT)))
    return cands


def candidates(fund: Fund, filings: list[Filing], fetch: Callable[[Filing], object],
               window: tuple[date, date]) -> list[Candidate]:
    out = []
    for filing in filings:
        path = fetch(filing)
        if fund.kind == "interval":
            out += _from_table(fund, filing, path, window, NAV_END, fund.share_class,
                               f"Financial Highlights (Class {fund.share_class})", _bridge)
        elif fund.kind == "mreit":
            out += _from_table(fund, filing, path, window, BOOK_VALUE, None,
                               "MD&A, Book Value per Share", _book_value_check)
        else:
            out += _from_ixbrl(fund, filing, path, window)
    return out

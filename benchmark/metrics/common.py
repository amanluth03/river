"""Helpers every metric uses: build cited candidates, run them through the gate, and build
computed values whose inputs are all verified.

A metric module never returns a bare number. It returns ValueRecords: either a verified value with
its citation, a computed value with every input cited, or a labeled gap with the reason.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .. import verify
from ..cache import Cache
from ..config import UNITS, Fund
from ..edgar import archive_url
from ..extract import ixbrl
from ..extract.tables import RowHit
from ..filings import Filing
from ..records import Candidate, Citation, Issue, ValueRecord


@dataclass
class FundData:
    """Everything a metric needs about one fund for one run."""
    fund: Fund
    filings: list[Filing]  # every filing in the window, oldest first
    fetch: Callable[[Filing], Path]  # cached path of a filing's main document
    cache: Cache
    as_of: date
    nav: dict[date, ValueRecord]  # resolved NAV (or KREF book value) per period
    nav_cell: ValueRecord  # the NAV shown in the table (latest verified period)
    issues: list[Issue] = field(default_factory=list)


def citation(fund: Fund, filing: Filing, section: str, quote: str, period: date | None,
             row_label: str | None = None, **extra) -> Citation:
    return Citation(cik=fund.cik, form=filing.form, accession=filing.accession, filing_date=filing.filing_date,
                    period_end=period, url=archive_url(fund.cik, filing.accession, filing.primary_doc),
                    document=filing.primary_doc, section=section, quote=quote, row_label=row_label,
                    column_label=period.isoformat() if period else None, **extra)


def table_candidate(fund: Fund, filing: Filing, hit: RowHit, i: int, metric: str, unit: str,
                    section: str) -> Candidate:
    """Column i of a table row, as a candidate the gate can check (quote, column, header)."""
    period = hit.column_dates[i]
    return Candidate(fund=fund.ticker, metric=metric, value=hit.values[i], unit=unit, period_end=period,
                     method="table", column_index=i, is_amendment=filing.amendment,
                     citation=citation(fund, filing, section, hit.quote, period, hit.label,
                                       column_header=hit.column_headers[i]))


def ixbrl_candidates(fund: Fund, filing: Filing, path: Path, concept: str, metric: str, unit: str,
                     section: str) -> list[tuple[ixbrl.Fact, Candidate]]:
    """Tagged numbers that sit in a table row, one per (period start, period end).

    Facts in running text are skipped: the same number is usually also in a table, often rounded
    differently (GBDC: "178.9%" in a note, "178.94%" in the highlights), which would be a false conflict.
    The candidate holds the number as printed; the gate compares it with the tagged element's text.
    """
    out, seen = [], set()
    for fact in ixbrl.facts(path, concept):
        if fact.dims or not fact.row_label:
            continue
        key = (fact.period_start, fact.period_end)
        if key in seen:  # the same fact is often tagged twice in one document
            continue
        seen.add(key)
        cand = Candidate(fund=fund.ticker, metric=metric, value=fact.shown, unit=unit, period_end=fact.period_end,
                         method="ixbrl", is_amendment=filing.amendment,
                         citation=citation(fund, filing, section, fact.row_quote, fact.period_end, fact.row_label,
                                           fact_id=fact.fact_id, concept=concept))
        out.append((fact, cand))
    return out


def check_all(cands: list[Candidate], cache: Cache) -> list[Candidate]:
    """Run every candidate through the verification gate; return the ones that passed."""
    for c in cands:
        verify.check(c, cache)
    return [c for c in cands if c.verified]


def missing(fund: str, metric: str, status: str, reason: str, period: date | None = None,
            citation: Citation | None = None, label: str | None = None, note: str = "") -> ValueRecord:
    """A labeled gap. It may still carry a citation: the place we looked, so the reviewer can check."""
    return ValueRecord(fund=fund, metric=metric, value=None, unit=UNITS.get(metric, "pct"), status=status,
                       reason=reason, period_end=period, citation=citation, label=label, note=note)


def chosen_candidate(record: ValueRecord) -> Candidate | None:
    """The candidate a resolved record shows (the one its citation came from)."""
    for c in record.candidates:
        if record.citation and c.citation.accession == record.citation.accession and c.value == record.value:
            return c
    return None


def computed(fund: str, metric: str, value: Decimal, unit: str, period: date, inputs: list[Candidate],
             formula: str, check: tuple[str, bool] | None = None, basis_assumption: str = "",
             label: str | None = None, note: str = "") -> ValueRecord:
    """A value calculated from verified inputs. Confidence (decision 33, refined by decision 38):
      high   - arithmetic on verified inputs, and an independent reported figure agrees (the check);
      medium - arithmetic on verified inputs, no independent figure to compare with;
      low    - the independent figure disagrees, or the calculation needs an assumption.
    """
    record = ValueRecord(fund=fund, metric=metric, value=value, unit=unit, status="ok", period_end=period,
                         citation=inputs[0].citation, method="computed", inputs=inputs,
                         normalizations=[formula], label=label, note=note)
    if check:
        record.check = check[0]
    if check and check[1] and basis_assumption:
        basis_assumption = ""  # the independent figure agrees, so the assumption is confirmed
    if check and not check[1]:
        record.confidence, record.confidence_reason = "low", f"Computed from verified inputs, but the check failed: {check[0]}"
        record.flags.append("check_failed")
    elif basis_assumption:
        record.confidence, record.confidence_reason = "low", f"Computed with an assumption: {basis_assumption}"
    elif check:
        record.confidence, record.confidence_reason = "high", f"Computed from verified inputs; independent check passed: {check[0]}"
    else:
        record.confidence, record.confidence_reason = "medium", "Computed from verified inputs; no independent figure to compare with."
    return record


def latest_filing_for(data: FundData, period: date) -> Filing | None:
    """The most recently filed report for a period (an amendment is filed after its original)."""
    same = [f for f in data.filings if f.period == period]
    return max(same, key=lambda f: (f.filing_date, f.amendment, f.accession)) if same else None


def searched_citation(data: FundData, period: date | None) -> Citation | None:
    """For a gap: a link to the report that was searched (the latest one for the period), with no quote,
    so every cell links to a filing (decision 21)."""
    filing = latest_filing_for(data, period) if period else None
    filing = filing or (max(data.filings, key=lambda f: (f.period, f.filing_date)) if data.filings else None)
    if filing is None:
        return None
    return citation(data.fund, filing, "Searched: whole report (nothing quoted)", "", filing.period)

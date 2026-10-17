"""Amendment tracking (decision 19): on every run, check each fund's EDGAR filing index for an amendment
(form ending "/A") to any filing whose values we show.

An amendment to filing F is a filing of form F.form + "/A" with the same period of report, filed after F.
If one exists and the value we show still comes from F, the value is flagged "Superseded by amendment:
re-check" in the table and the exceptions list. When the amendment itself was read and has the value,
the conflict rules already prefer it (an amendment supersedes the original), so nothing is flagged.
v1 flags only; the analyst re-runs after checking (Dana, W2: "Even if v1 just flags it ... that is better
than nothing").
"""
from datetime import date

from .config import AMENDMENT_FLAG, Fund
from .filings import Filing, list_filings
from .records import Citation, Issue, ValueRecord


def amendments_of(submissions: dict, form: str, period, filed) -> list[Filing]:
    """Every amendment in the index for this form and period of report, filed after `filed`."""
    base = form.removesuffix("/A")
    every = list_filings(submissions, (base,), since=filed)
    return [f for f in every if f.form == base + "/A" and f.period == period and f.filing_date >= filed]


def _citations(record: ValueRecord) -> list[Citation]:
    cits = [record.citation] if record.citation else []
    return cits + [c.citation for c in record.inputs]


def cited_accessions(records: list[ValueRecord]) -> set[str]:
    return {c.accession for r in records if r.status == "ok" for c in _citations(r)}


def flag(submissions: dict, fund: Fund, records: list[ValueRecord], issues: list[Issue]) -> None:
    for record in records:
        if record.status != "ok":
            continue
        for cit in _citations(record):
            if cit.cik == "client" or cit.period_end is None:
                continue
            newer = [a for a in amendments_of(submissions, cit.form, cit.period_end, cit.filing_date)
                     if a.accession != cit.accession]
            if not newer:
                continue
            names = ", ".join(f"{a.form} {a.accession} (filed {a.filing_date})" for a in newer)
            if AMENDMENT_FLAG not in record.flags:
                record.flags.append(AMENDMENT_FLAG)
            issues.append(Issue(kind="amendment", fund=fund.ticker, metric=record.metric, message=(
                f"{AMENDMENT_FLAG}. {record.metric} for {record.period_end} cites {cit.form} {cit.accession}, "
                f"which was amended by {names}. Re-check the value against the amendment.")))


def amended_filings(submissions: dict, forms: tuple[str, ...]) -> list[tuple[Filing, list[Filing]]]:
    """Every original in the index that has a later amendment, with its amendments (for the run log)."""
    every = list_filings(submissions, forms, since=date.min)
    originals = [f for f in every if not f.amendment]
    out = []
    for original in originals:
        amended = [f for f in every if f.amendment and f.form == original.form + "/A"
                   and f.period == original.period and f.filing_date >= original.filing_date]
        if amended:
            out.append((original, amended))
    return out

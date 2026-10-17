"""Pick one value per (fund, metric, period) from verified candidates, and say why.

Rules: equal values agree; otherwise the most recently filed document wins
(an amendment is always filed after the original it amends). Two different values in the
same filing have no rule, so they go to the PM. Nothing is resolved silently.
"""
from .confidence import score
from .config import CONFLICT_PM_CHOOSE
from .records import Candidate, ValueRecord


def _describe(c: Candidate) -> str:
    kind = "amendment " if c.is_amendment else ""
    return f"{c.value} in {kind}{c.citation.form} {c.citation.accession} (filed {c.citation.filing_date})"


def resolve(cands: list[Candidate], label: str | None = None) -> ValueRecord:
    first = cands[0]
    base = dict(fund=first.fund, metric=first.metric, unit=first.unit, period_end=first.period_end,
                label=label, candidates=cands)
    verified = [c for c in cands if c.verified]
    if not verified:
        return ValueRecord(value=None, status="not_verified", reason=first.verify_reason, **base)

    latest = max(verified, key=lambda c: (c.citation.filing_date, c.is_amendment))
    flags, resolution = [], ""
    distinct = {c.value for c in verified}
    if len(distinct) > 1:
        same_filing = {c.citation.accession for c in verified if c.value != latest.value} & {latest.citation.accession}
        others = "; ".join(_describe(c) for c in verified if c is not latest)
        if same_filing:
            # Client, W3, for every row: one filing contradicting itself is the PM's call.
            # Show both, select neither: no value, no confidence, a citation that quotes neither.
            listed = "; ".join(_describe(c) for c in verified)
            neutral = latest.citation.model_copy(update={
                "section": "Both sources below; neither selected", "quote": "", "row_label": None,
                "column_label": None, "column_header": None, "char_offset": None, "find_match": None,
                "find_total": None})
            return ValueRecord(value=None, status="conflict", reason=f"{CONFLICT_PM_CHOOSE}: {listed}.",
                               citation=neutral, flags=["conflict"],
                               resolution=f"One filing shows different values: {listed}. PM to choose.",
                               **{**base, "candidates": verified})
        else:
            flags.append("conflict")
            rule = "the amendment supersedes the original" if latest.is_amendment else "the more recent filing wins"
            resolution = f"Sources disagree. Chose {_describe(latest)} because {rule}. Other: {others}."
    elif len({c.citation.accession for c in verified}) > 1:
        resolution = f"{len(verified)} filings agree on {latest.value}."

    record = ValueRecord(value=latest.value, status="ok", citation=latest.citation, method=latest.method,
                         resolution=resolution, flags=flags, **base)
    record.confidence, record.confidence_reason = score(record, verified, latest)
    return record

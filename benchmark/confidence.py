"""Confidence per value (spec section 9). The reason always names the rule that fired."""
from .records import Candidate, ValueRecord


def score(record: ValueRecord, verified: list[Candidate], chosen: Candidate) -> tuple[str, str]:
    if "conflict" in record.flags or "pm_review" in record.flags:
        return "low", "Sources disagree; see resolution."
    if chosen.reconciliation_ok is False:
        return "low", f"Verified in the filing, but the reconciliation failed: {chosen.reconciliation}"
    if record.method in ("regex", "llm"):
        if chosen.reconciliation_ok:
            return "medium", f"Read from narrative text and confirmed by a structured source: {chosen.reconciliation}"
        return "low", "Read from narrative text only."
    if record.method == "computed":
        return "low", "Computed with a change of period basis."
    source = "inline XBRL tag" if chosen.method == "ixbrl" else "table cell"
    agreeing = sorted({c.citation.accession for c in verified if c.value == chosen.value})
    if len(agreeing) > 1:
        return "high", f"Verified {source}; the same value appears in {len(agreeing)} filings: {', '.join(agreeing)}."
    if chosen.reconciliation_ok:
        return "high", f"Verified {source}; independent check passed: {chosen.reconciliation}"
    return "medium", f"Verified {source} in {chosen.citation.accession}; no second source for this period."

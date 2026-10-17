from datetime import date
from decimal import Decimal

from benchmark.conflicts import resolve
from benchmark.records import Candidate, Citation


def cand(value, acc, filed, amendment=False, verified=True, recon=None, reason="verified"):
    cit = Citation(cik="1", form="N-CSRS/A" if amendment else "N-CSRS", accession=acc, filing_date=filed,
                   url="u", document="d.htm", section="Financial Highlights", quote=f"NAV {value}")
    return Candidate(fund="CCLFX", metric="nav_per_share", value=Decimal(value), unit="usd",
                     period_end=date(2025, 9, 30), method="table", citation=cit, is_amendment=amendment,
                     verified=verified, verify_reason=reason, reconciliation_ok=recon,
                     reconciliation="NAV bridge ok" if recon else None)


def test_two_filings_agree_gives_high_naming_both():
    rec = resolve([cand("10.77", "A-1", date(2025, 12, 5)), cand("10.77", "A-2", date(2026, 6, 8))])
    assert rec.value == Decimal("10.77") and rec.confidence == "high"
    assert "A-1" in rec.confidence_reason and "A-2" in rec.confidence_reason
    assert rec.citation.accession == "A-2"  # latest filing cited


def test_amendment_with_different_value_wins_and_is_low():
    rec = resolve([cand("10.77", "ORIG", date(2025, 12, 5)), cand("10.78", "AMEND", date(2026, 1, 9), amendment=True)])
    assert rec.value == Decimal("10.78") and rec.confidence == "low"
    assert "conflict" in rec.flags
    assert "10.77" in rec.resolution and "10.78" in rec.resolution and "amendment" in rec.resolution


def test_two_values_in_one_filing_show_both_and_choose_neither():
    """Client, W3, now for every row: a same-filing disagreement is the PM's call."""
    rec = resolve([cand("10.77", "SAME", date(2025, 12, 5)), cand("10.70", "SAME", date(2025, 12, 5))])
    assert rec.status == "conflict" and rec.value is None and rec.confidence is None
    assert rec.gap == "Conflict: PM to choose"
    assert sorted(str(c.value) for c in rec.candidates) == ["10.70", "10.77"]
    assert rec.citation.quote == ""  # links the filing, quotes neither value


def test_single_verified_with_reconciliation_is_high():
    rec = resolve([cand("10.77", "A-1", date(2025, 12, 5), recon=True)])
    assert rec.confidence == "high" and "NAV bridge" in rec.confidence_reason


def test_single_verified_alone_is_medium():
    assert resolve([cand("10.77", "A-1", date(2025, 12, 5))]).confidence == "medium"


def test_failed_reconciliation_is_low():
    rec = resolve([cand("10.77", "A-1", date(2025, 12, 5), recon=False)])
    assert rec.confidence == "low"


def test_nothing_verified_is_not_shown():
    rec = resolve([cand("10.77", "A-1", date(2025, 12, 5), verified=False, reason="quote not found verbatim")])
    assert rec.status == "not_verified" and rec.value is None and "verbatim" in rec.reason


def test_nav_conflict_cell_shows_both_dollar_values():
    from benchmark.export_excel import cell_text
    rec = resolve([cand("10.77", "SAME", date(2025, 12, 5)), cand("10.70", "SAME", date(2025, 12, 5))])
    text = cell_text(rec)
    assert text.startswith("Conflict: PM to choose") and "$10.77" in text and "$10.70" in text

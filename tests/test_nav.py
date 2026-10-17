from datetime import date
from decimal import Decimal
from pathlib import Path

from benchmark.config import load_funds
from benchmark.filings import Filing
from benchmark.metrics import nav

FX = Path(__file__).parent / "fixtures"
FUNDS = {f.ticker: f for f in load_funds()}
WINDOW = (date(2024, 3, 31), date(2025, 12, 31))


def filing(form, acc, period, doc):
    return Filing(form=form, accession=acc, filing_date=date(2026, 1, 1), period=period, primary_doc=doc,
                  amendment=form.endswith("/A"))


def run(ticker, fixture, form, acc, period):
    f = filing(form, acc, period, fixture)
    return nav.candidates(FUNDS[ticker], [f], fetch=lambda fl: FX / fl.primary_doc, window=WINDOW)


def test_cclfx_candidates_in_window_with_bridge_reconciliation():
    cands = run("CCLFX", "cclfx_ncsrs_2025-09.html", "N-CSRS", "0001213900-25-118573", date(2025, 9, 30))
    by_date = {c.period_end: c for c in cands}
    assert set(by_date) == {date(2025, 9, 30), date(2025, 3, 31), date(2024, 3, 31)}  # 2023 and earlier dropped
    c = by_date[date(2025, 9, 30)]
    assert c.value == Decimal("10.77") and c.method == "table" and c.column_index == 0
    assert c.reconciliation_ok is True and "10.83" in c.reconciliation
    assert c.citation.section.startswith("Financial Highlights")


def test_takix_class_i_candidates():
    cands = run("TAKIX", "takix_ncsr_2025.html", "N-CSR", "0001725472-26-000003", date(2025, 12, 31))
    by_date = {c.period_end: c.value for c in cands}
    assert by_date == {date(2025, 12, 31): Decimal("8.32"), date(2024, 12, 31): Decimal("8.55")}


def test_kref_book_value_reconciles_to_equity_over_shares():
    cands = run("KREF", "kref_10k_2025.html", "10-K", "0001628280-26-005092", date(2025, 12, 31))
    c = {c.period_end: c for c in cands}[date(2025, 12, 31)]
    assert c.value == Decimal("13.04")
    assert c.reconciliation_ok is True


def test_gbdc_tagged_nav():
    cands = run("GBDC", "gbdc_10q_2025-12.html", "10-Q", "0001476765-26-000012", date(2025, 12, 31))
    c = {c.period_end: c for c in cands}[date(2025, 12, 31)]
    assert c.value == Decimal("14.84") and c.method == "ixbrl"
    assert c.citation.fact_id and c.citation.concept == "us-gaap:NetAssetValuePerShare"

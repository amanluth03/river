"""Every new metric end to end on fixtures cut from the real filings (tests/cut_fixtures.py).

Expected values are the ones printed in the filings (accessions in tests/test_pipeline.py FILINGS);
docs/CODE_TOUR.md section 2 traces each one from the filing to the cell.
"""
from datetime import date
from decimal import Decimal

import pytest

from tests.test_pipeline import make_bundle


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    b, _ = make_bundle(tmp_path_factory.mktemp("run"))
    return b


def cell(bundle, metric, fund):
    return bundle.table[metric][fund]


@pytest.mark.parametrize("fund,value,confidence", [
    ("CCLFX", "0.31", "medium"),  # no fund-level figure to check against
    ("TAKIX", "0.40", "high"),  # checked against 352.0% asset coverage
    ("GBDC", "1.25", "high"),  # checked against 178.94% asset coverage
    ("KREF", "4.00", "high"),  # checked against KREF's own 3.9x total leverage ratio (net of cash)
])
def test_economic_leverage(bundle, fund, value, confidence):
    rec = cell(bundle, "leverage_economic", fund)
    assert rec.value == Decimal(value) and rec.confidence == confidence and rec.method == "computed"
    assert all(c.verified for c in rec.inputs)


def test_takix_economic_leverage_counts_mandatory_redeemable_preferred(bundle):
    labels = [c.citation.row_label for c in cell(bundle, "leverage_economic", "TAKIX").inputs]
    assert any(label.startswith("Mandatory redeemable preferred shares") for label in labels)


def test_regulatory_leverage(bundle):
    takix = cell(bundle, "leverage_regulatory", "TAKIX")
    assert takix.value == Decimal("352.0") and takix.method == "regex" and takix.confidence == "medium"
    assert "704.8%" in takix.note and "Implies D/E 0.40x" in takix.note
    gbdc = cell(bundle, "leverage_regulatory", "GBDC")
    assert gbdc.value == Decimal("178.94") and gbdc.method == "ixbrl" and "150%" in gbdc.note
    cclfx = cell(bundle, "leverage_regulatory", "CCLFX")
    assert cclfx.value == Decimal("421.1") and cclfx.method == "computed" and cclfx.confidence == "low"
    kref = cell(bundle, "leverage_regulatory", "KREF")
    assert kref.status == "not_applicable" and kref.gap == "Not applicable: KREF is not a 1940 Act fund"
    assert "3.9x" in kref.note and kref.citation is not None


def test_apex_regulatory_leverage_not_in_client_data(bundle):
    assert cell(bundle, "leverage_regulatory", "Apex Ridge").gap == "Not in client data"


@pytest.mark.parametrize("fund,value,n_inputs", [
    ("CCLFX", "10.58", 4),  # 0.54 + 0.90 - 0.30 = 1.14 over NAV 10.77; three pieces + NAV
    ("TAKIX", "9.01", 2),  # 0.75 for the year to 12/31/25 over NAV 8.32
    ("GBDC", "10.51", 4),  # 0.39 + 1.65 - 0.48 = 1.56 over NAV 14.84
    ("KREF", "7.67", 2),  # 1.00 over book value 13.04
])
def test_distribution_yield_trailing_twelve_months(bundle, fund, value, n_inputs):
    rec = cell(bundle, "distribution_yield", fund)
    assert rec.value == Decimal(value) and len(rec.inputs) == n_inputs and "under_12_months" not in rec.flags


def test_cclfx_yield_cites_both_semiannual_reports(bundle):
    accessions = {c.citation.accession for c in cell(bundle, "distribution_yield", "CCLFX").inputs}
    assert {"0001213900-25-118573", "0001213900-24-106851"} <= accessions


def test_interval_fund_returns(bundle):
    takix = {m: cell(bundle, m, "TAKIX") for m in ("net_return_1y", "net_return_3y", "net_return_5y")}
    assert takix["net_return_1y"].value == Decimal("6.27") and takix["net_return_1y"].confidence == "high"
    assert takix["net_return_3y"].gap == "Not reported by fund" and takix["net_return_3y"].citation is not None
    assert takix["net_return_5y"].value == Decimal("8.21")
    cclfx_1y = cell(bundle, "net_return_1y", "CCLFX")
    # The performance table says 11.78%; the same year's Financial Highlights say 11.58%. Shown, flagged Low.
    assert cclfx_1y.value == Decimal("11.78") and cclfx_1y.confidence == "low" and "11.58" in cclfx_1y.confidence_reason
    assert cclfx_1y.period_end == date(2025, 3, 31) and cclfx_1y.lag_quarters == 3
    assert cell(bundle, "net_return_3y", "CCLFX").value == Decimal("10.69")  # CCLFX does report a 3Y


def test_gbdc_return_is_labeled_a_different_measure(bundle):
    rec = cell(bundle, "net_return_1y", "GBDC")
    assert rec.value == Decimal("9.36") and rec.label == "Return on average net assets"
    assert "Not directly comparable" in rec.note and "not_comparable" in rec.flags
    for metric in ("net_return_3y", "net_return_5y"):
        assert cell(bundle, metric, "GBDC").gap == "Not reported by fund"


def test_kref_has_no_nav_return(bundle):
    assert all(cell(bundle, m, "KREF").status == "not_applicable" for m in ("net_return_1y", "net_return_3y"))


@pytest.mark.parametrize("fund,rate_text", [
    ("CCLFX", "1.00%"), ("TAKIX", "1.00%"), ("GBDC", "1.0%"), ("KREF", "0.375%")])
def test_fees_link_to_the_fee_sentence(bundle, fund, rate_text):
    rec = cell(bundle, "management_fee", fund)
    assert rec.gap == "Not extracted in v1" and rec.value is None
    assert rec.citation.url.startswith("https://www.sec.gov/") and rate_text in rec.citation.quote
    assert rec.citation.find_total >= 1


def test_apex_gap_note_is_framed_as_a_hypothesis(bundle):
    rec = cell(bundle, "net_return_1y", "Apex Ridge")
    assert rec.value == Decimal("10.31")  # the reported figure is official
    assert "fund accountant to confirm" in rec.normalizations[-1]
    assert any("fund accountant to confirm" in n for n in bundle.footnotes)

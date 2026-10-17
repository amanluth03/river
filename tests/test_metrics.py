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
    assert "704.8%" in " ".join(takix.normalizations) and "Implies D/E 0.40x" in takix.note
    gbdc = cell(bundle, "leverage_regulatory", "GBDC")
    assert gbdc.value == Decimal("178.94") and gbdc.method == "ixbrl" and "150%" in " ".join(gbdc.normalizations)
    cclfx = cell(bundle, "leverage_regulatory", "CCLFX")  # client, W3: not reported; computed figure in a note
    assert cclfx.value is None and cclfx.gap == "Not reported by fund"
    assert "421.1%" in cclfx.note and "computed, low confidence" in cclfx.note and cclfx.inputs
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
    assert cell(bundle, "net_return_3y", "CCLFX").period_end == date(2025, 3, 31)
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


def test_cclfx_1y_conflict_shows_both_and_chooses_neither(bundle):
    """Client, W3: the performance table (11.78%) and Financial Highlights (11.58%) disagree for the
    year to 3/31/25. Show both with their sources, flagged for the PM; nothing selected."""
    rec = cell(bundle, "net_return_1y", "CCLFX")
    assert rec.status == "conflict" and rec.value is None and rec.confidence is None
    assert rec.gap == "Conflict: PM to choose"
    values = sorted(str(c.value) for c in rec.candidates)
    assert values == ["11.58", "11.78"] and all(c.verified for c in rec.candidates)
    sections = {c.citation.section.split(":")[0] for c in rec.candidates}
    assert any(s.startswith("Performance") for s in sections) and any(s.startswith("Financial Highlights") for s in sections)
    assert rec.citation.quote == ""  # the cell links the filing but quotes neither value as "the" source
    assert any(i.kind == "conflict" and i.fund == "CCLFX" and "11.58" in i.message and "11.78" in i.message
               for i in bundle.issues)


def test_conflict_cell_text_lists_both_values(bundle):
    from benchmark.export_excel import cell_text
    text = cell_text(cell(bundle, "net_return_1y", "CCLFX"))
    assert text.startswith("Conflict: PM to choose") and "11.78%" in text and "11.58%" in text


def test_window3_rules_hold_at_another_as_of(tmp_path):
    """Client, W3: the conflict and the "Not reported by fund" rule apply at every as-of, not just Q4 2025."""
    from tests.test_pipeline import FakeEdgar
    from benchmark import pipeline
    from benchmark.cache import Cache
    class NoMissingDocs(FakeEdgar):  # at 3/31/25 the window reaches 2023, where the test index has a dummy row
        def submissions(self, cik):
            subs = super().submissions(cik)
            recent = subs["filings"]["recent"]
            keep = [i for i, doc in enumerate(recent["primaryDocument"]) if doc != "missing_on_purpose.html"]
            subs["filings"]["recent"] = {k: [v[i] for i in keep] for k, v in recent.items()}
            return subs
    cache = Cache(tmp_path / "cache")
    q1 = pipeline.run(date(2025, 3, 31), progress=lambda m: None, edgar=NoMissingDocs(cache), cache=cache,
                      runs_dir=tmp_path / "runs")
    one_year = q1.table["net_return_1y"]["CCLFX"]
    assert one_year.status == "conflict" and one_year.value is None
    assert sorted(str(c.value) for c in one_year.candidates) == ["11.58", "11.78"]
    coverage = q1.table["leverage_regulatory"]["CCLFX"]
    assert coverage.value is None and coverage.gap == "Not reported by fund" and "computed, low confidence" in coverage.note


def test_fee_cells_show_their_link_and_cclfx_incentive_note(bundle):
    from benchmark.export_excel import cell_text
    for fund in ("CCLFX", "TAKIX", "GBDC", "KREF"):
        assert cell_text(cell(bundle, "management_fee", fund)).startswith("Not extracted in v1 · view fee terms ↗")
    cclfx = cell(bundle, "incentive_fee", "CCLFX")
    assert cclfx.note == "Annual report states no incentive-fee terms; see prospectus fee table"
    assert cclfx.citation.form == "N-CSR" and cclfx.citation.accession == "0001213900-25-052571"
    assert "#:~:text=" in cclfx.citation.url  # lands on the annual report's fee sentence
    assert all(cell(bundle, "incentive_fee", f).note == "" for f in ("TAKIX", "GBDC", "KREF"))


def test_conflict_cell_shows_its_lag(bundle):
    """Aman, final pass: the CCLFX 1Y conflict cell says "as of 3/31/25 · 3Q lag" like the 3Y/5Y cells."""
    from benchmark.export_excel import cell_text
    rec = cell(bundle, "net_return_1y", "CCLFX")
    assert rec.status == "conflict" and rec.lag_quarters == 3
    assert "as of 2025-03-31 (3Q lag)" in cell_text(rec)


def test_kref_return_cells_say_why(bundle):
    from benchmark.export_excel import cell_text
    for metric in ("net_return_1y", "net_return_3y", "net_return_5y"):
        rec = cell(bundle, metric, "KREF")
        assert rec.gap == "Not applicable: no NAV-based return (REIT reports book value)"
        assert cell_text(rec).startswith("Not applicable: no NAV-based return (REIT reports book value)")
    assert cell(bundle, "leverage_regulatory", "KREF").gap == "Not applicable: KREF is not a 1940 Act fund"


def test_final_pass_labels_and_links(bundle):
    """Aman, final pass: incentive links land on incentive sentences; plain cross-check wording;
    CCLFX coverage note without 'Computed'; an Exceptions row for it; Apex trend gaps labeled."""
    takix, gbdc = cell(bundle, "incentive_fee", "TAKIX"), cell(bundle, "incentive_fee", "GBDC")
    assert "incentive fee" in takix.citation.quote and "incentive fee" in gbdc.citation.quote.lower()
    assert takix.citation.url != cell(bundle, "management_fee", "TAKIX").citation.url
    assert "agree within 0.05x" in cell(bundle, "leverage_economic", "TAKIX").check
    assert cell(bundle, "leverage_regulatory", "CCLFX").note == "421.1% (computed, low confidence)"
    assert any(i.kind == "check_failed" and i.fund == "CCLFX" and i.metric == "leverage_regulatory"
               and "421.1% (computed, low confidence)" in i.message for i in bundle.issues)
    apex_gaps = [p for p in bundle.trend["Apex Ridge"] if p.value is None]
    assert all(p.gap == "Not in client data (CSV starts Q1 2024)" for p in apex_gaps)
    assert cell(bundle, "distribution_yield", "GBDC").note == "TTM ÷ NAV"  # Q4 2025: no specials in the window

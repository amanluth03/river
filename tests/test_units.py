"""Small rules that the end-to-end tests depend on, each with the case that would go wrong without it."""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from benchmark import amendments
from benchmark.config import load_funds
from benchmark.extract import tables
from benchmark.metrics.distributions import months_before
from benchmark.metrics.leverage import implied_de
from benchmark.records import Candidate, Citation, ValueRecord

FX = Path(__file__).parent / "fixtures"
CCLFX = {f.ticker: f for f in load_funds()}["CCLFX"]


def test_months_before_lands_on_month_ends():
    assert months_before(date(2025, 9, 30), 6) == date(2025, 3, 31)
    assert months_before(date(2025, 12, 31), 3) == date(2025, 9, 30)
    assert months_before(date(2025, 9, 30), 12) == date(2024, 9, 30)
    assert months_before(date(2024, 5, 31), 3) == date(2024, 2, 29)  # leap year


def test_period_length_comes_from_the_column_title():
    assert tables.period_months("For the Six Months Ended September 30, 2025 (Unaudited)") == 6
    assert tables.period_months("For the Year Ended March 31, 2025") == 12
    assert tables.period_months("Three months ended December 31,") == 3
    # CCLFX's short fiscal period: no length stated, so never used in a trailing-12-month sum.
    assert tables.period_months("For the Period January 1, 2022 through March 31, 2022**") is None


def test_implied_debt_to_equity_from_asset_coverage():
    assert implied_de(Decimal("352.0")).quantize(Decimal("0.01")) == Decimal("0.40")  # TAKIX
    assert implied_de(Decimal("178.94")).quantize(Decimal("0.01")) == Decimal("1.27")  # GBDC
    assert implied_de(Decimal("200")) == 1  # 200% coverage = 1:1


def test_row_pattern_ending_in_dollar_sign_still_finds_the_row():
    # "^Net Assets$" once found nothing: the fast text prefilter kept the "$" (a bug found on CCLFX).
    hits = tables.find_row(FX / "cclfx_ncsrs_2025-09_full.html", r"^Net Assets$", None)
    assert any(h.values == [Decimal("31488743589")] for h in hits)


def test_header_of_two_periods_sharing_a_month_day_is_refused(tmp_path):
    # KREF-style "Three Months Ended | Year Ended December 31," over "2025 2025 2024": one month-day
    # shared by columns of different lengths. Refuse rather than date all three as fiscal years.
    doc = tmp_path / "d.html"
    doc.write_text("<html><body><table><tr><td></td><td>Three Months Ended</td><td>Year Ended December 31,</td></tr>"
                   "<tr><td></td><td>2025</td><td>2025</td><td>2024</td></tr>"
                   "<tr><td>Dividends declared per share</td><td>0.25</td><td>1.00</td><td>1.00</td></tr>"
                   "</table></body></html>")
    assert tables.find_row(doc, r"^Dividends declared per share", None) == []


def test_caption_dated_balance_sheet_has_one_column(tmp_path):
    doc = tmp_path / "d.html"
    doc.write_text("<html><body><p>Consolidated Statement of Assets and Liabilities September 30, 2025 (Unaudited)</p>"
                   "<table><tr><td>Assets:</td></tr><tr><td>Total assets</td><td>100</td></tr>"
                   "<tr><td>Net Assets</td><td>$</td><td>60</td></tr></table></body></html>")
    hit = tables.find_row(doc, r"^Net Assets$", None)[0]
    assert hit.column_dates == [date(2025, 9, 30)] and hit.column_headers == ["September 30, 2025"]


def _record_citing(accession, form, period, filed):
    cit = Citation(cik=CCLFX.cik, form=form, accession=accession, filing_date=filed, period_end=period,
                   url="https://www.sec.gov/x", document="x.htm", section="s", quote="10.77")
    cand = Candidate(fund="CCLFX", metric="nav_per_share", value=Decimal("10.77"), unit="usd", period_end=period,
                     method="table", citation=cit, verified=True)
    return ValueRecord(fund="CCLFX", metric="nav_per_share", value=Decimal("10.77"), unit="usd", status="ok",
                       period_end=period, citation=cit, candidates=[cand])


def test_amendment_to_a_cited_filing_is_flagged():
    # Real index: CCLFX N-CSRS 0001213900-23-094373 (period 2023-09-30) has two N-CSRS/A amendments.
    subs = json.loads((FX / "submissions_cclfx.json").read_text())
    rec = _record_citing("0001213900-23-094373", "N-CSRS", date(2023, 9, 30), date(2023, 12, 7))
    issues = []
    amendments.flag(subs, CCLFX, [rec], issues)
    assert "Superseded by amendment: re-check" in rec.flags
    assert "0001213900-24-027119" in issues[0].message and "0001213900-24-034098" in issues[0].message


def test_filing_without_amendment_is_not_flagged():
    subs = json.loads((FX / "submissions_cclfx.json").read_text())
    rec = _record_citing("0001213900-25-118573", "N-CSRS", date(2025, 9, 30), date(2025, 12, 5))
    issues = []
    amendments.flag(subs, CCLFX, [rec], issues)
    assert rec.flags == [] and issues == []


def test_amended_filings_found_in_the_index():
    subs = json.loads((FX / "submissions_cclfx.json").read_text())
    found = {o.accession: [a.accession for a in amended] for o, amended in amendments.amended_filings(subs, CCLFX.forms)}
    assert found["0001213900-23-094373"] == ["0001213900-24-027119", "0001213900-24-034098"]


def test_leverage_that_disagrees_with_reported_coverage_is_low(tmp_path):
    """If a debt line were missed, D/E from the balance sheet would disagree with reported coverage.
    The value is still shown (both inputs are verified) but Low, with the check text, never High."""
    from benchmark.cache import Cache
    from benchmark.filings import Filing
    from benchmark.metrics import leverage
    from benchmark.metrics.common import FundData

    takix = {f.ticker: f for f in load_funds()}["TAKIX"]
    html = ("<html><body><p>CONSOLIDATED STATEMENT OF ASSETS AND LIABILITIES As of December 31, 2025</p><table>"
            "<tr><td></td><td>December 31, 2025</td></tr>"
            "<tr><td>Secured credit facilities</td><td>$</td><td>920,159</td></tr>"
            "<tr><td>Mandatory redeemable preferred shares</td><td>946,446</td></tr>"
            "<tr><td>Note-on-note loans</td><td>27,686</td></tr>"
            "<tr><td>Net Assets</td><td>$</td><td>4,782,841</td></tr></table>"
            "<p>As of December 31, 2025, asset coverage (exclusive of preferred equity shares) was 704.8% and asset "
            "coverage (inclusive of preferred equity shares) was 200.0%.</p></body></html>")
    cache = Cache(tmp_path)
    cache.store(takix.cik, "X-1", "d.htm", html.encode())
    filing = Filing(form="N-CSR", accession="X-1", filing_date=date(2026, 2, 27), period=date(2025, 12, 31),
                    primary_doc="d.htm", amendment=False)
    nav_cell = _record_citing("X-1", "N-CSR", date(2025, 12, 31), date(2026, 2, 27))
    data = FundData(fund=takix, filings=[filing], fetch=lambda f: cache.path(takix.cik, "X-1", "d.htm"),
                    cache=cache, as_of=date(2025, 12, 31), nav={}, nav_cell=nav_cell)
    out = leverage.records(data)
    econ = out["leverage_economic"]
    assert econ.value == Decimal("0.40") and econ.confidence == "low" and "check_failed" in econ.flags
    assert "DISAGREE" in econ.check
    assert out["leverage_regulatory"].confidence == "low"  # the narrative figure is not confirmed either


def test_amendment_flag_reaches_conflict_cells_and_notes():
    """Reviewer finding: a conflict cell (no value) and a 'Not reported' cell whose note is computed from
    filings must still be flagged when one of those filings is amended."""
    subs = json.loads((FX / "submissions_cclfx.json").read_text())
    rec = _record_citing("0001213900-23-094373", "N-CSRS", date(2023, 9, 30), date(2023, 12, 7))
    conflict = ValueRecord(fund="CCLFX", metric="net_return_1y", value=None, unit="pct", status="conflict",
                           reason="Conflict: PM to choose", period_end=date(2023, 9, 30),
                           citation=rec.citation.model_copy(update={"quote": ""}), candidates=rec.candidates)
    note_only = ValueRecord(fund="CCLFX", metric="leverage_regulatory", value=None, unit="pct",
                            status="not_reported", reason="Not reported by fund", inputs=rec.candidates)
    issues = []
    amendments.flag(subs, CCLFX, [conflict, note_only], issues)
    assert "Superseded by amendment: re-check" in conflict.flags
    assert "Superseded by amendment: re-check" in note_only.flags

from datetime import date
from pathlib import Path

from benchmark import pipeline, verify
from benchmark.cache import Cache
from benchmark.edgar import EdgarError

FX = Path(__file__).parent / "fixtures"
# cik -> (form, accession, period, filed, fixture document). Fixtures are cut from the real filings
# by tests/cut_fixtures.py; accessions and dates are the real ones.
FILINGS = {
    "0001735964": [("N-CSRS", "0001213900-25-118573", "2025-09-30", "2025-12-05", "cclfx_ncsrs_2025-09_full.html"),
                   ("N-CSR", "0001213900-25-052571", "2025-03-31", "2025-06-09", "cclfx_ncsr_2025-03.html"),
                   ("N-CSRS", "0001213900-24-106851", "2024-09-30", "2024-12-09", "cclfx_ncsrs_2024-09.html"),
                   ("N-CSRS/A", "0001213900-24-027119", "2023-09-30", "2024-03-01", "missing_on_purpose.html")],
    "0001725472": [("N-CSR", "0001725472-26-000003", "2025-12-31", "2026-02-27", "takix_ncsr_2025_full.html"),
                   ("N-CSRS", "0001725472-25-000010", "2025-06-30", "2025-08-21", "empty_report.html")],
    "0001476765": [("10-Q", "0001476765-26-000012", "2025-12-31", "2026-02-04", "gbdc_10q_2025-12_full.html"),
                   ("10-K", "0001476765-25-000096", "2025-09-30", "2025-11-18", "gbdc_10k_2025.html")],
    "0001631596": [("10-K", "0001628280-26-005092", "2025-12-31", "2026-02-03", "kref_10k_2025.html")],
}


class FakeEdgar:
    def __init__(self, cache):
        self.cache = cache

    def submissions(self, cik):
        if cik not in FILINGS:
            raise EdgarError("EDGAR refused the request (403). This usually means a missing or invalid User-Agent")
        rows = FILINGS[cik]
        return {"fiscalYearEnd": "1231", "filings": {"recent": {
            "form": [r[0] for r in rows], "accessionNumber": [r[1] for r in rows],
            "filingDate": [r[3] for r in rows], "reportDate": [r[2] for r in rows],
            "primaryDocument": [r[4] for r in rows]}}}

    def fetch(self, cik, accession, filename):
        if not self.cache.has(cik, accession, filename):
            self.cache.store(cik, accession, filename, (FX / filename).read_bytes())
        return self.cache.path(cik, accession, filename)


class GbdcRefused(FakeEdgar):
    def submissions(self, cik):
        if cik == "0001476765":
            raise EdgarError("EDGAR refused the request (403). This usually means a missing or invalid User-Agent")
        return super().submissions(cik)



def make_bundle(tmp_path, edgar_class=FakeEdgar):
    cache = Cache(tmp_path / "cache")
    bundle = pipeline.run(date(2025, 12, 31), progress=lambda m: None, edgar=edgar_class(cache), cache=cache,
                          runs_dir=tmp_path / "runs")
    return bundle, cache


def test_pipeline_continues_when_one_fund_fails(tmp_path):
    bundle, _ = make_bundle(tmp_path, GbdcRefused)
    nav = bundle.table["nav_per_share"]
    assert nav["GBDC"].status == "fetch_failed" and "User-Agent" in nav["GBDC"].reason
    assert all(bundle.table[m]["GBDC"].status == "fetch_failed" for m, _ in bundle.rows)
    assert nav["KREF"].status == "ok" and str(nav["KREF"].value) == "13.04"
    assert nav["TAKIX"].status == "ok" and str(nav["TAKIX"].value) == "8.32"
    assert any(i.kind == "fetch" and i.fund == "GBDC" for i in bundle.issues)


def test_lag_shown_for_cclfx(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    cell = bundle.table["nav_per_share"]["CCLFX"]
    assert cell.period_end == date(2025, 9, 30) and cell.lag_quarters == 1 and "lagged" in cell.flags


def test_trend_has_gaps_not_estimates(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    points = {p.period_end: p for p in bundle.trend["TAKIX"]}
    assert points[date(2025, 12, 31)].status == "ok"
    assert points[date(2025, 9, 30)].status == "not_reported" and points[date(2025, 9, 30)].value is None


def test_kref_labeled_book_value_and_flagged_as_peer_question(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    assert bundle.table["nav_per_share"]["KREF"].label == "Book value per share"  # exact label, never "NAV per share"
    assert all(p.label == "Book value per share" for p in bundle.trend["KREF"] if p.status == "ok")
    assert any(i.kind == "peer_question" and i.fund == "KREF" for i in bundle.issues)


def test_no_cell_is_blank(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    for metric, _ in bundle.rows:
        for fund in bundle.funds:
            rec = bundle.table[metric][fund]
            assert rec.value is not None or rec.gap, (metric, fund)


def test_every_shown_competitor_value_passes_the_gate_again(tmp_path):
    bundle, cache = make_bundle(tmp_path)
    shown = [r for row in bundle.table.values() for r in row.values() if r.status == "ok" and r.method != "client_csv"]
    shown += [p for pts in bundle.trend.values() for p in pts if p.status == "ok" and p.method != "client_csv"]
    assert shown
    for rec in shown:
        if rec.method == "computed":  # every input of a computed value must pass the gate again
            assert rec.inputs and all(verify.check(c.model_copy(deep=True), cache)[0] for c in rec.inputs)
            continue
        chosen = next(c for c in rec.candidates if c.citation.accession == rec.citation.accession and c.value == rec.value)
        assert verify.check(chosen.model_copy(deep=True), cache)[0]


def test_bundle_written_to_disk(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    assert pipeline.latest_bundle(tmp_path / "runs").as_of == bundle.as_of


def test_filing_read_but_no_value_is_not_found_not_not_reported(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    point = {p.period_end: p for p in bundle.trend["TAKIX"]}[date(2025, 6, 30)]
    assert point.status == "not_found" and "0001725472-25-000010" in point.reason
    assert any(i.fund == "TAKIX" and "0001725472-25-000010" in i.message for i in bundle.issues)


def test_filings_before_the_window_are_not_downloaded(tmp_path):
    bundle, _ = make_bundle(tmp_path)  # the 2023 amendment's document doesn't exist; fetching it would fail
    assert all(f["accession"] != "0001213900-24-027119" for f in bundle.filings)


def test_unexpected_error_in_one_fund_does_not_stop_the_run(tmp_path):
    class Broken(FakeEdgar):
        def submissions(self, cik):
            if cik == "0001631596":
                raise ValueError("Expecting value: line 1 column 1 (char 0)")
            return super().submissions(cik)
    cache = Cache(tmp_path / "cache")
    bundle = pipeline.run(date(2025, 12, 31), progress=lambda m: None, edgar=Broken(cache), cache=cache,
                          runs_dir=tmp_path / "runs")
    assert bundle.table["nav_per_share"]["KREF"].status == "fetch_failed"
    assert bundle.table["nav_per_share"]["TAKIX"].status == "ok"

from openpyxl import load_workbook

from benchmark import export_excel
from tests.test_pipeline import make_bundle


def test_workbook_layout(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    out = tmp_path / "benchmark.xlsx"
    export_excel.write(bundle, out)
    wb = load_workbook(out)
    assert wb.sheetnames == ["Benchmark", "Provenance", "Exceptions", "NAV Trend"]
    bench = wb["Benchmark"]
    assert [c.value for c in bench[1]][:6] == ["Metric", "Apex Ridge", "CCLFX", "TAKIX", "GBDC", "KREF"]
    nav_row = next(r for r in bench.iter_rows(values_only=True) if r[0] == "NAV per share")
    assert nav_row[3].startswith("$8.32")  # TAKIX
    assert nav_row[4].startswith("—")  # GBDC failed in this fake run


def test_provenance_has_one_row_per_record(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    out = tmp_path / "benchmark.xlsx"
    export_excel.write(bundle, out)
    prov = load_workbook(out)["Provenance"]
    n_records = sum(len(row) for row in bundle.table.values())
    assert prov.max_row - 1 == n_records
    header = [c.value for c in prov[1]]
    assert {"Accession", "Source quote", "Confidence", "Status"} <= set(header)

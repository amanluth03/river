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
    labels = [r[0].value for r in bench.iter_rows(min_row=2, max_row=10)]
    assert labels == [label for _, label in bundle.rows]  # deck rows, deck order (decision 17)
    nav_row = next(r for r in bench.iter_rows(values_only=True) if r[0] == "NAV per share")
    assert nav_row[3].startswith("$8.32")  # TAKIX
    assert nav_row[5].startswith("Book value per share: $13.04")  # KREF, exact label (decision 14)
    three_year = next(r for r in bench.iter_rows(values_only=True) if r[0].startswith("Net return, trailing 3Y"))
    assert three_year[3] == "Not reported by fund"  # TAKIX: labeled, never blank (decision 15)


def test_cells_link_to_filings_and_sheets_are_protected(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    out = tmp_path / "benchmark.xlsx"
    export_excel.write(bundle, out)
    wb = load_workbook(out)
    assert all(ws.protection.sheet for ws in wb.worksheets)
    bench = wb["Benchmark"]
    competitor_cells = [c for row in bench.iter_rows(min_row=2, max_row=10, min_col=3, max_col=6) for c in row]
    # Every competitor cell, gaps included, links to the filing it came from or was looked for in (decision 21).
    assert all(c.hyperlink and c.hyperlink.target.startswith("https://www.sec.gov/") for c in competitor_cells)


def test_provenance_has_one_row_per_record(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    out = tmp_path / "benchmark.xlsx"
    export_excel.write(bundle, out)
    prov = load_workbook(out)["Provenance"]
    n_records = sum(len(row) for row in bundle.table.values())
    assert prov.max_row - 1 == n_records
    header = [c.value for c in prov[1]]
    assert {"Accession", "Source quote", "Confidence", "Status"} <= set(header)


def test_amendment_flag_is_in_the_cell_and_styled(tmp_path):
    """Client, W3: "Superseded by amendment: re-check" appears in the cell itself, styled, in Excel and Word."""
    from docx import Document
    from benchmark import export_word
    from benchmark.config import AMENDMENT_FLAG

    bundle, _ = make_bundle(tmp_path)
    rec = bundle.table["nav_per_share"]["TAKIX"]
    rec.flags.append(AMENDMENT_FLAG)  # as amendments.flag would set it
    assert export_excel.cell_text(rec).startswith(AMENDMENT_FLAG)
    export_excel.write(bundle, tmp_path / "b.xlsx")
    nav_row = next(r for r in load_workbook(tmp_path / "b.xlsx")["Benchmark"].iter_rows() if r[0].value == "NAV per share")
    takix = nav_row[3]
    assert takix.value.startswith(AMENDMENT_FLAG) and takix.font.bold and takix.fill.fgColor.rgb.endswith("F8D7D3")
    export_word.write(bundle, tmp_path / "b.docx")
    word_cell = next(r for r in Document(tmp_path / "b.docx").tables[0].rows if r.cells[0].text == "NAV per share").cells[3]
    assert word_cell.text.startswith(AMENDMENT_FLAG) and "F8D7D3" in word_cell._tc.xml


RAW_KINDS = ["check_failed", "not_comparable", "not_like_for_like", "client_data", "peer_question", "data_quality"]


def test_exceptions_and_provenance_use_plain_labels(tmp_path):
    """Aman: exception types and metric names read as words, not code names, in the export."""
    from benchmark import labels

    bundle, _ = make_bundle(tmp_path)
    out = tmp_path / "benchmark.xlsx"
    export_excel.write(bundle, out)
    wb = load_workbook(out)
    exc_rows = list(wb["Exceptions"].iter_rows(min_row=2, values_only=True))
    assert len(exc_rows) == len(bundle.issues)
    types = {r[0] for r in exc_rows}
    assert not types & set(RAW_KINDS) and "Not directly comparable" in types and "Client data check" in types
    metrics = {r[2] for r in exc_rows}
    assert "Net return, trailing 1Y (ann.)" in metrics and "net_return_1y" not in metrics
    prov_metrics = {r[1] for r in wb["Provenance"].iter_rows(min_row=2, values_only=True)}
    assert "NAV per share" in prov_metrics and "Book value per share" in prov_metrics
    assert not {m for m, _ in bundle.rows} & prov_metrics
    assert labels.metric_label("incentive_hurdle_pct", bundle.rows) == "Incentive hurdle (client data)"
    assert set(labels.ISSUE_KINDS) == set(labels.ISSUE_KIND_LABELS)  # every Issue.kind has a label

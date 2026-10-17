"""Word export: the same run data as the Excel, so the two can never show different numbers."""
from docx import Document

from benchmark import export_excel, export_word
from tests.test_pipeline import make_bundle


def _doc(tmp_path):
    bundle, _ = make_bundle(tmp_path)
    out = tmp_path / "benchmark.docx"
    export_word.write(bundle, out)
    return bundle, Document(out)


def _table_after(doc, heading):
    """The first table after the heading paragraph with this text."""
    body = list(doc.element.body.iterchildren())
    head = next(par._p for par in doc.paragraphs if par.text == heading and par.style.name.startswith("Heading"))
    start = body.index(head)
    tbl = next(el for el in body[start:] if el.tag.endswith("}tbl"))
    return next(t for t in doc.tables if t._tbl is tbl)


def test_deck_table_matches_the_excel_cells(tmp_path):
    bundle, doc = _doc(tmp_path)
    table = doc.tables[0]
    assert [c.text for c in table.rows[0].cells] == ["Metric"] + bundle.funds
    for r, (metric, label) in enumerate(bundle.rows, start=1):
        cells = [c.text for c in table.rows[r].cells]
        assert cells[0] == label  # deck rows, deck order
        # Every cell starts with exactly the Excel cell text, built by the same function from the same run
        # (a conflict cell then adds one link per disagreeing source).
        for got, fund in zip(cells[1:], bundle.funds):
            assert got.startswith(export_excel.cell_text(bundle.table[metric][fund]))


def test_labels_gaps_and_identity(tmp_path):
    bundle, doc = _doc(tmp_path)
    text = "\n".join(p.text for p in doc.paragraphs)
    cells = [c.text for row in doc.tables[0].rows for c in row.cells]
    assert any(c.startswith("Book value per share: $13.04") for c in cells)
    assert "Not reported by fund" in cells and "Not in client data" in cells
    assert bundle.code_version in text and str(bundle.as_of) in text
    assert f"run ID {bundle.run_id}" in text  # client W3: stamped with the run ID (= runs/<run ID>/bundle.json)
    assert "Generated report" in text  # not a hand-edited source of record
    assert "fund accountant to confirm" in text  # Apex 1Y gap footnote


def test_every_competitor_cell_links_to_its_filing(tmp_path):
    bundle, doc = _doc(tmp_path)
    targets = {rel.target_ref for rel in doc.part.rels.values() if rel.reltype.endswith("/hyperlink")}
    for metric, _ in bundle.rows:
        for fund in bundle.funds[1:]:
            cit = bundle.table[metric][fund].citation
            assert cit and cit.url in targets, (metric, fund)


def test_exceptions_and_provenance_sections(tmp_path):
    bundle, doc = _doc(tmp_path)
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert {"Benchmark", "Exceptions for review", "Provenance"} <= set(headings)
    exceptions = _table_after(doc, "Exceptions for review")
    assert len(exceptions.rows) - 1 == len(bundle.issues)
    provenance = _table_after(doc, "Provenance")
    shown = [bundle.table[m][f] for m, _ in bundle.rows for f in bundle.funds[1:]]
    assert len(provenance.rows) - 1 == len(shown)
    assert any("0001725472-26-000003" in c.text for row in provenance.rows for c in row.cells)


def test_word_keeps_every_flag_no_clean_version(tmp_path):
    """Client, W3: conflicts, lags, computed notation and citations all carried into Word."""
    bundle, doc = _doc(tmp_path)
    cells = [c.text for row in doc.tables[0].rows for c in row.cells]
    assert any(c.startswith("Conflict: PM to choose") and "11.78%" in c and "11.58%" in c for c in cells)
    assert any("(computed)" in c for c in cells)
    assert any("Q lag)" in c for c in cells)


def test_word_provenance_uses_the_kref_label(tmp_path):
    """Reviewer finding: KREF's figure is never called "NAV per share", anywhere (decision 14)."""
    bundle, doc = _doc(tmp_path)
    first_cells = [row.cells[0].text for row in _table_after(doc, "Provenance").rows]
    assert "KREF · Book value per share" in first_cells and "KREF · NAV per share" not in first_cells


def test_nav_trend_section_lists_every_point_with_gaps(tmp_path):
    bundle, doc = _doc(tmp_path)
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert "NAV trend" in headings
    table = _table_after(doc, "NAV trend")
    assert [c.text for c in table.rows[0].cells] == ["Fund", "Quarter end", "Value", "Status / reason", "Form",
                                                     "Accession", "Source quote (or section)", "Confidence"]
    n_points = sum(len(points) for points in bundle.trend.values())
    assert n_points == 5 * 8 and len(table.rows) - 1 == n_points
    rows = [[c.text for c in r.cells] for r in table.rows[1:]]
    takix_gap = next(r for r in rows if r[0].startswith("TAKIX") and r[1] == "2025-09-30")
    assert takix_gap[3].startswith("Not reported by fund: ") and "semi-annually" in takix_gap[3]
    assert any(r[3].startswith("Not found in the filings read: ") for r in rows)
    assert not any("NAV" in r[0] for r in rows if r[0].startswith("KREF"))
    assert any(r[0] == "KREF (Book value per share)" for r in rows)
    targets = {rel.target_ref for rel in doc.part.rels.values() if rel.reltype.endswith("/hyperlink")}
    for points in bundle.trend.values():
        for p in points:
            if p.citation and p.citation.url.startswith("http"):
                assert p.citation.url in targets


def test_footer_carries_run_id_code_version_and_as_of(tmp_path):
    bundle, doc = _doc(tmp_path)
    footer = doc.sections[0].footer.paragraphs[0].text
    assert footer == f"Run ID {bundle.run_id} · code version {bundle.code_version} · as of {bundle.as_of}"


def test_word_exceptions_and_provenance_use_plain_labels(tmp_path):
    bundle, doc = _doc(tmp_path)
    exc = [[c.text for c in r.cells] for r in _table_after(doc, "Exceptions for review").rows[1:]]
    types = {r[0] for r in exc}
    assert not types & {"check_failed", "not_comparable", "client_data", "peer_question", "data_quality"}
    assert "Not directly comparable" in types
    assert "Net return, trailing 1Y (ann.)" in {r[2] for r in exc}


def test_word_provenance_prints_the_find_hint(tmp_path):
    bundle, doc = _doc(tmp_path)
    cit = bundle.table["nav_per_share"]["TAKIX"].citation
    assert cit.find_match  # fixture: a table citation with a find hint
    hint = f"search “{cit.row_label}”: match {cit.find_match} of {cit.find_total}"
    row = next(r for r in _table_after(doc, "Provenance").rows if r.cells[0].text == "TAKIX · NAV per share")
    assert hint in row.cells[3].text

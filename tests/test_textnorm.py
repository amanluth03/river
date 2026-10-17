from lxml import html

from benchmark import textnorm


def test_normalize_maps_nbsp_dashes_and_collapses_space():
    assert textnorm.normalize("Net\xa0asset  – value​") == "Net asset - value"


def test_element_text_puts_a_space_between_table_cells():
    row = html.fromstring("<table><tr><td>$</td><td>8.32</td><td>(0.54</td><td>)</td></tr></table>")
    assert textnorm.element_text(row) == "$ 8.32 (0.54 )"


def test_document_text_contains_row_text_verbatim(tmp_path):
    doc = tmp_path / "d.htm"
    doc.write_text("<html><body><p>Intro</p><table><tr><td>Net asset value, end of period</td>"
                   "<td>$</td><td>8.32</td></tr></table></body></html>")
    text = textnorm.document_text(doc)
    assert "Net asset value, end of period $ 8.32" in text


def test_utf8_document_without_charset_is_not_misread_as_latin1(tmp_path):
    doc = tmp_path / "d.htm"
    doc.write_bytes("<html><body><table><tr><td>Net asset value, end of period</td><td>8.32</td></tr>"
                    "</table></body></html>".encode("utf-8"))
    text = textnorm.document_text(doc)
    assert "Â" not in text
    assert "Net asset value, end of period 8.32" in text

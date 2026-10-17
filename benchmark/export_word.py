"""Word export: the deck table, footnotes, exceptions, the NAV trend and a provenance appendix.

Built from the same run bundle as the Excel export, and every table cell uses export_excel.cell_text,
so the Word and Excel files can never show different numbers. Word can't be locked like the Excel
sheets, so the document says it is generated and prints the run time and code version: any edit can be
checked against the run it came from. The run ID, code version and as-of date are in every page footer.
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from .export_excel import TREND_COLUMNS, alert, cell_text, find_hint, issue_row, trend_row
from .records import RunBundle, ValueRecord

LINK_COLOR = "1F4E79"


def _hyperlink(paragraph, url: str, text: str):
    """Add `text` as a clickable link to `url` (python-docx has no high-level call for this)."""
    rel_id = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color, underline = OxmlElement("w:color"), OxmlElement("w:u")
    color.set(qn("w:val"), LINK_COLOR)
    underline.set(qn("w:val"), "single")
    props.append(color)
    props.append(underline)
    run.append(props)
    text_el = OxmlElement("w:t")
    text_el.text = text
    text_el.set(qn("xml:space"), "preserve")
    run.append(text_el)
    link.append(run)
    paragraph._p.append(link)


ALERT_SHADE = {"amendment": "F8D7D3", "conflict": "FCEFD2"}  # same colors as the Excel export


def _shade(cell, hex_color: str):
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shading)


def _fill(cell, rec: ValueRecord):
    """A table cell: the same text as the Excel cell, linked to its filing when it has one. An amendment
    flag or a conflict is shaded and printed in bold red in the cell itself (client, W3)."""
    text = cell_text(rec)
    paragraph = cell.paragraphs[0]
    kind = alert(rec)
    if kind:
        _shade(cell, ALERT_SHADE[kind])
        first, _, text = text.partition("\n") if kind == "amendment" else ("", "", text)
        if first:
            flag = paragraph.add_run(first + "\n")
            flag.bold, flag.font.color.rgb = True, RGBColor(0x9B, 0x2C, 0x1F)
    if rec.citation and rec.citation.url.startswith("http"):
        _hyperlink(paragraph, rec.citation.url, text)
    else:
        paragraph.add_run(text)
    if rec.citation and rec.status == "conflict":
        for c in rec.candidates:  # each disagreeing source keeps its own link
            _hyperlink(cell.add_paragraph(), c.citation.url,
                       f"{c.value}%: {c.citation.section.split(':')[0]} ({c.citation.form} {c.citation.accession})")


def _small(table, size=8):
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(size)


def _header_row(table, names):
    for cell, name in zip(table.rows[0].cells, names):
        cell.text = name
        cell.paragraphs[0].runs[0].bold = True


def _benchmark(doc, bundle: RunBundle):
    doc.add_heading("Benchmark", level=1)
    table = doc.add_table(rows=1, cols=1 + len(bundle.funds))
    table.style = "Table Grid"
    _header_row(table, ["Metric"] + bundle.funds)
    for metric, label in bundle.rows:
        cells = table.add_row().cells
        cells[0].text = label
        for cell, fund in zip(cells[1:], bundle.funds):
            _fill(cell, bundle.table[metric][fund])
    _small(table)
    doc.add_paragraph("Click a value to open its filing. [H]/[M]/[L] = confidence.").runs[0].font.size = Pt(8)
    for i, note in enumerate(bundle.footnotes, start=1):
        doc.add_paragraph(f"{i}. {note}").runs[0].font.size = Pt(8)


def _exceptions(doc, bundle: RunBundle):
    doc.add_heading("Exceptions for review", level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    _header_row(table, ["Type", "Fund", "Metric", "Message"])
    for issue in bundle.issues:
        cells = table.add_row().cells
        for cell, value in zip(cells, issue_row(issue, bundle)):  # plain labels, same as the Excel sheet
            cell.text = value
    _small(table)


def _input_text(x) -> str:
    """One input of a computed value: value, row label, filing, and its find hint when it has one."""
    c = x.citation
    hint = find_hint(c)
    return f"{x.value} = {c.row_label} ({c.form} {c.accession}{'; ' + hint if hint else ''})"


def _trend(doc, bundle: RunBundle):
    """Every NAV point for every fund, the same rows as the Excel "NAV Trend" sheet. Gaps are rows with
    their reason (decision 4); each sourced point's accession links to its filing (decision 21)."""
    doc.add_heading("NAV trend", level=1)
    doc.add_paragraph("Interval funds report NAV semi-annually: other quarters are gaps with the reason, never "
                      "estimates. KREF reports book value per share.").runs[0].font.size = Pt(8)
    table = doc.add_table(rows=1, cols=len(TREND_COLUMNS))
    table.style = "Table Grid"
    _header_row(table, TREND_COLUMNS)
    accession_col = TREND_COLUMNS.index("Accession")
    for fund, points in bundle.trend.items():
        for p in points:
            cells = table.add_row().cells
            for i, (cell, value) in enumerate(zip(cells, trend_row(fund, p))):
                text = "" if value is None else str(value)
                if i == accession_col and text and p.citation and p.citation.url.startswith("http"):
                    _hyperlink(cell.paragraphs[0], p.citation.url, text)
                else:
                    cell.text = text
    _small(table, 7)


def _footer(doc, bundle: RunBundle):
    """Run ID, code version and as-of date on every page, so a printed page traces back to its run."""
    for section in doc.sections:
        paragraph = section.footer.paragraphs[0]
        paragraph.text = f"Run ID {bundle.run_id} · code version {bundle.code_version} · as of {bundle.as_of}"
        paragraph.runs[0].font.size = Pt(8)


def _provenance(doc, bundle: RunBundle):
    doc.add_heading("Provenance", level=1)
    doc.add_paragraph("One row per competitor cell: the filing, where in it, and the source text. Computed values "
                      "list each input with its own filing.").runs[0].font.size = Pt(8)
    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    _header_row(table, ["Fund / metric", "Value", "Filing", "Section", "Source text or inputs"])
    for metric, label in bundle.rows:
        for fund in bundle.funds[1:]:
            rec = bundle.table[metric][fund]
            cit = rec.citation
            cells = table.add_row().cells
            cells[0].text = f"{fund} · {rec.label or label}"  # KREF: "Book value per share", never NAV
            cells[1].text = rec.display() if rec.value is not None else rec.gap
            if cit:
                _hyperlink(cells[2].paragraphs[0], cit.url, f"{cit.form} {cit.accession}")
                hint = find_hint(cit)  # same hint as the Excel "Find hint" column
                cells[3].text = f"{cit.section}\n{hint}" if hint else cit.section
            if rec.inputs:
                cells[4].text = " | ".join(_input_text(x) for x in rec.inputs)
            elif cit:
                cells[4].text = cit.quote or rec.reason
            else:
                cells[4].text = rec.reason
    _small(table, 7)


def write(bundle: RunBundle, path: Path) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    doc.add_heading("Peer benchmark", level=0)
    meta = doc.add_paragraph(
        f"As of {bundle.as_of}. Generated report: run ID {bundle.run_id} ({bundle.created_at:%Y-%m-%d %H:%M}), "
        f"code version {bundle.code_version}. Do not edit figures here; re-run the tool and export again.")
    meta.runs[0].font.size = Pt(9)
    meta.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    _benchmark(doc, bundle)
    _exceptions(doc, bundle)
    _trend(doc, bundle)
    _provenance(doc, bundle)
    _footer(doc, bundle)
    doc.save(path)
    return Path(path)

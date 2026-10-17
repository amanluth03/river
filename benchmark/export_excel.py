"""Excel export: the deck table plus provenance (one row per value), exceptions and the NAV trend.

Layout matches the board deck (same rows, same order; decision 17). Every cell that has a source links
to its filing (decision 21). All sheets are protected against accidental edits, as the locked template
was (decision 17); protection has no password, so a PM who needs to can still unprotect a sheet.
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .config import AMENDMENT_FLAG, FEE_LINK_TEXT
from .labels import issue_kind_label, metric_label, status_label
from .records import RunBundle, ValueRecord

BOLD = Font(bold=True)
LINK = Font(color="1F4E79", underline="single")
HEADER_FILL = PatternFill("solid", fgColor="E8ECF1")
LETTER = {"high": "H", "medium": "M", "low": "L"}
# Cells that need a reviewer's eye are styled in the cell itself (client, W3: decision 58).
ALERT_FILL = {"amendment": PatternFill("solid", fgColor="F8D7D3"), "conflict": PatternFill("solid", fgColor="FCEFD2")}
ALERT_FONT = Font(color="9B2C1F", bold=True)


def alert(rec: ValueRecord) -> str | None:
    """'amendment' if the value's filing was amended since, 'conflict' if two sources disagree, else None."""
    if AMENDMENT_FLAG in rec.flags:
        return "amendment"
    if rec.status == "conflict" or "conflict" in rec.flags or "pm_review" in rec.flags:
        return "conflict"
    return None


def cell_text(rec: ValueRecord) -> str:
    """Everything the table shows for one value, as text. The UI, Excel and Word all use this content,
    so no export is a "clean" version: amendment flags, conflicts, lags, computed notation all appear."""
    lines = [AMENDMENT_FLAG] if AMENDMENT_FLAG in rec.flags else []
    if rec.value is None:
        gap = f"{rec.gap} ({rec.label})" if rec.label else rec.gap
        if rec.status == "not_extracted" and rec.citation and rec.citation.url.startswith("http"):
            gap += f" · {FEE_LINK_TEXT}"  # client, W3: the link is visible in the cell (the cell is the link)
        lines.append(gap)
        if rec.status == "conflict":
            lines += [f"{c.value}% · {c.citation.section} ({c.citation.form} {c.citation.accession})"
                      for c in rec.candidates]
    else:
        head = f"{rec.label}: {rec.display()}" if rec.label else rec.display()
        if rec.confidence:
            head += f" [{LETTER[rec.confidence]}]"
        if rec.method == "computed":
            head += " (computed)"
        lines.append(head)
    if rec.note:
        lines.append(rec.note)
    if rec.lag_quarters:
        lines.append(f"as of {rec.period_end} ({rec.lag_quarters}Q lag)")
    return "\n".join(lines)


def _header(ws, names):
    ws.append(names)
    for c in ws[1]:
        c.font, c.fill = BOLD, HEADER_FILL
    ws.freeze_panes = "B2"


def _benchmark(ws, bundle: RunBundle):
    _header(ws, ["Metric"] + bundle.funds)
    for metric, label in bundle.rows:
        row = bundle.table[metric]
        ws.append([label] + [cell_text(row[f]) for f in bundle.funds])
        for col, fund in enumerate(bundle.funds, start=2):
            cit = row[fund].citation
            cell = ws.cell(row=ws.max_row, column=col)
            if cit and cit.url.startswith("http"):
                cell.hyperlink, cell.font = cit.url, LINK
            kind = alert(row[fund])
            if kind:
                cell.fill, cell.font = ALERT_FILL[kind], ALERT_FONT
    ws.append(["Data as of"] + [str(bundle.table["nav_per_share"][f].period_end or "—") for f in bundle.funds])
    ws.append([])
    for i, note in enumerate(bundle.footnotes + [f"Run ID {bundle.run_id} ({bundle.created_at:%Y-%m-%d %H:%M}), code "
                                                 f"version {bundle.code_version}."], start=1):
        ws.append([f"{i}. {note}"])
    ws.column_dimensions["A"].width = 44
    for col in "BCDEF":
        ws.column_dimensions[col].width = 32
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")


PROVENANCE_COLUMNS = ["Fund", "Metric", "Value", "Unit", "Status", "Reason", "Period end", "Lag (Q)", "Form",
                      "Accession", "Filed", "Document", "URL", "Section", "Row label", "Column", "Source quote",
                      "Char offset", "Find hint", "SHA-256", "Method", "Normalization", "Inputs", "Check",
                      "Confidence", "Confidence reason", "Resolution", "Flags", "Note", "Other candidates"]


def _inputs_text(rec: ValueRecord) -> str:
    return " | ".join(f"{x.value} = {x.citation.row_label} ({x.citation.form} {x.citation.accession}, "
                      f"{x.citation.section}, column {x.citation.column_label}): \"{x.citation.quote}\""
                      for x in rec.inputs)


def find_hint(c) -> str:
    """How to land on the value in the filing with the browser's find: search the row label, take match N."""
    return f"search “{c.row_label}”: match {c.find_match} of {c.find_total}" if c and c.find_match else ""


def _provenance_row(rec: ValueRecord, metric_name: str) -> list:
    c = rec.citation
    others = "; ".join(f"{x.value} ({x.citation.accession}, {'verified' if x.verified else x.verify_reason})"
                       for x in rec.candidates
                       if c is None or x.citation.accession != c.accession or x.value != rec.value)
    return [rec.fund, metric_name, str(rec.value) if rec.value is not None else "", rec.unit, rec.status, rec.reason,
            str(rec.period_end or ""), rec.lag_quarters, c and c.form, c and c.accession,
            str(c.filing_date or "") if c else "", c and c.document, c and c.url, c and c.section,
            c and c.row_label, c and c.column_label, c and c.quote, c and c.char_offset, find_hint(c), c and c.sha256,
            rec.method, " ".join(rec.normalizations), _inputs_text(rec), rec.check, rec.confidence,
            rec.confidence_reason, rec.resolution, ", ".join(rec.flags), rec.note, others]


def issue_row(issue, bundle: RunBundle) -> list:
    """One Exceptions line in plain words: type, fund, metric (deck row label), message."""
    return [issue_kind_label(issue.kind), issue.fund, metric_label(issue.metric, bundle.rows), issue.message]


TREND_COLUMNS = ["Fund", "Quarter end", "Value", "Status / reason", "Form", "Accession",
                 "Source quote (or section)", "Confidence"]


def trend_row(fund: str, p: ValueRecord) -> list:
    """One NAV trend point. A gap is a row with its reason, never left out (decision 4); the record's label
    names the fund's measure, so KREF reads "Book value per share" (decision 18)."""
    c = p.citation
    status = "ok" if p.status == "ok" else f"{status_label(p.status)}: {p.reason}"
    return [f"{fund} ({p.label})" if p.label else fund, str(p.period_end),
            str(p.value) if p.value is not None else "", status, c and c.form, c and c.accession,
            c and (c.quote or c.section), p.confidence]


def write(bundle: RunBundle, path: Path) -> Path:
    wb = Workbook()
    _benchmark(wb.active, bundle)
    wb.active.title = "Benchmark"

    prov = wb.create_sheet("Provenance")
    _header(prov, PROVENANCE_COLUMNS)
    for metric, label in bundle.rows:
        for fund in bundle.funds:
            rec = bundle.table[metric][fund]
            prov.append(_provenance_row(rec, rec.label or label))  # KREF: "Book value per share"

    exc = wb.create_sheet("Exceptions")
    _header(exc, ["Type", "Fund", "Metric", "Message"])
    for issue in bundle.issues:
        exc.append(issue_row(issue, bundle))
    exc.column_dimensions["D"].width = 120

    trend = wb.create_sheet("NAV Trend")
    _header(trend, TREND_COLUMNS)
    for fund, points in bundle.trend.items():
        for p in points:
            trend.append(trend_row(fund, p))
            if p.citation and p.citation.url.startswith("http"):
                trend.cell(row=trend.max_row, column=6).hyperlink = p.citation.url  # the accession links
    for ws in wb.worksheets:
        ws.protection.sheet = True  # no password: stops accidental edits, like the locked template
    wb.save(path)
    return Path(path)

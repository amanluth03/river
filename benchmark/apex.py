"""Apex Ridge's own numbers from the client CSV, cited as client-provided, never modified.

Checks are reported as exceptions for the client to answer (decision 11), not fixed.
"""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from .config import APEX_COLUMNS as COLUMNS, APEX_FUND as FUND, quarter_end
from .records import Citation, Issue, ValueRecord


def _quarter_date(label: str) -> date:
    q, year = label.split()  # "Q4 2025"
    return quarter_end(int(year), int(q[1]))


def _record(path: Path, header: str, line: str, row: dict, metric: str) -> ValueRecord:
    column, unit = COLUMNS[metric]
    period = _quarter_date(row["quarter"])
    citation = Citation(cik="client", form="Client data", accession=path.name, period_end=period,
                        url=str(path.name), document=path.name, section=f"row {row['quarter']}",
                        quote=f"{header} | {line}", row_label=row["quarter"], column_label=column)
    note = f"hurdle {Decimal(row['incentive_hurdle_pct']):.2f}%" if metric == "incentive_fee" else ""
    return ValueRecord(fund=FUND, metric=metric, value=Decimal(row[column]), unit=unit, status="ok",
                       period_end=period, lag_quarters=0, citation=citation, method="client_csv", note=note,
                       confidence_reason="Client-provided data; not independently verifiable.")


def _compounding_issues(rows: list[dict]) -> list[Issue]:
    issues = []
    for i in range(3, len(rows)):
        growth = Decimal(1)
        for r in rows[i - 3:i + 1]:
            growth *= 1 + Decimal(r["net_return_qtd_pct"]) / 100
        compounded = ((growth - 1) * 100).quantize(Decimal("0.01"))
        reported = Decimal(rows[i]["net_return_1y_pct"])
        gap = int((compounded - reported) * 100)
        if gap != 0:
            issues.append(Issue(
                kind="client_data", fund=FUND, metric="net_return_1y",
                message=(f"{rows[i]['quarter']}: the four quarterly returns compound to {compounded}%, but the reported "
                         f"1Y is {reported}% ({gap:+d} bps). Showing the reported figure; question for the client."),
                details={"quarter": rows[i]["quarter"], "compounded": str(compounded), "reported": str(reported),
                         "gap_bps": gap}))
    return issues


def _fee_issues(rows: list[dict]) -> list[Issue]:
    issues = []
    for column in ("management_fee_pct", "incentive_fee_pct", "incentive_hurdle_pct"):
        values = {r[column] for r in rows}
        if len(values) > 1:
            issues.append(Issue(kind="client_data", fund=FUND, metric=column,
                                message=f"{column} changes across quarters: {sorted(values)}"))
    return issues


def load(path: Path) -> tuple[dict[date, dict[str, ValueRecord]], list[Issue]]:
    path = Path(path)
    lines = path.read_text().splitlines()
    header = lines[0]
    rows = list(csv.DictReader(lines))
    by_quarter = {}
    for line, row in zip(lines[1:], rows):
        by_quarter[_quarter_date(row["quarter"])] = {m: _record(path, header, line, row, m) for m in COLUMNS}
    return by_quarter, _compounding_issues(rows) + _fee_issues(rows)

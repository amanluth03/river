from datetime import date
from decimal import Decimal

from benchmark import apex
from benchmark.config import APEX_CSV


def test_loads_eight_quarters_with_client_citation():
    by_quarter, issues = apex.load(APEX_CSV)
    assert len(by_quarter) == 8
    nav = by_quarter[date(2025, 12, 31)]["nav_per_share"]
    assert nav.value == Decimal("26.12") and nav.method == "client_csv"
    assert "Q4 2025" in nav.citation.quote and nav.citation.column_label == "nav_per_share_usd"


def test_incentive_fee_carries_hurdle_note():
    by_quarter, _ = apex.load(APEX_CSV)
    fee = by_quarter[date(2025, 12, 31)]["incentive_fee"]
    assert fee.value == Decimal("12.50") and "6.00%" in fee.note


def test_compounding_gap_flagged_for_q4_2025_and_q4_2024():
    _, issues = apex.load(APEX_CSV)
    gaps = {i.details["quarter"]: i for i in issues if i.kind == "client_data" and i.metric == "net_return_1y"}
    assert gaps["Q4 2025"].details["compounded"] == "10.55" and gaps["Q4 2025"].details["gap_bps"] == 24
    assert gaps["Q4 2024"].details["gap_bps"] == 24
    assert "Q3 2024" not in gaps  # needs four quarters of QTD data, which start in Q1 2024

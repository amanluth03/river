from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from benchmark import config
from benchmark.records import Citation, ValueRecord


def test_window_quarters_ends_at_as_of_and_has_eight_points():
    quarters = config.window_quarters(date(2025, 12, 31))
    assert len(quarters) == 8
    assert quarters[0] == date(2024, 3, 31)
    assert quarters[-1] == date(2025, 12, 31)


def test_funds_loaded_from_client_csv_with_correct_ciks():
    by_ticker = {f.ticker: f for f in config.load_funds()}
    assert by_ticker["CCLFX"].cik == "0001735964"
    assert by_ticker["KREF"].kind == "mreit"
    assert by_ticker["TAKIX"].share_class == "I"
    assert len(by_ticker) == 4


def test_missing_value_must_carry_a_non_ok_status_and_reason():
    with pytest.raises(ValidationError):
        ValueRecord(fund="GBDC", metric="nav_per_share", value=None, unit="usd", status="ok")
    rec = ValueRecord(fund="GBDC", metric="nav_per_share", value=None, unit="usd",
                      status="not_found", reason="table not located")
    assert rec.display() == "—"


def test_ok_value_requires_citation():
    with pytest.raises(ValidationError):
        ValueRecord(fund="GBDC", metric="nav_per_share", value=Decimal("14.84"), unit="usd", status="ok")
    cit = Citation(cik="1476765", form="10-Q", accession="0001476765-26-000012", filing_date=date(2026, 2, 4),
                   period_end=date(2025, 12, 31), url="https://example", document="gbdc-20251231.htm",
                   section="Balance sheet", quote="14.84")
    rec = ValueRecord(fund="GBDC", metric="nav_per_share", value=Decimal("14.84"), unit="usd",
                      status="ok", citation=cit)
    assert rec.display() == "$14.84"

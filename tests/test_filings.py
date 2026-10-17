import json
from datetime import date
from pathlib import Path

import pytest

from benchmark import filings
from benchmark.edgar import Edgar, EdgarError

SUBS = json.loads((Path(__file__).parent / "fixtures" / "submissions_cclfx.json").read_text())


def test_lists_semiannual_report_with_period_from_index():
    found = filings.list_filings(SUBS, ("N-CSR", "N-CSRS"), since=date(2024, 1, 1))
    by_acc = {f.accession: f for f in found}
    f = by_acc["0001213900-25-118573"]
    assert f.form == "N-CSRS" and f.period == date(2025, 9, 30) and f.filing_date == date(2025, 12, 5)
    assert f.primary_doc == "ea0264761-01_ncsrs.htm"
    assert not f.amendment


def test_amendments_are_included_and_flagged():
    found = filings.list_filings(SUBS, ("N-CSR", "N-CSRS"), since=date(2024, 1, 1))
    amendments = [f for f in found if f.amendment]
    assert {f.accession for f in amendments} >= {"0001213900-24-027119", "0001213900-24-034098"}
    assert all(f.form == "N-CSRS/A" for f in amendments)


def test_other_forms_excluded():
    found = filings.list_filings(SUBS, ("N-CSR", "N-CSRS"), since=date(2024, 1, 1))
    assert {f.form.removesuffix("/A") for f in found} == {"N-CSR", "N-CSRS"}


def test_fiscal_year_end_mismatch_is_reported_not_trusted():
    found = filings.list_filings(SUBS, ("N-CSR", "N-CSRS"), since=date(2024, 1, 1))
    message = filings.fiscal_year_end_mismatch(SUBS, found, annual_form="N-CSR")
    assert message and "1231" in message and "03-31" in message


def test_document_period_reads_dei_tag(tmp_path):
    doc = tmp_path / "d.htm"
    doc.write_text('<html><body><ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c-1">'
                   'September 30, 2025</ix:nonNumeric></body></html>')
    assert filings.document_period(doc) == date(2025, 9, 30)


def test_403_raises_readable_error(monkeypatch, tmp_path):
    class Resp:
        status_code = 403
        content = b""
    edgar = Edgar("Aman Luthra amanluth03@gmail.com", cache=None, session_get=lambda *a, **k: Resp(),
                  pause=0)
    with pytest.raises(EdgarError, match="User-Agent"):
        edgar.get_bytes("https://data.sec.gov/submissions/CIK0001735964.json")

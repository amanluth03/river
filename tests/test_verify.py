from datetime import date
from decimal import Decimal

import pytest

from benchmark import verify
from benchmark.cache import Cache
from benchmark.records import Candidate, Citation

DOC = (b"<html><body><p>Consolidated Financial Highlights Class I</p><table>"
       b"<tr><td>Net asset value, end of period</td><td>$</td><td>10.77</td><td>$</td><td>10.83</td></tr>"
       b"<tr><td>Net asset value per share</td><td>"
       b'<ix:nonFraction name="us-gaap:NetAssetValuePerShare" id="f-113" contextRef="c-9" scale="0">14.84</ix:nonFraction>'
       b"</td></tr></table></body></html>")


@pytest.fixture
def cache(tmp_path):
    c = Cache(tmp_path)
    c.store("1735964", "0001213900-25-118573", "doc.htm", DOC)
    return c


def make(value, quote, column_index=0, method="table", fact_id=None, row_label="Net asset value, end of period",
         concept=None):
    cit = Citation(cik="1735964", form="N-CSRS", accession="0001213900-25-118573", url="u", document="doc.htm",
                   section="Financial Highlights", quote=quote, row_label=row_label, fact_id=fact_id, concept=concept)
    return Candidate(fund="CCLFX", metric="nav_per_share", value=Decimal(value), unit="usd",
                     period_end=date(2025, 9, 30), method=method, citation=cit, column_index=column_index)


def test_gate_accepts_exact_quote_and_records_offset(cache):
    cand = make("10.77", "Net asset value, end of period $ 10.77 $ 10.83")
    ok, reason = verify.check(cand, cache)
    assert ok, reason
    assert cand.citation.char_offset is not None
    assert cand.citation.sha256


def test_gate_rejects_altered_digit(cache):
    cand = make("10.77", "Net asset value, end of period $ 10.71 $ 10.83")
    ok, reason = verify.check(cand, cache)
    assert not ok
    assert "not found verbatim" in reason


def test_gate_rejects_value_from_wrong_column(cache):
    cand = make("10.77", "Net asset value, end of period $ 10.77 $ 10.83", column_index=1)
    ok, reason = verify.check(cand, cache)
    assert not ok
    assert "column" in reason


def test_gate_rejects_when_file_bytes_changed(cache):
    cache.path("1735964", "0001213900-25-118573", "doc.htm").write_bytes(DOC.replace(b"10.77", b"10.78"))
    ok, reason = verify.check(make("10.77", "Net asset value, end of period $ 10.77 $ 10.83"), cache)
    assert not ok
    assert "hash" in reason


def test_gate_checks_ixbrl_fact_id(cache):
    good = make("14.84", "Net asset value per share 14.84", method="ixbrl", fact_id="f-113",
                row_label="Net asset value per share", concept="us-gaap:NetAssetValuePerShare")
    assert verify.check(good, cache)[0]
    bad = make("14.84", "Net asset value per share 14.84", method="ixbrl", fact_id="f-999",
               row_label="Net asset value per share", concept="us-gaap:NetAssetValuePerShare")
    ok, reason = verify.check(bad, cache)
    assert not ok and "f-999" in reason


def test_parse_numbers_ignores_glued_footnotes_and_reads_parentheses():
    assert verify.parse_numbers("Net investment income1 0.48 (0.54 ) 4.60 %5 1,234") == [
        Decimal("0.48"), Decimal("-0.54"), Decimal("4.60"), Decimal("1234")]


def test_parse_numbers_reads_a_standalone_dash_as_zero():
    assert verify.parse_numbers("(0.54 ) - (0.90 )") == [Decimal("-0.54"), Decimal("0"), Decimal("-0.90")]

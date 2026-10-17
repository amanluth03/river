from datetime import date
from decimal import Decimal
from pathlib import Path

from benchmark.extract import ixbrl, tables

FX = Path(__file__).parent / "fixtures"
NAV_END = r"^Net asset value, end of (the )?(period|year)"


def value_at(hit, when):
    return hit.values[hit.column_dates.index(when)]


def test_takix_picks_class_i_not_class_a():
    hits = tables.find_row(FX / "takix_ncsr_2025.html", NAV_END, class_label="I")
    assert len(hits) == 1
    hit = hits[0]
    assert hit.share_class == "I"
    assert value_at(hit, date(2025, 12, 31)) == Decimal("8.32")
    assert value_at(hit, date(2024, 12, 31)) == Decimal("8.55")


def test_takix_class_a_is_a_different_table():
    hit = tables.find_row(FX / "takix_ncsr_2025.html", NAV_END, class_label="A")[0]
    assert value_at(hit, date(2025, 12, 31)) == Decimal("8.28")


def test_cclfx_class_from_heading_and_dates_from_column_headers():
    hit = tables.find_row(FX / "cclfx_ncsrs_2025-09.html", NAV_END, class_label="I")[0]
    assert value_at(hit, date(2025, 9, 30)) == Decimal("10.77")
    assert value_at(hit, date(2025, 3, 31)) == Decimal("10.83")
    assert value_at(hit, date(2022, 3, 31)) == Decimal("10.79")  # short Jan-Mar 2022 period
    assert hit.quote.startswith("Net asset value, end of period")


def test_kref_book_value_per_share():
    hit = tables.find_row(FX / "kref_10k_2025.html", r"^Book value per share", class_label=None)[0]
    assert value_at(hit, date(2025, 12, 31)) == Decimal("13.04")
    assert value_at(hit, date(2024, 12, 31)) == Decimal("14.76")


def test_row_lookup_returns_other_rows_of_same_table():
    hit = tables.find_row(FX / "kref_10k_2025.html", r"^Book value per share", class_label=None)[0]
    equity = tables.row_in_same_table(hit, r"^Common stockholders' equity")
    shares = tables.row_in_same_table(hit, r"^Total shares outstanding")
    assert equity.values[0] == Decimal("844800") and shares.values[0] == Decimal("64763626")


def test_gbdc_nav_fact_with_period():
    facts = ixbrl.facts(FX / "gbdc_10q_2025-12.html", "us-gaap:NetAssetValuePerShare")
    by_date = {f.period_end: f for f in facts if not f.dims}
    assert by_date[date(2025, 12, 31)].value == Decimal("14.84")
    assert by_date[date(2025, 12, 31)].fact_id
    assert "14.84" in by_date[date(2025, 12, 31)].row_quote


def test_parse_number_handles_parentheses_and_footnotes():
    assert tables.parse_number("(0.54") == Decimal("-0.54")
    assert tables.parse_number("$") is None
    assert tables.parse_number("—") == Decimal("0")  # nil in financial tables
    assert tables.parse_number("1,234.5") == Decimal("1234.5")


def test_column_mismatch_returns_none(tmp_path):
    doc = tmp_path / "d.htm"
    doc.write_text("<html><body><p>Financial Highlights Class I</p><table>"
                   "<tr><td>Year Ended December 31,</td></tr><tr><td>CLASS I</td><td>2025</td><td>2024</td></tr>"
                   "<tr><td>Net asset value, end of period</td><td>8.32</td><td>8.55</td><td>8.52</td></tr>"
                   "</table></body></html>")
    assert tables.find_row(doc, NAV_END, class_label="I") == []


def test_mixed_header_six_months_then_fiscal_years():
    hit = tables.find_row(FX / "takix_ncsrs_2025-06.html", NAV_END, class_label="I")[0]
    assert hit.column_dates[0] == date(2025, 6, 30)
    assert hit.column_dates[1] == date(2024, 12, 31)
    assert value_at(hit, date(2024, 12, 31)) == Decimal("8.55")  # matches the 2025 annual report


def test_mixed_header_with_ambiguous_order_is_refused():
    assert tables.find_row(FX / "takix_ncsrs_2025-06.html", NAV_END, class_label="M") == []


def _doc(tmp_path, body):
    p = tmp_path / "d.htm"
    p.write_text(f"<html><body>{body}</body></html>")
    return p


def test_month_day_inside_a_full_date_is_not_used_for_year_columns(tmp_path):
    # Review finding 1: "September 30, 2025" must not lend "September 30" to the fiscal-year columns.
    doc = _doc(tmp_path, "<p>Financial Highlights Class I</p><table>"
               "<tr><td></td><td>Six Months Ended</td><td>Year Ended March 31,</td></tr>"
               "<tr><td></td><td>September 30, 2025</td><td>2025</td><td>2024</td></tr>"
               "<tr><td>Net asset value, end of period</td><td>10.77</td><td>10.83</td><td>10.55</td></tr></table>")
    hits = tables.find_row(doc, NAV_END, class_label="I")
    assert all(date(2024, 9, 30) not in h.column_dates for h in hits)
    assert hits == []  # mixed shape we can't order with certainty: refuse


def test_class_comes_from_the_heading_of_each_table_not_the_first_match(tmp_path):
    # Review finding 3: identical tables must not all inherit the first table's heading.
    long_row = "<tr><td>Per Share Operating Data " + "for a share outstanding throughout the period " * 8 + "</td></tr>"
    table = ("<table><tr><td></td><td>December 31, 2025</td></tr>" + long_row +
             "<tr><td>Net asset value, end of period</td><td>{v}</td></tr></table>")
    doc = _doc(tmp_path, "<p>Financial Highlights Class A</p>" + table.format(v="8.28") +
               "<p>Financial Highlights Class I</p>" + table.format(v="8.32"))
    hits = tables.find_row(doc, NAV_END, class_label="I")
    assert [h.values[0] for h in hits] == [Decimal("8.32")]


def test_hit_records_the_header_evidence_for_each_column():
    hit = tables.find_row(FX / "takix_ncsr_2025.html", NAV_END, class_label="I")[0]
    assert hit.column_headers[0] == "Year Ended December 31, | 2025"

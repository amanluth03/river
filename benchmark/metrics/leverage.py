"""Leverage, two rows (decision 10): economic debt-to-equity and regulatory asset coverage.

Economic D/E = total debt (including mandatory redeemable preferred) / net assets. Every input is a
verified row of ONE balance-sheet table, so the table's scale (dollars or thousands) cancels out.
It is checked against a figure the fund reports itself, which catches a missed debt line:
  TAKIX, GBDC: the D/E implied by reported asset coverage, 1 / (coverage - 1);
  KREF: its own "total leverage ratio" (net of cash), recomputed from our inputs and cash;
  CCLFX: no fund-level figure is reported, so no check (Medium at best).

Regulatory leverage = asset coverage as the fund reports it under the 1940 Act:
  TAKIX: Note 7 sentence (inclusive of preferred); GBDC: tagged highlights row;
  CCLFX: computed from the balance sheet and labeled so (it reports per facility only);
  KREF: not applicable (not a 1940 Act fund); its own reported ratios go in the note.
"""
import re
from datetime import date
from decimal import Decimal

from .. import textnorm
from ..config import (COVERAGE_CONCEPT, COVERAGE_MINIMUM, KREF_DEBT_TO_EQUITY, KREF_NOT_1940_ACT,
                      KREF_TOTAL_LEVERAGE, LEVERAGE_ROWS, LEVERAGE_TOLERANCE, TAKIX_COVERAGE_SENTENCE)
from ..conflicts import resolve
from ..extract import tables
from ..records import Candidate, ValueRecord
from ..confidence import score
from .common import (FundData, check_all, chosen_candidate, citation, computed, ixbrl_candidates,
                     latest_filing_for, missing, table_candidate)

ECON, REG = "leverage_economic", "leverage_regulatory"
TWO = Decimal("0.01")
SECTION = "Balance sheet (Statement of Assets and Liabilities / Financial Condition)"


def implied_de(coverage_pct: Decimal) -> Decimal:
    """Asset coverage C = (net assets + senior securities) / senior securities, so D/E = 1 / (C - 1)."""
    return 1 / (coverage_pct / 100 - 1)


def _balance_sheet(data: FundData, filing, period: date):
    """Verified equity row, debt rows (and KREF's cash row) from one balance-sheet table, or a reason.

    A debt line can be absent when its balance is zero (CCLFX had no "Secured borrowings" at 3/31/25), so
    debt rows are optional, but the absent ones are returned so the caller can say so and lower confidence
    unless an independent check proves the total. Rows printed as percentages (a schedule of investments'
    "Net Assets 100.0%") are never balance-sheet amounts and are skipped.
    """
    rows = LEVERAGE_ROWS[data.fund.ticker]
    path = data.fetch(filing)
    best = None
    for equity_hit in tables.find_row(path, rows["equity"], None):
        if period not in equity_hit.column_dates or "%" in equity_hit.quote:
            continue
        found = {regex: tables.row_in_same_table(equity_hit, regex) for regex in rows["debt"]}
        found = {regex: hit for regex, hit in found.items() if hit is not None and "%" not in hit.quote}
        cash_hit = tables.row_in_same_table(equity_hit, rows["cash"]) if "cash" in rows else None
        if not found or ("cash" in rows and cash_hit is None):
            continue  # not the balance sheet
        if best is None or len(found) > len(best[1]):
            best = (equity_hit, found, cash_hit)
    if best is None:
        labels = ", ".join([rows["equity"]] + rows["debt"])
        return None, f"No balance-sheet table in {filing.form} {filing.accession} has these rows for {period}: {labels}", []
    equity_hit, found, cash_hit = best
    i = equity_hit.column_dates.index(period)
    make = lambda hit: table_candidate(data.fund, filing, hit, i, "leverage_input", "amount", SECTION)
    equity, debts = make(equity_hit), [make(h) for h in found.values()]
    cash = make(cash_hit) if cash_hit else None
    everything = [equity] + debts + ([cash] if cash else [])
    check_all(everything, data.cache)
    failed = [c for c in everything if not c.verified]
    if failed:
        return None, f"Balance-sheet row '{failed[0].citation.row_label}' failed verification: {failed[0].verify_reason}", []
    absent = [regex for regex in rows["debt"] if regex not in found]
    return (equity, debts, cash), "", absent


def _formula(equity: Candidate, debts: list[Candidate], value: Decimal) -> str:
    parts = " + ".join(f"{d.citation.row_label} {d.value:,}" for d in debts)
    return (f"Economic D/E = ({parts}) / {equity.citation.row_label} {equity.value:,} = {value}x. "
            f"All amounts from one balance-sheet table, so its scale cancels.")


def _takix_coverage(data: FundData, filing, period: date) -> ValueRecord | None:
    text = textnorm.document_text(data.fetch(filing))
    for m in re.finditer(TAKIX_COVERAGE_SENTENCE, text):
        stated = tables.FULL_DATE.search(m.group("date"))
        if not stated or tables._to_date(*stated.groups()) != period:
            continue
        cand = Candidate(fund=data.fund.ticker, metric=REG, value=Decimal(m.group("value")), unit="pct",
                         period_end=period, method="regex", is_amendment=filing.amendment,
                         citation=citation(data.fund, filing, "Notes, Borrowings (asset coverage)", m.group(0), period))
        check_all([cand], data.cache)
        record = resolve([cand])
        record.normalizations.append(f"Inclusive of preferred shares; debt only: {m.group('debt_only')}%. "
                                     f"1940 Act minimum {COVERAGE_MINIMUM['interval']}.")
        return record
    return None


def _gbdc_coverage(data: FundData, filing, period: date) -> ValueRecord | None:
    cands = [c for fact, c in ixbrl_candidates(data.fund, filing, data.fetch(filing), COVERAGE_CONCEPT, REG, "pct",
                                               f"Financial Highlights (inline XBRL {COVERAGE_CONCEPT})")
             if c.period_end == period]
    if not cands:
        return None
    check_all(cands, data.cache)
    record = resolve(cands)
    record.normalizations.append(f"1940 Act minimum for a BDC: {COVERAGE_MINIMUM['bdc']}.")
    return record


def _kref_reported(data: FundData, filing, period: date) -> list[Candidate]:
    """KREF's own debt-to-equity and total leverage ratios (MD&A table), verified."""
    path = data.fetch(filing)
    out = []
    for regex in (KREF_DEBT_TO_EQUITY, KREF_TOTAL_LEVERAGE):
        for hit in tables.find_row(path, regex, None):
            if period in hit.column_dates:
                out.append(table_candidate(data.fund, filing, hit, hit.column_dates.index(period), REG, "ratio",
                                           "MD&A, Debt-to-Equity Ratio and Total Leverage Ratio"))
                break
    return check_all(out, data.cache)


def records(data: FundData) -> dict[str, ValueRecord]:
    fund = data.fund
    cell = data.nav_cell
    if cell.status != "ok":
        reason = "No verified balance-sheet date (NAV not found), so no leverage."
        return {ECON: missing(fund.ticker, ECON, "not_found", reason), REG: missing(fund.ticker, REG, "not_found", reason)}
    period = cell.period_end
    filing = latest_filing_for(data, period)
    sheet, reason, absent = _balance_sheet(data, filing, period)
    if sheet is None:
        out = {ECON: missing(fund.ticker, ECON, "not_found", reason, period)}
    else:
        equity, debts, cash = sheet
        total_debt = sum(d.value for d in debts)
        de = total_debt / equity.value
        out = {}

    # Regulatory leverage, per fund type.
    if fund.kind == "mreit":
        reported = _kref_reported(data, filing, period)
        note = "; ".join(f"KREF reports {re.sub(r'[(][A-Z][)]$', '', c.citation.row_label)} {c.value}x"
                         for c in reported)
        out[REG] = missing(fund.ticker, REG, "not_applicable", KREF_NOT_1940_ACT, period,
                           citation=reported[0].citation if reported else None,
                           note=(note + " (net of cash; see the filing's definitions)") if note else "")
    elif fund.ticker == "TAKIX":
        out[REG] = _takix_coverage(data, filing, period) or missing(
            fund.ticker, REG, "not_found", f"Asset coverage sentence not found in {filing.form} {filing.accession}.", period)
    elif fund.kind == "bdc":
        out[REG] = _gbdc_coverage(data, filing, period) or missing(
            fund.ticker, REG, "not_found", f"Tagged asset coverage row not found in {filing.form} {filing.accession}.", period)
    elif sheet is not None:  # CCLFX: computed from the balance sheet (decision 36)
        coverage = ((equity.value + total_debt) / total_debt * 100).quantize(Decimal("0.1"))
        out[REG] = computed(fund.ticker, REG, coverage, "pct", period, [equity] + debts,
                            f"Asset coverage = (net assets {equity.value:,} + debt {total_debt:,}) / debt "
                            f"{total_debt:,} = {coverage}%",
                            basis_assumption=("the fund reports asset coverage per facility only; this fund-level "
                                              "figure uses balance-sheet carrying values, not principal"),
                            note="Computed")
        out[REG].normalizations.append(f"The fund reports asset coverage per facility only. 1940 Act minimum "
                                       f"{COVERAGE_MINIMUM['interval']}.")
    else:
        out[REG] = missing(fund.ticker, REG, "not_found", reason, period)

    reg = out[REG]
    if reg.status == "ok":
        reg.note = (f"Implies D/E {implied_de(reg.value).quantize(TWO)}x" + (f"; {reg.note}" if reg.note else "")).strip()

    if sheet is None:
        return out
    # The independent check on economic D/E.
    check = None
    if reg.status == "ok" and reg.method != "computed":
        implied = implied_de(reg.value)
        ok = abs(implied - de) <= LEVERAGE_TOLERANCE
        check = (f"D/E implied by reported asset coverage {reg.value}% is {implied.quantize(TWO)}x vs "
                 f"{de.quantize(TWO)}x from the balance sheet ({'agree' if ok else 'DISAGREE'} within "
                 f"{LEVERAGE_TOLERANCE}x)", ok)
    elif fund.kind == "mreit" and cash is not None:
        total = next((c for c in _kref_reported(data, filing, period) if re.match(KREF_TOTAL_LEVERAGE, c.citation.row_label)), None)
        if total is not None:
            ours = (total_debt - cash.value) / equity.value
            ok = abs(ours - total.value) <= LEVERAGE_TOLERANCE
            check = (f"KREF's reported total leverage ratio {total.value}x vs (debt {total_debt:,} - cash "
                     f"{cash.value:,}) / equity {equity.value:,} = {ours.quantize(TWO)}x "
                     f"({'agree' if ok else 'DISAGREE'} within {LEVERAGE_TOLERANCE}x)", ok)
    if check and reg.status == "ok" and reg.method != "computed":
        # The same comparison also confirms the reported coverage figure.
        shown = chosen_candidate(reg)
        shown.reconciliation, shown.reconciliation_ok = check
        reg.confidence, reg.confidence_reason = score(reg, [c for c in reg.candidates if c.verified], shown)
    value = de.quantize(TWO)
    inputs = [equity] + debts + ([cash] if cash and check else [])
    formula = _formula(equity, debts, value)
    assumption = ""
    if absent:
        names = ", ".join(a.lstrip("^") for a in absent)
        formula += f" Not on this balance sheet, so taken as zero: {names}."
        if not (check and check[1]):  # only an agreeing independent figure proves nothing is missing
            assumption = f"debt lines not on this balance sheet were taken as zero ({names})"
    out[ECON] = computed(fund.ticker, ECON, value, "ratio", period, inputs, formula, check=check,
                         basis_assumption=assumption)
    if fund.kind == "mreit":
        out[ECON].note = "Gross debt"
        out[ECON].normalizations.append("Gross debt / KREF stockholders' equity; preferred stock counted as "
                                        "equity, as KREF does.")
    return out

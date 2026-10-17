"""One benchmark run: fetch, extract, verify, resolve, and assemble the review bundle."""
import os
import subprocess
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from . import apex, config, filings, verify
from .cache import Cache
from .conflicts import resolve
from .edgar import Edgar, EdgarError, archive_url
from .metrics import nav
from .records import Issue, RunBundle, ValueRecord

ROWS = [
    ("net_return_1y", "Net return, trailing 1Y (ann.)"),
    ("net_return_3y", "Net return, trailing 3Y (ann.)"),
    ("net_return_5y", "Net return, trailing 5Y (ann.)"),
    ("management_fee", "Management fee"),
    ("incentive_fee", "Incentive fee (hurdle)"),
    ("nav_per_share", "NAV per share"),
    ("leverage_economic", "Leverage, economic (D/E)"),
    ("leverage_regulatory", "Leverage, regulatory (asset coverage)"),
    ("distribution_yield", "Distribution yield (ann.)"),
]
UNITS = {"nav_per_share": "usd", "leverage_economic": "ratio", "leverage_regulatory": "pct"}
ANNUAL_FORM = {"interval": "N-CSR", "bdc": "10-K", "mreit": "10-K"}


def _missing(fund: str, metric: str, status: str, reason: str, period: date | None = None) -> ValueRecord:
    return ValueRecord(fund=fund, metric=metric, value=None, unit=UNITS.get(metric, "pct"), status=status,
                       reason=reason, period_end=period)


def _code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=config.ROOT, timeout=5).stdout.strip() or "uncommitted"
    except OSError:
        return "unknown"


def _apex_column(as_of: date, issues: list[Issue]) -> dict[str, ValueRecord]:
    by_quarter, apex_issues = apex.load(config.APEX_CSV)
    issues.extend(apex_issues)
    current = by_quarter.get(as_of, {})
    column = {}
    for metric, _ in ROWS:
        if metric in current:
            column[metric] = current[metric]
        elif metric == "leverage_regulatory":
            column[metric] = _missing(apex.FUND, metric, "not_reported", "Client data provides D/E only.")
        else:
            column[metric] = _missing(apex.FUND, metric, "not_found", f"No row for {as_of} in the client CSV.")
    return column, by_quarter


def _fund_nav(fund, edgar, cache, as_of, window, issues, used, progress):
    """NAV records for every period with data, keyed by period end."""
    subs = edgar.submissions(fund.cik)
    # A filing whose period ends before the window can't contain a point inside it, so skip the download.
    found = [f for f in filings.list_filings(subs, fund.forms, since=window[0]) if window[0] <= f.period <= as_of]
    mismatch = filings.fiscal_year_end_mismatch(subs, found, ANNUAL_FORM[fund.kind])
    if mismatch:
        issues.append(Issue(kind="data_quality", fund=fund.ticker, message=mismatch))

    def fetch(f):
        progress(f"Fetching {fund.ticker} {f.form} for period {f.period}…")
        path = edgar.fetch(fund.cik, f.accession, f.primary_doc)
        stated = filings.document_period(path)
        if stated and stated != f.period:
            issues.append(Issue(kind="data_quality", fund=fund.ticker, message=(
                f"{f.form} {f.accession}: EDGAR index says period {f.period}, the document says {stated}. "
                f"Using the index period; please check.")))
        used.append({"fund": fund.ticker, "form": f.form, "accession": f.accession, "period": str(f.period),
                     "filed": str(f.filing_date), "document": f.primary_doc,
                     "url": archive_url(fund.cik, f.accession, f.primary_doc),
                     "sha256": cache.sha256(fund.cik, f.accession, f.primary_doc)})
        return path

    cands = nav.candidates(fund, found, fetch=fetch, window=(window[0], as_of))
    progress(f"Verifying {len(cands)} {fund.ticker} values against their filings…")
    for c in cands:
        verify.check(c, cache)
    by_period = defaultdict(list)
    for c in cands:
        by_period[c.period_end].append(c)
    label = nav.KREF_LABEL if fund.kind == "mreit" else None
    read = defaultdict(list)
    for f in found:
        read[f.period].append(f"{f.form} {f.accession}")
    return {period: resolve(group, label=label) for period, group in by_period.items()}, read


def _nav_trend(fund, records, read, window, issues) -> list[ValueRecord]:
    points = []
    for q in window:
        if q in records:
            points.append(records[q])
        elif q in read:
            # A report for this date exists and was read, so "not reported" would be false.
            reason = f"Report for this date was read ({', '.join(read[q])}) but no NAV row could be located."
            issues.append(Issue(kind="missing", fund=fund.ticker, metric="nav_per_share", message=f"{q}: {reason}"))
            points.append(_missing(fund.ticker, "nav_per_share", "not_found", reason, q))
        elif fund.kind == "interval":
            points.append(_missing(fund.ticker, "nav_per_share", "not_reported",
                                   "Interval fund reports NAV semi-annually; no published figure for this date.", q))
        else:
            points.append(_missing(fund.ticker, "nav_per_share", "not_found",
                                   "No verified figure found in the filings for this date.", q))
    return points


def _nav_cell(fund, records, as_of, issues) -> ValueRecord:
    shown = [r for r in records.values() if r.status == "ok"]
    if not shown:
        failed = next(iter(records.values()), None)
        reason = failed.reason if failed else "No NAV table or tag found in the filings."
        issues.append(Issue(kind="missing", fund=fund.ticker, metric="nav_per_share", message=reason))
        return _missing(fund.ticker, "nav_per_share", failed.status if failed else "not_found", reason)
    cell = max(shown, key=lambda r: r.period_end).model_copy(deep=True)
    cell.lag_quarters = config.quarters_between(cell.period_end, as_of)
    if cell.lag_quarters:
        cell.flags.append("lagged")
        issues.append(Issue(kind="lag", fund=fund.ticker, metric="nav_per_share", message=(
            f"Latest NAV is as of {cell.period_end} ({cell.lag_quarters}Q before {as_of}).")))
    return cell


def _record_issues(fund, records, issues):
    for r in records.values():
        if "conflict" in r.flags or "pm_review" in r.flags:
            issues.append(Issue(kind="conflict", fund=fund.ticker, metric=r.metric,
                                message=f"{r.period_end}: {r.resolution}"))
        elif r.status == "not_verified":
            issues.append(Issue(kind="missing", fund=fund.ticker, metric=r.metric,
                                message=f"{r.period_end}: not shown, failed verification ({r.reason})."))


def run(as_of: date = config.DEFAULT_AS_OF, progress: Callable[[str], None] = print, edgar=None,
        cache: Cache | None = None, runs_dir: Path = config.RUNS_DIR) -> RunBundle:
    load_dotenv(config.ROOT / ".env")
    cache = cache or Cache(config.CACHE_DIR)
    funds = config.load_funds()
    window = config.window_quarters(as_of)
    issues, used = [], []
    table = {metric: {} for metric, _ in ROWS}
    trend = {}

    apex_column, apex_by_quarter = _apex_column(as_of, issues)
    for metric, _ in ROWS:
        table[metric][apex.FUND] = apex_column[metric]
    trend[apex.FUND] = [apex_by_quarter[q]["nav_per_share"] if q in apex_by_quarter
                        else _missing(apex.FUND, "nav_per_share", "not_found", "No client row.", q) for q in window]

    try:
        edgar = edgar or Edgar(os.environ.get("SEC_USER_AGENT", ""), cache)
    except EdgarError as exc:
        edgar_error = str(exc)
        edgar = None
    for fund in funds:
        for metric, _ in ROWS:
            if metric != "nav_per_share":
                table[metric][fund.ticker] = _missing(fund.ticker, metric, "not_implemented",
                                                      "Extraction planned for milestone 2 (after Window 2).")
        if fund.kind == "mreit":
            table["leverage_regulatory"][fund.ticker] = _missing(
                fund.ticker, "leverage_regulatory", "not_applicable",
                "KREF is a REIT, not a 1940 Act fund; asset coverage does not apply.")
            issues.append(Issue(kind="peer_question", fund=fund.ticker, message=(
                "KREF is a commercial mortgage REIT, not a credit fund: no NAV (book value shown instead), "
                "no NAV-based return, no 1940 Act leverage limit. CIO to decide whether it stays in the peer set.")))
        try:
            if edgar is None:
                raise EdgarError(edgar_error)
            progress(f"Reading {fund.ticker} filing index…")
            records, read = _fund_nav(fund, edgar, cache, as_of, window, issues, used, progress)
        except EdgarError as exc:
            issues.append(Issue(kind="fetch", fund=fund.ticker, message=str(exc)))
            table["nav_per_share"][fund.ticker] = _missing(fund.ticker, "nav_per_share", "fetch_failed", str(exc))
            trend[fund.ticker] = [_missing(fund.ticker, "nav_per_share", "fetch_failed", str(exc), q) for q in window]
            continue
        _record_issues(fund, records, issues)
        table["nav_per_share"][fund.ticker] = _nav_cell(fund, records, as_of, issues)
        trend[fund.ticker] = _nav_trend(fund, records, read, window, issues)

    bundle = RunBundle(as_of=as_of, created_at=datetime.now(), code_version=_code_version(),
                       funds=[apex.FUND] + [f.ticker for f in funds], rows=ROWS, table=table, trend=trend,
                       issues=issues, filings=used)
    out = Path(runs_dir) / bundle.created_at.strftime("%Y%m%d-%H%M%S-%f")
    out.mkdir(parents=True, exist_ok=True)
    (out / "bundle.json").write_text(bundle.model_dump_json(indent=1))
    progress("Done.")
    return bundle


def latest_bundle(runs_dir: Path = config.RUNS_DIR) -> RunBundle | None:
    runs = sorted(Path(runs_dir).glob("*/bundle.json"))
    return RunBundle.model_validate_json(runs[-1].read_text()) if runs else None

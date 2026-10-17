"""One benchmark run: fetch, extract, verify, resolve, and assemble the review bundle."""
import os
import subprocess
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from . import amendments, apex, config, filings, verify
from .cache import Cache
from .config import APEX_GAP_NOTE, NOT_IN_CLIENT_DATA, ROWS
from .conflicts import resolve
from .edgar import Edgar, EdgarError, archive_url
from .metrics import distributions, fees, leverage, nav, returns
from .metrics.common import FundData, missing, searched_citation
from .records import Issue, RunBundle, ValueRecord


def _missing(fund: str, metric: str, status: str, reason: str, period: date | None = None) -> ValueRecord:
    return missing(fund, metric, status, reason, period)


def _code_version() -> str:
    """The commit the run used, marked if the working tree had uncommitted changes (reviewer finding:
    a report must not claim a commit that didn't produce it)."""
    try:
        git = lambda *args: subprocess.run(["git", *args], capture_output=True, text=True, cwd=config.ROOT,
                                           timeout=5).stdout.strip()
        commit = git("rev-parse", "--short", "HEAD") or "uncommitted"
        dirty = git("status", "--porcelain", "--untracked-files=no", "--", "benchmark")
        return f"{commit}+uncommitted changes" if dirty else commit
    except OSError:
        return "unknown"


def _apex_column(as_of: date, issues: list[Issue]):
    by_quarter, apex_issues = apex.load(config.APEX_CSV)
    issues.extend(apex_issues)
    current = by_quarter.get(as_of, {})
    column = {}
    for metric, _ in ROWS:
        if metric in current:
            column[metric] = current[metric]
        elif metric == "leverage_regulatory":
            column[metric] = _missing(apex.FUND, metric, "not_reported", NOT_IN_CLIENT_DATA)
        else:
            column[metric] = _missing(apex.FUND, metric, "not_found", f"No row for {as_of} in the client CSV.")
    gaps = [i.details["gap_bps"] for i in apex_issues if i.metric == "net_return_1y" and "gap_bps" in i.details]
    if gaps and column["net_return_1y"].status == "ok":
        note = APEX_GAP_NOTE.format(gap=round(sum(gaps) / len(gaps)))
        column["net_return_1y"].note = "See gap footnote"
        column["net_return_1y"].normalizations.append(note)
        issues.append(Issue(kind="client_data", fund=apex.FUND, metric="net_return_1y", message=note,
                            details={"gaps_bps": gaps}))
    return column, by_quarter


def _filings_in_window(fund, subs, as_of, window, issues):
    # A filing whose period ends before the window can't contain a point inside it, so skip the download.
    found = [f for f in filings.list_filings(subs, fund.forms, since=window[0]) if window[0] <= f.period <= as_of]
    mismatch = filings.fiscal_year_end_mismatch(subs, found, fund.annual_form)
    if mismatch:
        issues.append(Issue(kind="data_quality", fund=fund.ticker, message=mismatch))
    return found


def _fetcher(fund, edgar, cache, issues, used, progress):
    """fetch(filing) -> cached path; records every filing read, once, with its hash."""
    done = {}

    def fetch(f):
        if f.accession in done:
            return done[f.accession]
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
        done[f.accession] = path
        return path
    return fetch


def _fund_nav(fund, found, fetch, cache, as_of, window, progress):
    """NAV records for every period with data, keyed by period end."""
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
    return max(shown, key=lambda r: r.period_end).model_copy(deep=True)


def _apply_lag(record: ValueRecord, as_of: date, issues: list[Issue]):
    """Every shown competitor value says how far its period is from the as-of date (decision 4)."""
    if record.status != "ok" or record.period_end is None:
        return
    record.lag_quarters = config.quarters_between(record.period_end, as_of)
    if record.lag_quarters:
        record.flags.append("lagged")
        issues.append(Issue(kind="lag", fund=record.fund, metric=record.metric, message=(
            f"Latest figure is as of {record.period_end} ({record.lag_quarters}Q before {as_of}).")))


def _record_issues(records: list[ValueRecord], issues: list[Issue]):
    for r in records:
        if "conflict" in r.flags or "pm_review" in r.flags:
            issues.append(Issue(kind="conflict", fund=r.fund, metric=r.metric, message=f"{r.period_end}: {r.resolution}"))
        elif r.status == "not_verified":
            issues.append(Issue(kind="missing", fund=r.fund, metric=r.metric,
                                message=f"{r.period_end}: not shown, failed verification ({r.reason})."))
        if r.status == "ok" and r.confidence == "low":  # Low is always flagged for review (CLAUDE.md)
            issues.append(Issue(kind="check_failed", fund=r.fund, metric=r.metric,
                                message=f"{r.period_end}: shown with Low confidence. {r.confidence_reason}"))
        if r.method == "computed" and r.status == "ok":
            issues.append(Issue(kind="computed", fund=r.fund, metric=r.metric, message=r.normalizations[0]))
        if "not_comparable" in r.flags:
            issues.append(Issue(kind="not_comparable", fund=r.fund, metric=r.metric, message=r.note))
        if r.status in ("not_found", "not_verified") and r.metric != "nav_per_share":
            issues.append(Issue(kind="missing", fund=r.fund, metric=r.metric, message=r.reason))


def _competitor(fund, edgar, cache, as_of, window, issues, used, progress):
    """All rows of one competitor's column, plus its NAV trend."""
    progress(f"Reading {fund.ticker} filing index…")
    subs = edgar.submissions(fund.cik)
    found = _filings_in_window(fund, subs, as_of, window, issues)
    fetch = _fetcher(fund, edgar, cache, issues, used, progress)
    nav_records, read = _fund_nav(fund, found, fetch, cache, as_of, window, progress)
    _record_issues(nav_records.values(), issues)
    nav_cell = _nav_cell(fund, nav_records, as_of, issues)
    trend = _nav_trend(fund, nav_records, read, window, issues)

    data = FundData(fund=fund, filings=found, fetch=fetch, cache=cache, as_of=as_of, nav=nav_records,
                    nav_cell=nav_cell, issues=issues)
    progress(f"Reading {fund.ticker} leverage, distributions, returns and fee sections…")
    column = {"nav_per_share": nav_cell}
    column.update(leverage.records(data))
    column["distribution_yield"] = distributions.record(data)
    column.update(returns.records(data))
    column.update(fees.records(data))
    for record in column.values():
        _apply_lag(record, as_of, issues)
        if record.citation is None:
            record.citation = searched_citation(data, record.period_end or (nav_cell.period_end if nav_cell.status == "ok" else None))
    _record_issues([r for m, r in column.items() if m != "nav_per_share"], issues)

    progress(f"Checking {fund.ticker} filing index for amendments…")
    amendments.flag(subs, fund, list(column.values()) + trend, issues)
    cited = amendments.cited_accessions(list(column.values()) + trend)
    for original, amended in amendments.amended_filings(subs, fund.forms):
        if original.accession in cited:
            continue  # already flagged on the value itself by amendments.flag
        names = ", ".join(f"{a.form} {a.accession} (filed {a.filing_date})" for a in amended)
        issues.append(Issue(kind="amendment", fund=fund.ticker, message=(
            f"Amendment check: {original.form} {original.accession} (period {original.period}) was amended by "
            f"{names}. No value shown cites the original.")))
    return column, trend


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

    edgar_error = ""
    try:
        edgar = edgar or Edgar(os.environ.get("SEC_USER_AGENT", ""), cache)
    except EdgarError as exc:
        edgar_error = str(exc)
        edgar = None
    for fund in funds:
        if fund.kind == "mreit":
            issues.append(Issue(kind="peer_question", fund=fund.ticker, message=(
                "KREF is a commercial mortgage REIT, not a credit fund: no NAV (book value per share shown instead), "
                "no NAV-based return, no 1940 Act leverage limit. CIO to decide whether it stays in the peer set.")))
        try:
            if edgar is None:
                raise EdgarError(edgar_error)
            column, trend[fund.ticker] = _competitor(fund, edgar, cache, as_of, window, issues, used, progress)
        except Exception as exc:  # any failure stops this fund only; the others still run (review finding 5)
            message = str(exc) if isinstance(exc, EdgarError) else f"Error while reading {fund.ticker} filings: {exc}"
            issues.append(Issue(kind="fetch", fund=fund.ticker, message=message))
            column = {metric: _missing(fund.ticker, metric, "fetch_failed", message) for metric, _ in ROWS}
            trend[fund.ticker] = [_missing(fund.ticker, "nav_per_share", "fetch_failed", message, q) for q in window]
        for metric, _ in ROWS:
            table[metric][fund.ticker] = column[metric]

    footnotes = [n.format(as_of=as_of) for n in config.FOOTNOTES]
    if apex_column["net_return_1y"].normalizations:
        footnotes.append("Apex Ridge 1Y: " + apex_column["net_return_1y"].normalizations[-1])
    bundle = RunBundle(as_of=as_of, created_at=datetime.now(), code_version=_code_version(),
                       funds=[apex.FUND] + [f.ticker for f in funds], rows=ROWS, table=table, trend=trend,
                       issues=issues, filings=used, footnotes=footnotes)
    out = Path(runs_dir) / bundle.run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "bundle.json").write_text(bundle.model_dump_json(indent=1))
    progress("Done.")
    return bundle


def latest_bundle(runs_dir: Path = config.RUNS_DIR, as_of: date | None = None) -> RunBundle | None:
    """The most recent run, optionally only among runs for one as-of date."""
    for path in sorted(Path(runs_dir).glob("*/bundle.json"), reverse=True):
        bundle = RunBundle.model_validate_json(path.read_text())
        if as_of is None or bundle.as_of == as_of:
            return bundle
    return None

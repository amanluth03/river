# Session handoff (written 2026-10-16, end of session 1)

Start a new session with: "Read CLAUDE.md and context/session_handoff.md, then continue the build order."

## Where things stand

- **On main:** `f2068a6` (milestone 1: NAV per share end to end) and `709cdce` (fixes from the independent review). 72 tests pass (`uv run pytest`, offline).
- **Live run** (`uv run python -c "from benchmark import pipeline; pipeline.run()"`, or Run in `uv run benchmark`): 24 filings, about 26 s cold and 10 s cached. All 32 competitor NAV points are verified: 31 High, 1 Medium (GBDC 12/31/25).
- **Built:**
  - EDGAR client and hash cache
  - filing selection, with periods taken from each filing
  - text normalization
  - extractors: lxml inline XBRL, and labeled table rows with share class and column dates
  - NAV metric with reconciliations (interval funds: NAV bridge; KREF: equity ÷ shares)
  - the verification gate:
    - the file hash still matches
    - the quote is verbatim in the filing
    - the value sits in its column
    - the column header gives the period
    - the XBRL element id exists
    - a find hint ("match N of M")
  - conflicts and confidence rules
  - Apex CSV loader and checks
  - pipeline, bundle JSON, Excel export, and the 3-tab review page with a localhost host check
- **Docs in the repo:** `README.md`, `context/how_it_works.md` (module walkthrough), `context/build_log.md` (findings with accession numbers and hand-check links). The spec and plan sit in `docs/superpowers/` locally; that folder is gitignored.

## What Aman asked for next (this order; CLAUDE.md "Build order after Window 2")

1. Leverage, two rows (decisions 13 and 21 in CLAUDE.md)
2. Distribution yield: trailing 12 months ÷ period-end NAV (16)
3. Returns with labels: GBDC "Return on average net assets", marked not directly comparable and not compounded (12); interval funds' 3Y "Not reported by fund" (15)
4. Amendment detection flag (20)
5. Sheet protection on the export (17)
6. Fees, or "Not extracted in v1" with a section-level link (23)

Also from CLAUDE.md, items 14, 18, 21 and 22:
- KREF label exactly "Book value per share"; it's currently "Book value per share (KREF does not report NAV)", so check against item 18.
- Apex 1Y gap note: a footnote on the cell plus an exceptions entry, framed as "fund accountant to confirm".
- Apex regulatory leverage: "Not in client data".
- A filing link on every cell.

## Aman's working rules for this phase

- **No per-module walkthroughs during the build.** At the end, write `docs/CODE_TOUR.md` with:
  1. a one-page pipeline map (file and function)
  2. each metric's exact path: filing → function → normalization → confidence → UI/Excel cell
  3. every hard-coded value or mapping, where it lives and its source
  4. every place a filing-format change could break it, and what happens then
  5. the 10 questions a skeptical interviewer is likely to ask, each answered in 2 to 3 sentences
- **Log every decision** in `context/decisions.md`, appended after the last row. Never mark one "Client" unless Dana said it.
- **All constants in one config file, each with its source.** Not done yet. Constants to move today:
  - `metrics/nav.py`: the row-label regexes, `NAV_CONCEPT`, `TOLERANCE = 0.01`, the `* 1000` (KREF equity "in thousands")
  - `verify.py`: `HEADER_WINDOW = 6000`
  - `textnorm.py`: `BLOCK_TAGS`
  - `pipeline.py`: `ROWS` labels, `UNITS`, `ANNUAL_FORM`
  - `config.py`: `FUND_SETTINGS`
  - `apex.py`: `COLUMNS`
- **Unsourced assumption to verify first: KREF `* 1000`.** It assumes the equity row is in thousands. Find the caption text in KREF's 10-K table (e.g. "in thousands") and cite it, or derive the multiplier from the caption. (Aman's last interview went badly over a hard-coded label nobody could source.)
- **Tests on real values:** small fixtures cut from cached filings in `tests/fixtures/` (the cutter script is in the old session scratchpad; recreate as needed). Test-first; watch the test fail.
- **Decision log gap:** Aman's new `decisions.md` dropped the earlier technical rows (gate, hash cache, lxml, periods from filings, find hint, computed-value confidence, build order). They're in `git show f2068a6:context/decisions.md`. Ask Aman before re-adding them, and if yes, add them after his rows under "Technical decisions". `how_it_works.md` refers to them by their old numbers (D18, D21, D26).

## Filing facts already found (use for milestone 2)

- **TAKIX** N-CSR 0001725472-26-000003:
  - inline XBRL tags only senior securities: `cef:SeniorSecuritiesCvgPerUnit` (15), `cef:SeniorSecuritiesAmt` (15), `us-gaap:PreferredStockLiquidationPreference` (4)
  - asset coverage is per $1,000 → %
  - the financial highlights per class include "Total Return, at Net Asset Value (2)" (fiscal-year, e.g. Class I 6.27% FY2025) and "Total Dividends and/or distributions to shareholders:" (Class I (0.75) FY2025)
  - there's an "Average Annual Total Returns through December 31, 2025" table
  - semi-annual reports mix "Six Months Ended June 30" with fiscal-year columns (handled)
- **CCLFX** N-CSRS 0001213900-25-118573:
  - Class I highlights: "Total Distributions to shareholders" (0.54) for the 6 months to 9/30/25; "Total return4" 4.60% (6 months, not annualized)
  - companyfacts has `cef:SeniorSecuritiesAmt`
  - TTM distributions = Apr–Sep 2025 (this N-CSRS) + Oct 2024–Mar 2025 (FY to 3/31/25 minus the 6 months to 9/30/24 from N-CSRS 0001213900-24-106851). That's a computed value citing two or three filings.
- **GBDC**, us-gaap tags:
  - `InvestmentCompanyTotalReturn` = return on average net assets: FY25 9.36%, FY21 13.70%, all in 10-K 0001476765-25-000096
  - `InvestmentCompanyTotalReturnMarketValue`: excluded
  - `NetAssetValuePerShare`, `InvestmentCompanySeniorSecurityIndebtednessAssetCoverageRatio`, `InvestmentCompanyDistributionToShareholdersPerShare`
  - `cef:ManagementFeesPercent` / `IncentiveFeesPercent` are fee-table percentages of net assets, not contract rates
  - fiscal quarters align with calendar quarters
- **KREF** 10-K 0001628280-26-005092:
  - book value table: equity $844,800k / 64,763,626 shares = $13.04
  - the debt-to-equity ratio is in the MD&A (not yet located)
  - externally managed: fee terms are in the 10-K
- **Amendments:** CCLFX N-CSRS/A 0001213900-24-027119 and -034098 (period 2023-09-30). This is the test case for decision 20 (detect, even though it's outside the window).

## Environment gotchas

- `/usr/bin/python3` is blocked (Xcode license). Use `uv run`.
- zsh doesn't word-split `$var`; use `${=var}`. An unquoted `=====` triggers zsh's `=` expansion.
- Playwright screenshots must be saved inside the repo (`.playwright-mcp/`, gitignored).
- `.gitignore` excludes `docs/superpowers/`, `.superpowers/`, `data/cache/`, `runs/` and `.env`.

## Open items from review (deferred minors; consider before submission)

- Two filings made on the same day with different values: currently "latest wins"; should go to PM review.
- The Excel "other candidates" column leaves out alternatives from the same filing.
- A second, different XBRL fact in one filing is dropped silently.
- The lag message can mislead when the newest period failed verification.
- Submissions are always refetched (no offline rerun).
- Apex CSV rows are assumed to be in date order.
- "($0.54)" and a Unicode minus parse as positive (reconciliation rows only).
- Ruling to keep or revisit: KREF confidence stays High (confidence = extraction certainty; comparability is shown by the label and flag).

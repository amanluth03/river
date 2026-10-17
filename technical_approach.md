# Technical approach: Apex Ridge peer benchmarking

*For Apex Ridge's technical counterpart. Prepared by River Technologies. As-of date for the figures below: December 31, 2025.*

## 1. What the system does

Each quarter, an analyst opens a local web page, picks a quarter-end and presses **Run**. The system:
- reads each competitor's filing index from SEC EDGAR;
- downloads the periodic reports for the last eight quarters;
- extracts the board-deck metrics, checks each value against the filing it came from, and compares the result with Apex Ridge's own data.

The output is a review page and an Excel workbook in the deck's layout. Every cell carries a confidence level and a link to its source.

The governing rule is that **a gap beats a wrong number**. A value is shown only if the system can prove it is in the filing. Anything it can't prove is shown as a labeled gap with the reason, for example "Not reported by fund" or "Not extracted in v1". Gaps are never left blank or estimated.

## 2. Architecture and data flow

```
EDGAR index ─► filing list ─► download + cache ─► extract candidates ─► verification gate ─► resolve conflicts ─► confidence ─► review page / Excel
 (per CIK)     (per-filing     (by accession,      (XBRL tags, then       (re-reads every      (later filing wins,     (rule named
               period)          SHA-256 hash)       table rows, then       number from the      both values shown)      in the reason)
                                                    narrative)             cached text)
```

- **Retrieval** (`edgar.py`, `filings.py`, `cache.py`). The system uses EDGAR's submissions API with a named User-Agent and paces requests at 5 per second (the SEC's limit is 10). Every document is stored by accession number with a SHA-256 hash, so reruns are fast and reproducible.
- **Periods come from each filing,** never from company metadata. Cliffwater's EDGAR record still says its fiscal year ends December 31; its filings say March 31.
- **Extraction** goes in order of reliability:
  1. inline-XBRL tags (Golub: NAV, asset coverage, distributions, return);
  2. labeled rows in the filing's own tables, such as financial highlights, balance sheets and performance tables, dated by their column headers;
  3. one narrative sentence (Carlyle's asset coverage), matched by a fixed pattern.

  No language model is used for any number in v1.
- **The verification gate** (`verify.py`) runs on every candidate before display. It checks:
  - the cached file's hash is unchanged;
  - the quoted source text appears verbatim in the filing;
  - the number in the expected column of that quote equals the value;
  - the column header above the row gives the claimed period;
  - for tagged values, the XBRL element with that id exists and shows that number.

  A value that fails any check is not shown; the cell shows "not verified" and the reason.
- **Computed values** (economic leverage, distribution yield, Cliffwater's asset coverage) are built only from inputs that each passed the gate. The data model rejects any other kind. Each input is listed with its own citation.
- **Output** (`app.py`, `export_excel.py`). This is a local FastAPI page with three tabs: Table, Exceptions and NAV trend. Clicking a cell shows the filing, accession number, section, row, column header, exact source text, a find hint ("search this label: match 2 of 7") and any check that was run. The Excel export repeats the deck table and adds Provenance (one row per value, with every input), Exceptions and NAV Trend sheets. All sheets are protected against accidental edits.

## 3. Key decisions and reasoning

The full log, with alternatives and costs, is in `context/decisions.md` (51 rows). The ones that shape the output:

| Decision | Reason |
|---|---|
| Common calendar quarter-end. Each fund's latest report for a period ending on or before it; the lag is shown in the cell | Matches how PMs compare today. Cliffwater's returns are visibly three quarters older than its NAV |
| NAV basis, Class I, no market-price returns | Agreed with the client; compares fund performance, not trading |
| Golub's return is shown as reported: "Return on average net assets", "Not directly comparable"; never compounded into 3Y/5Y | It is a different calculation; the PM must see that at a glance |
| Leverage in two rows. Economic D/E = total debt (incl. mandatory redeemable preferred) ÷ net assets. Regulatory = asset coverage as reported under the 1940 Act | Agreed with the client. D/E works for all four funds, including KREF |
| Distribution yield = trailing 12 months of distributions ÷ period-end NAV, built only from reported periods | Same basis as Apex Ridge's own figure. Cliffwater's 12 months combine two semi-annual reports, and both are cited |
| Reported trailing returns with their lag, not semi-annual returns chained together | A reported number beats a computed one with a reinvestment assumption |
| Deterministic parsers plus a verification gate, not an LLM reading filings | Compliance re-pulls sources: a figure they can't find is treated as wrong, and an LLM can return a plausible number from the wrong share class |

## 4. Validation strategy and confidence model

There is no answer key, so trust comes from three things: the gate (every number re-read from the source), independent cross-checks, and making every judgment visible.

**Confidence levels** (each cell's reason names the rule that fired):
- **High:** verified, and confirmed by an independent source. That can be the same value in another filing, a reconciliation that holds, or a figure the fund reports itself that agrees with our computation.
- **Medium:** verified from a single source, or computed from verified inputs with nothing independent to compare against.
- **Low:** sources disagree, a check failed, the value is narrative-only, or it is computed with an assumption. Every Low value is listed in Exceptions for review.

**Reconciliations run:**

| Value | Check |
|---|---|
| Interval-fund NAV | Beginning NAV + total from operations + distributions = ending NAV, to the cent |
| KREF book value | Equity × the table's own stated scale ("in thousands") ÷ shares = book value per share |
| Carlyle D/E (0.40x) | Equals the D/E implied by its reported 352.0% asset coverage (0.40x) |
| Golub D/E (1.25x) | Within 0.05x of the 1.27x implied by its 178.94% coverage. The difference arises because coverage counts debt at principal and the balance sheet at carrying value |
| KREF D/E (4.00x gross) | Recomputed net of cash (3.93x), it agrees with KREF's own reported total leverage ratio of 3.9x |
| Carlyle 1Y return (6.27%) | Equal in the performance table and the financial highlights |
| NAV trend points | 11 points appear in two filings each, with identical values |

These checks also guard against the most likely silent error, a debt line we didn't sum. If one were missed, the reported coverage would disagree and the value would drop to Low.

**Where sources disagreed, and what we chose:**
- **Cliffwater's 1Y return for the year to 3/31/25** is 11.78% in its performance table and 11.58% in its financial highlights, in the same report. We show 11.78% (the fund's presented return), marked Low with both figures visible, and it is a question for the client.
- **Cliffwater reports asset coverage only per facility.** The fund-level 421.1% is computed from its balance sheet, labeled as computed, and marked Low.
- **Apex Ridge's own data:** compounding the four quarterly returns gives 22 to 28 bps more than the reported 1Y in every quarter. The reported figure is shown as official. The gap is footnoted as a likely fixed annual cost, with "fund accountant to confirm".
- **General rule:** a later filing wins over an earlier one and an amendment over its original, with both values shown. Two different values in the same filing go to the PM.

**Amendments:** every run checks each fund's EDGAR index for `/A` filings. A value whose source was later amended is flagged "Superseded by amendment: re-check". The test case is Cliffwater's two amendments to its 9/30/23 semi-annual report, which are detected.

**Tests:** 104 automated tests run offline on extracts cut verbatim from the real filings by a script. They also check that every shown value passes the gate a second time, that no cell is blank, and that every competitor cell links to a filing.

## 5. Known limitations

- **Fee terms are not extracted.** The cell reads "Not extracted in v1" and links to the exact sentence that states the terms in the latest report, not to the prospectus.
- **N-PORT filings and prospectus supplements are not read in v1.** Periodic reports cover every metric in the deck.
- **Parsing is tuned to these four funds.** Row labels, tags and sentence patterns are listed with their sources in one file (`benchmark/config.py`). A reworded label produces a labeled gap, not a wrong value.
- **Cliffwater's D/E has no independent cross-check,** so it is Medium.
- **The interval funds report NAV semi-annually.** Their trend shows four points out of eight; the others are gaps, not estimates.
- **HTML filings have no page numbers.** Citations use section, row, column header, character offset and a find hint.

## 6. Production risks and mitigations

| Risk | Mitigation |
|---|---|
| A fund changes a table layout or label | The value fails to a labeled gap, and the Exceptions list names the missing row. Fixing it is a one-line change in `config.py` plus re-cutting the test extract |
| A new debt line is not summed | Cross-check against reported coverage or the fund's own ratio drops the value to Low. Add Cliffwater's senior-securities table as a second source |
| A filing is amended after use | Each run checks the index and flags the value. Next phase: re-pull and replace automatically |
| EDGAR outage or rate limit | Retries with backoff; a failure stops only that fund's column, and the cache keeps reruns offline |
| Peer set changes (a new fund) | New fund settings and row labels in `config.py`, plus a test extract; expect about a day per fund type |
| Fee extraction with an LLM in a later phase | The LLM must return the exact source sentence, which is checked verbatim against the filing (same gate). Narrative-only values are always Low |
| Key-person dependence | One config file with sources, a code tour (`docs/CODE_TOUR.md`), a decision log and tests on real values |

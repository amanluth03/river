# Technical approach: Apex Ridge peer benchmarking

*For Apex Ridge's technical counterpart. Prepared by River Technologies. Figures are from the run as of December 31, 2025.*

## What the system does

On a local review page, the analyst picks a quarter-end and presses **Run**. The system downloads each competitor's SEC filings for the eight quarters up to that date, extracts the board-deck metrics, checks each value against its filing, and places them beside Apex Ridge's own data. Outputs: the page, an Excel workbook in the deck's layout and a Word report. Every cell has a confidence level and a source link. In v1 the page is started with `uv run benchmark`, so River starts it during the pilot.

The governing rule: **a gap beats a wrong number**. A value is shown only if the system can prove it is in the filing. Otherwise the cell is a labeled gap with the reason, such as "Not reported by fund" or "Not extracted in v1". No cell is blank or estimated.

## Architecture and data flow

```
EDGAR index ─► filing list ─► download + cache ─► extract ─► verification gate ─► resolve conflicts ─► confidence ─► page / Excel / Word
```

- **Retrieval** (`edgar.py`, `filings.py`, `cache.py`). Every document is cached by accession number with a SHA-256 hash, so reruns are fast, offline and reproducible. Periods come from each filing, never from company metadata.
- **Extraction** (`benchmark/metrics/`) produces *candidates*: a value, its period and a citation (form, accession, section, row, column header, verbatim quote).
- **Output** (`app.py`, `export_excel.py`, `export_word.py`). Clicking a cell shows its citation, source text and a find hint ("match 2 of 7"). Excel adds protected Provenance, Exceptions and NAV Trend sheets. Word takes its cell text from the same function as Excel (`export_excel.cell_text`), so every flag and label carries through, and it is stamped with the run ID and code version.

## Validation strategy

There is no answer key for a competitor's filing, so the system can't check its output against the truth. It checks each value against the filing three ways: the number must be found in the filing, it must reconcile with related figures in the same filing, and it must agree with the fund's other filings. Where none of these can confirm a value, the cell says so.

### How a value earns its confidence

**Source order.** Structured sources come first: inline-XBRL tags (Golub), then labeled rows of the filing's own tables, dated by their column headers. Narrative text is used once, for Carlyle's asset-coverage sentence, matched by a fixed pattern. **No language model produces any number.**

**The gate** (`verify.py`). Every candidate passes these checks or is not shown:
1. The cached file's SHA-256 hash is unchanged since download.
2. The quote appears verbatim in the filing's normalized text.
3. The value is the number in the expected column of that quote. The row label is skipped, so a digit in a label can't be mistaken for the value.
4. For a table value, the recorded column header gives the claimed period, and that header actually appears above the row in the filing.
5. For a tagged value, the XBRL element with that id and concept exists and shows that number.

A failed check removes the value. The cell then reads "not verified" with the reason (decision 23). A **computed value** (economic D/E, distribution yield, Cliffwater's coverage note) is built only from inputs that each passed the gate. Each input is cited, and the formula sits next to the result.

**Confidence** (`confidence.score`, `common.computed`; the reason shown with each cell names the rule that fired):

| Level | Read from a filing | Computed from verified inputs |
|---|---|---|
| **High** | Table or XBRL value that either appears unchanged in two or more filings, or passes an independent reconciliation | An independent reported figure agrees (the check) |
| **Medium** | Single structured source with no conflict; or narrative text confirmed by a structured source (never High) | No independent figure exists to compare with |
| **Low** | Reconciliation failed; narrative only; or sources disagree | The check disagrees, or the calculation needs an assumption (for example a debt line taken as zero) |

Low values are always listed in Exceptions. Custom metrics are capped at Medium (`custom_metrics.MAX_CONFIDENCE`, client Window 3): the gate proves a number is in the filing, not that it means what a new definition says.

### Coverage at December 31, 2025

Of the **36 competitor cells** (4 funds × 9 rows), **19 are verified numbers**: 8 High, 11 Medium, 0 Low. Eight of them are computed from verified inputs (four economic D/E, four distribution yields). The other **17 are labeled gaps**, and each is a finding: the fund doesn't report the metric, or the client set a rule.
- **"Not reported by fund" (4).** Carlyle's 3Y: its performance table shows 1-Year, 5-Year and Since Inception only (decision 15). Golub's 3Y and 5Y: Golub reports one fiscal year at a time, and the client ruled out compounding (decision 13). Cliffwater's regulatory leverage: the fund reports asset coverage per facility only, so the computed figure sits in a labeled note (decision 57).
- **"Not applicable" (4).** KREF's 1Y, 3Y and 5Y read "Not applicable: no NAV-based return (REIT reports book value)" (decisions 2, 14). KREF's regulatory leverage reads "Not applicable: KREF is not a 1940 Act fund" (decision 10).
- **Conflict for the PM (1).** Cliffwater's 1Y: 11.78% vs 11.58%, both sources shown and neither selected (decision 56).
- **"Not extracted in v1" (8).** Management and incentive fees for all four funds, each linked to the fee sentence (decisions 20, 45; see Known limitations).

Every cell is listed with its checks in Appendix A.

### Reconciliations run

Each reconciliation tests a value against other figures the fund printed. A pass is what lifts a value to High.

| Reconciliation | Inputs (all verified) | Expected relationship | Result at 12/31/25 | Tolerance |
|---|---|---|---|---|
| Interval-fund NAV roll-forward (every NAV point) | Beginning NAV, total from operations, total distributions, ending NAV: one Class I highlights column | Beginning + operations + distributions = ending | CCLFX 9/30/25: 10.83 + 0.48 − 0.54 = **10.77** = reported. TAKIX FY25: 8.55 + 0.52 − 0.75 = **8.32** = reported. All 8 interval-fund points pass | $0.01 (one printed cent) |
| KREF book value per share (every point) | Common equity, shares outstanding, the table caption's scale ("in thousands") | Equity × scale ÷ shares = book value per share | 844,800 × 1,000 ÷ 64,763,626 = **13.04** = reported; all 8 points pass | $0.01 |
| TAKIX D/E vs its asset coverage | Credit facilities 920,159 + mandatory redeemable preferred 946,446 + note-on-note loans 27,686; net assets 4,782,841; coverage 352.0% (inclusive of preferred) | D/E = 1 ÷ (coverage − 1) | Balance sheet **0.396x** vs implied **0.397x**: agree | 0.05x |
| GBDC D/E vs its asset coverage | Debt 4,903,076; total net assets 3,909,154; coverage 178.94% | Same formula | Balance sheet **1.25x** vs implied **1.27x**: agree (cause of the gap below) | 0.05x |
| KREF D/E vs its own ratio | Secured financing 2,862,689 + CLOs 1,198,332 + term loan 632,516; cash 84,617; equity 1,172,550 | (Debt − cash) ÷ equity = KREF's "Total leverage ratio" | Gross **4.00x** shown. Net of cash **3.93x** vs KREF's **3.9x**: agree | 0.05x (half of KREF's 0.1x printing step) |
| 1Y return across two tables (interval funds) | Performance-table 1Y; same fiscal year's highlights total return | Equal | TAKIX **6.27% = 6.27%**. CCLFX **11.78% vs 11.58%**: disagree, so it becomes a conflict | 0.00 (exact) |
| NAV across filings | Every verified NAV for a period, from every filing in the window | Equal | **11 of the 24 NAV points shown** appear in **2 to 6 filings each**, all agreeing: CCLFX 2, TAKIX 1, GBDC 7, KREF 1. No cross-filing NAV conflict | Exact |

The 0.05x leverage tolerance is half of KREF's rounding step (decision 37). A missing debt line moves D/E by far more than that (Carlyle's preferred alone is 0.20x).

### Where sources disagreed

| Disagreement | Sources | Why they differ, from the filings | Choice, rule, and what the PM sees |
|---|---|---|---|
| **Cliffwater 1Y to 3/31/25:** 11.78% vs 11.58% | Both in N-CSR 0001213900-25-052571: "Average Annual Total Returns as of March 31, 2025" (performance section), and Financial Highlights, Class I, "Total return" (footnote 4) | **Cause unconfirmed.** Footnote 4 on the 11.58% reads, in full: "Total returns would have been lower had expenses not been waived by Cliffwater LLC, the Investment Manager. Returns shown do not reflect the deduction of taxes that a shareholder would pay on Fund distributions or the repurchase of Fund shares." It does not explain a 20 bps difference from 11.78%. The performance text says returns "reflect the reinvestment of distributions". Share class is ruled out: "Only Class I shares have been issued as of March 31, 2025." *Hypothesis:* the two tables use different calculation conventions | No rule applies: recency and amendment can't separate two figures in one filing. The cell reads **"Conflict: PM to choose · as of 3/31/25 · 3Q lag"**, lists both values with citations, selects neither, has no confidence, and is in Exceptions |
| **Golub D/E:** 1.25x vs 1.27x implied by coverage | 10-Q 0001476765-26-000012: balance-sheet "Debt $4,903,076"; Financial Highlights "Asset coverage ratio(7) 178.94%" | Footnote (7) states only the 150% minimum, which excludes SBA debentures, and does not define the debt amount. Footnote (8) measures coverage against "the aggregate amount of senior securities representing indebtedness". The 10-Q says the 4,903,076 "Represents principal outstanding plus unamortized premium and / or unaccreted original issue discount", and is "inclusive of an adjustment for the change in fair value of an effective hedge". The gap fits face amount vs carrying value. *Not reconciled to the dollar*: the implied senior securities are about $4.95bn | Not a conflict: two rows with two definitions. D/E 1.25x (balance-sheet definition, decision 10). Coverage 178.94% with the note "Implies D/E 1.27x". The check passes, so both are High |
| **KREF D/E:** 4.00x vs KREF's 3.9x and 2.2x | 10-K 0001628280-26-005092: balance sheet; MD&A "Debt-to-Equity Ratio and Total Leverage Ratio" | (A) debt-to-equity "excluding non-recourse facilities… less cash". (B) total leverage "total outstanding debt agreements, secured term loan, and collateralized loan obligations, less cash" | The row is total debt ÷ equity (decision 10), so the cell shows 4.00x, labeled "Gross debt". The note carries 2.2x and 3.9x. Our net-of-cash recomputation (3.93x) matches (B). Open item for the client |
| **Golub return:** three measures for one fiscal year | 10-K 0001476765-25-000096: MD&A returns table, footnotes (6), (7), (8); tagged highlights row 9.36% | (6) "net increase (decrease) in net assets resulting from operations divided by… the daily average of total net assets" (9.4%). (7) "net income per share… divided by net asset value per share as of the end of the period" (9.5%). (8) market value with DRIP (0.8%) | None is a NAV total return. Market value is excluded by the NAV-basis rule. The tagged (6) figure is shown as **"Return on average net assets", "Not directly comparable"**, and is never compounded (decision 13) |
| **Cliffwater fiscal year-end** | EDGAR company metadata: 1231. The N-CSR highlights: "Fiscal year end changed to March 31, effective January 1, 2022" | The metadata is stale | Each filing's own period is used (decision 26). A data-quality exception names the mismatch |
| **Apex Ridge 1Y vs compounded quarters** | Client CSV | Compounding four quarters exceeds the reported 1Y by 22 to 28 bps in each of the five quarters checked (Q4 2025: 10.55% vs 10.31%) | The reported figure is official (decisions 11, 22). *Hypothesis, fund accountant to confirm:* the steady gap behaves like a fixed annual cost counted in the 1-year figure only. The footnote and Exceptions say so |

These checks produce the six catches the brief leads with: **KREF is not a BDC**; **Golub's return is a different measure**; **Cliffwater's annual report contradicts itself on its 1-year return**; **Cliffwater does report a 3-year return** (10.69%, against the planning assumption, decision 40); **Apex Ridge's own 1-year return sits 24 bps below its compounded quarters**; and **amended filings are detected** (below).

**Amendments.** Each run checks every fund's EDGAR index for `/A` filings. A value whose source, or any input's source, was amended shows **"Superseded by amendment: re-check"** in the cell, styled red, in all three outputs and in Exceptions (flag-only, approved for v1). The run found four amendments to three older reports: Cliffwater's two to its 9/30/23 report, one to its 6/30/21 report, and one to KREF's 2018 10-K. No value shown cites an amended filing.

### What validation can't catch

- **A verified number that means the wrong thing**: the right digits for the wrong measure, class or period. The gate proves presence, not meaning, and two filings agreeing proves only a consistent reprint. *Mitigations:* per-fund row labels in `config.py`, each with its source; a Class I filter on every interval-fund row; the period re-derived from the column header; cross-checks, since a wrong row rarely reconciles; labels such as "Return on average net assets"; and PM review of every Low.
- **A debt line that should have been summed but wasn't.** *Mitigations:* D/E is checked against the fund's reported coverage (TAKIX, GBDC) or its own ratio (KREF). Cliffwater has no such figure, so its 0.31x stays Medium. A configured debt line absent from the balance sheet is named in the formula, and the value is Low unless a check proves the total. A new, unconfigured kind of debt line would fail the check where one exists. At Cliffwater it would not be caught, and the pilot quarter's side-by-side is the backstop.

### What changed after client review

- **Cliffwater 1Y is now the PM's call.** Our first version chose 11.78% and flagged it. That made the PM's choice for them and broke the Window 1 rule that conflicts are never resolved silently. Now a disagreement between two figures in one report shows both and selects neither (decision 56).
- **Cliffwater's computed asset coverage moved from the cell to a labeled note.** The cell reads "Not reported by fund". The 421.1%, computed from balance-sheet carrying values, appears only as "computed, low confidence", with inputs and formula in the citation panel (decision 57).

**Tests:** 166 automated tests, all passing, run offline on extracts cut verbatim from the real filings. Among them: every shown value passes the gate again, no cell is blank, every competitor cell links to a filing, Word cells match Excel cells, and each fee link targets text found once in its document.

## Key decisions and normalizations

All 77 decisions, with who made them, alternatives and costs, are in `context/decisions.md`; the numbers cited above refer to it. The client confirmed the common quarter-end with lags shown, NAV basis, Class I, the two leverage rows and trailing-12-month distribution yield. River chose deterministic parsers plus a gate over an LLM reading filings, because an LLM can return a plausible number from the wrong share class. **Normalizations**, each shown next to its value: fiscal-year lag, trailing-12-month distributions, Carlyle's preferred shares as debt, and KREF's "Book value per share". No return is annualized or converted from gross to net.

## Known limitations

- **Fee terms are not extracted, because the four management fees are on different bases.** The fee sentences quoted from the cached filings:
  - CCLFX (N-CSRS 0001213900-25-118573): "a monthly Investment Management Fee equal to 1.00% accrued daily, on an annualized basis of the Fund's Net Assets"
  - TAKIX (N-CSR 0001725472-26-000003): "The base management fee is calculated at an annual rate of 1.00% of the Fund's consolidated month-end Managed Assets (such amount not to exceed, in any case, 1.50% of the Fund's net assets)"
  - GBDC (10-Q 0001476765-26-000012): "The base management fee is calculated at an annual rate equal to 1.0% (or 1.375% for periods ending on or before June 30, 2023) of the fair value of the average adjusted gross assets of the Company"
  - KREF (10-K 0001628280-26-005092): "a quarterly management fee equal to the greater of $62,500 or 0.375% of weighted average adjusted equity"

  Net assets, managed assets, gross assets and adjusted equity: a row of "1.00%" would look comparable when it is not. So v1 shows "Not extracted in v1" and links to the fee sentence, using a URL text fragment of words that occur once in the document. Each link was clicked in a real browser and lands within Dana's two-scroll limit. Normalizing fees to a common basis is next phase.
- **Parsing is tuned to these four funds.** A reworded label gives a labeled gap, not a wrong value.
- **Interval funds report NAV semi-annually:** four trend points of eight; the rest are labeled gaps.
- **HTML filings have no page numbers.** Every link carries a text fragment that lands on the cited row or quote (or the nearest unique text above it, with a find hint counted ignoring case); a test checks every exported link's fragment text is in the cached filing. One citation (KREF cash, a check input) has no unique text nearby and opens the filing with its hint. The Word report adds a NAV trend section (every point, gaps labeled) and a footer with run ID and code version on every page.

## Scope change: what shipped and what is designed

Dana accepted the scoping in Window 3 and ranked Word first. Word shipped. **Custom metrics:** the definitions file (`benchmark/custom_metrics.json`, loaded and saved by `custom_metrics.py`) exists, with portfolio turnover as the worked example. Nine fields are required, including what the metric measures, its unit, its source shape (table row, XBRL tag or ratio), normalization assumptions and owner. A definition with a missing field is rejected, and the error names every gap. Wiring definitions into extraction (one extractor per source shape, feeding the same gate) is next phase. **Fund browser (design only):** search EDGAR by name, ticker or CIK. Only supported types (interval fund, BDC, mortgage REIT) can be added; others show "Not yet supported". Each new type is roughly a day of setup and tests (River's estimate).

## Production risks and rollout

Dana named two ways this fails. **A citation that doesn't lead to its number:** every run re-verifies every citation against the cached filing, and tests check that every cell links and that fee links target unique text. **Any step that looks like IT work:** the analyst only opens the page and clicks. Other risks: a relabeled row gives a labeled gap that Exceptions names, fixed with one `config.py` entry and a test extract. An EDGAR failure stops only that fund's column, and cached reruns work offline. Key-person dependence is covered by `config.py` (every constant sourced), `docs/CODE_TOUR.md`, the decision log and tests.

**Rollout:** (1) a pilot quarter in parallel with the manual process, with every difference resolved; (2) hosting (a link or one-click launcher), decided with Apex Ridge's operations lead, whom Dana offered to introduce; (3) custom metrics, then the fund browser; (4) fee extraction and normalization, automatic amendment re-pull, PM sign-off in the tool.

## Open items for next client review

Cliffwater returns shown with their 3-quarter lag (decisions 4, 39). KREF economic leverage on gross debt (4.00x). The turnover rule "never annualize a not-annualized figure by scaling" is Proposed (Aman), not yet a client decision. Still with the client: whether KREF stays in the peer set (the CIO's call), and who owns each custom-metric definition.

## Appendix A: Per-value validation at December 31, 2025

Gate checks: **H** = file hash unchanged; **Q** = quote verbatim; **C** = value in expected column; **P** = column header gives the period; **X** = XBRL element shows the number. "Computed" means every input passed its own gate. Fee rows cover two cells each (management and incentive).

| Fund | Row | Shown | Source | Checks | Reconciliation | Confidence: reason |
|---|---|---|---|---|---|---|
| CCLFX | 1Y | Conflict: PM to choose (11.78% / 11.58%) · 3/31/25 | Two table rows, N-CSR 0001213900-25-052571 | H Q C P (both) | Performance vs highlights: disagree | None: two figures in one filing; PM chooses |
| CCLFX | 3Y | 10.69% · 3/31/25 | Table row (performance) | H Q C P | None available | Medium: single structured source |
| CCLFX | 5Y | 10.98% · 3/31/25 | Table row (performance) | H Q C P | None available | Medium: single structured source |
| CCLFX | Fees | Not extracted in v1 | Narrative link, N-CSRS 0001213900-25-118573 (incentive: N-CSR, no incentive terms stated) | Sentence located in cached file | — | Gap: fees not extracted (decision 20) |
| CCLFX | NAV per share | $10.77 · 9/30/25 | Table row (highlights, Class I) | H Q C P | NAV roll-forward exact | High: roll-forward passed |
| CCLFX | Economic D/E | 0.31x · 9/30/25 | Computed (3 debt rows ÷ net assets) | Inputs H Q C P | None: no fund-level figure | Medium: no independent figure |
| CCLFX | Asset coverage | Not reported by fund (note: 421.1% computed, low) | Gap; note computed from balance sheet | Inputs H Q C P | — | Gap: per-facility only (decision 57) |
| CCLFX | Distribution yield | 10.58% · 9/30/25 | Computed (0.54 + 0.90 − 0.30) ÷ 10.77 | Inputs H Q C P | None | Medium: no independent figure |
| TAKIX | 1Y | 6.27% | Table row (performance) | H Q C P | Highlights 6.27%: agree | High: independent check passed |
| TAKIX | 3Y | Not reported by fund | Gap; links the performance table | — | — | Gap: table shows 1Y, 5Y, since inception (decision 15) |
| TAKIX | 5Y | 8.21% | Table row (performance) | H Q C P | None available | Medium: single structured source |
| TAKIX | Fees | Not extracted in v1 | Narrative link, N-CSR 0001725472-26-000003 | Sentence located | — | Gap (decision 20) |
| TAKIX | NAV per share | $8.32 | Table row (highlights, Class I) | H Q C P | NAV roll-forward exact | High: roll-forward passed |
| TAKIX | Economic D/E | 0.40x | Computed (facilities + preferred + note-on-note ÷ net assets) | Inputs H Q C P | Implied by 352.0%: 0.397x vs 0.396x | High: check passed |
| TAKIX | Asset coverage | 352.0% | Narrative sentence, Note 7 | H Q (value in sentence; date in sentence matched) | Balance-sheet D/E agrees | Medium: narrative confirmed by structured source |
| TAKIX | Distribution yield | 9.01% | Computed 0.75 ÷ 8.32 (fiscal year = calendar year) | Inputs H Q C P | None | Medium: no independent figure |
| GBDC | 1Y | Return on average net assets 9.36% · FY to 9/30/25, not directly comparable | XBRL tag, 10-K 0001476765-25-000096 | H Q X | None available | Medium: single structured source |
| GBDC | 3Y | Not reported by fund | Gap | — | — | Gap: one fiscal year at a time; no compounding (decision 13) |
| GBDC | 5Y | Not reported by fund | Gap | — | — | Gap: as 3Y |
| GBDC | Fees | Not extracted in v1 | Narrative link, 10-Q 0001476765-26-000012 | Sentence located | — | Gap (decision 20) |
| GBDC | NAV per share | $14.84 | XBRL tag, 10-Q 0001476765-26-000012 | H Q X | Only one filing covers 12/31/25 so far | Medium: single structured source |
| GBDC | Economic D/E | 1.25x | Computed (Debt ÷ total net assets) | Inputs H Q C P | Implied by 178.94%: 1.27x, within 0.05x | High: check passed |
| GBDC | Asset coverage | 178.94% | XBRL tag (highlights) | H Q X | Balance-sheet D/E agrees | High: check passed |
| GBDC | Distribution yield | 10.51% | Computed (0.39 + 1.65 − 0.48) ÷ 14.84 | Inputs H Q X | None | Medium: no independent figure |
| KREF | 1Y / 3Y / 5Y | Not applicable: no NAV-based return (REIT reports book value) | Gap (3 cells); links the 10-K | — | — | Gap: NAV basis rule (decisions 2, 14) |
| KREF | Fees | Not extracted in v1 | Narrative link, 10-K 0001628280-26-005092 | Sentence located | — | Gap (decision 20) |
| KREF | Book value per share | $13.04 | Table row (MD&A) | H Q C P | Equity × scale ÷ shares exact | High: check passed |
| KREF | Economic D/E | 4.00x (gross debt) | Computed (3 debt rows ÷ equity) | Inputs H Q C P | Net of cash 3.93x vs KREF's 3.9x | High: check passed |
| KREF | Asset coverage | Not applicable: KREF is not a 1940 Act fund | Gap; note cites KREF's 2.2x and 3.9x | Note values H Q C P | — | Gap (decision 10) |
| KREF | Distribution yield | 7.67% on book value | Computed 1.00 ÷ 13.04 | Inputs H Q C P | None | Medium: no independent figure |

The fee sentences are located in, and quoted from, the hashed cached file. They are not passed through the numeric gate, because no fee value is shown.

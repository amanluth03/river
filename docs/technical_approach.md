# Technical approach: Apex Ridge peer benchmarking

*For Apex Ridge's technical counterpart. Prepared by River Technologies. Figures are as of December 31, 2025.*

## 1. What the system does

On a local review page, the analyst picks a quarter-end and presses **Run**. The system downloads each competitor's SEC filings for the eight quarters up to that date, extracts the board-deck metrics, checks each value against its filing, and places them beside Apex Ridge's own data. Outputs: the page, an Excel workbook in the deck's layout and a Word report, every cell with a confidence level and a source link. In v1 the page is started with one command (`uv run benchmark`), so River starts it during the pilot (section 7).

The governing rule: **a gap beats a wrong number**. A value is shown only if the system can prove it is in the filing; otherwise the cell is a labeled gap with the reason, such as "Not reported by fund" or "Not extracted in v1". No cell is blank or estimated.

## 2. Architecture and data flow

```
EDGAR index ─► filing list ─► download + cache ─► extract ─► verification gate ─► resolve conflicts ─► confidence ─► page / Excel / Word
```

- **Retrieval** (`edgar.py`, `filings.py`, `cache.py`). Every document is cached by accession number with a SHA-256 hash, so reruns are fast, offline and reproducible. Periods come from each filing, never company metadata (Cliffwater's EDGAR record has the wrong year-end).
- **Extraction**, in order of reliability: (1) inline-XBRL tags (Golub); (2) labeled rows in the filing's own tables, dated by their column headers; (3) one narrative sentence (Carlyle's asset coverage), matched by a fixed pattern. No language model produces any number in v1.
- **The verification gate** (`verify.py`) runs on every candidate: the cached file's hash is unchanged, the quote appears verbatim, the number in the quote equals the value, the column header gives the claimed period, and any XBRL element exists with that number. A value that fails is not shown; the cell says "not verified" and why.
- **Computed values** (economic leverage, distribution yield, Cliffwater's coverage note) use only inputs that each passed the gate, each cited; the formula sits next to the value.
- **Output** (`app.py`, `export_excel.py`, `export_word.py`). Clicking a cell shows filing, accession number, section, row, column header, source text and a find hint ("match 2 of 7"). The **Excel** adds protected Provenance, Exceptions and NAV Trend sheets. The **Word** report (deck table, footnotes, exceptions, provenance appendix) is built from the same run. All three take cell text from one function (`export_excel.cell_text`), so conflict flags, lag labels, computed notation and amendment flags carry through, and every competitor cell links to its filing. Word can't be locked, so it is labeled "Generated report" and stamped with the run ID (the run's folder name under `runs/`, holding its `bundle.json`), run time and code version.

## 3. Key decisions and reasoning

The full log, with alternatives and costs, is `context/decisions.md` (75 rows). The ones that shape the output:

| Decision | Reason |
|---|---|
| Common quarter-end; each fund's latest report for a period ending on or before it, lag shown; NAV basis; Class I | Confirmed by Dana |
| Golub: "Return on average net assets", "Not directly comparable", not compounded into 3Y/5Y | Confirmed by Dana |
| Two leverage rows: economic D/E (total debt incl. mandatory redeemable preferred ÷ net assets) and regulatory asset coverage **as reported** | Format approved by Dana |
| Same-report conflict: both shown, nothing selected; a computed figure never fills a "reported" row | Client decisions, Window 3 |
| Distribution yield = trailing 12 months ÷ period-end NAV, from reported pieces only (e.g. six months + fiscal year − prior six months), each cited | Confirmed by Dana |
| Reported trailing returns with their lag, never chained semi-annual returns | A reported number beats one computed with a reinvestment assumption |
| Deterministic parsers plus a gate, not an LLM reading filings | An LLM can return a plausible number from the wrong share class |

**Normalizations** (each shown next to the value): fiscal-year lag; trailing-12-month distributions; Carlyle's preferred shares as debt; KREF's "Book value per share". No return is annualized or converted from gross to net.

## 4. Validation strategy and confidence model

**Confidence** (each cell's reason names the rule that fired):
- **High:** verified and independently confirmed (another filing, a reconciliation, or a fund-reported figure that agrees with our computation).
- **Medium:** verified, single source; or computed with nothing independent to compare against.
- **Low:** a check failed, narrative-only, or computed with an assumption. Listed in Exceptions.

**Cross-checks:**

| Value | Check |
|---|---|
| Interval-fund NAV | Beginning NAV + operations + distributions = ending NAV, to the cent |
| KREF book value per share ($13.04) | Equity × stated scale ÷ shares |
| Carlyle D/E 0.40x | Equals the D/E implied by its reported 352.0% coverage |
| Golub D/E 1.25x | Within 0.05x of the 1.27x implied by 178.94% coverage |
| KREF D/E 4.00x gross | Net of cash 3.93x, agreeing with KREF's reported 3.9x |
| Every 1Y return | Compared with the same year in the financial highlights (Carlyle's 6.27% agrees) |

**Where sources disagreed:**
- **Cliffwater 1Y to 3/31/25:** 11.78% in the performance table, 11.58% in the financial highlights of the same report. Our first version chose 11.78% and flagged it, which made the PM's choice for them and broke the Window 1 rule that conflicts are never resolved silently. The system now refuses to choose on any same-report conflict: the cell reads **"Conflict: PM to choose"**, lists both values with citations, selects neither, and appears in Exceptions.
- **Cliffwater asset coverage** is reported per facility only. The cell reads **"Not reported by fund"**; the fund-level 421.1% computed from the balance sheet appears only in a note, "computed, low confidence", with inputs and formula in the citation panel.
- **Apex Ridge 1Y:** compounding the quarterly returns gives 22 to 28 bps more than the reported 1Y every quarter (Q4 2025: 10.55% vs 10.31%). The reported figure is official; the footnote says the steady gap behaves like a fixed annual cost counted in one figure only, fund accountant to confirm.

**Amendments:** each run checks every fund's EDGAR index for `/A` filings. A value whose source, or any input's source, was amended shows **"Superseded by amendment: re-check"** in the cell itself, styled red, on the page, in Excel and in Word, and is listed in Exceptions. The analyst re-pulls (flag-only approved for v1 in Window 3). Cliffwater's two amendments to its 9/30/23 report are detected; no value shown at 12/31/25 cites an amended filing.

**Tests:** 160 automated tests, all passing, run offline on extracts cut verbatim from the real filings. Among them: every shown value passes the gate again, no cell is blank, one fund failing doesn't stop the run, every competitor cell links to a filing, Word cells match Excel cells, and each fee link targets text found once in its document.

**Result at 12/31/25:**

| Row | CCLFX | TAKIX | GBDC | KREF |
|---|---|---|---|---|
| NAV per share | $10.77 (9/30/25) High | $8.32 High | $14.84 Medium | Book value per share $13.04 High |
| Economic D/E | 0.31x (9/30/25) Medium | 0.40x High | 1.25x High | 4.00x High |
| Asset coverage | Not reported by fund (note: 421.1%, computed, low confidence) | 352.0% Medium | 178.94% High | Not applicable: KREF is not a 1940 Act fund |
| Distribution yield (all Medium) | 10.58% (9/30/25) | 9.01% | 10.51% | 7.67% on book value |
| Returns 1Y / 3Y / 5Y | Conflict: PM to choose (11.78% / 11.58%) / 10.69% / 10.98% (3/31/25) | 6.27% High / Not reported by fund / 8.21% | Return on average net assets 9.36% (FY to 9/30/25), not directly comparable | Not applicable (no NAV) |

## 5. Known limitations

- **Fee terms are not extracted.** The cell reads "Not extracted in v1" and links into the latest annual report or 10-K, which Dana accepted if it lands within two scrolls of the fee sentence. Each link is a URL text fragment of words that occur once in the document (fallback: the nearest anchor before it); all four were clicked in a real browser and open with the sentence highlighted about half a screen down. Fragments need a current browser and a click.
- **Parsing is tuned to these four funds;** a reworded label gives a labeled gap, not a wrong value. **Cliffwater's D/E** has no independent cross-check, so it is Medium.
- **Interval funds report NAV semi-annually:** four trend points of eight; the rest are labeled gaps.
- **HTML filings have no page numbers;** citations use section, row, column and a find hint.

## 6. Scope change: what shipped and what is designed

Apex Ridge asked for Word output, custom metrics and a fund browser. In Window 3 Dana accepted the scoping and constraints and ranked Word first. Word shipped (section 2); the others are next phase.

**Custom metrics: definitions built, not wired into extraction.** `benchmark/custom_metrics.json` holds definitions; `benchmark/custom_metrics.py` loads and saves them. Nine fields are required, including what it measures, unit, source shape (table row, XBRL tag or ratio of two metrics), normalization assumptions, owner and cited example sources. Loading or saving fails if any is missing, naming every gap, and a failed save writes nothing. The example is portfolio turnover (Cliffwater's is not annualized, Golub's is; the labels say so). Wiring means one extractor per source shape feeding the same gate. New metrics are capped at Medium confidence: the gate proves a number is in the filing, not that it means what the definition says.

**Fund browser (design only).** Search EDGAR by name, ticker or CIK and show each fund's latest filings. "Add to peer set" appears only for types the parsers support (interval fund, BDC, mortgage REIT); others show "Not yet supported", never empty columns. Each new type needs its own setup and tests, roughly a day (River's estimate).

## 7. Production risks and rollout

Dana named two ways this fails. **A citation that doesn't lead to its number:** every run re-verifies every citation against the cached filing, tests check that links are present and fee links target unique text, and each fee link was clicked in a real browser. **Any step that looks like IT work:** the analyst only opens the page and clicks, with nothing to edit. Today the page is started with `uv run benchmark`, so River starts it during the pilot.

**Rollout:** (1) one pilot quarter in parallel with the manual process, every difference resolved; (2) production hosting, a link or one-click launcher, decided with Apex Ridge's operations lead (vendor approvals with compliance and IT), whom Dana offered to introduce; (3) custom metrics wired into extraction, then the fund browser; (4) fee extraction, automatic amendment re-pull, PM sign-off in the tool.

| Risk | Mitigation |
|---|---|
| A fund changes a label or layout | Labeled gap; Exceptions names the row. Fix: one `config.py` entry plus a test extract |
| A debt line is not summed | Coverage cross-check drops the value to Low |
| EDGAR outage | Retries; a failure stops only that fund's column; cached reruns work offline |
| Key-person dependence | `config.py` (every constant sourced), `docs/CODE_TOUR.md`, decision log, tests on real values |

## 8. Open questions for the client

Raised in Window 3 and not overruled, to confirm explicitly: lagged figures shown with their lag (Cliffwater returns as of 3/31/25), and KREF D/E on gross debt (4.00x) with its own 3.9x net of cash in the note. Still open: whether KREF stays in the peer set (the CIO's call), and who at Apex Ridge owns each custom-metric definition.

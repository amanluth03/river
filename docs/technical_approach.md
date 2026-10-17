# Technical approach: Apex Ridge peer benchmarking

*For Apex Ridge's technical counterpart. Prepared by River Technologies. Figures are from the run as of December 31, 2025. Appendices A to D, with the full validation tables, are in [docs/validation_appendix.md](validation_appendix.md).*

## What the system does

On a local review page, the analyst picks a quarter-end and presses **Run**. The system downloads each competitor's SEC filings for the eight quarters up to that date, extracts the board-deck metrics, checks each value against its filing, and places them beside Apex Ridge's own data. Outputs: the page, a protected Excel workbook in the deck's layout and a Word report, with a confidence level and source link on every cell. The governing rule: **a gap beats a wrong number**. A value is shown only if the system can prove it is in the filing; otherwise the cell is a labeled gap with the reason. No cell is blank or estimated.

```
EDGAR index ─► filing list ─► download + cache ─► extract ─► verification gate ─► resolve conflicts ─► confidence ─► page / Excel / Word
```

- **Retrieval** (`edgar.py`, `cache.py`): filings are cached by accession number with a SHA-256 hash, so reruns are offline and reproducible. Periods come from each filing, never from company metadata.
- **Extraction** (`benchmark/metrics/`): candidates, each a value, period and citation (form, accession, section, row, column header, quote).
- **Output** (`export_excel.py`, `export_word.py`): Excel and Word share one cell-text function, so every flag carries through; both carry the run ID and code version.

## Validation strategy

There is no answer key for a competitor's filing, so each value is checked against the filing three ways: the number must be found in it, it must reconcile with related figures in the same filing, and it must agree with the fund's other filings. Where none of these can confirm a value, the cell says so.

**Source order.** Inline-XBRL tags first (Golub), then labeled rows of the filing's own tables, dated by their column headers. Narrative text is used once, for Carlyle's asset-coverage sentence, matched by a fixed pattern. **No language model produces any number.**

**The gate** (`verify.py`). A candidate is shown only if it passes every check:

1. The cached file's SHA-256 hash is unchanged since download.
2. The quote appears verbatim in the filing's normalized text.
3. The value is the number in the expected column of that quote, with the row label skipped so a digit in a label can't be mistaken for the value.
4. For a table value, the column header gives the claimed period and appears above the row in the filing.
5. For a tagged value, the XBRL element with that id and concept exists and shows that number.

A **computed value** (economic D/E, distribution yield, Cliffwater's coverage note) is built only from inputs that each passed the gate, each cited, with the formula next to the result.

**Confidence:**

| Level | Read from a filing | Computed from verified inputs |
|---|---|---|
| **High** | Appears unchanged in two or more filings, or passes an independent reconciliation | An independent reported figure agrees |
| **Medium** | Single structured source with no conflict; or narrative confirmed by a structured source | No independent figure exists to compare with |
| **Low** | Reconciliation failed; narrative only; or sources disagree | The check disagrees, or the calculation needs an assumption |

Low values are always listed in Exceptions. Custom metrics are capped at Medium: the gate proves a number is in the filing, not that it means what a new definition says.

**Coverage.** Of the **36 competitor cells**, **19 are verified numbers** (8 High, 11 Medium, 0 Low), eight of them computed from verified inputs. The other **17 are labeled gaps**, each a finding: 4 "Not reported by fund" (Carlyle's 3Y, Golub's 3Y and 5Y, Cliffwater's fund-level asset coverage); 4 "Not applicable" (KREF's three returns, since a REIT has no NAV, and its regulatory leverage, since it is not a 1940 Act fund); 1 conflict for the PM (Cliffwater's 1Y); and 8 fee cells "Not extracted in v1". Appendix C lists every cell with its checks.

**Reconciliations** (Appendix A). Every interval-fund NAV point rolls forward to the cent (beginning NAV + operations + distributions = ending NAV), and KREF's book value equals equity ÷ shares at every point. Carlyle's and Golub's balance-sheet D/E agree with the D/E implied by their reported asset coverage (0.396x vs 0.397x; 1.25x vs 1.27x), and KREF's D/E net of cash (3.93x) matches its own 3.9x. Eleven of the 24 NAV points shown appear in 2 to 6 filings each, all agreeing. One check failed: Cliffwater's 1Y.

**Where sources disagreed** (Appendix B, with quotes). Each cause is taken from the filings' own wording, or labeled a hypothesis.

- **Cliffwater 1Y: 11.78% vs 11.58% in one N-CSR.** Cause unconfirmed (footnote 4 covers only waivers and taxes; share class is ruled out), so both are shown and the PM chooses.
- **Golub D/E: 1.25x vs 1.27x implied by coverage.** Balance-sheet debt is carrying value; coverage uses senior securities. Within tolerance, not reconciled to the dollar.
- **KREF D/E: 4.00x vs its own 3.9x and 2.2x.** KREF nets cash (and, for 2.2x, non-recourse debt); the row is total debt ÷ equity, with KREF's figures in the note.
- **Golub return: three measures, none a NAV total return.** Shown as "Return on average net assets", "Not directly comparable", never compounded.
- **Cliffwater fiscal year-end:** EDGAR metadata says December, the filings March; each filing's own period is used.
- **Apex Ridge 1Y vs compounded quarters:** a steady 22 to 28 bps gap. The reported figure is official; the cause is a hypothesis for the fund accountant.

**Amendments.** Each run checks every fund's EDGAR index for `/A` filings; a value whose source or any input was amended shows **"Superseded by amendment: re-check"** in the cell in all three outputs. The run found four amendments to three older reports, none behind a value shown.

**What validation can't catch.** A verified number that means the wrong thing: the gate proves presence, not meaning, so row labels are configured per fund, rows are filtered to Class I, and every Low goes to the PM. A missed debt line: D/E is checked against reported coverage or the fund's own ratio where one exists; Cliffwater has neither, so its 0.31x stays Medium.

**What changed after client review.** Our first version chose Cliffwater's 11.78% and flagged it, making the PM's choice for them and breaking the agreed rule that conflicts are never resolved silently; it now shows both and selects neither. Its computed 421.1% asset coverage moved from the cell to a labeled note.

**Tests:** 187 automated tests run offline on verbatim extracts of the real filings, including: every shown value re-passes the gate, no cell is blank, every cell links to a filing, and Word cells match Excel cells.

## Decisions, normalizations and limits

Every decision, with owner, alternatives and cost, is in `context/decisions.md`. The client confirmed the common quarter-end with lags shown, NAV basis, Class I, the two leverage rows and trailing-12-month yield. River chose deterministic parsers plus a gate over an LLM reading filings, because an LLM can return a plausible number from the wrong share class. No return is annualized or converted from gross to net.

- **Fees are not extracted, because the four management fees are on different bases**: net assets, managed assets, gross assets and adjusted equity (Appendix D). A row of "1.00%" would look comparable when it is not, so v1 links each cell to the fee sentence. The four management-fee links were clicked in a real browser and land within the two-scroll limit.
- **Parsing is tuned to these four funds.** A reworded label gives a labeled gap, not a wrong value.
- **HTML filings have no page numbers.** Every link lands on its source text: the row label or quote when it is unique in the filing, else the nearest unique text above the row, with a find hint; a test checks each link's target text is in the cached filing. One check input (KREF cash) has no unique text nearby and opens the filing with its hint.

## Scope change, risks and rollout

Word shipped in full, Dana's first priority. **Custom metrics:** the definitions file exists, with portfolio turnover as the example; a definition missing a required field (what it measures, unit, source, normalization, owner) is rejected, and wiring definitions into extraction is next phase. **Fund browser (design only):** search EDGAR by name, ticker or CIK; unsupported fund types show "Not yet supported".

Dana named two ways this fails. A broken citation: every run re-verifies every citation against the cached filing. Anything that looks like IT work: the analyst only opens the page and clicks; River starts the page during the pilot, and production access (a link or one-click launcher) is decided with Apex Ridge's operations lead.

**Rollout:** a pilot quarter in parallel with the manual process; hosting with the operations lead; custom metrics, then the fund browser; then fee normalization, automatic amendment re-pull and PM sign-off in the tool. **Open items for the client:** Cliffwater's returns shown with a 3-quarter lag; KREF leverage on gross debt; the Proposed turnover rule (never annualize a not-annualized figure by scaling); whether KREF stays in the peer set; and who owns each custom-metric definition.

# Validation appendix: Apex Ridge peer benchmarking

## Appendix A: Reconciliations run

| Reconciliation | Inputs (all verified) | Expected relationship | Result at 12/31/25 | Tolerance |
|---|---|---|---|---|
| Interval-fund NAV roll-forward (every NAV point) | Beginning NAV, total from operations, total distributions, ending NAV: one Class I highlights column | Beginning + operations + distributions = ending | CCLFX 9/30/25: 10.83 + 0.48 − 0.54 = **10.77** = reported. TAKIX FY25: 8.55 + 0.52 − 0.75 = **8.32** = reported. All 8 interval-fund points pass | $0.01 (one printed cent) |
| KREF book value per share (every point) | Common equity, shares outstanding, the table caption's scale ("in thousands") | Equity × scale ÷ shares = book value per share | 844,800 × 1,000 ÷ 64,763,626 = **13.04** = reported; all 8 points pass | $0.01 |
| TAKIX D/E vs its asset coverage | Credit facilities 920,159 + mandatory redeemable preferred 946,446 + note-on-note loans 27,686; net assets 4,782,841; coverage 352.0% (inclusive of preferred) | D/E = 1 ÷ (coverage − 1) | Balance sheet **0.396x** vs implied **0.397x**: agree | 0.05x |
| GBDC D/E vs its asset coverage | Debt 4,903,076; total net assets 3,909,154; coverage 178.94% | Same formula | Balance sheet **1.25x** vs implied **1.27x**: agree (see Appendix B) | 0.05x |
| KREF D/E vs its own ratio | Secured financing 2,862,689 + CLOs 1,198,332 + term loan 632,516; cash 84,617; equity 1,172,550 | (Debt − cash) ÷ equity = KREF's "Total leverage ratio" | Gross **4.00x** shown. Net of cash **3.93x** vs KREF's **3.9x**: agree | 0.05x (half of KREF's 0.1x printing step) |
| 1Y return across two tables (interval funds) | Performance-table 1Y; same fiscal year's highlights total return | Equal | TAKIX **6.27% = 6.27%**. CCLFX **11.78% vs 11.58%**: disagree, so it becomes a conflict | 0.00 (exact) |
| NAV across filings | Every verified NAV for a period, from every filing in the window | Equal | **11 of the 24 NAV points shown** appear in **2 to 6 filings each**, all agreeing: CCLFX 2, TAKIX 1, GBDC 7, KREF 1. No cross-filing NAV conflict | Exact |

The 0.05x leverage tolerance is half of KREF's rounding step (decision 37). A missing debt line moves D/E by far more than that (Carlyle's preferred alone is 0.20x).

## Appendix B: Where sources disagreed

| Disagreement | Sources | Why they differ, from the filings | Choice, rule, and what the PM sees |
|---|---|---|---|
| **Cliffwater 1Y to 3/31/25:** 11.78% vs 11.58% | Both in N-CSR 0001213900-25-052571: "Average Annual Total Returns as of March 31, 2025" (performance section), and Financial Highlights, Class I, "Total return" (footnote 4) | **Cause unconfirmed.** Footnote 4 says only that returns "would have been lower had expenses not been waived" and exclude taxes. The performance text says returns "reflect the reinvestment of distributions". Share class is ruled out: "Only Class I shares have been issued as of March 31, 2025." *Hypothesis:* the two tables use different calculation conventions | No rule applies: recency and amendment can't separate two figures in one filing. The cell reads **"Conflict: PM to choose · as of 3/31/25 · 3Q lag"**, lists both values with citations, selects neither, has no confidence, and is in Exceptions |
| **Golub D/E:** 1.25x vs 1.27x implied by coverage | 10-Q 0001476765-26-000012: balance-sheet "Debt $4,903,076"; Financial Highlights "Asset coverage ratio(7) 178.94%" | Footnote (7) states only the 150% minimum, which excludes SBA debentures, and does not define the debt amount. Footnote (8) measures coverage against "the aggregate amount of senior securities representing indebtedness". The 10-Q says the 4,903,076 "Represents principal outstanding plus unamortized premium and / or unaccreted original issue discount", and is "inclusive of an adjustment for the change in fair value of an effective hedge". The gap fits face amount vs carrying value. *Not reconciled to the dollar*: the implied senior securities are about $4.95bn | Not a conflict: two rows with two definitions. D/E 1.25x (balance-sheet definition, decision 10). Coverage 178.94% with the note "Implies D/E 1.27x". The check passes, so both are High |
| **KREF D/E:** 4.00x vs KREF's 3.9x and 2.2x | 10-K 0001628280-26-005092: balance sheet; MD&A "Debt-to-Equity Ratio and Total Leverage Ratio" | (A) debt-to-equity "excluding non-recourse facilities… less cash". (B) total leverage "total outstanding debt agreements, secured term loan, and collateralized loan obligations, less cash" | The row is total debt ÷ equity (decision 10), so the cell shows 4.00x, labeled "Gross debt". The note carries 2.2x and 3.9x. Our net-of-cash recomputation (3.93x) matches (B). Open item for the client |
| **Golub return:** three measures for one fiscal year | 10-K 0001476765-25-000096: MD&A returns table, footnotes (6), (7), (8); tagged highlights row 9.36% | (6) "net increase (decrease) in net assets resulting from operations divided by… the daily average of total net assets" (9.4%). (7) "net income per share… divided by net asset value per share as of the end of the period" (9.5%). (8) market value with DRIP (0.8%) | None is a NAV total return. Market value is excluded by the NAV-basis rule. The tagged (6) figure is shown as **"Return on average net assets", "Not directly comparable"**, and is never compounded (decision 13) |
| **Cliffwater fiscal year-end** | EDGAR company metadata: 1231. The N-CSR highlights: "Fiscal year end changed to March 31, effective January 1, 2022" | The metadata is stale | Each filing's own period is used (decision 26). A data-quality exception names the mismatch |
| **Apex Ridge 1Y vs compounded quarters** | Client CSV | Compounding four quarters exceeds the reported 1Y by 22 to 28 bps in each of the five quarters checked (Q4 2025: 10.55% vs 10.31%) | The reported figure is official (decisions 11, 22). *Hypothesis, fund accountant to confirm:* the steady gap behaves like a fixed annual cost counted in the 1-year figure only. The footnote and Exceptions say so |

## Appendix C: Per-value validation at December 31, 2025

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

## Appendix D: Management-fee sentences

Quoted from the cached filings. The bases differ, which is why v1 shows no single fee number.

- **CCLFX** (N-CSRS 0001213900-25-118573): "a monthly Investment Management Fee equal to 1.00% accrued daily, on an annualized basis of the Fund's Net Assets"
- **TAKIX** (N-CSR 0001725472-26-000003): "The base management fee is calculated at an annual rate of 1.00% of the Fund's consolidated month-end Managed Assets (such amount not to exceed, in any case, 1.50% of the Fund's net assets)"
- **GBDC** (10-Q 0001476765-26-000012): "The base management fee is calculated at an annual rate equal to 1.0% (or 1.375% for periods ending on or before June 30, 2023) of the fair value of the average adjusted gross assets of the Company"
- **KREF** (10-K 0001628280-26-005092): "a quarterly management fee equal to the greater of $62,500 or 0.375% of weighted average adjusted equity"

# Build log

Short entries, newest at the bottom. Findings include fund, form, accession number and values.
Tags: **DONE** finished · **FIND** data/filing surprise · **ASSUME** assumption · **BLOCK** blocker.

## 2026-10-16 — Hour 0: discovery (no product code yet)

- **DONE** Read brief, Window 1 transcript, starter package (`apex-ridge-starter/`). Moved notes into `context/` to match CLAUDE.md (`handoff_notes.md`, `window1_transcript.md`, `decisions.md`).
- **DONE** Research: incumbents (Daloopa, Hebbia, AlphaSense, Capital IQ, Morningstar, Preqin, Blue Vault, Canoe) and tooling (edgartools, data.sec.gov companyfacts, Claude Citations API). Nobody found offers cited, verified, fund-level metrics for interval funds.
- **BLOCK→resolved** System `python3` fails (Xcode license not accepted). Using `uv run --python 3.12`.
- **FIND** CCLFX fiscal year-end conflict. EDGAR submissions metadata says `fiscalYearEnd=1231`; the filings say Mar 31: N-CSR 0001213900-25-052571 (period 2025-03-31), N-CSR 0001213900-26-066324 (period 2026-03-31). Trust the filings' period dates, not the metadata.
- **FIND** CCLFX latest period ≤ 2025-12-31 is N-CSRS 0001213900-25-118573 (period 2025-09-30, filed 2025-12-05). One-quarter lag vs. as-of date.
- **FIND** CCLFX has two amendments to the same semi-annual: N-CSRS/A 0001213900-24-027119 (filed 2024-03-28) and 0001213900-24-034098 (filed 2024-04-18), both period 2023-09-30. Just outside the 8-quarter window, but a live test case for "amendment supersedes, later amendment wins".
- **FIND** TAKIX N-CSR 0001725472-26-000003 (period 2025-12-31, filed 2026-02-27, doc `ctac-20251231.htm`). Inline XBRL only tags `cef:` senior-securities items (15× `SeniorSecuritiesCvgPerUnit`, 15× `SeniorSecuritiesAmt`) plus text blocks. NAV/share, returns and distributions are untagged HTML. Financial highlights appear 7 times (one per share class); need Class I only. "Average Annual Total Returns through December 31, 2025" table present.
- **FIND** CCLFX and TAKIX companyfacts are near-empty (6 and 5 `cef` keys). Interval funds aren't covered by the tailored-shareholder-report XBRL rule (open-end only). Expect HTML table parsing for NAV, returns, distributions.
- **FIND** GBDC: rich us-gaap XBRL incl. `NetAssetValuePerShare`, `InvestmentCompanyTotalReturn`, `InvestmentCompanyTotalReturnMarketValue` (separate tag; verified below: the first is "based on average net asset value", not a standard NAV total return), `InvestmentCompanySeniorSecurityIndebtednessAssetCoverageRatio`, `cef:ManagementFeesPercent`, `cef:IncentiveFeesPercent`.
- **FIND** GBDC fiscal-year total return (tag `InvestmentCompanyTotalReturn`, 10-K 0001476765-25-000096): FY22 5.89%, FY23 10.25%, FY24 8.98%, FY25 9.36%. Each prior-year value repeats identically in later 10-Ks (e.g. FY23 in -23-000077, -24-000132, -25-000096), a free cross-filing check. FY21 needed for 5Y; found later (see below).
- **FIND** GBDC latest period ≤ 2025-12-31: 10-Q 0001476765-26-000012 (period 2025-12-31, filed 2026-02-04). Latest 10-K 0001476765-25-000096 (FY end 2025-09-30), so fiscal-year returns lag one quarter.
- **FIND** KREF 10-K 0001628280-26-005092 (period 2025-12-31). No investment-company tags: no NAV, no NAV-based total return. Book value per share only (see decision 14).
- **FIND** Apex Ridge CSV: compounding the four QTD returns ≠ reported 1Y. Q4 2025: 2.52, 2.34, 2.71, 2.59 → 10.55% vs reported 10.31% (+24 bps). Q4 2024: 2.41, 2.63, 2.28, 2.87 → 10.58% vs 10.34% (+24 bps). Use reported; flag (decision 11).
- **ASSUME** As-of 2025-12-31 = latest period ending on or before it, filed any time up to today (decision 9, Aman, confirm W2).

## 2026-10-16 — Hour 0: where to see each number yourself

Tip: links starting `sec.gov/ix?doc=` open the SEC inline-XBRL viewer. Use Ctrl+F for the quoted text; tagged numbers are highlighted and clickable (shows the tag name and period).

| Finding | Where to look | Search for |
|---|---|---|
| CCLFX metadata says FYE Dec 31 | [EDGAR company page](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001735964) (header shows "Fiscal Year End: 1231"); raw: [submissions JSON](https://data.sec.gov/submissions/CIK0001735964.json) field `fiscalYearEnd` | `1231` |
| CCLFX filings say FYE Mar 31 | [N-CSR 0001213900-25-052571](https://www.sec.gov/Archives/edgar/data/1735964/000121390025052571/ea0241342-01_ncsr.htm) cover page and financial highlights footnote | `Date of fiscal year end: March 31` and `Fiscal year end changed to March 31, effective January 1, 2022` |
| CCLFX latest ≤ 12/31/25 | [N-CSRS 0001213900-25-118573 index](https://www.sec.gov/Archives/edgar/data/1735964/000121390025118573/0001213900-25-118573-index.htm) (period 2025-09-30, filed 2025-12-05) | "Period of Report" |
| CCLFX double amendment | [N-CSRS/A -24-027119](https://www.sec.gov/Archives/edgar/data/1735964/000121390024027119/0001213900-24-027119-index.htm), [N-CSRS/A -24-034098](https://www.sec.gov/Archives/edgar/data/1735964/000121390024034098/0001213900-24-034098-index.htm) | both "Period of Report 2023-09-30" |
| TAKIX tags only senior securities | [N-CSR 0001725472-26-000003 in viewer](https://www.sec.gov/ix?doc=/Archives/edgar/data/1725472/000172547226000003/ctac-20251231.htm) | `Average Annual Total Returns through December`; `Net asset value, end of period` (7 class tables) |
| TAKIX/CCLFX near-empty XBRL API | [TAKIX companyfacts](https://data.sec.gov/api/xbrl/companyfacts/CIK0001725472.json), [CCLFX companyfacts](https://data.sec.gov/api/xbrl/companyfacts/CIK0001735964.json) | only a handful of `cef` keys |
| GBDC FY returns 13.70 / 5.89 / 10.25 / 8.98 / 9.36 % (FY21→FY25) | [10-K 0001476765-25-000096 in viewer](https://www.sec.gov/ix?doc=/Archives/edgar/data/1476765/000147676525000096/gbdc-20250930.htm), financial highlights | `Total return based on average net asset value (6) 9.36` |
| Same, as API data | [companyconcept JSON](https://data.sec.gov/api/xbrl/companyconcept/CIK0001476765/us-gaap/InvestmentCompanyTotalReturn.json) | `"val": 0.0936` |
| GBDC 10-Q for 12/31/25 | [10-Q 0001476765-26-000012 in viewer](https://www.sec.gov/ix?doc=/Archives/edgar/data/1476765/000147676526000012/gbdc-20251231.htm) | "Period of Report" on the index |
| KREF 10-K | [10-K 0001628280-26-005092 in viewer](https://www.sec.gov/ix?doc=/Archives/edgar/data/1631596/000162828026005092/kref-20251231.htm) | `book value per share` |
| Apex 1Y gap | `apex-ridge-starter/data/apex_ridge_fund_data.csv`, rows Q4 2024 and Q4 2025 | |

- **FIND (important)** GBDC's tagged "NAV-based" return is **not** a standard NAV total return. 10-K 0001476765-25-000096 shows three measures:
  - (6) "Total return based on average net asset value" = net increase in net assets from operations ÷ daily average net assets. FY25 **9.36%** (tagged `InvestmentCompanyTotalReturn`, 5 years in the highlights table).
  - (7) "Total return based on net asset value per share" = net income per share ÷ ending NAV per share. FY25 **9.5%**, FY24 **9.0%** (MD&A table only, 1 decimal, 2 years, untagged).
  - (8) "Total return based on market value", FY25 0.8%, FY24 15.8% (tagged `InvestmentCompanyTotalReturnMarketValue`). Excluded per decision 2.
  - Neither (6) nor (7) is "NAV change + reinvested distributions" (how interval funds report total return). Both are return-on-equity style. **Open question for Aman / W2**: use (6) for 1/3/5Y with a definition note, or show GBDC returns as not like-for-like.
- **FIND** GBDC FY24 includes a one-time $51.7M write-down from the GBDC 3 merger. The 10-K also shows FY24 (6) "excluding the one-time write-down": 10.7% vs 8.98%. Use the as-reported figure; note it.
- **FIND** FY21 (13.70%) is in the same 10-K's five-year highlights table, so all 5Y inputs come from one filing, with FY22–FY24 cross-checked against earlier 10-Ks.

## 2026-10-16 — Green light for spec

- **DONE** Decisions 21–24 logged (lxml, SEC User-Agent, `.env` secrets, GBDC returns to W2).
- **FIND (correction)** My hour-0 summary said KREF fees "not applicable". Wrong: KREF is externally managed and its 10-K describes the management and incentive fees. Fees will be extracted for KREF like the others.
- **DONE** Spec written: `docs/superpowers/specs/2026-10-16-competitor-benchmarking-design.md`. Decisions 25–26 (computed-value confidence, citation links) logged as Proposed.

## 2026-10-16 — Milestone 1 built: NAV per share end to end

- **DONE** Pipeline, verification gate, Apex loader, review page (Table · Exceptions · NAV trend), Excel export. 63 tests pass (`uv run pytest`). Live run reads 24 filings; ~26 s cold, ~10 s cached.
- **FIND** TAKIX semi-annual reports mix header styles ("Six Months Ended June 30, 2025" + "Year Ended December 31," over years). First live run missed 6/30 points and labeled them "not reported", which was false. Fixed both: parser handles that exact layout; any read-but-empty date now says "not found in <accession>".
- **FIND** TAKIX Class M highlights add a trailing "Period Ended December 31, 2020" column; the parser refuses that mix rather than risk mis-ordered dates (Class I unaffected).
- **FIND** Filings declare no charset; lxml assumed Latin-1 and turned non-breaking spaces into "Â". Parser now detects UTF-8. A standalone "—" in a table row is read as zero (CCLFX distributions, Jan–Mar 2022 column).
- **FIND** GBDC 12/31/25 NAV is Medium: only the Dec 2025 10-Q reports it within the as-of scope (later filings not read in M1).

### Live NAV values (as of 2025-12-31) — hand-check links

| Fund | Value | Period | Confidence | Filing | Check it |
|---|---|---|---|---|---|
| CCLFX | $10.77 | 2025-09-30 | high | N-CSRS 0001213900-25-118573 | [document](https://www.sec.gov/Archives/edgar/data/1735964/000121390025118573/ea0264761-01_ncsrs.htm) — search `Net asset value, end of period` |
| TAKIX | $8.32 | 2025-12-31 | high | N-CSR 0001725472-26-000003 | [document](https://www.sec.gov/Archives/edgar/data/1725472/000172547226000003/ctac-20251231.htm) — search `Net asset value, end of period` |
| GBDC | $14.84 | 2025-12-31 | medium | 10-Q 0001476765-26-000012 | [document](https://www.sec.gov/Archives/edgar/data/1476765/000147676526000012/gbdc-20251231.htm) — search `Net asset value per common share` |
| KREF | $13.04 | 2025-12-31 | high | 10-K 0001628280-26-005092 | [document](https://www.sec.gov/Archives/edgar/data/1631596/000162828026005092/kref-20251231.htm) — search `Book value per share` |

### 8-quarter NAV trend (H/M/L = confidence, — = not reported or not found)

| Fund | 2024-03-31 | 2024-06-30 | 2024-09-30 | 2024-12-31 | 2025-03-31 | 2025-06-30 | 2025-09-30 | 2025-12-31 |
|---|---|---|---|---|---|---|---|---|
| Apex Ridge | $24.86 | $25.04 | $25.17 | $25.42 | $25.61 | $25.73 | $25.94 | $26.12 |
| CCLFX | $10.55 H | — | $10.93 H | — | $10.83 H | — | $10.77 H | — |
| TAKIX | — | $8.58 H | — | $8.55 H | — | $8.41 H | — | $8.32 H |
| GBDC | $15.12 H | $15.32 H | $15.19 H | $15.13 H | $15.04 H | $15.00 H | $14.97 H | $14.84 M |
| KREF | $15.18 H | $15.24 H | $14.84 H | $14.76 H | $14.44 H | $13.84 H | $13.78 H | $13.04 H |

- **ASSUME** KREF book value per share uses KREF's own "Total shares outstanding" (includes deferred stock units), as KREF reports it. Pending client confirmation (decision 14).

## 2026-10-16 — Independent review fixes

- **DONE** Fresh code review: 0 Critical, 5 Important (all latent: none changed a current value), 7 Minor deferred. A security check flagged DNS rebinding on the local server. All 6 fixed with failing-first tests; 72 tests pass; live rerun gives the same 32 NAV points.
- **DONE** Gate now also re-derives each table value's period from its column header and confirms that header sits above the row. Citations carry a find hint (TAKIX $8.32: "Net asset value, end of period", match 2 of 7 = the Class I table).
- **FIND** The "open at this row" link would have opened TAKIX's Class A table ($8.28), not Class I ($8.32). Removed (decision 26 revised).

## 2026-10-16 — Milestone 2: leverage, distribution yield, returns, amendments, protection, fee links

- **DONE** Built in the agreed order: leverage (two rows), distribution yield (TTM ÷ NAV), returns with labels, amendment check, sheet protection, fees fallback (sentence-level link). All constants moved to `benchmark/config.py` with sources (decision 35). 104 tests pass offline; live run ~17 s on cached filings.
- **DONE** Fixtures are now cut verbatim from the cached filings by `tests/cut_fixtures.py` (decision 50). The old KREF fixture's caption was hand-typed; the regenerated one has the real "(amounts in thousands, except share and per share data)", which the KREF reconciliation now reads instead of assuming `* 1000`.
- **NOTE (honest TDD gap)** The metric tests in `tests/test_metrics.py` were written after the code and passed first time; they are regression tests on real values, not failing-first. The parser-fix tests in `tests/test_units.py` reproduce bugs found live.
- **FIND** CCLFX reports a 3Y return (10.69% as of 3/31/25). Only TAKIX lacks one (decision 40).
- **FIND** CCLFX FY to 3/31/25: performance table 1Y 11.78% vs Financial Highlights total return 11.58% (same report). Shown 11.78%, Low, both values visible (decision 41). Question for Dana.
- **FIND** CCLFX reports asset coverage per facility only (Senior Credit Facility 10,802, Senior Notes 6,202, Secured Borrowings 63,977 per $1,000). Fund-level 421.1% is computed and Low (decision 36).
- **FIND** TAKIX Note 7: coverage 704.8% excluding preferred, 352.0% including. Implied D/E 0.40x matches the balance sheet 0.40x.
- **FIND** GBDC coverage 178.94% implies 1.27x vs 1.25x from the balance sheet (coverage uses principal; within 0.05x).
- **FIND** KREF's own ratios: D/E 2.2x (recourse only, net of cash), total leverage 3.9x (net of cash). Our gross 4.00x recomputes to 3.93x net of cash.
- **FIND (bugs fixed)** (1) The XPath prefilter kept a trailing `$`, so `^Net Assets$` matched nothing. (2) Joined header rows made "Year Ended December 31," + "2025" look like a full date, so KREF's income statement was refused. (3) A header naming two periods sharing "December 31" would have dated a 3-month column as a fiscal year; now refused (decision 49).
- **ASSUME** GBDC and KREF distributions are "declared" per share (what they report); interval funds' are distributions in the highlights.

### Live values (as of 2025-12-31) — hand-check links

| Fund | Row | Value | Source to check |
|---|---|---|---|
| CCLFX | Economic D/E | 0.31x | [N-CSRS 0001213900-25-118573](https://www.sec.gov/Archives/edgar/data/1735964/000121390025118573/ea0264761-01_ncsrs.htm), Statement of Assets and Liabilities: senior notes 6,093,192,507 + credit facility 3,212,500,000 + secured borrowings 500,000,000 ÷ net assets 31,488,743,589 |
| CCLFX | Asset coverage | 421.1% (computed) | same table |
| CCLFX | Distribution yield | 10.58% | same filing, Class I highlights "Total Distributions to shareholders" (0.54) and (0.90); [N-CSRS 0001213900-24-106851](https://www.sec.gov/Archives/edgar/data/1735964/000121390024106851/ea0221175-01_ncsrs.htm) (0.30); NAV 10.77 |
| CCLFX | 1Y / 3Y / 5Y | 11.78 / 10.69 / 10.98% | [N-CSR 0001213900-25-052571](https://www.sec.gov/Archives/edgar/data/1735964/000121390025052571/ea0241342-01_ncsr.htm), "Average Annual Total Returns as of March 31, 2025" |
| TAKIX | Economic D/E | 0.40x | [N-CSR 0001725472-26-000003](https://www.sec.gov/Archives/edgar/data/1725472/000172547226000003/ctac-20251231.htm), balance sheet: 920,159 + 946,446 + 27,686 ÷ 4,782,841 |
| TAKIX | Asset coverage | 352.0% | same filing, Note 7 "asset coverage (inclusive of preferred equity shares) was 352.0%" |
| TAKIX | Distribution yield | 9.01% | same filing, Class I "Total Dividends and/or distributions to shareholders" (0.75) ÷ 8.32 |
| TAKIX | 1Y / 5Y | 6.27 / 8.21% | same filing, "Average Annual Total Returns through December 31, 2025", I Share |
| GBDC | Economic D/E | 1.25x | [10-Q 0001476765-26-000012](https://www.sec.gov/Archives/edgar/data/1476765/000147676526000012/gbdc-20251231.htm), "Debt $ 4,903,076" ÷ "Total Net Assets 3,909,154" |
| GBDC | Asset coverage | 178.94% | same filing, "Asset coverage ratio(7) 178.94%" |
| GBDC | Distribution yield | 10.51% | same 10-Q (0.39, 0.48) + [10-K 0001476765-25-000096](https://www.sec.gov/Archives/edgar/data/1476765/000147676525000096/gbdc-20250930.htm) FY25 1.65; NAV 14.84 |
| GBDC | Return on average net assets | 9.36% (FY to 9/30/25) | same 10-K, "Total return based on average net asset value(6)" |
| KREF | Economic D/E | 4.00x | [10-K 0001628280-26-005092](https://www.sec.gov/Archives/edgar/data/1631596/000162828026005092/kref-20251231.htm), balance sheet: 2,862,689 + 1,198,332 + 632,516 ÷ 1,172,550 |
| KREF | Distribution yield | 7.67% | same filing, "Dividends Declared per Share of Common Stock $ 1.00" ÷ book value 13.04 |

## 2026-10-16 — Scope change and Window 3 fixes

- **DONE** Word export (`benchmark/export_word.py`): same run bundle and same cell text as the Excel (`export_excel.cell_text`), footnotes, exceptions, provenance appendix, links on every competitor cell, "Generated report" with run time and code version (decision 55). Tests compare every Word cell with the Excel cell.
- **DONE (client W3)** CCLFX 1Y now "Conflict: PM to choose" listing 11.78% (performance table) and 11.58% (Financial Highlights), both verified and cited, nothing selected (decision 56).
- **DONE (client W3)** CCLFX regulatory leverage "Not reported by fund", computed 421.1% in the note "computed, low confidence" (decision 57).
- **DONE (client W3)** "Superseded by amendment: re-check" at the top of the cell, styled, in UI, Excel and Word; one cell-text function for all outputs, so Word carries every flag, lag, "(computed)" and conflict (decisions 58, 59).
- **IN PROGRESS** Fee links landing at the fee sentence (decision 62), custom-metrics definitions file (decision 60), doc updates.
- **FIX** Quarter-end runs at Q1–Q3 2025 exposed: zero-balance debt lines absent from balance sheets (CCLFX 3/31/25), TAKIX "Secured credit facility" (singular) in 2024, GBDC 6/9-month distribution pieces ignored (2.59% at 3/31/25 was a 3-month figure). Fixed (decisions 52, 53).
- **NOTE** The grey area and unopenable downloads Aman saw in Chrome came from the Playwright test browser (its viewport had been resized; its downloads go to a temp folder), not from the app. The test browser was closed.
- **DONE** Fee links land on the fee sentence via unique-text fragments, checked by clicking in a real browser (decision 72). Custom-metrics definitions file with validation and Medium cap (decisions 63, 66). Run ID stamped on exports (74).
- **REVIEW** Independent reviewer: Word matches Excel cell for cell; 44/44 citations re-verified; fee fragments unique; no blank cells. Fixed its findings: amendment flags now reach conflict cells and computed notes; KREF label in Word provenance; dirty-tree marker on the code version; conflict link lines named (decision 75). Open nit: CCLFX has no incentive fee terms in its report, so its incentive cell links to the management fee sentence.
- **DONE (pre-briefing fixes)** Window 3 rules confirmed at all four quarter-ends (Q4 and Q1 screenshots; Excel and Word checked for both): CCLFX 1Y conflict lists 11.78% and 11.58%; CCLFX regulatory "Not reported by fund" with computed 421.1% (Q3/Q4) or 512.4% (Q1/Q2, 3/31/25 balance sheet) in the note. Q4 2025 is the default as-of. Fee cells show "Not extracted in v1 · view fee terms ↗". CCLFX incentive: "Annual report states no incentive-fee terms; see prospectus fee table" (no "incentive" or "hurdle" anywhere in N-CSR 0001213900-25-052571), linked to that report's fee sentence. Root copies of the two docs removed; docs/ is the only version. 163 tests pass.
- **CONFIRMED** TAKIX reports 5Y but not 3Y: N-CSR 0001725472-26-000003, "Average Annual Total Returns through December 31, 2025", columns "1-Year 5-Year(1) Since Inception(1)", row "I Share TAKIX 9/4/2018 6.27% 8.21% 6.38%". The only "three years" in the report is about expense reimbursement.
- **NOTE** returns._interval picks annual reports with form.startswith("N-CSR"), which also matches N-CSRS; harmless (semi-annual reports have no performance table, so they are skipped) but sloppy. Left unchanged per "no extraction changes".

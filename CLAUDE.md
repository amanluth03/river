# Apex Ridge competitor benchmarking (River take-home)

Context for Claude Code. Read this whole file before writing anything.

Source material lives in `context/`: `handoff_notes.md` (the original brief) and `window1_transcript.md` (the full client conversation). This file is the summary and wins where they differ. Consult the sources when you need the client's exact words, for example when writing the docs.

## First principles (the tie-breaker for every decision)

Objective: replace the 6 to 8 hour manual benchmark with output a PM can put in a board deck and defend to compliance, the CIO and LPs.

- **P1. A gap beats a wrong number.** Never show a value we can't source. Missing values show as missing, with the reason.
- **P2. Every number proves itself.** Filing, accession number, section and source text, verified against the source before display.
- **P3. Judgment is visible.** Conflicts, normalizations, computed values and data lags are shown next to the number, never handled silently.
- **P4. Compare on the client's terms.** NAV basis, Class I, a common calendar quarter-end, and the deck layout the PMs already use.
- **P5. Built for the people who use it.** An analyst with no command line runs it; a PM reviews it in minutes.
- **P6. Simple enough to explain.** Plain code and logged decisions that Aman can defend line by line and the client can maintain.

When two principles conflict, earlier ones win, and the decision goes in `context/decisions.md` with the principle it rests on.

## The situation

River Technologies builds custom software for financial firms. This repo is a timed (8-hour) mock engagement for a fictional client, **Apex Ridge Capital Partners**: a $3B open-ended private credit fund (senior secured direct lending and broadly syndicated loans, U.S. middle market). Their contact is **Dana Kellerman**.

Every quarter an Apex Ridge credit analyst pulls four competitors' SEC filings from EDGAR, reads 100 to 200+ pages each, and hand-types metrics into a locked Excel template (6 to 8 hours, from scratch each time). A misread basis point reached a board deck last year. We are automating this.

Deliverables (all in this repo):
1. A working prototype with a README that lets someone clone, install and run it locally.
2. `docs/technical_approach.md`: 2 to 3 pages for the client's technical counterpart.
3. `docs/solution_brief.md`: 1 to 2 pages for the CIO and Managing Partner.

## Inputs in the starter package

- `apex_ridge_fund_data.csv`: Apex Ridge's own 8 quarters, Q1 2024 to Q4 2025. Columns: quarter, net_return_qtd_pct, net_return_1y_pct, net_return_3y_pct, net_return_5y_pct, nav_per_share_usd, total_aum_usd_mm, management_fee_pct, incentive_fee_pct, incentive_hurdle_pct, leverage_ratio_dte, distribution_yield_pct. Values are percents (10.31 means 10.31%).
- `competitor_cik_list.csv`: the four competitors below.
- `board_deck_excerpt.md`: the current output format (redacted). Metrics as rows, funds as columns: Apex Ridge, CCLFX, TAKIX, GBDC, KREF. Rows: net return 1Y/3Y/5Y (annualized), management fee, incentive fee (hurdle), NAV per share, leverage (D/E), distribution yield (annualized).

## Competitors (CIKs verified on EDGAR except GBDC)

| Fund | Ticker | CIK | Type | Main forms |
|---|---|---|---|---|
| Cliffwater Corporate Lending Fund | CCLFX | 0001735964 | Non-traded interval fund (registered under the 1940 Act) | N-CSR (annual), N-CSRS (semi-annual), N-PORT, 424B3/497 supplements, N-2 |
| Carlyle Tactical Private Credit Fund | TAKIX | 0001725472 | Non-traded interval fund. TAKIX = Class I | N-CSR, N-CSRS, N-PORT, 424B3 |
| Golub Capital BDC | GBDC | 0001476765 | Listed BDC | 10-K, 10-Q, 8-K |
| KKR Real Estate Finance Trust | KREF | 0001631596 | Listed commercial mortgage REIT. **Not a BDC**, despite what the handoff says. Exempt from the 1940 Act | 10-K, 10-Q, 8-K |

Known quirks:
- Cliffwater changed its fiscal year-end from Dec 31 to Mar 31 in 2022 (a short Jan to Mar 2022 period exists). Semi-annual period ends Sep 30. Amended filings (N-CSRS/A) exist.
- Carlyle has share classes A, I, L, M, N, Y; use Class I only. It issues mandatory redeemable preferred shares, which matter for leverage. It changed valuation methodology in April 2020.
- GBDC fiscal year ends Sep 30 (verify). KREF fiscal year ends Dec 31.

## Decisions confirmed by the client (Window 1)

These are requirements, not suggestions.

1. **Benchmark date:** align to a common calendar quarter-end. Use the latest filing available for each fund as of that date, and **show the lag** for any fund whose data is from an earlier period. Working assumption: as-of date is **Dec 31, 2025** (Apex Ridge's latest quarter), and the 8-quarter window is Q1 2024 to Q4 2025.
2. **NAV basis everywhere:** returns and distribution rate are NAV-based, never market-price-based, including for the listed funds.
3. **Class I** for the interval funds.
4. **8-quarter NAV per share trend** is a real, new requirement. For the interval funds, show **only the semi-annual points they actually report**, clearly labeled. **Never derive or estimate interim values.** An honest gap beats a number that can't be sourced.
5. **Filing conflicts are never resolved silently.** When sources disagree, the output shows both values, which one was chosen, and why. Rule: the more recent filing wins and an amendment supersedes the original. Anything truly ambiguous is flagged for the reviewing PM.
6. **Citations:** every number cites the exact filing (form, accession number, period), the page or section, and the source text. Compliance re-pulls sources, and a figure they can't find is treated as wrong. **The system must verify each value is really in the source before showing it.**
7. **KREF stays in, flagged** as not a like-for-like peer, with a note that the CIO should decide whether it belongs.
8. **Normalization is explicit and documented.** Every conversion (cumulative to annualized, gross to net, leverage definition, fiscal-year lag) is recorded and visible next to the value.
9. **Users:** a credit analyst runs it each quarter and PMs review the output. **No command line, no config files, and IT won't install developer tools.** The analyst needs a simple UI; the repo still needs a one-command local run for River's reviewers.
10. **Leverage:** the table has always used D/E, but the CIO wants more. Dana asked River for a recommendation (see proposal below).

## Design rules (follow strictly)

- **No made-up numbers.** If a value can't be found and verified, show it as missing with the reason. Never fill gaps with model guesses, defaults or estimates.
- **Structured sources first:** XBRL / data.sec.gov company facts, then financial-highlights tables in the filing HTML, then narrative text. Use an LLM only for narrative items (fee terms, hurdle rates) and require it to return the exact source quote. Then check that quote appears verbatim in the filing text before accepting the value.
- **Every extracted value is a record**, not a bare number: fund, metric, value, unit, period/as-of date, form, accession number, filing URL, section or table, source snippet, extraction method, normalization applied, confidence, confidence reason, conflicts (other candidate values and their sources).
- **Confidence levels:**
  - High: structured source and confirmed by a second independent source or a reconciliation (for example, NAV per share times shares outstanding matches net assets).
  - Medium: a single structured source with no conflict, or two sources that agree within tolerance.
  - Low: narrative-only, computed with an assumption (for example, annualizing a cumulative return), or conflicting sources. Always flagged for review.
- **EDGAR etiquette:** set a User-Agent with a name and contact email from an environment variable (`SEC_USER_AGENT`); stay under 10 requests per second; cache every downloaded filing locally by accession number so reruns are fast and reproducible.
- **Apex Ridge data quirk:** in `apex_ridge_fund_data.csv`, compounding the four quarterly (QTD) returns gives a 1Y figure 22 to 28 bps higher than the reported `net_return_1y_pct`, in every quarter (Q4 2025: 10.55% compounded vs 10.31% reported). Use the reported value, show the discrepancy in the exceptions output, and don't "fix" it. It's an open question for the client.

## Leverage proposal (to confirm with the client)

Report both, side by side, and say which applies to each fund:
- **Economic leverage:** total debt (including mandatory redeemable preferred where present) divided by net assets. Comparable across all four funds, KREF included, and matches Apex Ridge's `leverage_ratio_dte`.
- **Regulatory leverage:** asset coverage as reported under the 1940 Act (BDCs: minimum 150%; registered closed-end/interval funds: 300% for debt, 200% for preferred), plus its implied D/E. Shown as "not applicable" for KREF, with KREF's own reported leverage measure in a note.

## Output

- A review screen (simple local web UI) for the analyst/PM: the benchmark table in the deck layout, each cell with a confidence badge, click-through to its citation and source snippet, an exceptions and conflicts list, and the 8-quarter NAV trend chart (semi-annual points labeled and gaps left as gaps).
- Exports: an Excel file in the deck layout, plus sheets for provenance (one row per value) and exceptions.
- Apex Ridge's column comes from the CSV, cited as client-provided data.

## Plan and timeline (submission around hour 5; hard stop on new features at hour 4:30)

1. Hour 1 to 2: retrieval (filing index by CIK and form family, download and cache), value-record schema, Apex CSV loader with checks.
2. Window 2 with the client around hour 2.
3. Hour 2 to 3: extraction per metric and fund type, normalization, conflict handling, confidence scoring, citation verification.
4. Hour 3 to 3:45: comparison table, exports, review UI, tests on known values.
5. Window 3 around hour 3:45, then fixes, then docs and a fresh-clone check.

Keep it small and correct. One metric done right with full provenance beats six with silent guesses. Ask before adding scope.

## Working with Aman (required)

Aman has to defend every line and every decision to a technical interviewer afterward. So:

- **Decision log:** append every non-trivial decision to `context/decisions.md` (decision, who decided, why, alternatives, cost). Product or client-facing decisions are Aman's: propose them and ask; don't make them silently. Never mark a row "Client" unless Dana said it.
- **Explain before building:** before each module, say in 3 to 5 lines what it will do and why this approach, then build it.
- **Explain after building:** after each module, walk Aman through it: what each function does, what can go wrong, and why this approach over the alternatives. Keep going until he can explain it back.
- **Plain, readable code:** standard Python, small functions, clear names, no frameworks or clever one-liners he couldn't explain. Prefer a few well-understood libraries (requests, pandas, openpyxl, a simple web UI) over heavy ones.
- **Build log:** keep `context/build_log.md` updated with what was built, findings, assumptions and blockers.
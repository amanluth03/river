# Solution brief: automated peer benchmarking

*For Apex Ridge's Chief Investment Officer and Managing Partner. Prepared by River Technologies.*

## The problem

Every quarter, an analyst spends 6 to 8 hours reading four competitors' SEC filings and typing numbers into a locked spreadsheet. Nothing checks the typing, and last year a misread basis point reached a board deck. Saving those hours is expected. What matters is whether every number in front of the board can be traced to its page, and whether the process catches what an analyst would miss.

## What the first run caught (as of December 31, 2025)

- **KREF is not a BDC.** It is a commercial mortgage REIT outside the 1940 Act. Its figure is labeled "Book value per share", regulatory leverage shows as not applicable, and it is flagged for the CIO to decide whether it stays.
- **Golub's return is a different measure.** What looks like a NAV return is a return on average net assets, shown under that name and marked "Not directly comparable".
- **Cliffwater's annual report contradicts itself on its 1-year return.** It gives two figures for the same year: 11.78% in the performance table and 11.58% in the financial highlights, and no footnote explains the difference. The cell shows both, each cited, flagged "Conflict: PM to choose". Nothing is selected.
- **Cliffwater does report a 3-year return** (10.69%), though we had assumed neither interval fund did. Among the interval funds, only Carlyle's 3-year cell reads "Not reported by fund".
- **Apex Ridge's own 1-year return sits 24 bps below its compounded quarters** (22 to 28 bps in every quarter checked). The reported figure stays official. The steady gap behaves like a fixed annual cost counted in the 1-year figure only; fund accountant to confirm.
- **Amended filings are detected.** Each run checks. It found four amendments to three older reports, including Cliffwater's two to its September 2023 report. None touches a number in the current table.

**One miss, owned.** Our first version picked Cliffwater's 11.78% and flagged it, making the PM's choice for them and breaking the rule agreed at the start. The system now refuses to choose when a single report contradicts itself.

## What we built

A review page where the analyst picks the quarter-end and clicks **Run**. It fetches the SEC filings and fills the deck's layout beside Apex Ridge's own numbers.

1. **Every number proves itself.** Click any cell to see the filing, section and exact source text, linked to the SEC document. Each run re-reads every number from its filing and tests it against the fund's other figures; if it can't confirm a number, it doesn't show it.
2. **Every number has a confidence rating.** Green means confirmed by an independent second source, amber means one source, red means a check failed or an assumption was needed.
3. **No silent judgment calls.** Conflicts, lags and calculations are labeled next to the number, and gaps say why. A calculation never fills a reported row: Cliffwater's computed 421.1% asset coverage sits in a note, and its cell says "Not reported by fund".
4. **Amendments are impossible to miss.** If a filing we use is amended, the cell itself reads "Superseded by amendment: re-check", in red, on the page, in Excel and Word, and in exceptions. The analyst re-pulls; the client confirmed flag-only is right for v1.

Outputs: the review page, a locked Excel workbook in the deck's layout, and a Word report for the IC from the same run, stamped with a run ID and code version.

## What changes each quarter

- **Today:** an analyst spends 6 to 8 hours finding filings, reading them and typing numbers, and nothing checks the typing.
- **With this:** the analyst picks the quarter-end and clicks Run (about 40 seconds on a first run). Their time goes to the flagged items (conflicts, lags and low-confidence values), each listed with its source.
- **The PM** reviews the same table with every source one click away, then exports the locked Excel and the Word report from the same run.
- **Compliance** can re-pull any figure from its cited filing, section and quote.

## Key choices, in business terms

- **One date for every fund.** All funds are compared at the same quarter-end, and a fund whose latest report is older shows how far behind it is.
- **Fund performance, not stock price.** Returns and yields use NAV, including for the two listed funds, and the institutional share class.
- **Two leverage measures.** Debt-to-equity, comparable across all four funds, and the regulatory coverage ratio where the 1940 Act applies.
- **Yield on Apex Ridge's own basis:** trailing 12 months of distributions divided by NAV.
- **KREF stays in, flagged** as not a like-for-like peer, for the CIO to decide.

## Tradeoffs we made for the timeline

- **Fee terms are not extracted yet.** The four management fees are charged on different bases (net assets, managed assets, gross assets, adjusted equity), so a single "1.00%" would mislead. Those cells say "Not extracted in v1" and link to each fund's fee sentence, landing within two scrolls of it, which the client accepted. Putting fees on a common basis comes next.
- **Built for these four competitors;** a new fund type takes roughly a day of setup and testing. **PM sign-off** stays outside the tool, as agreed.

## Rollout and next phase

1. **Pilot quarter.** River starts the page; it runs in parallel with the manual process and every difference is resolved.
2. **Production access.** Hosting (an internal link or a one-click launcher) goes to Apex Ridge's operations lead, who handles vendor approvals with compliance and IT; the client offered to make the introduction.
3. **Custom metrics.** The definitions file exists: a metric can't be saved without stating what it measures, its unit, its source, its normalization assumptions and its owner. Portfolio turnover is the worked example. Feeding definitions into the run comes next; new metrics start at medium confidence at most.
4. **Fund browser (designed, not built).** Search the SEC by name, ticker or CIK. Funds of a type the system already reads (interval funds, BDCs, mortgage REITs) can be added; others show "Not yet supported", never empty columns.
5. **Later:** fee extraction, automatic re-pull of amendments, PM sign-off in the tool.

The client named two ways this fails: a broken citation and any step that looks like IT work. Every run re-verifies every citation against its stored filing and tests check that every cell links, and the analyst only opens the page and clicks Run.

**Decisions we need:** whether KREF stays in the peer set (the CIO's call), who owns each custom-metric definition, and the introduction to the operations lead.

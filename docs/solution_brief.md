# Solution brief: automated peer benchmarking

*For Apex Ridge's Chief Investment Officer and Managing Partner. Prepared by River Technologies.*

## The problem

Every quarter, an analyst spends 6 to 8 hours reading four competitors' SEC filings and typing numbers into a locked spreadsheet. Nothing checks the typing, and last year a misread basis point reached a board deck. What matters is whether every number in front of the board can be traced to its page, and whether the process catches what an analyst would miss. As Dana put it: "Speed is expected. Accuracy he will remember."

## What the first run caught (as of December 31, 2025)

- **KREF is not a BDC.** It is a commercial mortgage REIT outside the 1940 Act. Its figure is labeled "Book value per share", regulatory leverage shows as not applicable, and it is flagged for the CIO to decide whether it stays.
- **Golub's return is a different measure.** What looks like a NAV return is a return on average net assets, shown under that name and marked "Not directly comparable".
- **Cliffwater's annual report contradicts itself.** It gives two 1-year returns for the same year: 11.78% in the performance table and 11.58% in the financial highlights. The cell shows both, each cited, flagged "Conflict: PM to choose". Nothing is selected.
- **Cliffwater does report a 3-year return** (10.69%), though we had assumed neither interval fund did. Only Carlyle shows "Not reported by fund".
- **Apex Ridge's own 1-year return** sits a steady 24 bps below what its quarterly returns compound to. The reported figure stays official. The pattern behaves like a fixed annual cost counted in one figure only; fund accountant to confirm.
- **Amended filings are detected.** Each run checks; it found Cliffwater's two amendments to a 2023 report (neither affects the current table).

**One miss, owned.** Our first version picked Cliffwater's 11.78% and flagged it, making the PM's choice for them and breaking the rule agreed at the start. The system now refuses to choose when a single report contradicts itself.

## What we built

A review page where the analyst picks the quarter-end and clicks **Run**. It fetches the SEC filings and fills the deck's layout beside Apex Ridge's own numbers.

1. **Every number proves itself.** Click any cell to see the filing, section and exact source text, linked to the SEC document. Each run re-reads every number from its filing; if it can't confirm it, it doesn't show it.
2. **Every number has a confidence rating.** Green: confirmed by an independent second source. Amber: one source. Red: a check failed or an assumption was needed; listed for review.
3. **No silent judgment calls.** Conflicts, lags and calculations are labeled next to the number; gaps say why. A calculation never fills a reported row: Cliffwater reports asset coverage only per credit facility, so its cell says "Not reported by fund" and our 421.1% sits in a note marked computed, low confidence.
4. **Amendments are impossible to miss.** If a filing we use is amended, the cell itself reads "Superseded by amendment: re-check", in red, on the page, in Excel and Word, and in exceptions. The analyst re-pulls; Dana confirmed flag-only is right for v1.

Outputs: the review page; a locked Excel workbook in the deck's exact layout, tracing every value; and a Word report for the IC, which Dana ranked first. Word uses the same run and cell text as the Excel, every flag, lag label, computed note and citation included: "The IC sees what the PM sees." It is stamped with a run ID, run time and code version, so edits can be checked.

## Designed against the two ways this fails

Dana named them: a broken citation, after which PMs trust none of it; and any step that looks like IT work, after which the tool goes unused.

- **Citations:** every citation is re-verified against its stored filing on every run. Automated tests check that every cell links to a filing and that each fee link targets text found only once in the document; each fee link was also clicked through in a real browser.
- **Usability:** the analyst picks a quarter and clicks Run; nothing to edit. Today the page itself is started with a command, so during the pilot River starts it. For production, a link or one-click launcher replaces that step, decided with Apex Ridge's operations lead.

## Tradeoffs we made for the timeline

- **Fee terms are not extracted yet;** an unverified fee is worse than a link. Those cells say "Not extracted in v1" and link into each fund's latest annual report or 10-K, landing within two scrolls of the fee sentence, which Dana accepted.
- **Built for these four competitors;** a new fund type takes roughly a day of setup and testing. **PM sign-off** stays outside the tool, as agreed.

## Rollout and next phase

1. **Pilot quarter.** River starts the page; it runs in parallel with the manual process and every difference is resolved.
2. **Production access.** Hosting (an internal link or a one-click launcher) goes to Apex Ridge's operations lead, who handles vendor approvals with compliance and IT; Dana offered to make the introduction.
3. **Custom metrics.** The definitions file exists: a metric can't be saved without stating what it measures, its unit, its source, its normalization assumptions and its owner. Portfolio turnover is the worked example. Feeding definitions into the run comes next; new metrics start at medium confidence at most.
4. **Fund browser (designed, not built).** Search the SEC by name, ticker or CIK. Funds of a type the system already reads (interval funds, BDCs, mortgage REITs) can be added; others show "Not yet supported", never empty columns.
5. **Later:** fee extraction, automatic re-pull of amendments, PM sign-off in the tool.

**Decisions we need:** whether KREF stays in the peer set (the CIO's call), who owns each custom-metric definition, and the introduction to the operations lead.

**The result:** every number in the board deck traceable to its page in one click, with the catches a hurried read would miss.

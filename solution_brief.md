# Solution brief: automated peer benchmarking

*For Apex Ridge's Chief Investment Officer and Managing Partner. Prepared by River Technologies.*

## The problem we solved

Every quarter, an analyst spends 6 to 8 hours pulling four competitors' SEC filings, reading 100 to 200 pages each, and typing numbers into a locked spreadsheet. Nothing checks the typing, and last year a misread basis point reached a board deck.

## What we built

The analyst opens a page on their own computer, picks the quarter and presses **Run**. In under a minute, the system:
- fetches the competitors' latest filings directly from the SEC;
- extracts the figures in the board deck's layout, including NAV per share, two leverage rows, distribution yield and returns;
- puts them next to Apex Ridge's own numbers.

The PM gets the same table they use today, plus three things they never had:

1. **Every number proves itself.** Click any cell to see the filing, the section, and the exact sentence or table row the number came from, with a link to the SEC document. Before a number is displayed, the system re-reads it from the filing and checks it is really there. If it can't confirm a number, it doesn't show it.
2. **Every number has a confidence rating.** Green means confirmed by a second, independent source. Amber means a single source. Red means sources disagree or the figure needed an assumption; red items appear on a review list.
3. **No silent judgment calls.** When filings disagree, when a fund's data is a quarter or more behind, or when a figure was calculated rather than reported, the output says so next to the number. Gaps are labeled with the reason, such as "Not reported by fund", and are never left blank.

The Excel export matches the deck's layout and is locked against accidental edits.

## What changes in the quarterly workflow

| Today | With the system |
|---|---|
| 6 to 8 hours of reading and typing | Under a minute to run; the analyst's time goes to reviewing a short list of flagged items |
| Accuracy depends on careful typing | Every value is checked against its filing before it appears |
| Compliance re-pulls sources by hand | Every cell links to its source document and section |
| Amended filings can go unnoticed | Each run checks for amendments and flags affected numbers |
| Judgment calls live in the analyst's head | Every choice is written next to the number and in the export |

## Key choices, in business terms

- **A gap is better than a wrong number.** Where a fund doesn't report a figure, the cell says so rather than us estimating it. For example, Carlyle publishes no 3-year return.
- **Like-for-like where possible, clearly labeled where not.**
  - Golub reports a different kind of return. It is shown as "Return on average net assets: not directly comparable".
  - KREF is a mortgage REIT, not a credit fund. It shows "Book value per share", has no 1940 Act leverage limit, and is flagged so the CIO can decide whether it stays in the peer set.
- **Leverage shown two ways, as the CIO asked.** Economic leverage (debt-to-equity, comparable across all four funds) and regulatory asset coverage (the 1940 Act measure).
- **Same yardstick as Apex Ridge.** Distribution yield is trailing 12 months of distributions ÷ NAV, the way Apex Ridge calculates its own.

## What the first run found

- **Cliffwater's annual report gives two different 1-year returns for the same year:** 11.78% and 11.58%. Both are shown. We need Apex Ridge's call on which belongs in the deck.
- **Apex Ridge's own 1-year return** sits a steady 24 bps below what its quarterly returns compound to. The reported figure stays official. The pattern suggests a fee counted in one figure but not the other, and the fund accountant is confirming.
- **Cliffwater's most recent annual return figures are as of March 31, 2025.** They are shown with that date rather than recalculated.

## Tradeoffs we made for the timeline

- **Fee terms are not extracted yet.** Those cells link directly to the sentence in each filing that states the fee terms. Fees are written in prose, and an unverified fee is worse than a link.
- **Built for these four competitors.** Adding a fund takes setup and testing, roughly a day per type of fund.
- **PM sign-off stays outside the tool for now,** as agreed.

## What a production rollout looks like

1. **Weeks 1–2: pilot.** Run it alongside the manual process for one quarter, and compare and resolve every difference.
2. **Weeks 3–4: harden.** Add fee extraction with the same source-checking. Add a second source for Cliffwater's leverage. Re-fetch amended filings automatically.
3. **Weeks 5–6: operate.** Install on the analytics team's machines, with no developer tools needed by the analyst. Record PM sign-off in the tool, and hand over the runbook.

**The result:** a quarterly benchmark that takes minutes instead of a day, where every number in the board deck can be traced to its source in one click.

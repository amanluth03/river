Hey Dana, quick update on what we're building so far. The NAV per share and the 8-quarter NAV trend are now all working for all four funds, and every value has been checked against its own filing before it's shown. Cliffwater's latest report is as of September 30, 2025, which is one quarter behind, so that is shown with that lag. Just a few questions, if you don't mind.
Client · Dana Kellerman
Good progress. Go ahead.
You
Golub’s 10-K reports its return on average net assets (9.36% for FY2025), not a per-share NAV total return (about 9.5%); the market-price return was 0.8%. Should I show Golub’s reported figure clearly labeled as a different measure, or mark Golub’s returns as not comparable?
My leverage recommendation: two rows. Economic leverage is debt (including preferred shares that act like debt) divided by equity. It works for all four funds and matches your current D/E. Regulatory leverage is asset coverage as the 1940 Act funds report it, not applicable for KREF. Does that give the CIO what he’s after?
In your own data, compounding your four quarterly returns gives about 24 bps more than the reported 1-year return, every quarter (Q4 2025: 10.55% vs 10.31%). Which figure is official? For now I show the reported one and flag the gap.
Client · Dana Kellerman
On Golub's return: show the reported figure, label it clearly as return on average net assets, and mark it not directly comparable to the other funds' NAV total return. Do not force it into the same row and let someone assume it is the same measure. The PM reviewing it needs to see immediately that they are looking at a different calculation, not a different performance.

On leverage: yes, that is what the CIO is after. Two rows, clearly labeled, with a note that regulatory leverage is not applicable for KREF. Bring that format to the output and I will show it to him.

On the compounding gap in our own data: the reported figure is official. That is what goes in the deck, full stop. But I want to understand why the gap is consistent at 24 basis points every quarter — that is not rounding, that is a methodology difference, and I need to know what it is before anyone asks me. Flag it in the output as you are doing, but also bring me a plain-English explanation of where the difference comes from. Not the math — what the two calculations are actually doing differently. I will take it from there.
You
Thank you. That's clear in all three. I'll bring in the explanation for the gap. Next questions:
The interval funds don’t report a 3-year return. Is “not reported” acceptable there, rather than me calculating one?
How is your distribution yield calculated: trailing 12 months of distributions divided by NAV, or the latest distribution annualized? I want the competitors on the same basis.
Does the output need to drop into your locked Excel template, or is a new workbook in the same layout fine?
Client · Dana Kellerman
On 3-year returns for the interval funds: "not reported" is acceptable, but label it as such. Do not leave it blank — a blank looks like a data error. I need the PM to see that the fund does not report it, not wonder if we missed it.

On distribution yield: trailing 12 months of distributions divided by period-end NAV. That is how we calculate our own, so that is the basis competitors need to be on. If a fund does not have 12 months of distribution history in the filing, flag it and show what period you did use.

On the Excel output: a new workbook in the same layout is fine. The locked template exists because analysts were making accidental edits — if the new output is clean and the layout matches, the PMs will not care that it is a different file. What they cannot have is a different structure that makes them re-learn where to look.
You
Okay, cool, makes sense. Just two more questions here. 
Three quick confirmations: (a) “as of Dec 31, 2025” means each fund’s latest report covering a period ending on or before that date, even if filed later; (b) KREF has no NAV, so I show its book value per share in that row, clearly labeled; (c) for v1, the PM reviews in the tool and signs off the way they do today, and recording sign-off in the tool comes in a later phase. Is that ok?
Anything I didn’t ask that I should have?
Client · Dana Kellerman
All three confirmations: yes, yes, and yes. On KREF book value — make sure the label is unambiguous. "Book value per share" not "NAV per share." If a PM skims it, I do not want any ambiguity about what they are looking at.

On what you did not ask: one thing. Amendment tracking. Filings get amended after the fact and today we have no way to catch it — that is how a stale number sits in a board deck without anyone knowing. I do not know how you handle that on your side, but I need to know the system has some way of recognizing when a filing it already pulled has been superseded. Even if v1 just flags it for the analyst to re-pull manually, that is better than nothing.

Beyond that, you have covered the ground well. When you have the compounding gap explanation and the leverage format ready, bring them together and we will do a review.You
Since we have a few minutes, here are both drafts now so you can react, and in our last session I'll show them filled in with real numbers.
Leverage format (two rows, labeled exactly like this):
* Economic leverage (debt-to-equity): total debt, including preferred shares that act like debt, divided by net assets. Shown for every fund, including Apex Ridge.
* Regulatory leverage (asset coverage, 1940 Act): as each fund reports it, with the equivalent debt-to-equity alongside. KREF: "Not applicable: not a 1940 Act fund." Apex Ridge: "Not in client data," unless you can provide it.
* Every cell links to its filing and section.
The 24 bps gap, in plain English: the gap is steady every quarter. A rounding difference would bounce around, and a timing difference would move with your cash flows. A steady gap behaves like a fixed annual cost that's counted in the 1-year figure but not in the quarterly ones. The usual causes are that the two figures are calculated for different share classes or fee loads (for example, one includes a roughly 0.25% servicing fee), or that a fee is charged once a year, like an annual incentive-fee true-up, and isn't reflected quarterly. Your fund accountant can confirm which fees each figure is net of. I can show the size and pattern of the gap, but I can't prove the cause from this data alone.
One scope check: fee terms sit in narrative text and are the slowest to verify. If I can't verify them in this version, is it OK to show "Not extracted in v1" with a link to the source prospectus rather than an unverified number?
Client · Dana Kellerman
On leverage format: that works. "Not in client data" for our regulatory leverage is fine for v1 — I will check with our fund accountant on whether we can provide it for future quarters. The filing links on every cell are not optional; that is exactly what compliance needs.

On the 24 basis points: that explanation is useful and the logic is sound. A consistent gap pointing to a fee that is in one figure but not the other — that I can take to our fund accountant and ask a specific question. You have given me enough to do that. Note the gap and the likely cause in the output exactly as you framed it, and flag that the accountant needs to confirm.

On fee terms: "Not extracted in v1" with a direct link to the source prospectus is acceptable, but only if the link lands as close to the relevant section as possible. A link to a 300-page document with no guidance is not useful — the analyst still has to hunt. If you can point to the page or section, do that. If you genuinely cannot, the link plus a note that fee terms are in the prospectus narrative is better than an unverified number in the table.

Bring the real numbers in the next session and we will see how it holds together.
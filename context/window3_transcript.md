Hey Dana, Here are the real numbers as of Dec 31, 2025. Every competitor cell links to its filing and section, and lags are shown.

Economic leverage (D/E): Apex 0.96x, Cliffwater 0.31x (as of Sep 30), Carlyle 0.40x, Golub 1.25x, KREF 4.00x.
Regulatory leverage (asset coverage): Carlyle 352% (including preferred), Golub 179%, KREF not applicable, Apex not in client data.
Distribution yield (trailing 12 months ÷ NAV): Apex 9.22%, Cliffwater 10.58%, Carlyle 9.01%, Golub 10.51%, KREF 7.67% (on book value).
1-year return: Apex 10.31% with the gap note as you approved, Cliffwater 11.78% (as of Mar 31, 2025), Carlyle 6.27%, Golub 9.36% (return on average net assets, not comparable), KREF not applicable.
The amendment check runs every time and correctly caught Cliffwater’s two 2023 amendments.

Calls I made, which you can overrule: lagged figures are shown with their lag, never recalculated, and KREF’s leverage uses gross debt like the other funds, with KREF’s own net-of-cash figure (3.9x) in a note. Three things I need from you:

Cliffwater’s annual report shows two 1-year returns for the same period: 11.78% in the performance table and 11.58% in the financial highlights. I show 11.78% with both visible and flagged. Is that the one the deck should carry?
Cliffwater only reports asset coverage per credit facility. I calculated a fund-level 421%, labeled “computed,” low confidence. Keep it, or show “Not reported by fund”?
Fee links land on the exact fee sentence in each fund’s annual report or 10-K, not the prospectus. Close enough for the analyst?
Client · Dana Kellerman
These numbers look right directionally and the format is what I asked for. On your three questions:

Cliffwater's conflicting returns: do not choose for me on this one. Show both figures, both sources, and flag the conflict clearly. The PM signs off on which one goes in the deck — that is exactly the judgment call I said needed to stay with a human. I am not comfortable with the system picking 11.78% and burying 11.58%.

Cliffwater's asset coverage: show "Not reported by fund" and put your computed 421% in a note, clearly labeled as computed and low confidence. Do not put a derived number in the main cell — if the board asks where it came from and the answer is "we calculated it," that is a different conversation than "the fund reported it." The note gives the CIO the information without misrepresenting its provenance.

Fee links to the annual report or 10-K: yes, close enough, provided the link lands on or immediately adjacent to the fee sentence. If the analyst clicks it and finds the fee disclosure in two scrolls or less, that works. If it drops them at page one of a 300-page document, it does not.

One thing I want confirmed before this goes to the PM: the amendment catch on Cliffwater — did the system re-pull the corrected figures, or did it flag for the analyst to re-pull manually? I need to know which one happened.
You
Clear on all three; I’ll make those changes now.

On the amendment catch: it flagged, it did not re-pull. And none of the numbers in the current table come from the amended filings. Those are 2023 reports, outside our window, so no value you’re looking at was affected. In this version, if an amendment hits a filing we do use, that value shows “Superseded by amendment: re-check” and the analyst re-pulls. Automatic re-pull is next phase.

On today’s three requests: I want to give you something solid on each without risking the numbers you’ve already approved. Here’s what I propose for this version:

Word document: the same table, labels, footnotes and citations, formatted for the IC to attach to the board deck, stamped with a run ID so any later edit can be checked. Fully done.
Fund browser: search EDGAR by name, ticker or CIK and add a fund. Funds of the types we already read (interval funds, BDCs, mortgage REITs) work right away; other types show “Not yet supported” rather than empty columns or guesses, because each new fund type needs its labels checked.
Custom metrics: a definitions file where a new metric is a table row, a reported tag or a ratio of existing metrics, with the same verification and citations, plus one working example (portfolio turnover). New metrics start at medium confidence at most. Spread and default rates, and editing through a screen, come next phase.

Does that match your priorities? If only one of the three can be fully done for this quarter’s deck, which is it?
Client · Dana Kellerman
The amendment handling is acceptable for v1. Flag and re-pull manually is the right call over an automatic re-pull that might introduce errors. Confirm that the "Superseded by amendment" label is visible enough that an analyst cannot miss it — not a footnote, in the cell.

On the three additions: your scoping on all three is sensible and I have no objection to the constraints you have described.

If only one ships fully for this quarter's deck, it is the Word document. That is what the IC committee asked for by name and it is the one that changes what the PMs can actually do with the output this quarter. The fund browser and custom metrics matter, but they do not affect the board deck that is due.

Two things I want before we close this out. First, the Word document needs to carry the same conflict flags, lag labels, computed notations, and citations that are in the table — not a clean version with the caveats stripped out. The IC sees what the PM sees. Second, on the definitions file for custom metrics: whoever sets up a new metric needs to specify what the metric is measuring and what normalization assumptions apply, the same way you documented the leverage rows. A metric with no definition is the same problem as a number with no citation. Make sure that is part of the structure from the start.

When is the Word document ready to review?
You
Understood on all of it.

Superseded label: it will be in the cell itself, not a footnote. The value is shown as “Superseded by amendment: re-check,” styled so it can’t be missed, and it’s repeated in the exceptions list.
Word document: it carries everything the table does: conflict flags, lag labels, computed notations and citations. The IC sees what the PM sees. It’s built from the same run as the Excel, so the two can’t differ.
Custom metric definitions: a metric can’t be saved without a stated definition (what it measures), its unit, where it comes from, and its normalization assumptions, the same as the leverage rows. A metric with no definition is rejected, just like a number with no citation.
Timing: the Word document will be ready within the hour and included in the final delivery, generated from today’s run, so you’ll review it there.

Last question: imagine it’s six months from now and the PMs have stopped using this. What’s the most likely reason?
Client · Dana Kellerman
Honestly? One of two things.

The citations break. A PM clicks a link, cannot find the number where it says it is, and from that point forward they do not trust any of it. They go back to pulling it manually because at least then they know where the number came from. That happened once with a vendor data feed we used to subscribe to — one bad quarter and it was done.

Or the interface requires something they will not do. If kicking off the quarterly run requires any step that looks like a technical task — editing a file, running something from a terminal, anything that feels like IT work — it will sit unused and an analyst will get handed the Excel template again. The PMs are not going to troubleshoot anything. If it does not work the first time they touch it, they will not try a second time.

Everything else — missing metrics, imperfect normalization, features that did not make v1 — those are problems I can work around while you fix them. Those two are not. If the numbers cannot be trusted or the tool cannot be used without help, it is dead on arrival.

That is what I would watch for.
You
That's very useful. Both are things I can design against. Two last ones:
1. On the interface: in v1 the analyst opens the review page and clicks Run. There's nothing to edit, and no terminal. For production, would IT rather host it internally so it's just a bookmark, or is a one-click desktop launcher acceptable? And who needs to approve that?
2. For the managing partner: if the quarterly benchmark goes from 6 to 8 hours of transcription to a short review of cited numbers, is that the bar he'll judge it by, or is there something else he'll look for?
Thanks, Dana. The Word document will be in the final package.
Client · Dana Kellerman
On hosting: I do not know enough about our IT setup to answer the internal hosting question — that is not my area. What I can tell you is that whatever the answer is, it cannot require the analyst to do anything beyond opening something and clicking. Route that question to our operations lead; she handles vendor tool approvals and she will know what compliance and IT need to sign off on. I can make the introduction.

On the CIO: time saved is table stakes — he will assume that part works. What he will actually judge it on is whether he can stand behind the numbers in front of the board. Last year's incident is still in the room every time we present. If he can point at the page for every figure and the output caught something an analyst would have missed — an amendment, a conflicting footnote, a normalization issue — that is what makes this worth it to him. Speed is expected. Accuracy he will remember.

Get me the Word document and we will take it from there.
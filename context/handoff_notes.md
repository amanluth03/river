Inherited handoff notes
FROM RIVER · ENGAGEMENT LEAD
Apex Ridge Capital - Handoff Notes
You are the sole River engineer tasked with this engagement. Everything you need is in this brief - information about the client, the problem at hand, the scope, and the required deliverables. You have three 15-minute chat windows on the left with the client herself to ask any questions regarding the engagement. Read through this brief, then start building.

The client
Apex Ridge Capital Partners is a $3B open-ended private credit fund (senior secured direct lending and broadly syndicated loans, U.S. middle market; founded 2018, consistently top-quartile). Three PMs, twelve credit analysts, a four-person ops/quant team, no in-house engineering. Every quarter their PMs benchmark the fund against competitor credit funds, and today that means an analyst pulls each competitor's SEC filings from EDGAR, reads 100–200+ pages, and hand-transcribes metrics into a locked Excel template — 6–8 hours per quarter, from scratch every time. A misread basis point made it into a board deck last year. They want it automated.

What you're building
An automated system that:

Connects to SEC EDGAR and retrieves the relevant filings (annual and semi-annual reports, N-PORT filings, prospectus supplements) for the competitor set below. It must actually connect to EDGAR — no mock data on the competitor side.
Extracts key performance and operational metrics from those filings. The data is buried in a mix of structured tables, narrative text, footnotes, and exhibits; the system must handle that heterogeneity.
Normalizes the extracted data into a comparable format — funds report the same metric differently (gross vs. net, annualized vs. cumulative, different fiscal year-ends).
Compares against Apex Ridge's own fund data — provided in the starter package as apex_ridge_fund_data.csv (8 quarters of fund metrics).
Produces a clean, reviewable benchmarking output the PMs can use directly for board decks and LP reporting — and reports, for every extracted value, its provenance and a confidence level. The starter package includes a format-only excerpt of how the comparison is presented today.
How you'll know you're right
The manual process you're replacing was the client's only source for these numbers — there is nothing to check your output against. Deciding which figure in a 200-page filing to trust used to be an analyst's judgment call; now it's your system's, and it has to show its work. Every value you report must carry:

Provenance — which filing, and where in it, the number came from. The client's compliance team will ask; so will their board.
Confidence — a rating you define, applied per value, that you can stand behind. "The model said so" won't survive their board.
Filings disagree with themselves and with each other. When yours do, what you did about it — and why — will come up in the final session.

Metrics to extract and compare
Category	Metric	Notes
Returns	Net return, trailing 1 / 3 / 5 year	Annualized, net of fees
Fees	Management fee (%)	As stated in prospectus/filing
Fees	Incentive fee / carried interest (%)	Include hurdle rate if disclosed
Valuation	NAV per share	Trend over last 8 quarters
Leverage	Leverage ratio (debt-to-equity)	Regulatory and/or economic leverage
Income	Distribution rate / yield (%)	Annualized
Competitor fund set
Fund	Ticker	CIK
Cliffwater Corporate Lending Fund	CCLFX	0001735964
Carlyle Tactical Private Credit Fund	TAKIX	0001725472
Golub Capital BDC	GBDC	0001476765
KKR Real Estate Finance Trust	KREF	0001631596
Note the mix: two of these are listed BDCs, two are non-traded interval funds. They all file with the SEC, but not on the same forms — the interval funds report annually and semi-annually as registered investment companies, not on 10-K.

Deliverables
Working prototype — a GitHub repository with clear setup instructions in the README. We should be able to clone, install, and run it locally by following your instructions. Any AI/ML tools, frameworks, or APIs are fair game; it should run locally or be deployable for a live demo. The output must surface per-value confidence and provenance, not just the numbers.
Technical approach document — 2–3 pages, written for the client's technical counterpart: architecture and data flow, key decisions and reasoning, your validation strategy and confidence model (how you established trust in extracted values without an answer key, what reconciliations you ran, where sources disagreed and what you chose and why), known limitations, and production risks with mitigations. Keep it in the repository.
Solution brief — 1–2 pages, written for the client's CIO and Managing Partner (a sharp, non-engineering audience). This is the business-facing counterpart to the technical approach document: what you built and what it changes about their quarterly workflow, your key choices explained in business terms, what a production rollout would look like, and the tradeoffs you made given the timeline. The kind of document they could forward to their board without you in the room. Keep it in the repository.
Scope may evolve during the build, as it does in real engagements — if anything changes, we'll reach out. If something is unclear, use a consultation window and ask rather than assume: the client relationship is yours now.
Hi Dana! My name is Aman and I'm an engineer from River. I've read the handoff and started looking at the filings. I just have a few questions to ask you so we make sure we build the right thing. I'll send them in small batches so we can group together these questions and really get to the bottom of what we're trying to do for you here. Does that sound ok to you?
Client · Dana Kellerman
Works for me. Go ahead.
You
Walk me through last quarter's benchmark: who did it, which filings they used, and what the final table looked like.
Who sees this output (PMs, board, LPs), and what decisions does it feed?
KREF is a commercial mortgage REIT, not a BDC, and lends against real estate rather than to middle-market companies. Should it stay in the peer set?
Client · Dana Kellerman
On last quarter's process: one of my credit analysts ran it. She pulled annual and semi-annual reports plus N-PORT filings from EDGAR for all four funds, read through them manually, and transcribed the numbers into our Excel comparison template. The final table has the funds as columns and the metrics as rows — net returns at 1/3/5 year, fees, NAV per share, leverage, distribution yield. That is it. No trend lines, no history, just the snapshot.

Who sees it: the PMs use it to prep the quarterly board deck and the LP letter. The board and the LP advisory committee see the final deck. So the numbers go all the way up.

What it feeds: mostly positioning narrative — how our returns and fee structure compare, whether our leverage is in line with peers. The CIO uses it to answer LP questions about why they should stay allocated to us versus rotating to one of these names.

On KREF: that is a fair question and honestly one I have not had the nerve to push on with the CIO. You are right that it is a different animal — real estate collateral, different risk profile, different LP base. My read is it ended up on the list because it is a KKR vehicle and some of our LPs have asked about it by name. But whether it belongs in a true peer comparison is debatable. I would not pull it without the CIO signing off, but I would not argue hard to keep it either. Flag it as a question for him if the data pull turns out to be meaningfully different.

What else do you have?
You
Okay, that makes sense. Thanks, Dana. That is really helpful. Just a quick follow-up: the hands-off that I was given asked for an 8-quarter nav per share trend, but you said today's table, or I guess today's table, is a snapshot. Is a trend something new that you want, or should the first version match the current snapshot? 

Also my other questions:
For the listed funds, do you compare NAV-based returns or market-price returns? For the interval funds, should I use Class I?
The funds have different fiscal year-ends. Do PMs compare as of a common quarter-end, or each fund's latest filing?
For leverage, do the PMs and board use regulatory leverage (asset coverage) or economic leverage (debt-to-equity, including preferred)? Is distribution rate measured on NAV or on price?
Client · Dana Kellerman
The 8-quarter NAV trend is something we want — it is not in the current snapshot and that is one of the gaps we are trying to close. So yes, that is new, and it is a real requirement, not a nice-to-have. The CIO wants to see how NAV has moved over time, not just where it sits today.

On NAV versus market price: for the listed funds, NAV-based. We are not trading these; we are comparing fund performance, and market price introduces noise we do not want.

On share class: yes, Class I for the interval funds. That is what is relevant to our LP base.

On fiscal year-ends: we align to a common calendar quarter-end. Latest available filing as of that date. If a fund's fiscal year-end is off-cycle, the analyst uses the most recent data available and notes the lag. That normalization problem is exactly what eats time.

On leverage: this is where I have to be honest with you. Debt-to-equity is what has always been in the table. But when I was last in front of the CIO, he said something about wanting more on leverage — regulatory versus economic, maybe both. He was not specific. I would rather you figure out what the standard treatment is for these fund types and propose something than have me guess and then have you build the wrong thing. Bring a recommendation and we will react to it.

Distribution rate: on NAV. Same logic as returns — price-based yield is not the comparison we want.

What is next?
You
Okay, yeah, that definitely clears things up. Last few questions that come to mind:
When two filings disagree, for example an amendment versus the original, or an annual report versus a later supplement, how did the analyst decide which number to use? Who signs off before it goes in the deck?
The interval funds only report NAV per share in their semi-annual reports. For the quarters in between, I can derive it from other filings and flag it as lower confidence, or show semi-annual points only. Which would you rather have?
Client · Dana Kellerman
On conflicting filings: the analyst used judgment — generally the more recent filing wins, and an amendment supersedes the original. But when it was genuinely ambiguous, she flagged it to the PM reviewing that quarter's output, and the PM made the call. The PM is the one who signs off before anything goes into the deck. I review the final output, but I am not re-pulling filings at that stage — I am trusting the PM's sign-off.

I will say this directly: if the system encounters a conflict between filings, I need to know that it did, what both values were, and which one it chose. That is not optional. That is exactly the judgment call that used to sit with the analyst, and whoever reviews the output — PM, then me — needs to be able to stand behind the choice. A silent resolution is worse than flagging it.

On the NAV trend for interval funds: show the semi-annual points only and label them clearly as such. Do not derive interim values. A derived number that looks like a real data point is the kind of thing that gets us in trouble — if someone asks where Q2 came from and the answer is "we estimated it," that is a problem at the board level. I would rather have an honest gap in the chart than a filled-in number I cannot source.

Anything else?
You
No, that is perfectly clear. Just a quick recap of what I'm thinking: I build the right thing, and please feel free to clarify whatever I say or where you think there are gaps:
an 8-quarter NAV trend (semi-annual points only for the interval funds, clearly labeled), NAV basis for returns and yield, Class I, a common calendar quarter-end with the data lag shown, every filing conflict surfaced with both values and the reason for the choice, KREF kept but flagged for the CIO, and a leverage recommendation from me.

Is there anything else I didn't ask that I should have?
Client · Dana Kellerman
That recap is accurate. A few things you did not ask that matter:

Citations. Every number needs to point to the exact filing, page, and section it came from. My compliance team re-pulls the source when they review board numbers — if they cannot find the figure where you say it is, they treat it as a wrong number. The system needs to be able to prove each value is really there before it surfaces it.

Who runs this. One of my credit analysts kicks it off each quarter. The PMs review the output directly. Nobody here uses a command line or edits configuration files, and IT will not install developer tools. Whatever the interface is, it has to work for people like that.

Normalization. You acknowledged the different fiscal year-ends, but the metric definitions vary too — gross versus net returns, annualized versus cumulative distributions, different leverage definitions across fund types. That normalization logic needs to be explicit and documented, not just handled quietly, because the PMs will ask why two numbers are not directly comparable and I need to be able to answer.

Those are the gaps I would have pushed on if you had not gotten there yourself. You have enough to move. When you have a leverage recommendation, bring it back and we will react to it.
"""Management and incentive fees: not extracted in v1 (decision 20).

Fee terms sit in narrative text and are the slowest to verify, so v1 shows "Not extracted in v1" and a
citation that lands on the sentence stating the terms: the filing link, the sentence verbatim, and a
find hint. The sentence is located and checked against the cached file like any other quote.
If it can't be located, the cell links the filing and says the terms are in the narrative.
"""
from .. import textnorm
from ..config import FEE_QUOTE_CHARS, FEE_SECTION, FEES_IN_NARRATIVE, FEES_NOT_EXTRACTED
from ..records import ValueRecord
from .common import FundData, citation, latest_filing_for, missing

METRICS = ("management_fee", "incentive_fee")


def records(data: FundData) -> dict[str, ValueRecord]:
    fund = data.fund
    latest = max(data.filings, key=lambda f: (f.period, f.filing_date)) if data.filings else None
    if latest is None:
        return {m: missing(fund.ticker, m, "not_extracted", FEES_NOT_EXTRACTED) for m in METRICS}
    filing = latest_filing_for(data, latest.period)
    path = data.fetch(filing)
    text = textnorm.document_text(path)
    phrase = FEE_SECTION[fund.ticker]
    offset = text.find(phrase)
    if offset < 0:
        where = citation(fund, filing, "Whole report", "", filing.period)
        reason = f"{FEES_NOT_EXTRACTED}. {FEES_IN_NARRATIVE} ({filing.form} {filing.accession})."
    else:
        quote = text[offset:offset + FEE_QUOTE_CHARS]
        where = citation(fund, filing, "Fee terms (narrative)", quote, filing.period, row_label=phrase,
                         char_offset=offset, find_match=text.count(phrase, 0, offset + len(phrase)),
                         find_total=text.count(phrase), sha256=data.cache.sha256(fund.cik, filing.accession,
                                                                                 filing.primary_doc))
        reason = f"{FEES_NOT_EXTRACTED}: fee terms are at the linked sentence ({filing.form} {filing.accession})."
    return {m: missing(fund.ticker, m, "not_extracted", reason, filing.period, citation=where) for m in METRICS}

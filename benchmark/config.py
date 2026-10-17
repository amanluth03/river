"""Every constant the tool depends on, in one place, each with its source.

Rule: no literal in the code without a cited source. If a filing changes the text
a pattern here relies on, the extractor finds nothing and the cell shows "not found" with the reason;
it never falls back to a guess.

Source shorthand used below (all on SEC EDGAR, cached under data/cache/<cik>/<accession>/):
  CCLFX-S25  N-CSRS 0001213900-25-118573 (period 2025-09-30)
  CCLFX-A25  N-CSR  0001213900-25-052571 (period 2025-03-31)
  TAKIX-A25  N-CSR  0001725472-26-000003 (period 2025-12-31)
  GBDC-Q126  10-Q   0001476765-26-000012 (period 2025-12-31)
  GBDC-K25   10-K   0001476765-25-000096 (period 2025-09-30)
  KREF-K25   10-K   0001628280-26-005092 (period 2025-12-31)
  W1, W2, W3 the three client conversations (Windows 1 to 3)
"""
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------- paths and the as-of window
ROOT = Path(__file__).resolve().parent.parent
STARTER = ROOT / "apex-ridge-starter" / "data"
COMPETITOR_CSV = STARTER / "competitor_cik_list.csv"  # client starter package
APEX_CSV = STARTER / "apex_ridge_fund_data.csv"  # client starter package
CACHE_DIR = ROOT / "data" / "cache"
RUNS_DIR = ROOT / "runs"
RUN_ID_FORMAT = "%Y%m%d-%H%M%S-%f"  # run folder name = run ID, stamped on exports
EXPORTS_DIR = ROOT / "exports"  # every Excel export is also saved here (gitignored)

# Apex Ridge's latest quarter in the client CSV (Q4 2025); confirmed as the as-of reading in W2.
DEFAULT_AS_OF = date(2025, 12, 31)
WINDOW_QUARTERS = 8  # "8-quarter NAV per share trend"

# ---------------------------------------------------------------- SEC EDGAR
# SEC fair-access policy: at most 10 requests/second and a User-Agent naming a contact
# (https://www.sec.gov/os/accessing-edgar-data). 0.2 s between requests keeps us at 5/second.
EDGAR_PAUSE_SECONDS = 0.2

# ---------------------------------------------------------------- funds
# The CSV carries name, ticker and CIK; these settings it doesn't.
#   kind: decides which extractor and rules apply. Sources: the CCLFX and TAKIX N-CSR cover pages
#     ("registered under the Investment Company Act of 1940 ... closed-end ... interval fund");
#     GBDC 10-K Item 1 ("elected to be regulated as a business development company");
#     KREF 10-K Item 1 (a REIT, "not ... an investment company under the Investment Company Act").
#   share_class: "Class I" for interval funds. TAKIX = Class I per its ticker in the
#     TAKIX-A25 performance table ("I Share TAKIX"). CCLFX has only Class I (CCLFX-S25 balance sheet:
#     "Class I Shares: Net assets applicable to shares outstanding").
#   forms: the periodic reports each files (EDGAR filing index for each CIK).
#   annual_form: the form that covers a fiscal year (used for the fiscal-year-end cross-check).
FUND_SETTINGS = {
    "CCLFX": {"kind": "interval", "share_class": "I", "forms": ("N-CSR", "N-CSRS"), "annual_form": "N-CSR"},
    "TAKIX": {"kind": "interval", "share_class": "I", "forms": ("N-CSR", "N-CSRS"), "annual_form": "N-CSR"},
    "GBDC": {"kind": "bdc", "share_class": None, "forms": ("10-K", "10-Q"), "annual_form": "10-K"},
    "KREF": {"kind": "mreit", "share_class": None, "forms": ("10-K", "10-Q"), "annual_form": "10-K"},
}

# ---------------------------------------------------------------- the deck table
# Row order and labels: apex-ridge-starter/docs/board_deck_excerpt.md (slide 14). The single
# "Leverage (D/E)" row became two rows, approved by Dana in W2.
ROWS = [
    ("net_return_1y", "Net return, trailing 1Y (ann.)"),
    ("net_return_3y", "Net return, trailing 3Y (ann.)"),
    ("net_return_5y", "Net return, trailing 5Y (ann.)"),
    ("management_fee", "Management fee"),
    ("incentive_fee", "Incentive fee (hurdle)"),
    ("nav_per_share", "NAV per share"),
    ("leverage_economic", "Economic leverage (debt-to-equity)"),
    ("leverage_regulatory", "Regulatory leverage (asset coverage, 1940 Act)"),
    ("distribution_yield", "Distribution yield (ann.)"),
]
# Units: usd per share, pct (10.31 means 10.31%, as in the client CSV), ratio (x).
UNITS = {"nav_per_share": "usd", "leverage_economic": "ratio", "leverage_regulatory": "pct"}

# Apex Ridge column: deck metric -> (column in apex_ridge_fund_data.csv, unit). Column names are the CSV
# header; the starter README says values are percents (10.31 means 10.31%). The CSV has no regulatory
# leverage column, so that cell shows NOT_IN_CLIENT_DATA.
APEX_FUND = "Apex Ridge"  # deck column header (board_deck_excerpt.md)
APEX_COLUMNS = {
    "net_return_1y": ("net_return_1y_pct", "pct"),
    "net_return_3y": ("net_return_3y_pct", "pct"),
    "net_return_5y": ("net_return_5y_pct", "pct"),
    "management_fee": ("management_fee_pct", "pct"),
    "incentive_fee": ("incentive_fee_pct", "pct"),
    "nav_per_share": ("nav_per_share_usd", "usd"),
    "leverage_economic": ("leverage_ratio_dte", "ratio"),
    "distribution_yield": ("distribution_yield_pct", "pct"),
}

# ---------------------------------------------------------------- labels the client fixed (exact wording)
KREF_BOOK_VALUE_LABEL = "Book value per share"  # W2: '"Book value per share" not "NAV per share"'
GBDC_RETURN_LABEL = "Return on average net assets"  # W2: "label it clearly as return on average net assets"
GBDC_RETURN_NOTE = "Not directly comparable"  # W2: "mark it not directly comparable"
NOT_REPORTED_BY_FUND = "Not reported by fund"  # W2: '"not reported" is acceptable, but label it'
NOT_IN_CLIENT_DATA = "Not in client data"
# Apex trend quarters before the CSV's first row: "Not in client data (CSV starts Q1 2024)";
# the first quarter is read from the CSV, not typed here.
APEX_TREND_GAP = NOT_IN_CLIENT_DATA + " (CSV starts {first})"  # W2: '"Not in client data" for our regulatory leverage is fine' (21)
KREF_NOT_1940_ACT = "Not applicable: KREF is not a 1940 Act fund"  # W2 draft approved by Dana
# KREF return cells: the short reason in the cell. KREF-K25 reports book value
# per share, not NAV, so there is no NAV-based total return; market-price returns are excluded.
KREF_NO_NAV_RETURN = "Not applicable: no NAV-based return (REIT reports book value)"
FEES_NOT_EXTRACTED = "Not extracted in v1"  # W2: '"Not extracted in v1" with a direct link'
FEES_IN_NARRATIVE = "Fee terms are in the prospectus narrative"  # W2 fallback wording
# Window 3: when two reported figures disagree inside one filing, show both, choose neither.
CONFLICT_PM_CHOOSE = "Conflict: PM to choose"
# Window 3: CCLFX reports asset coverage per facility only; the computed fund-level
# figure moves to a note with this label, and the cell says NOT_REPORTED_BY_FUND.
COMPUTED_LOW_NOTE = "computed, low confidence"
# What a missing cell shows: the first of these its reason starts with, else the status label below.
GAP_LABELS = [CONFLICT_PM_CHOOSE, NOT_REPORTED_BY_FUND, FEES_NOT_EXTRACTED, NOT_IN_CLIENT_DATA, KREF_NOT_1940_ACT,
              KREF_NO_NAV_RETURN, "Not applicable"]
STATUS_LABELS = {"not_found": "Not found in the filings read", "not_verified": "Not verified against the filing",
                 "fetch_failed": "EDGAR fetch failed", "excluded_by_rule": "Excluded by rule",
                 "not_reported": NOT_REPORTED_BY_FUND, "not_applicable": "Not applicable",
                 "not_extracted": FEES_NOT_EXTRACTED, "conflict": CONFLICT_PM_CHOOSE}
AMENDMENT_FLAG = "Superseded by amendment: re-check"  # client, W2: flag a value whose filing was amended

# Apex 1Y gap note: framed exactly as drafted in W2 and approved by Dana ("Note the gap and the likely
# cause in the output exactly as you framed it, and flag that the accountant needs to confirm").
APEX_GAP_NOTE = (
    "The reported 1-year return is the official figure. Compounding the four quarterly returns gives about "
    "{gap} bps more, and the gap is steady every quarter. A rounding difference would bounce around and a "
    "timing difference would move with cash flows; a steady gap behaves like a fixed annual cost counted in "
    "the 1-year figure but not in the quarterly ones (for example, a different share class or fee load, or a "
    "fee charged once a year). Likely cause, not confirmed: fund accountant to confirm.")

# Footnotes under the table (UI, Excel and Word). Each restates a rule the client set.
FOOTNOTES = [
    "As-of date {as_of}: each fund's latest report for a period ending on or before it; lags are shown in the "
    "cell.",
    "Competitor figures from SEC EDGAR filings, each verified against the source text before display. Every cell "
    "links to its filing; the Provenance table has form, accession, section, source quote and every input of "
    "a computed value.",
    "[H]/[M]/[L] = confidence. Low values are listed under Exceptions for review.",
    "CCLFX and TAKIX: Class I. Returns and distribution yields on NAV basis.",
    "Economic leverage = total debt (incl. mandatory redeemable preferred) / net assets. Regulatory leverage = "
    "asset coverage as reported under the 1940 Act.",
    "Distribution yield = trailing 12 months of distributions per share / period-end NAV per share.",
    "GBDC 1Y is its reported return on average net assets: not directly comparable to NAV total return.",
    "KREF is a mortgage REIT, not a like-for-like peer: Book value per share, no 1940 Act leverage. CIO to decide "
    "whether it stays.",
]

# ---------------------------------------------------------------- NAV per share (milestone 1)
# Row labels as printed in the filings. Interval funds: Financial Highlights, Class I
# (CCLFX-S25: "Net asset value, end of period"; TAKIX-A25: "Net asset value, end of period").
NAV_END = r"^Net asset value, end of (the )?(period|year)"
NAV_BEGIN = r"^Net asset value, beginning of (the )?(period|year)"
TOTAL_OPS = r"^Total (income )?from investment operations"  # TAKIX: "Total income from investment operations"
TOTAL_DIST = r"^Total (dividends and/or )?distributions"  # TAKIX: "Total Dividends and/or distributions..."
# KREF-K25 MD&A: "The following table calculates our book value per share (amounts in thousands, ...)".
BOOK_VALUE = r"^Book value per (common )?share"
COMMON_EQUITY = r"^Common stockholders'? equity"
TOTAL_SHARES = r"^Total shares outstanding"
# GBDC-Q126 balance sheet: "Net asset value per common share", tagged us-gaap:NetAssetValuePerShare.
NAV_CONCEPT = "us-gaap:NetAssetValuePerShare"
# Per-share figures are printed to the cent, so one cent is the rounding step of a reconciliation.
PER_SHARE_TOLERANCE = Decimal("0.01")
# Table captions that state the scale of amounts. KREF-K25 book value table: "(amounts in thousands, ...)".
SCALE_WORDS = {"in thousands": 1000, "in millions": 1_000_000}

# ---------------------------------------------------------------- leverage
# Economic leverage = total debt (incl. mandatory redeemable preferred) / net assets, all rows read from
# ONE balance-sheet table, so the table's scale (dollars or thousands) cancels out. Row labels as printed:
LEVERAGE_ROWS = {
    "CCLFX": {  # CCLFX-S25 Consolidated Statement of Assets and Liabilities
        "equity": r"^Net Assets$",
        "debt": [r"^Senior notes", r"^Secured credit facility", r"^Secured borrowings"],
    },
    "TAKIX": {  # TAKIX-A25 Consolidated Statement of Assets and Liabilities
        "equity": r"^Net Assets$",
        # "Secured credit facilities" in TAKIX-A25; "Secured credit facility" in N-CSR 0001725472-25-000003 (2024).
        "debt": [r"^Secured credit facilit(y|ies)", r"^Mandatory redeemable preferred shares", r"^Note-on-note loans"],
    },
    "GBDC": {  # GBDC-Q126 Consolidated Statements of Financial Condition. "Debt $ 4,903,076" is carrying value: the
        # 10-Q says it "Represents principal outstanding plus unamortized premium and / or unaccreted original
        # issue discount" and is "inclusive of an adjustment for the change in fair value of an effective hedge".
        "equity": r"^Total Net Assets",
        "debt": [r"^Debt$"],
    },
    "KREF": {  # KREF-K25 Consolidated Balance Sheets. Debt lines = KREF's own "total leverage ratio" footnote
        # (B): "total outstanding debt agreements, secured term loan, and collateralized loan obligations".
        "equity": r"^Total KKR Real Estate Finance Trust Inc\. Stockholders'? Equity",
        "debt": [r"^Secured financing agreements", r"^Collateralized loan obligations", r"^Secured term loan"],
        "cash": r"^Cash and cash equivalents",
    },
}
# Regulatory leverage as each fund reports it.
#   TAKIX-A25 Note 7: "asset coverage (exclusive of preferred equity shares) was 704.8% and asset coverage
#   (inclusive of preferred equity shares) was 352.0%". We show the inclusive figure (debt + preferred).
TAKIX_COVERAGE_SENTENCE = (r"As of (?P<date>\w+ \d{1,2}, \d{4}), asset coverage \(exclusive of preferred equity "
                           r"shares\) was (?P<debt_only>[\d.]+)% and asset coverage \(inclusive of preferred equity "
                           r"shares\) was (?P<value>[\d.]+)%\.")
#   GBDC-Q126 financial highlights: "Asset coverage ratio(7) 178.94%", tagged with this concept.
COVERAGE_CONCEPT = "us-gaap:InvestmentCompanySeniorSecurityIndebtednessAssetCoverageRatio"
#   CCLFX-S25 reports asset coverage per facility only ("Asset Coverage Per $1,000 of Borrowings"), so the
#   fund-level figure is computed from the balance sheet and labeled as computed.
# 1940 Act minimums, shown next to the value:
#   BDC: 150% (GBDC-K25: "the asset coverage ratio under the 1940 Act applicable to us decreased to 150%").
#   Registered closed-end fund: 300% for debt (1940 Act s.18(a)(1)(A); TAKIX-A25 Note 7 "at least 300%"),
#   200% for debt plus preferred (1940 Act s.18(a)(2)(A)).
COVERAGE_MINIMUM = {"bdc": "150%", "interval": "300% for debt, 200% for debt plus preferred"}
# Our D/E and the D/E implied by reported coverage need not match exactly: coverage counts senior securities
# at principal while balance sheets show carrying value, and KREF prints its ratio to 0.1x. 0.05x is half of
# KREF's rounding step; a larger gap means a debt line is missing or misread.
LEVERAGE_TOLERANCE = Decimal("0.05")
# KREF-K25 MD&A "Debt-to-Equity Ratio and Total Leverage Ratio" table: "Total leverage ratio(B) 3.9x".
KREF_TOTAL_LEVERAGE = r"^Total leverage ratio"
KREF_DEBT_TO_EQUITY = r"^Debt-to-equity ratio"

# ---------------------------------------------------------------- distributions
# Yield = trailing-12-month distributions per share / period-end NAV per share (W2, Apex's own basis).
DISTRIBUTION_ROWS = {
    "CCLFX": r"^Total Distributions to shareholders",  # CCLFX-S25 Financial Highlights Class I
    "TAKIX": r"^Total Dividends and/or distributions to shareholders",  # TAKIX-A25 Financial Highlights
    "KREF": r"^Dividends Declared per Share of Common Stock",  # KREF-K25 Consolidated Statements of Income
}
# Column titles that state a period's length, as printed: CCLFX-S25 "For the Six Months Ended September 30,
# 2025", "For the Year Ended March 31, 2025"; TAKIX-A25 "Year Ended December 31,"; GBDC-Q126 "Three months
# ended December 31,". A title matching none (CCLFX "For the Period January 1, 2022 through March 31, 2022")
# or two of these gets no length, and is never used in a trailing-12-month sum.
PERIOD_LENGTHS = [(r"\bthree months ended\b", 3), (r"\bsix months ended\b", 6), (r"\bnine months ended\b", 9),
                  (r"\byears? ended\b", 12)]
# GBDC-Q126 / GBDC-K25: "Dividends and distributions declared per common share", tagged with:
DISTRIBUTION_CONCEPT = "us-gaap:CommonStockDividendsPerShareDeclared"
# GBDC special and supplemental distributions: a trailing 12 months that includes one says so.
# Source: GBDC-K25 Item 5 distributions table, footnotes (4) and (5); each quote must still be in the cached
# filing for the note to appear. Payment dates and amounts are as those footnotes state them.
GBDC_SPECIALS_SOURCE = ("1476765", "0001476765-25-000096", "gbdc-20250930.htm",
                        "10-K 0001476765-25-000096, Item 5 distributions table, footnotes (4) and (5)")
GBDC_SPECIALS_QUOTES = [
    "declared a supplemental distribution of $0.04 paid on December 13, 2024",
    "declared a series of special distributions totaling $0.15 per share, distributed in three consecutive "
    "quarterly payments of $0.05 per share per quarter. The first and second special distributions were paid to "
    "stockholders on June 27, 2024 and September 13, 2024, respectively. The remaining special distribution was "
    "paid on December 13, 2024",
]
# GBDC per-quarter distributions declared per share: 10-K Item 5 table ("Period ... Distributions Declared",
# rows "Fiscal year ended September 30, 2024" then "Fourth quarter ... $ 0.44" etc.; GBDC-K24 and GBDC-K25).
# Used when a fiscal-year total differs from the sum of its quarters: the FY2024 statement total ($1.89) is per
# weighted-average share (highlights footnote (1)) in the year of the GBDC 3 merger, while the quarters declared
# per share sum to $1.94. Distributions are the table's last column ("Distributions Declared").
GBDC_QUARTERS_YEAR_ROW = r"^Fiscal year ended (\w+ \d{1,2}, \d{4})$"
GBDC_QUARTERS_LAST_HEADER = "Distributions Declared"
GBDC_QUARTER_NUMBER = {"First quarter": 1, "Second quarter": 2, "Third quarter": 3, "Fourth quarter": 4}
GBDC_SPECIALS = [("2024-06-27", "0.05", "special"), ("2024-09-13", "0.05", "special"),
                 ("2024-12-13", "0.05", "special"), ("2024-12-13", "0.04", "supplemental")]
# A fiscal year or a trailing year is 365 or 366 days between context start and end; 360-370 allows
# for period ends that fall on a weekend.
DAYS_ONE_YEAR = (360, 370)
# XBRL duration (days from context start to end) -> months. A 10-Q tags the quarter and the year to date
# (GBDC-Q2 FY25: six months to 3/31/25), so 6- and 9-month pieces exist and are needed for a TTM.
PERIOD_DAYS = [((88, 93), 3), ((180, 184), 6), ((271, 276), 9), (DAYS_ONE_YEAR, 12)]

# ---------------------------------------------------------------- returns
# Interval funds: the annual report's performance table.
#   TAKIX-A25: "Average Annual Total Returns through December 31, 2025* Class Ticker Inception Date 1-Year
#   5-Year(1) Since Inception(1) ... I Share TAKIX 9/4/2018 6.27% 8.21% 6.38%".
#   CCLFX-A25: "Average Annual Total Returns as of March 31, 2025 1 Year 3 Year 5 Year Since Inception
#   Cliffwater Corporate Lending Fund (Inception Date June 5, 2019) 11.78 % 10.69 % 10.98 % 9.62 %".
RETURN_TABLE_CAPTION = r"Average Annual Total Returns (?:through|as of) (\w+ \d{1,2}, \d{4})"
RETURN_ROW = {"CCLFX": r"^Cliffwater Corporate Lending Fund", "TAKIX": r"^I Share$"}
RETURN_HEADER = r"^\d+[- ]Year"  # a header cell like "1-Year" or "1 Year" marks the header row
RETURN_COLUMNS = {"net_return_1y": r"^1[- ]Year", "net_return_3y": r"^3[- ]Year", "net_return_5y": r"^5[- ]Year"}
# Second source for the 1Y figure: the same fiscal year's total return in the Financial Highlights.
HIGHLIGHTS_RETURN_ROW = {"CCLFX": r"^Total return", "TAKIX": r"^Total Return, at Net Asset Value"}
# Returns are printed to two decimals; agreement means equal to the basis point.
RETURN_TOLERANCE = Decimal("0.00")
# GBDC-K25 Financial Highlights: "Total return based on average net asset value(6) 9.36%", footnote (6):
# "the net increase (decrease) in net assets resulting from operations divided by ... the daily average
# of total net assets". Tagged with this concept. Market-value return (InvestmentCompanyTotalReturnMarketValue)
# is excluded by the NAV-basis rule.
GBDC_RETURN_CONCEPT = "us-gaap:InvestmentCompanyTotalReturn"

# ---------------------------------------------------------------- fees
# Fee terms are not extracted in v1. The link goes to the sentence in the latest report that states the
# fee terms; the citation records it verbatim with a find hint. Each phrase below is where that sentence
# starts, copied from the filing named.
FEE_SECTION = {
    "CCLFX": "the Fund pays the Investment Manager a monthly Investment Management Fee",  # CCLFX-S25 notes
    "TAKIX": "The base management fee is calculated at an annual rate of",  # TAKIX-A25 Note 5
    "GBDC": "The base management fee is calculated at an annual rate equal to",  # GBDC-Q126 Note 3
    "KREF": "our Manager is entitled to a quarterly management fee",  # KREF-K25 MD&A
}
FEE_QUOTE_CHARS = 400
# Client, W3: if the latest annual report never mentions incentive-fee terms (CCLFX N-CSR
# 0001213900-25-052571 has 0 matches for "incentive" or "hurdle"; TAKIX, GBDC and KREF reports do), the
# incentive cell says so and links the nearest fee section. Never "charges no incentive fee": no quote says it.
INCENTIVE_TERMS = r"incentive|hurdle"
# Where each report states its incentive-fee terms; the incentive row links here.
# Each phrase occurs once in its report. KREF's management and incentive terms share one sentence (FEE_SECTION).
INCENTIVE_FEE_SECTION = {
    "TAKIX": "the Fund pays its Adviser an incentive fee",  # TAKIX-A25 Note 5
    "GBDC": "The income and capital gains incentive fee calculation",  # GBDC-Q126 Note 3
}
NO_INCENTIVE_TERMS_NOTE = "Annual report states no incentive-fee terms; see prospectus fee table"
# Client, W3: the fee cell shows its link in the cell itself.
FEE_LINK_TEXT = "view fee terms ↗"  # how much of the fee sentence the citation shows (enough for the rate and its base)

# ---------------------------------------------------------------- text handling
# HTML tags that end a visual unit. A space is inserted there so "$" and "8.32" in two table cells
# become "$ 8.32", not "$8.32". Block-level and table elements per the HTML spec.
BLOCK_TAGS = {"td", "th", "tr", "p", "div", "br", "li", "table", "tbody", "thead",
              "h1", "h2", "h3", "h4", "h5", "h6"}
# How far (characters of normalized text) above a quoted row the verifier looks for the column header.
# Longest header-to-row distance among the values shown on 2025-12-31: 1,721 characters (KREF income
# statement, "Dividends Declared per Share of Common Stock"). 6000 leaves room for longer statements;
# tests/test_verify.py::test_header_window_covers_every_row_we_read re-measures it on every test run.
HEADER_WINDOW = 6000
# A single-period statement may carry its date only in the caption just above the table, e.g. CCLFX-S25
# "Consolidated Statement of Assets and Liabilities September 30, 2025 (Unaudited)" (73 characters).
# Only the last 150 characters before the table are searched, so an unrelated date further up is ignored.
CAPTION_CHARS = 150


@dataclass(frozen=True)
class Fund:
    ticker: str
    name: str
    cik: str
    kind: str  # "interval" | "bdc" | "mreit"
    share_class: str | None
    forms: tuple[str, ...]
    annual_form: str


def load_funds(path: Path = COMPETITOR_CSV) -> list[Fund]:
    """Read the client's competitor list and attach our per-fund settings."""
    funds = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            settings = FUND_SETTINGS[row["ticker"]]
            funds.append(Fund(ticker=row["ticker"], name=row["fund"], cik=row["cik"], **settings))
    return funds


def quarter_end(year: int, quarter: int) -> date:
    month = quarter * 3
    day = 31 if month in (3, 12) else 30
    return date(year, month, day)


def window_quarters(as_of: date, count: int = WINDOW_QUARTERS) -> list[date]:
    """The `count` calendar quarter-ends ending at `as_of` (which must be a quarter-end)."""
    year, quarter = as_of.year, (as_of.month - 1) // 3 + 1
    ends = []
    for _ in range(count):
        ends.append(quarter_end(year, quarter))
        quarter -= 1
        if quarter == 0:
            year, quarter = year - 1, 4
    return list(reversed(ends))


def quarters_between(earlier: date, later: date) -> int:
    """Whole quarters from `earlier` to `later` (used to show data lag)."""
    return ((later.year - earlier.year) * 12 + (later.month - earlier.month)) // 3


# ---------------------------------------------------------------- fee link landing (Window 3 fix)
# FEE-LINK CONSTANTS: owned by the fee-link task; add new fee-link constants below this line only.
# Client, W3: a fee link must land "on or right next to the fee sentence (at most two scrolls away)".
# First choice is a URL text fragment (#:~:text=..., the W3C/WICG "Text Fragments" spec; Chrome/Edge 81+,
# Safari 16.1+, Firefox 131+). Browsers match it case-insensitively and jump to the FIRST match, so it is
# only used when the words occur once in the document (a repeated label once landed on TAKIX's Class A table).
# The fragment grows one word at a time from the FEE_SECTION phrase until unique, up to this many words
# (the fee sentence itself is rarely longer; past that we are no longer pointing at one sentence).
FEE_FRAGMENT_MAX_EXTRA_WORDS = 40
# Characters our text normalizer may have produced from a different page character (textnorm._CHAR_MAP:
# curly quotes and dashes become ' " -). A fragment containing one might not match the page, so it never
# grows past a word that holds one.
FEE_FRAGMENT_UNSAFE_CHARS = "'\"-"
# Fallback: the nearest HTML element id before the sentence (#id), if it is at most this many characters
# of document text before it. "Two scrolls" ~ two screens; a screen of an EDGAR filing on a laptop shows
# roughly 2,000 characters when tables or spacing are present (dense prose shows more), so 4,000 is the
# conservative end. Beyond that the link stays the plain document URL and the record says so.
FEE_ANCHOR_MAX_CHARS = 4000


# DEEP-LINK CONSTANTS (owned by the deep-link task)
# Every citation link lands on its source text. benchmark/links.py
# reuses the fee-link rules above (FEE_FRAGMENT_UNSAFE_CHARS, FEE_FRAGMENT_MAX_EXTRA_WORDS, the encoding).
# A narrative quote (no row label) starts its fragment with this many words, then grows until unique:
# four words make a visible highlight; one or two could be a lone common word.
DEEP_LINK_QUOTE_START_WORDS = 4
# When the row label repeats (TAKIX "Net asset value, end of period": 7 classes), the link goes to the
# nearest text before the row that occurs once: a heading or caption, so at most this many words
# (task brief: "a cell/paragraph text of <= ~12 words"; longer blocks are body text, not a heading).
DEEP_LINK_HEADING_MAX_WORDS = 12
# ...and no further back than this many characters of document text: the same "two scrolls" bound
# as the fee anchor fallback (FEE_ANCHOR_MAX_CHARS), so the reader still sees the row after one search.
DEEP_LINK_HEADING_WINDOW = FEE_ANCHOR_MAX_CHARS

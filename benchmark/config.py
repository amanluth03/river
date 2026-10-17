"""Fund list, per-fund settings, paths and the as-of window."""
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STARTER = ROOT / "apex-ridge-starter" / "data"
COMPETITOR_CSV = STARTER / "competitor_cik_list.csv"
APEX_CSV = STARTER / "apex_ridge_fund_data.csv"
CACHE_DIR = ROOT / "data" / "cache"
RUNS_DIR = ROOT / "runs"

DEFAULT_AS_OF = date(2025, 12, 31)

# Settings the CSV doesn't carry. "kind" decides which extractor and which rules apply.
FUND_SETTINGS = {
    "CCLFX": {"kind": "interval", "share_class": "I", "forms": ("N-CSR", "N-CSRS")},
    "TAKIX": {"kind": "interval", "share_class": "I", "forms": ("N-CSR", "N-CSRS")},
    "GBDC": {"kind": "bdc", "share_class": None, "forms": ("10-K", "10-Q")},
    "KREF": {"kind": "mreit", "share_class": None, "forms": ("10-K", "10-Q")},
}


@dataclass(frozen=True)
class Fund:
    ticker: str
    name: str
    cik: str
    kind: str  # "interval" | "bdc" | "mreit"
    share_class: str | None
    forms: tuple[str, ...]


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


def window_quarters(as_of: date, count: int = 8) -> list[date]:
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

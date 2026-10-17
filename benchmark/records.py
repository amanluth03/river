"""The data model. Every number travels as a record with its source, never as a bare value."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from .config import GAP_LABELS, RUN_ID_FORMAT, STATUS_LABELS

Status = Literal[
    "ok",  # verified and shown
    "not_found",  # we looked where it should be and didn't find it
    "not_verified",  # found, but failed the verification gate
    "not_reported",  # the fund doesn't report this
    "not_applicable",  # the metric doesn't apply to this fund type
    "not_extracted",  # v1 does not extract this (fees); the record links to where the terms are
    "excluded_by_rule",  # e.g. market-price return, excluded by the NAV-basis rule
    "fetch_failed",  # EDGAR could not be reached for this fund
    "conflict",  # two verified figures disagree and the client's rule is to show both, choose neither
]
Method = Literal["ixbrl", "table", "regex", "llm", "computed", "client_csv"]


class Citation(BaseModel):
    cik: str
    form: str
    accession: str
    filing_date: date | None = None
    period_end: date | None = None
    url: str
    document: str
    section: str
    quote: str
    row_label: str | None = None
    column_label: str | None = None
    column_header: str | None = None  # header text that dates the column, e.g. "Year Ended December 31, | 2025"
    char_offset: int | None = None
    find_match: int | None = None  # the value's row is match N of find_total when searching the row label
    find_total: int | None = None
    sha256: str | None = None
    fact_id: str | None = None  # inline XBRL element id, when the value is tagged
    concept: str | None = None  # inline XBRL concept name, e.g. us-gaap:NetAssetValuePerShare


class Candidate(BaseModel):
    """One value seen in one place. Several candidates may compete for one table cell."""
    fund: str
    metric: str
    value: Decimal
    unit: str
    period_end: date
    method: Method
    citation: Citation
    column_index: int | None = None  # which number in the quote is the value (tables)
    is_amendment: bool = False
    reconciliation: str | None = None  # description of the check that was run
    reconciliation_ok: bool | None = None
    verified: bool = False
    verify_reason: str = ""


class ValueRecord(BaseModel):
    fund: str
    metric: str
    value: Decimal | None
    unit: str
    status: Status
    reason: str = ""
    label: str | None = None  # overrides the row label, e.g. KREF book value
    note: str = ""  # short text shown with the value, e.g. "hurdle 6.00%"
    period_end: date | None = None
    lag_quarters: int | None = None
    citation: Citation | None = None
    method: Method | None = None
    confidence: Literal["high", "medium", "low"] | None = None
    confidence_reason: str = ""
    candidates: list[Candidate] = Field(default_factory=list)
    resolution: str = ""
    flags: list[str] = Field(default_factory=list)
    normalizations: list[str] = Field(default_factory=list)
    inputs: list[Candidate] = Field(default_factory=list)  # computed values: every verified input, each cited
    check: str = ""  # an independent comparison that was run on a computed value, and its result

    @model_validator(mode="after")
    def _status_matches_value(self):
        if self.status == "ok":
            if self.value is None:
                raise ValueError("status 'ok' needs a value")
            if self.citation is None:
                raise ValueError("a shown value must carry a citation")
            if self.method == "computed" and not self.inputs:
                raise ValueError("a computed value must list its inputs")
            if self.method == "computed" and not all(c.verified for c in self.inputs):
                raise ValueError("a computed value may only use verified inputs")
        elif self.value is not None:
            raise ValueError("a missing value must not carry a number")
        return self

    @computed_field
    @property
    def gap(self) -> str:
        """What a missing cell says, never blank: the client's wording if it applies."""
        if self.value is not None:
            return ""
        for label in GAP_LABELS:
            if self.reason.startswith(label + " ("):  # keep a short qualifier, e.g. "(CSV starts Q1 2024)"
                return self.reason[:self.reason.index(")", len(label)) + 1]
            if self.reason.startswith(label):
                return label
        return STATUS_LABELS.get(self.status, self.status)

    def display(self) -> str:
        if self.value is None:
            return "—"
        if self.unit == "usd":
            return f"${self.value:,.2f}"
        if self.unit == "pct":
            return f"{self.value:.2f}%"
        return f"{self.value:.2f}x"


class Issue(BaseModel):
    """One line in the Exceptions list."""
    kind: Literal["conflict", "missing", "lag", "computed", "not_like_for_like",
                  "client_data", "peer_question", "data_quality", "fetch", "amendment",
                  "not_comparable", "check_failed"]
    fund: str
    metric: str | None = None
    message: str
    details: dict = Field(default_factory=dict)


class RunBundle(BaseModel):
    as_of: date
    created_at: datetime
    code_version: str = ""
    funds: list[str]
    rows: list[tuple[str, str]]  # (metric key, display label), deck order
    table: dict[str, dict[str, ValueRecord]]  # metric -> fund -> record
    trend: dict[str, list[ValueRecord]]  # fund -> NAV points in the window
    issues: list[Issue]
    filings: list[dict] = Field(default_factory=list)  # every filing used, with hash
    footnotes: list[str] = Field(default_factory=list)  # shown under the table and in Excel

    @property
    def run_id(self) -> str:
        """The run's folder name under runs/, which holds its bundle.json (pipeline.run writes it there)."""
        return self.created_at.strftime(RUN_ID_FORMAT)

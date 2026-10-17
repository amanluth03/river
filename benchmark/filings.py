"""Which filings exist for a fund, and what period each one covers."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class Filing:
    form: str
    accession: str
    filing_date: date
    period: date
    primary_doc: str
    amendment: bool


def list_filings(submissions: dict, forms: tuple[str, ...], since: date) -> list[Filing]:
    """Filings of the given forms (and their /A amendments) filed on or after `since`, oldest first.

    The period is the per-filing "period of report", never the company-level fiscalYearEnd.
    """
    recent = submissions["filings"]["recent"]
    wanted = set(forms) | {f + "/A" for f in forms}
    found = []
    for form, acc, filed, period, doc in zip(recent["form"], recent["accessionNumber"], recent["filingDate"],
                                             recent["reportDate"], recent["primaryDocument"]):
        if form not in wanted or not period:
            continue
        filed_date = date.fromisoformat(filed)
        if filed_date < since:
            continue
        found.append(Filing(form=form, accession=acc, filing_date=filed_date, period=date.fromisoformat(period),
                            primary_doc=doc, amendment=form.endswith("/A")))
    return sorted(found, key=lambda f: (f.filing_date, f.accession))


def fiscal_year_end_mismatch(submissions: dict, filings: list[Filing], annual_form: str) -> str | None:
    """Explain it if EDGAR's company-level fiscal year-end disagrees with the annual reports' periods."""
    metadata = submissions.get("fiscalYearEnd")
    annuals = [f for f in filings if f.form == annual_form]
    if not metadata or not annuals:
        return None
    actual = {f.period.strftime("%m-%d") for f in annuals}
    if actual == {f"{metadata[:2]}-{metadata[2:]}"}:
        return None
    example = annuals[-1]
    return (f"EDGAR company metadata lists fiscal year-end {metadata}, but {annual_form} annual reports cover "
            f"periods ending {', '.join(sorted(actual))} (e.g. {example.accession}, period {example.period}). "
            f"Using each filing's own period.")


_DEI_PERIOD = re.compile(r'name="dei:DocumentPeriodEndDate"[^>]*>(.*?)</ix:nonNumeric>', re.IGNORECASE | re.DOTALL)


def document_period(path: Path) -> date | None:
    """The period the document says it covers (inline XBRL cover tag), for cross-checking the index."""
    with open(path, "rb") as f:
        head = f.read(3_000_000).decode("utf-8", "ignore")
    match = _DEI_PERIOD.search(head)
    if not match:
        return None
    text = re.sub(r"<[^>]+>", "", match.group(1)).replace("\xa0", " ").strip()
    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None

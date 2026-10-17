"""Cut small test fixtures out of the cached EDGAR filings, so tests run offline on real values.

Run once after the filings are cached (a live run caches them):  uv run python tests/cut_fixtures.py

Each fixture keeps, verbatim from the filing: every table that contains one of the listed row labels
(with the text just above it, which carries captions such as "(amounts in thousands)"), every paragraph
containing one of the listed phrases, and the inline-XBRL contexts the kept tags refer to.
Nothing is typed by hand, so a test value is a value in the real filing.
"""
import re
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from benchmark import textnorm  # noqa: E402
from benchmark.extract import tables  # noqa: E402

CACHE = ROOT / "data" / "cache"
OUT = Path(__file__).parent / "fixtures"

# fixture name -> (cached document, row labels whose tables to keep, phrases whose paragraphs to keep)
FIXTURES = {
    "cclfx_ncsrs_2025-09_full.html": (
        "1735964/000121390025118573/ea0264761-01_ncsrs.htm",
        ["Net asset value, end of period", "Secured credit facility (Note 2)"],
        ["the Fund pays the Investment Manager a monthly Investment Management Fee"]),
    "cclfx_ncsrs_2024-09.html": (
        "1735964/000121390024106851/ea0221175-01_ncsrs.htm", ["Net asset value, end of period"], []),
    "cclfx_ncsr_2025-03.html": (
        "1735964/000121390025052571/ea0241342-01_ncsr.htm",
        ["Net asset value, end of period", "Cliffwater Corporate Lending Fund (Inception Date",
         "Secured credit facility (Note 2)"],
        ["the Fund pays the Investment Manager a monthly Investment Management Fee"]),
    "takix_ncsr_2025_full.html": (
        "1725472/000172547226000003/ctac-20251231.htm",
        ["Net asset value, end of period", "Note-on-note loans", "I Share"],
        ["asset coverage (inclusive of preferred equity shares)",
         "The base management fee is calculated at an annual rate of"]),
    "gbdc_10q_2025-12_full.html": (
        "1476765/000147676526000012/gbdc-20251231.htm",
        ["Net asset value per common share", "Asset coverage ratio", "Dividends and distributions declared per common share"],
        ["The base management fee is calculated at an annual rate equal to"]),
    "gbdc_10k_2025.html": (
        "1476765/000147676525000096/gbdc-20250930.htm",
        ["Total return based on average net asset value", "Dividends and distributions declared per common share"], []),
    "kref_10k_2025.html": (
        "1631596/000162828026005092/kref-20251231.htm",
        ["Book value per share", "Secured term loan, net", "Dividends Declared per Share of Common Stock",
         "Total leverage ratio"],
        ["our Manager is entitled to a quarterly management fee"]),
}


def _serialize(el) -> str:
    """The element's HTML without style attributes (layout only; the text and tags are unchanged)."""
    html = etree.tostring(el, encoding="unicode", method="html", with_tail=False)
    return re.sub(r'\s(?:style|class)="[^"]*"', "", html)


def _rows_starting(root, label: str):
    for tr in root.xpath("//tr"):
        cells = tables._cells(tr)
        if cells and cells[0].startswith(label):
            yield tr


def _paragraph(root, phrase: str):
    for el in root.xpath("//p|//div[not(.//div) and not(.//table)]|//span[not(ancestor::p)]"):
        if phrase in textnorm.element_text(el):
            return el
    return None


def cut(source: Path, labels: list[str], phrases: list[str]) -> str:
    root = textnorm.parse_html(source)
    parts, kept = [], []
    for label in labels:
        for tr in _rows_starting(root, label):
            table = tables._table_of(tr)
            if table is None or any(table is k for k in kept):
                continue
            kept.append(table)
            parts.append(f"<p>{_escape(tables._preceding_text(table))}</p>")
            parts.append(_serialize(table))
    for phrase in phrases:
        el = _paragraph(root, phrase)
        if el is None:
            raise SystemExit(f"phrase not found in {source}: {phrase}")
        parts.append(f"<p>{_escape(textnorm.element_text(el))}</p>")
    body = "\n".join(parts)
    # Keep the XBRL contexts the kept tags point to, so tagged facts keep their periods.
    refs = set(re.findall(r'contextref="([^"]+)"', body, re.IGNORECASE))
    raw = source.read_text(encoding="utf-8", errors="ignore")
    contexts = [m.group(0) for m in re.finditer(r'<xbrli:context id="([^"]+)">.*?</xbrli:context>', raw, re.S)
                if m.group(1) in refs]
    if contexts:
        body += '\n<div style="display:none"><ix:header><ix:resources>' + "".join(contexts) + "</ix:resources></ix:header></div>"
    return "<html><body>" + body + "</body></html>"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    for name, (doc, labels, phrases) in FIXTURES.items():
        html = cut(CACHE / doc, labels, phrases)
        (OUT / name).write_text(html, encoding="utf-8")
        print(f"{name}: {len(html):,} bytes")

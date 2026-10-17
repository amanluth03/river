"""Read inline-XBRL tagged numbers straight from a filing document, with their periods.

We use lxml rather than a full XBRL processor. Only what we need:
concept name, context period, dimensions (e.g. share class), scale, sign and the shown text.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from .. import textnorm
from ..verify import parse_numbers


@dataclass
class Fact:
    concept: str
    value: Decimal  # the true value (scale and sign applied)
    shown: Decimal  # the number as printed on the page
    period_end: date
    period_start: date | None = None  # None for an instant (balance-sheet date); set for a duration
    dims: dict = field(default_factory=dict)
    fact_id: str = ""
    row_quote: str = ""  # the table row (or paragraph) the number sits in
    row_label: str = ""


def _contexts(root) -> dict[str, tuple[date, date | None, dict]]:
    contexts = {}
    for ctx in root.xpath("//*[name()='xbrli:context']"):
        end = ctx.xpath(".//*[name()='xbrli:instant' or name()='xbrli:enddate']/text()")
        if not end:
            continue
        start = ctx.xpath(".//*[name()='xbrli:startdate']/text()")
        dims = {m.get("dimension"): textnorm.normalize(m.text or "")
                for m in ctx.xpath(".//*[name()='xbrldi:explicitmember']")}
        contexts[ctx.get("id")] = (date.fromisoformat(end[0].strip()),
                                   date.fromisoformat(start[0].strip()) if start else None, dims)
    return contexts


def _container_text(el) -> tuple[str, str]:
    node = el
    while node is not None and node.tag not in ("tr", "p", "div"):
        node = node.getparent()
    if node is None:
        return "", ""
    if node.tag == "tr":
        cells = [t for t in (textnorm.element_text(c) for c in node.xpath("./td|./th")) if t]
        return textnorm.element_text(node), (cells[0] if cells else "")
    return textnorm.element_text(node), ""


def facts(path: Path, concept: str) -> list[Fact]:
    root = textnorm.parse_html(path)
    contexts = _contexts(root)
    found = []
    for el in root.xpath("//*[name()='ix:nonfraction'][@name=$c]", c=concept):
        ctx = contexts.get(el.get("contextref"))
        numbers = parse_numbers(textnorm.element_text(el))
        if ctx is None or not numbers:
            continue
        shown = numbers[0]
        value = shown.scaleb(int(el.get("scale", "0")))
        if el.get("sign") == "-":
            value = -value
        quote, label = _container_text(el)
        found.append(Fact(concept=concept, value=value, shown=shown, period_end=ctx[0], period_start=ctx[1],
                          dims=ctx[2],
                          fact_id=el.get("id", ""), row_quote=quote, row_label=label))
    return found

"""Custom-metric definitions: what a metric means, where it comes from, and who owns it.

Definitions layer only (Window 3). Nothing here extracts values; the pipeline does not read
this file yet. A definition with any required field missing or blank is refused on load and
on save, and save validates every definition before writing anything.
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path

# Every field a definition must have. All are required; none may be blank.
REQUIRED_FIELDS = ("key", "name", "definition", "unit", "source_shape", "shape",
                   "normalization_assumptions", "owner", "sources")
# The units ValueRecord already formats, see ValueRecord.display in benchmark/records.py.
ALLOWED_UNITS = ("pct", "usd", "ratio")
# The source shapes the client asked for, each with the shape details it needs.
SHAPE_FIELDS = {
    "table_row": ("row_label_pattern", "section"),  # a labeled row in a filing table
    "xbrl_tag": ("concept",),  # an inline XBRL concept, e.g. us-gaap:NetAssetValuePerShare
    "ratio_of_metrics": ("numerator", "denominator"),  # two other metric keys
}
# Client, W3: a custom metric starts at Medium confidence at most, whatever its
# checks, until it has a track record. The pipeline will apply this cap when it reads definitions.
MAX_CONFIDENCE = "medium"


def capped_confidence(confidence: str) -> str:
    """The confidence a custom-metric value may show: never above MAX_CONFIDENCE."""
    order = ["low", "medium", "high"]
    return min(confidence, MAX_CONFIDENCE, key=order.index)


# What a reviewer needs to re-find a source, matching the Citation fields in benchmark/records.py.
SOURCE_FIELDS = ("form", "accession", "document", "section", "quote")


class DefinitionError(ValueError):
    """Raised with every problem found, one line per problem, each naming its metric."""


@dataclass
class Definition:
    key: str
    name: str
    definition: str
    unit: str
    source_shape: str
    shape: dict
    normalization_assumptions: list
    owner: str
    sources: list


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _problems(raw: dict) -> list[str]:
    """Every problem with one definition, as plain sentences naming the metric."""
    name = raw.get("key") if not _is_blank(raw.get("key")) else "(no key)"
    problems = [f"{name}: '{f}' is missing or blank" for f in REQUIRED_FIELDS if _is_blank(raw.get(f))]
    if not _is_blank(raw.get("unit")) and raw["unit"] not in ALLOWED_UNITS:
        problems.append(f"{name}: unit '{raw['unit']}' is not one of {ALLOWED_UNITS}")
    shape_type = raw.get("source_shape")
    if not _is_blank(shape_type) and shape_type not in SHAPE_FIELDS:
        problems.append(f"{name}: source_shape '{shape_type}' is not one of {tuple(SHAPE_FIELDS)}")
    elif shape_type in SHAPE_FIELDS:
        details = raw.get("shape") or {}
        for f in SHAPE_FIELDS[shape_type]:
            if _is_blank(details.get(f)):
                problems.append(f"{name}: {shape_type} needs shape.{f}")
    for i, source in enumerate(raw.get("sources") or []):
        for f in SOURCE_FIELDS:
            if _is_blank(source.get(f)):
                problems.append(f"{name}: sources[{i}].{f} is missing or blank")
    return problems


def _validate(raws: list[dict]) -> None:
    problems = []
    for raw in raws:
        problems.extend(_problems(raw))
    keys = [r.get("key") for r in raws if not _is_blank(r.get("key"))]
    problems.extend(f"{k}: duplicate key" for k in sorted({k for k in keys if keys.count(k) > 1}))
    if problems:
        raise DefinitionError("Custom metric definitions are invalid:\n" + "\n".join(problems))


def load(path: Path) -> list[Definition]:
    raws = json.loads(Path(path).read_text())
    _validate(raws)
    return [Definition(**{f: raw[f] for f in REQUIRED_FIELDS}) for raw in raws]


def save(definitions: list[Definition], path: Path) -> None:
    """Validate every definition first; write only if all pass, so no partial file is left."""
    raws = [asdict(d) for d in definitions]
    _validate(raws)
    Path(path).write_text(json.dumps(raws, indent=2) + "\n")

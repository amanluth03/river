"""Custom-metric definitions: every field is required, and a bad file is never written."""
import copy
import json
from pathlib import Path

import pytest

from benchmark import custom_metrics
from benchmark.custom_metrics import DefinitionError, load, save

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "benchmark" / "custom_metrics.json"


def good_raw() -> dict:
    """A valid definition as it appears in the JSON file."""
    return {
        "key": "test_metric",
        "name": "Test metric",
        "definition": "A metric used only by the tests.",
        "unit": "pct",
        "source_shape": "table_row",
        "shape": {"row_label_pattern": "Test row", "section": "Financial Highlights"},
        "normalization_assumptions": ["none"],
        "owner": "Apex Ridge analytics team (to confirm)",
        "sources": [{"form": "10-Q", "accession": "0000000000-00-000000",
                     "document": "x.htm", "section": "Financial Highlights",
                     "quote": "Test row 1.00%"}],
    }


def write_raw(path: Path, raws: list[dict]) -> None:
    path.write_text(json.dumps(raws))


def test_example_file_loads_with_portfolio_turnover():
    definitions = load(EXAMPLE_PATH)
    keys = [d.key for d in definitions]
    assert "portfolio_turnover" in keys
    turnover = definitions[keys.index("portfolio_turnover")]
    assert turnover.unit == "pct"
    assert turnover.source_shape == "table_row"
    accessions = {s["accession"] for s in turnover.sources}
    assert {"0001213900-25-118573", "0001476765-26-000012"} <= accessions


def test_save_round_trips(tmp_path):
    original = load(EXAMPLE_PATH)
    out = tmp_path / "out.json"
    save(original, out)
    assert load(out) == original


BLANKS = {str: "  ", list: [], dict: {}}


@pytest.mark.parametrize("field", custom_metrics.REQUIRED_FIELDS)
@pytest.mark.parametrize("bad", ["missing", "blank"])
def test_save_fails_and_writes_nothing_when_field_missing_or_blank(tmp_path, field, bad):
    good = custom_metrics.Definition(**good_raw())
    broken_raw = good_raw()
    broken_raw["key"] = "broken_metric" if field != "key" else broken_raw["key"]
    if bad == "missing":
        broken_raw[field] = None
    else:
        broken_raw[field] = BLANKS[type(broken_raw[field])]
    broken = custom_metrics.Definition(**broken_raw)
    out = tmp_path / "out.json"
    with pytest.raises(DefinitionError) as err:
        save([good, broken], out)
    assert field in str(err.value)
    if field != "key":
        assert "broken_metric" in str(err.value)
    assert not out.exists()


def test_save_does_not_overwrite_existing_file_on_failure(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("previous contents")
    broken_raw = good_raw()
    broken_raw["owner"] = ""
    with pytest.raises(DefinitionError):
        save([custom_metrics.Definition(**broken_raw)], out)
    assert out.read_text() == "previous contents"


def test_error_names_every_problem_per_metric(tmp_path):
    a, b = good_raw(), good_raw()
    a["key"], b["key"] = "metric_a", "metric_b"
    a["owner"] = ""
    del b["unit"]
    path = tmp_path / "defs.json"
    write_raw(path, [a, b])
    with pytest.raises(DefinitionError) as err:
        load(path)
    message = str(err.value)
    assert "metric_a" in message and "owner" in message
    assert "metric_b" in message and "unit" in message


def test_load_rejects_missing_field(tmp_path):
    raw = good_raw()
    del raw["definition"]
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="definition"):
        load(path)


def test_normalization_assumptions_must_not_be_empty(tmp_path):
    raw = good_raw()
    raw["normalization_assumptions"] = []
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="normalization_assumptions"):
        load(path)


def test_unknown_unit_is_rejected(tmp_path):
    raw = good_raw()
    raw["unit"] = "bps"
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="unit"):
        load(path)


def test_unknown_source_shape_is_rejected(tmp_path):
    raw = good_raw()
    raw["source_shape"] = "llm_guess"
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="source_shape"):
        load(path)


def test_table_row_needs_row_label_pattern_and_section(tmp_path):
    raw = good_raw()
    raw["shape"] = {"row_label_pattern": "Test row"}
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="section"):
        load(path)


def test_xbrl_tag_needs_concept(tmp_path):
    raw = good_raw()
    raw["source_shape"] = "xbrl_tag"
    raw["shape"] = {"concept": ""}
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="concept"):
        load(path)


def test_ratio_of_metrics_needs_numerator_and_denominator(tmp_path):
    raw = good_raw()
    raw["source_shape"] = "ratio_of_metrics"
    raw["unit"] = "ratio"
    raw["shape"] = {"numerator": "total_debt"}
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="denominator"):
        load(path)

    raw["shape"] = {"denominator": "net_assets"}
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="numerator"):
        load(path)

    raw["shape"] = {"numerator": "total_debt", "denominator": "net_assets"}
    write_raw(path, [raw])
    assert load(path)[0].shape["numerator"] == "total_debt"


def test_each_source_needs_accession_and_quote(tmp_path):
    raw = good_raw()
    raw["sources"] = [{"form": "10-Q", "accession": "", "document": "x.htm",
                       "section": "Financial Highlights", "quote": "Test row"}]
    path = tmp_path / "defs.json"
    write_raw(path, [raw])
    with pytest.raises(DefinitionError, match="accession"):
        load(path)


def test_duplicate_keys_rejected(tmp_path):
    path = tmp_path / "defs.json"
    write_raw(path, [good_raw(), copy.deepcopy(good_raw())])
    with pytest.raises(DefinitionError, match="duplicate"):
        load(path)


def test_custom_metric_confidence_is_capped_at_medium():
    """Client, W3: new metrics start at Medium confidence at most."""
    from benchmark.custom_metrics import capped_confidence
    assert capped_confidence("high") == "medium"
    assert capped_confidence("medium") == "medium" and capped_confidence("low") == "low"

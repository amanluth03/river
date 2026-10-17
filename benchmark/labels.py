"""Plain-English names for code names, used by the Excel and Word exports.

A PM reading an export should see "Not directly comparable", not "not_comparable" (P5). Metric names
come from the deck row labels (bundle.rows, built from config) wherever a metric is a deck row; this file
only names what the deck doesn't: exception types and the Apex CSV columns that the client-data checks
report on. Wording follows the review UI (EXCEPTION_TITLES in benchmark/static/app.js) so the screen and
the files read the same, shortened to a type name because the exports list one issue per row.
"""
from typing import get_args

from .config import STATUS_LABELS
from .records import Issue

ISSUE_KINDS = get_args(Issue.model_fields["kind"].annotation)  # every kind the data model allows

ISSUE_KIND_LABELS = {
    "conflict": "Conflict",  # app.js: "Conflicts between filings"
    "missing": "Missing",  # app.js: "Missing or not verified"
    "lag": "Data lag",  # app.js: "Data lags"
    "computed": "Computed value",  # app.js: "Computed values (formula and inputs)"
    "not_like_for_like": "Not like-for-like",  # app.js: same wording (KREF)
    "client_data": "Client data check",  # app.js: "Apex Ridge data checks (question for the client)"
    "peer_question": "Peer-set question",  # app.js: "Peer set questions"
    "data_quality": "Filing data quality",  # app.js: same wording
    "fetch": "EDGAR error",  # app.js: "EDGAR errors"
    "amendment": "Amendment",  # app.js: "Amendments (EDGAR index check)"
    "not_comparable": "Not directly comparable",  # app.js: same wording (Golub returns)
    "check_failed": "Check failed",  # app.js: "Low confidence: review before use"
}

# Metrics that appear in issues but are not deck rows: the Apex CSV columns checked for changes across
# quarters (apex._fee_issues). Named after the CSV column, marked as client data.
EXTRA_METRIC_LABELS = {
    "management_fee_pct": "Management fee (client data)",  # CSV column management_fee_pct
    "incentive_fee_pct": "Incentive fee (client data)",  # CSV column incentive_fee_pct
    "incentive_hurdle_pct": "Incentive hurdle (client data)",  # CSV column incentive_hurdle_pct
}


def issue_kind_label(kind: str) -> str:
    """The plain name for an exception type; an unknown kind is shown as-is rather than hidden."""
    return ISSUE_KIND_LABELS.get(kind, kind)


def metric_label(metric: str | None, rows: list[tuple[str, str]]) -> str:
    """The deck row label for a metric key, else a name from EXTRA_METRIC_LABELS, else the key itself."""
    if not metric:
        return ""
    deck = dict(rows)
    return deck.get(metric) or EXTRA_METRIC_LABELS.get(metric, metric)


def status_label(status: str) -> str:
    """The plain name for a record status (config.STATUS_LABELS); "ok" stays "ok"."""
    return STATUS_LABELS.get(status, status)

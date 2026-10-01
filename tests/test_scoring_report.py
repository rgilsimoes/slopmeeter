import json
from datetime import UTC, datetime

from slopmeter.checks.base import result
from slopmeter.report import render_json
from slopmeter.scoring import aggregate, label

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_verdict_boundaries():
    assert label(80) == "Solid. Receipts included."
    assert label(60) == "Promising. Some receipts."
    assert label(40) == "Mostly vibes."
    assert label(39.99) == "Peak slop."


def test_weighted_scoring_and_confidence():
    results = [
        result("H1", "pass", "ok"),
        result("H2", "warn", "mixed"),
        result("T1", "fail", "missing"),
        result("S2", "na", "offline"),
    ]
    score = aggregate(results, (), NOW)
    assert 0 < score.evidence_score < 100
    assert 0 < score.confidence < 1
    assert score.maturity_note and score.maturity_note.startswith("Too early to tell")


def test_json_is_byte_identical_and_has_schema_fields():
    results = [result("H1", "fail", "0 commits")]
    score = aggregate(results, (), NOW)
    first = render_json(".", results, score, False)
    second = render_json(".", results, score, False)
    assert first == second
    data = json.loads(first)
    assert data["schema_version"] == 1
    assert data["target"] == "."
    assert isinstance(data["checks"], list)


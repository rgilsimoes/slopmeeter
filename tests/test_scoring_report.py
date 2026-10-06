import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from slopmeter.checks.base import result
from slopmeter.report import render, render_json
from slopmeter.scoring import aggregate, label

NOW = datetime(2026, 1, 1, tzinfo=UTC)
GOLDEN = Path(__file__).with_name("golden")


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


def test_json_and_markdown_match_compatibility_goldens():
    results = [
        result("H1", "fail", "0 commits", ["no git history"]),
        result("H2", "warn", "one large commit"),
        result("H4", "pass", "specific messages"),
        result("S2", "na", "offline"),
    ]
    score = aggregate(results, (), NOW)

    assert render("json", ".", results, score, False) == (GOLDEN / "report.json").read_text()
    assert render("markdown", ".", results, score, False) == (GOLDEN / "report.md").read_text()


def test_coloured_text_is_plain_text_with_semantic_ansi_styles():
    results = [
        result("H1", "fail", "too few commits"),
        result("H2", "warn", "one large commit"),
        result("H4", "pass", "specific messages"),
        result("S2", "na", "offline"),
    ]
    score = aggregate(results, (), NOW)

    plain = render("text", ".", results, score, False, color=False)
    coloured = render("text", ".", results, score, False, color=True)

    assert "\x1b[" not in plain
    assert "\x1b[" in coloured
    assert re.sub(r"\x1b\[[0-9;]*m", "", coloured) == plain
    assert "! WARN" in plain
    assert "× FAIL" in plain
    assert "✓ PASS" in plain
    assert "\x1b[1;33m! WARN\x1b[0m" in coloured
    assert "\x1b[1;31m× FAIL\x1b[0m" in coloured
    assert "\x1b[1;32m✓ PASS\x1b[0m" in coloured
    assert plain.startswith("███████╗██╗")
    assert "score the evidence, not the vibes" in plain
    assert "Repository evidence score" in plain
    assert "│ Slop level" in plain
    assert "Category scores" in plain
    assert "■" in plain and "□" in plain
    assert "Evidence checks" in plain
    assert plain.index("H1  │") < plain.index("H2  │") < plain.index("H4  │")
    assert "S2  │ – N/A" in plain


def test_text_report_keeps_every_result_and_its_evidence():
    results = [
        result("H1", "fail", "too few commits", ["commit count: 3"]),
        result("H2", "fail", "one oversized commit"),
        result("H3", "fail", "short history"),
        result("T1", "pass", "tests are present"),
        result("T2", "pass", "tests contain assertions", ["9 of 10 test functions"]),
    ]
    score = aggregate(results, (), NOW)

    plain = render("text", ".", results, score, False, color=False)

    for check_id in ("H1", "H2", "H3", "T1", "T2"):
        assert f"{check_id}  │" in plain
    assert "↳ commit count: 3" in plain
    assert "↳ 9 of 10 test functions" in plain


def test_text_report_styles_not_applicable_results():
    results = [result("S2", "na", "offline")]
    score = aggregate(results, (), NOW)

    plain = render("text", ".", results, score, False, color=False)
    coloured = render("text", ".", results, score, False, color=True)

    assert "S2  │ – N/A  │ offline" in plain
    assert "\x1b[90m– N/A \x1b[0m" in coloured


def test_html_report_is_self_contained_safe_and_prioritises_inspection():
    results = [
        result("H1", "warn", "short history", ["<img src=x onerror=alert(1)>"]),
        result("T1", "fail", "tests are missing"),
        result("C1", "fail", "claims lack receipts"),
        result("S2", "na", "offline"),
        result("I1", "pass", "AGENTS.md found"),
    ]
    score = aggregate(results, (), NOW)

    document = render("html", '<repo data-x="unsafe">', results, score, False)

    assert document.startswith("<!doctype html>\n")
    assert document.endswith("\n")
    assert '<repo data-x="unsafe">' not in document
    assert "&lt;repo data-x=&quot;unsafe&quot;&gt;" in document
    assert "<img src=x onerror=alert(1)>" not in document
    assert "&lt;img src=x onerror=alert(1)&gt;" in document
    assert "Content-Security-Policy" in document
    assert "<script" not in document.lower()
    assert "https://" not in document
    assert "A score is a prompt for scrutiny, not a verdict on the authors." in document
    assert "Information · not scored" in document

    priorities = document.split("What to inspect next", 1)[1].split("Evidence checks", 1)[0]
    assert priorities.index("Claims have receipts") < priorities.index("Tests present")
    assert priorities.index("Tests present") < priorities.index("Commit depth")


def test_html_report_has_an_accessible_all_pass_state_without_a_maturity_note():
    results = [result("H1", "pass", "healthy history")]
    score = replace(aggregate(results, (), NOW), maturity_note=None)

    first = render("html", ".", results, score, False)
    second = render("html", ".", results, score, False)

    assert first == second
    assert 'role="img" aria-label="Evidence score' in first
    assert "<table>" in first
    assert 'scope="col"' in first
    assert 'aria-label="Check status counts"' in first
    assert "No failed or warning checks need immediate review." in first
    assert "A short history limits long-term signals." not in first
    assert "@media print" in first


def test_rendering_does_not_mutate_analysis_results():
    results = [result("H1", "warn", "short history", ["3 commits"])]
    original_results = list(results)
    score = aggregate(results, (), NOW)

    for format_name in ("text", "json", "markdown", "html"):
        render(format_name, ".", results, score, False, color=True)

    assert results == original_results
    assert results[0].evidence == ["3 commits"]

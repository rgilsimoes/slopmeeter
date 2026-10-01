from __future__ import annotations

import json
from dataclasses import asdict

from slopmeter import __version__
from slopmeter.checks.base import CATEGORIES, CheckResult
from slopmeter.scoring import Score


def _number(value: float) -> int | float:
    rounded = round(value, 2)
    return int(rounded) if rounded.is_integer() else rounded


def report_data(target: str, results: list[CheckResult], score: Score, online: bool) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool": {"name": "slopmeter", "version": __version__},
        "target": target,
        "mode": "online" if online else "offline",
        "evidence_score": _number(score.evidence_score),
        "slop_level": score.slop_level,
        "confidence": _number(score.confidence * 100),
        "verdict": score.verdict,
        "maturity_note": score.maturity_note,
        "categories": [
            {**asdict(category), "score": None if category.score is None else _number(category.score)}
            for category in score.categories
        ],
        "checks": [item.as_dict() for item in results],
    }


def render_json(target: str, results: list[CheckResult], score: Score, online: bool) -> str:
    return json.dumps(report_data(target, results, score, online), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_text(target: str, results: list[CheckResult], score: Score, online: bool) -> str:
    lines = [
        f"Slop Meeter v{__version__} · target: {target}",
        f"Evidence score: {score.evidence_score:.0f}/100 · Slop level: {score.slop_level}/10 · Confidence: {score.confidence:.0%} ({'online' if online else 'offline'})",
        f"Verdict: {score.verdict}" + (f" ({score.maturity_note})" if score.maturity_note else ""),
        "",
    ]
    for category in score.categories:
        if category.score is None:
            continue
        lines.append(f"{category.name:<30} {category.score:>3.0f}")
        for check in (item for item in results if item.category == category.id):
            lines.append(f"  {check.id:<3} {check.status:<4} {check.message}")
            lines.extend(f"      {evidence}" for evidence in check.evidence)
    information = [item for item in results if item.category == "info"]
    if information:
        lines.append("")
        lines.extend(f"Info: {item.name}: {item.message} (not scored)" for item in information)
    return "\n".join(lines) + "\n"


def render_markdown(target: str, results: list[CheckResult], score: Score, online: bool) -> str:
    lines = [
        "# Slop Meeter report",
        "",
        f"**Target:** `{target}`  ",
        f"**Evidence score:** {score.evidence_score:.0f}/100 · **Slop level:** {score.slop_level}/10 · **Confidence:** {score.confidence:.0%} ({'online' if online else 'offline'})  ",
        f"**Verdict:** {score.verdict}" + (f" ({score.maturity_note})" if score.maturity_note else ""),
        "",
        "| Category | Score | Check | Status | Evidence |",
        "|---|---:|---|---|---|",
    ]
    for category in score.categories:
        if category.score is None:
            continue
        category_name = CATEGORIES[category.id][0]
        category_results = [item for item in results if item.category == category.id]
        for index, check in enumerate(category_results):
            evidence = check.message.replace("|", "\\|")
            lines.append(f"| {category_name if index == 0 else ''} | {category.score:.0f} | {check.id} {check.name} | {check.status} | {evidence} |")
    return "\n".join(lines) + "\n"


def render(format_name: str, target: str, results: list[CheckResult], score: Score, online: bool) -> str:
    if format_name == "json":
        return render_json(target, results, score, online)
    if format_name == "markdown":
        return render_markdown(target, results, score, online)
    return render_text(target, results, score, online)


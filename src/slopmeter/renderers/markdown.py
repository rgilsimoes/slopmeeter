from __future__ import annotations

from typing import TYPE_CHECKING

from slopmeter.checks.base import CATEGORIES

if TYPE_CHECKING:
    from slopmeter.report import ReportView


def render_markdown_report(report: ReportView) -> str:
    lines = [
        "# Slop Meeter report",
        "",
        f"**Target:** `{report.target}`  ",
        f"**Evidence score:** {report.evidence_score:.0f}/100 · **Slop level:** {report.slop_level}/10 · **Confidence:** {report.confidence:.0%} ({report.mode})  ",
        f"**Verdict:** {report.verdict}"
        + (f" ({report.maturity_note})" if report.maturity_note else ""),
        "",
        "| Category | Score | Check | Status | Evidence |",
        "|---|---:|---|---|---|",
    ]
    for category in report.categories:
        if category.score is None:
            continue
        category_name = CATEGORIES[category.id][0]
        category_results = [item for item in report.checks if item.category == category.id]
        for index, check in enumerate(category_results):
            evidence = check.message.replace("|", "\\|")
            lines.append(
                f"| {category_name if index == 0 else ''} | {category.score:.0f} | "
                f"{check.id} {check.name} | {check.status} | {evidence} |"
            )
    return "\n".join(lines) + "\n"

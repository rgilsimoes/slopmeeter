from __future__ import annotations

from html import escape
from importlib import resources
from string import Template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slopmeter.checks.base import CheckResult
    from slopmeter.report import ReportView

STATUS = {
    "pass": ("✓", "PASS"),
    "warn": ("!", "WARN"),
    "fail": ("×", "FAIL"),
    "na": ("–", "N/A"),
}


def _resource(name: str) -> str:
    return resources.files("slopmeter.templates").joinpath(name).read_text(encoding="utf-8")


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _score_class(score: float) -> str:
    if score >= 80:
        return "score-pass"
    if score >= 60:
        return "score-accent"
    if score >= 40:
        return "score-warn"
    return "score-fail"


def _score_visual(report: ReportView) -> str:
    score = max(0.0, min(100.0, report.evidence_score))
    return (
        '<div class="score-card">'
        f'<div class="score-ring" role="img" aria-label="Evidence score {score:.0f} out of 100">'
        '<svg viewBox="0 0 120 120" aria-hidden="true">'
        '<circle class="score-track" cx="60" cy="60" r="50"></circle>'
        f'<circle class="score-value" cx="60" cy="60" r="50" pathLength="100" '
        f'stroke-dasharray="{score:.2f} 100"></circle></svg>'
        f'<div class="score-copy"><strong>{score:.0f}</strong><span>Evidence score<br>out of 100</span></div>'
        "</div></div>"
    )


def _categories(report: ReportView) -> str:
    rows = []
    for category in report.categories:
        if category.score is None:
            continue
        score = max(0.0, min(100.0, category.score))
        rows.append(
            '<div class="category-row">'
            f'<span class="category-name">{_e(category.name)}</span>'
            f'<strong class="category-score">{score:.0f}</strong>'
            f'<progress class="{_score_class(score)}" max="100" value="{score:.2f}" '
            f'aria-label="{_e(category.name)} score {score:.0f} out of 100">{score:.0f}</progress>'
            "</div>"
        )
    return "".join(rows)


def _status_pill(check: CheckResult) -> str:
    symbol, label = STATUS[check.status]
    return (
        f'<span class="status-pill status-{check.status}">'
        f'<span aria-hidden="true">{symbol}</span> {label}</span>'
    )


def _evidence(check: CheckResult) -> str:
    if not check.evidence:
        return '<span class="empty-evidence">—</span>'
    return (
        '<ul class="evidence-list">'
        + "".join(f"<li>{_e(item)}</li>" for item in check.evidence)
        + "</ul>"
    )


def _checks(report: ReportView) -> str:
    return "".join(
        "<tr>"
        f'<td class="check-name"><span class="check-id">{_e(check.id)}</span>{_e(check.name)}</td>'
        f"<td>{_status_pill(check)}</td>"
        f"<td>{_e(check.message)}</td>"
        f"<td>{_evidence(check)}</td>"
        "</tr>"
        for check in report.checks
        if check.category != "info"
    )


def _counts(report: ReportView) -> str:
    labels = {"pass": "Pass", "warn": "Warn", "fail": "Fail", "na": "N/A"}
    return "".join(
        f'<span class="count-pill status-{status}">{labels[status]} <strong>{count}</strong></span>'
        for status, count in report.status_counts
    )


def _inspections(report: ReportView) -> str:
    if not report.inspections:
        return '<p class="positive-state">No failed or warning checks need immediate review.</p>'
    items = "".join(
        "<li>"
        f"<h3>{_e(item.title)}</h3>"
        f"<p>{_e(item.finding)}</p>"
        f'<p class="why">{_e(item.rationale)}</p>'
        "</li>"
        for item in report.inspections
    )
    return f'<ol class="inspection-list">{items}</ol>'


def _information(report: ReportView) -> str:
    checks = [check for check in report.checks if check.category == "info"]
    if not checks:
        return ""
    items = "".join(
        f"<li><strong>{_e(check.name)}</strong><span>{_e(check.message)}</span></li>"
        for check in checks
    )
    return (
        '<section class="panel section-panel information" aria-labelledby="information-heading">'
        '<div class="section-heading"><div><p class="eyebrow">Context</p>'
        '<h2 id="information-heading">Information · not scored</h2></div></div>'
        f'<ul class="information-list">{items}</ul></section>'
    )


def _maturity(report: ReportView) -> str:
    if not report.maturity_note:
        return ""
    return (
        '<div class="maturity"><span class="label">Maturity</span>'
        f"<strong>{_e(report.maturity_note)}</strong>"
        "<span>A short history limits long-term signals. Reassess as the project evolves.</span></div>"
    )


def render_html_report(report: ReportView) -> str:
    template = Template(_resource("report.html"))
    return (
        template.substitute(
            styles=_resource("report.css").rstrip(),
            target=_e(report.target),
            version=_e(report.version),
            mode=_e(report.mode.title()),
            score_visual=_score_visual(report),
            slop_level=report.slop_level,
            confidence=f"{report.confidence:.0%}".removesuffix("%"),
            verdict=_e(report.verdict),
            maturity=_maturity(report),
            categories=_categories(report),
            status_counts=_counts(report),
            checks=_checks(report),
            information=_information(report),
            inspections=_inspections(report),
        ).rstrip()
        + "\n"
    )

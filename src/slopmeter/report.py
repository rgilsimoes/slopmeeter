from __future__ import annotations

from dataclasses import asdict, dataclass

from slopmeter import __version__
from slopmeter.checks.base import CHECK_BY_ID, CHECKS, CheckResult
from slopmeter.profiles import AnalysisProfile
from slopmeter.scoring import CategoryScore, Score


@dataclass(frozen=True)
class InspectionItem:
    check_id: str
    title: str
    status: str
    finding: str
    rationale: str


@dataclass(frozen=True)
class ReportView:
    version: str
    target: str
    mode: str
    evidence_score: float
    slop_level: int
    confidence: float
    verdict: str
    maturity_note: str | None
    categories: tuple[CategoryScore, ...]
    checks: tuple[CheckResult, ...]
    status_counts: tuple[tuple[str, int], ...]
    inspections: tuple[InspectionItem, ...]


def _inspection_items(results: list[CheckResult]) -> tuple[InspectionItem, ...]:
    check_order = {check.id: index for index, check in enumerate(CHECKS)}
    candidates = [
        check for check in results if check.category != "info" and check.status in {"fail", "warn"}
    ]
    candidates.sort(
        key=lambda check: (
            0 if check.status == "fail" else 1,
            -check.weight,
            check_order[check.id],
        )
    )
    return tuple(
        InspectionItem(
            check_id=check.id,
            title=check.name,
            status=check.status,
            finding=check.message,
            rationale=CHECK_BY_ID[check.id].rationale,
        )
        for check in candidates[:3]
    )


def _report_view(target: str, results: list[CheckResult], score: Score, online: bool) -> ReportView:
    return ReportView(
        version=__version__,
        target=target,
        mode="online" if online else "offline",
        evidence_score=score.evidence_score,
        slop_level=score.slop_level,
        confidence=score.confidence,
        verdict=score.verdict,
        maturity_note=score.maturity_note,
        categories=score.categories,
        checks=tuple(results),
        status_counts=tuple(
            (status, sum(check.category != "info" and check.status == status for check in results))
            for status in ("pass", "warn", "fail", "na")
        ),
        inspections=_inspection_items(results),
    )


def _number(value: float) -> int | float:
    rounded = round(value, 2)
    return int(rounded) if rounded.is_integer() else rounded


def report_data(
    target: str,
    results: list[CheckResult],
    score: Score,
    online: bool,
    *,
    profile: AnalysisProfile | None = None,
    revision: str | None = None,
    acquisition: dict[str, object] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": 2 if profile else 1,
        "tool": {"name": "slopmeter", "version": __version__},
        "target": target,
        "mode": "browser" if profile else ("online" if online else "offline"),
        "evidence_score": _number(score.evidence_score),
        "slop_level": score.slop_level,
        "confidence": _number(score.confidence * 100),
        "verdict": score.verdict,
        "maturity_note": score.maturity_note,
        "categories": [
            {
                **asdict(category),
                "score": None if category.score is None else _number(category.score),
            }
            for category in score.categories
        ],
        "checks": [item.as_dict() for item in results],
    }
    if profile:
        total_weight = sum(check.weight for check in CHECKS if check.weight > 0)
        run_ids = set(profile.run)
        maximum_weight = sum(
            check.weight for check in CHECKS if check.id in run_ids and check.weight > 0
        )
        data.update(
            {
                "analysis_profile": profile.id,
                "analyzer_version": __version__,
                "revision": revision,
                "coverage": {
                    "run": list(profile.run),
                    "unavailable": list(profile.unavailable),
                    "maximum_confidence": _number(100 * maximum_weight / total_weight),
                },
                "acquisition": acquisition or {},
            }
        )
    return data


def render_json(target: str, results: list[CheckResult], score: Score, online: bool) -> str:
    from slopmeter.renderers.json import render_json_report

    return render_json_report(report_data(target, results, score, online))


def render_text(
    target: str,
    results: list[CheckResult],
    score: Score,
    online: bool,
    *,
    color: bool = False,
) -> str:
    from slopmeter.renderers.text import render_text_report

    return render_text_report(_report_view(target, results, score, online), color=color)


def render_markdown(target: str, results: list[CheckResult], score: Score, online: bool) -> str:
    from slopmeter.renderers.markdown import render_markdown_report

    return render_markdown_report(_report_view(target, results, score, online))


def render_html(target: str, results: list[CheckResult], score: Score, online: bool) -> str:
    from slopmeter.renderers.html import render_html_report

    return render_html_report(_report_view(target, results, score, online))


def render(
    format_name: str,
    target: str,
    results: list[CheckResult],
    score: Score,
    online: bool,
    *,
    color: bool = False,
) -> str:
    if format_name == "json":
        return render_json(target, results, score, online)
    if format_name == "markdown":
        return render_markdown(target, results, score, online)
    if format_name == "html":
        return render_html(target, results, score, online)
    return render_text(target, results, score, online, color=color)

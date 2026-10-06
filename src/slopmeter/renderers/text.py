from __future__ import annotations

from dataclasses import dataclass
from textwrap import wrap
from typing import TYPE_CHECKING

from slopmeter.checks.base import CATEGORIES, CheckResult

if TYPE_CHECKING:
    from slopmeter.report import ReportView

LINE_WIDTH = 104
SUMMARY_SCORE_WIDTH = 26
SUMMARY_DETAIL_WIDTH = 28

BANNER = (
    "███████╗██╗      ██████╗ ██████╗     ███╗   ███╗███████╗███████╗████████╗███████╗██████╗",
    "██╔════╝██║     ██╔═══██╗██╔══██╗    ████╗ ████║██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗",
    "███████╗██║     ██║   ██║██████╔╝    ██╔████╔██║█████╗  █████╗     ██║   █████╗  ██████╔╝",
    "╚════██║██║     ██║   ██║██╔═══╝     ██║╚██╔╝██║██╔══╝  ██╔══╝     ██║   ██╔══╝  ██╔══██╗",
    "███████║███████╗╚██████╔╝██║         ██║ ╚═╝ ██║███████╗███████╗   ██║   ███████╗██║  ██║",
    "╚══════╝╚══════╝ ╚═════╝ ╚═╝         ╚═╝     ╚═╝╚══════╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝",
)


@dataclass(frozen=True)
class _Theme:
    enabled: bool

    def apply(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\x1b[{code}m{text}\x1b[0m"

    def accent(self, text: str) -> str:
        return self.apply(text, "1;36")

    def pass_(self, text: str) -> str:
        return self.apply(text, "1;32")

    def warn(self, text: str) -> str:
        return self.apply(text, "1;33")

    def fail(self, text: str) -> str:
        return self.apply(text, "1;31")

    def muted(self, text: str) -> str:
        return self.apply(text, "90")

    def bold(self, text: str) -> str:
        return self.apply(text, "1")


STATUS_LABELS = {
    "pass": ("✓", "PASS"),
    "warn": ("!", "WARN"),
    "fail": ("×", "FAIL"),
    "na": ("–", "N/A"),
}


def _score_style(theme: _Theme, text: str, score: float):
    if score >= 60:
        return theme.pass_(text)
    if score >= 40:
        return theme.warn(text)
    return theme.fail(text)


def _bar(theme: _Theme, score: float) -> str:
    filled_count = max(0, min(10, int(score / 10 + 0.5)))
    filled = " ".join("■" for _ in range(filled_count))
    empty = " ".join("□" for _ in range(10 - filled_count))
    if not filled:
        return theme.muted(empty)
    if not empty:
        return _score_style(theme, filled, score)
    return _score_style(theme, filled, score) + " " + theme.muted(empty)


def _wrapped_line(prefix: str, message: str, *, width: int = LINE_WIDTH) -> list[str]:
    chunks = wrap(message, width=max(20, width - len(prefix))) or [""]
    return [prefix + chunks[0], *(" " * len(prefix) + chunk for chunk in chunks[1:])]


def _status(theme: _Theme, check: CheckResult) -> str:
    symbol, label = STATUS_LABELS[check.status]
    text = f"{symbol} {label:<4}"
    style = {
        "pass": theme.pass_,
        "warn": theme.warn,
        "fail": theme.fail,
        "na": theme.muted,
    }[check.status]
    return style(text)


def _check_lines(theme: _Theme, check: CheckResult) -> list[str]:
    plain_prefix = (
        f"  {check.id:<3} │ {STATUS_LABELS[check.status][0]} "
        f"{STATUS_LABELS[check.status][1]:<4} │ "
    )
    visible_prefix = f"  {check.id:<3} {theme.muted('│')} {_status(theme, check)} {theme.muted('│')} "
    chunks = wrap(check.message, width=max(20, LINE_WIDTH - len(plain_prefix))) or [""]
    lines = [visible_prefix + chunks[0]]
    lines.extend(" " * len(plain_prefix) + chunk for chunk in chunks[1:])
    evidence_prefix = " " * len(plain_prefix) + "↳ "
    for evidence in check.evidence:
        lines.extend(_wrapped_line(evidence_prefix, evidence))
    return lines


def _summary_cell(visible: str, plain: str, width: int) -> str:
    return visible + " " * max(1, width - len(plain))


def _summary_row(
    theme: _Theme,
    score: tuple[str, str],
    detail: tuple[str, str],
    verdict: str,
) -> str:
    separator = f" {theme.accent('│')} "
    return (
        _summary_cell(*score, SUMMARY_SCORE_WIDTH)
        + separator
        + _summary_cell(*detail, SUMMARY_DETAIL_WIDTH)
        + separator
        + verdict
    )


def _maturity_text(note: str | None) -> str:
    if not note:
        return "Based on observable repository evidence"
    if note.startswith("Too early to tell: "):
        detail = note.removeprefix("Too early to tell: ").replace(", ", " · ")
        return f"Too early to tell · {detail}"
    return note


def render_text_report(report: ReportView, *, color: bool = False) -> str:
    theme = _Theme(color)
    score_plain = f"{report.evidence_score:.0f} / 100"
    score_text = theme.accent(score_plain)
    slop_plain = f"{report.slop_level} / 10"
    slop_text = theme.warn(slop_plain) if report.slop_level >= 4 else theme.pass_(slop_plain)
    confidence_plain = f"{report.confidence:.0%}"
    confidence_text = _score_style(theme, confidence_plain, report.confidence * 100)
    divider = theme.accent("─" * LINE_WIDTH)

    lines = [
        *(theme.accent(line) for line in BANNER),
        theme.muted("score the evidence, not the vibes"),
        theme.muted(f"v{report.version} · target {report.target}"),
        "",
        divider,
        _summary_row(
            theme,
            (score_text, score_plain),
            (f"Slop level  {slop_text}", f"Slop level  {slop_plain}"),
            _score_style(theme, report.verdict, report.evidence_score),
        ),
        _summary_row(
            theme,
            ("Repository evidence score", "Repository evidence score"),
            (
                f"Confidence  {confidence_text} · {report.mode}",
                f"Confidence  {confidence_plain} · {report.mode}",
            ),
            theme.muted(_maturity_text(report.maturity_note)),
        ),
        divider,
    ]

    lines.extend(["", theme.accent("Category scores")])
    for category in report.categories:
        if category.score is None:
            continue
        lines.append(
            f"  {category.name:<31} {_bar(theme, category.score)}   "
            f"{_score_style(theme, f'{category.score:>3.0f}', category.score)}"
        )

    lines.extend(["", divider, "", theme.accent("Evidence checks")])
    for category_id, (category_name, _) in CATEGORIES.items():
        if category_id == "info":
            continue
        checks = [check for check in report.checks if check.category == category_id]
        if not checks:
            continue
        lines.extend(["", theme.bold(category_name)])
        for check in checks:
            lines.extend(_check_lines(theme, check))

    information = [check for check in report.checks if check.category == "info"]
    if information:
        lines.extend(["", theme.accent("Information") + theme.muted(" · not scored")])
        for check in information:
            lines.extend(_wrapped_line(f"  {check.id:<3} ", f"{check.name}: {check.message}"))

    return "\n".join(lines) + "\n"

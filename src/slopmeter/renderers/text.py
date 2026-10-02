from __future__ import annotations

from dataclasses import dataclass
from textwrap import wrap
from typing import TYPE_CHECKING

from slopmeter.checks.base import CATEGORIES, CheckResult

if TYPE_CHECKING:
    from slopmeter.report import ReportView

LINE_WIDTH = 96


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
    if score >= 80:
        return theme.pass_(text)
    if score >= 60:
        return theme.accent(text)
    if score >= 40:
        return theme.warn(text)
    return theme.fail(text)


def _bar(theme: _Theme, score: float) -> str:
    filled_count = max(0, min(10, int(score / 10 + 0.5)))
    filled = "█" * filled_count
    empty = "░" * (10 - filled_count)
    return _score_style(theme, filled, score) + theme.muted(empty)


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
        f"  {check.id:<3} {STATUS_LABELS[check.status][0]} {STATUS_LABELS[check.status][1]:<4} "
    )
    visible_prefix = f"  {check.id:<3} {_status(theme, check)} "
    chunks = wrap(check.message, width=max(20, LINE_WIDTH - len(plain_prefix))) or [""]
    lines = [visible_prefix + chunks[0]]
    lines.extend(" " * len(plain_prefix) + chunk for chunk in chunks[1:])
    for evidence in check.evidence:
        lines.extend(_wrapped_line("      ↳ ", evidence))
    return lines


def render_text_report(report: ReportView, *, color: bool = False) -> str:
    theme = _Theme(color)
    score_plain = f"{report.evidence_score:.0f} / 100"
    score_text = _score_style(theme, score_plain, report.evidence_score)
    slop_plain = f"{report.slop_level} / 10"
    slop_text = theme.warn(slop_plain) if report.slop_level >= 4 else theme.pass_(slop_plain)

    lines = [
        theme.accent(f"SLOP MEETER v{report.version}"),
        theme.muted("score the evidence, not the vibes"),
        f"target  {report.target}",
        theme.muted("─" * LINE_WIDTH),
        (
            f"EVIDENCE SCORE  {score_text}{' ' * (18 - len(score_plain))}  "
            f"SLOP LEVEL  {slop_text}{' ' * (12 - len(slop_plain))}  "
            f"CONFIDENCE  {report.confidence:.0%} · {report.mode}"
        ),
        f"VERDICT         {theme.bold(report.verdict)}",
    ]
    if report.maturity_note:
        lines.append(f"MATURITY        {theme.muted(report.maturity_note)}")

    lines.extend(["", theme.accent("CATEGORY SCORES")])
    for category in report.categories:
        if category.score is None:
            continue
        lines.append(
            f"{category.name:<32} {_bar(theme, category.score)}  "
            f"{_score_style(theme, f'{category.score:>3.0f}', category.score)}"
        )

    lines.extend(["", theme.accent("EVIDENCE CHECKS")])
    for category_id, (category_name, _) in CATEGORIES.items():
        if category_id == "info":
            continue
        checks = [check for check in report.checks if check.category == category_id]
        if not checks:
            continue
        lines.append("")
        lines.append(theme.bold(category_name))
        for check in checks:
            lines.extend(_check_lines(theme, check))

    information = [check for check in report.checks if check.category == "info"]
    if information:
        lines.extend(["", theme.accent("INFORMATION") + theme.muted(" · not scored")])
        for check in information:
            lines.extend(_wrapped_line(f"  {check.id:<3} ", f"{check.name}: {check.message}"))

    return "\n".join(lines) + "\n"

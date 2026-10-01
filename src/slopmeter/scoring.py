from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from slopmeter.checks.base import CATEGORIES, CheckResult
from slopmeter.gitlog import Commit

STATUS_POINTS = {"pass": 1.0, "warn": 0.5, "fail": 0.0}


@dataclass(frozen=True)
class CategoryScore:
    id: str
    name: str
    weight: int
    score: float | None


@dataclass(frozen=True)
class Score:
    evidence_score: float
    slop_level: int
    confidence: float
    verdict: str
    maturity_note: str | None
    categories: tuple[CategoryScore, ...]


def label(score: float) -> str:
    if score >= 80:
        return "Solid. Receipts included."
    if score >= 60:
        return "Promising. Some receipts."
    if score >= 40:
        return "Mostly vibes."
    return "Peak slop."


def maturity_note(commits: tuple[Commit, ...], now: datetime) -> str | None:
    count = len(commits)
    if commits:
        first = min(commit.date for commit in commits)
        age = max((now - first.astimezone(now.tzinfo)).days, 0)
    else:
        age = 0
    if age < 14 or count < 10:
        return f"Too early to tell: {count} commit{'s' if count != 1 else ''}, {age} day{'s' if age != 1 else ''} old"
    return None


def aggregate(results: list[CheckResult], commits: tuple[Commit, ...], now: datetime) -> Score:
    categories: list[CategoryScore] = []
    weighted_categories = 0.0
    applicable_category_weight = 0
    for category_id, (name, category_weight) in CATEGORIES.items():
        if category_weight == 0:
            continue
        applicable = [item for item in results if item.category == category_id and item.status != "na" and item.weight > 0]
        denominator = sum(item.weight for item in applicable)
        score = None
        if denominator:
            score = 100 * sum(item.weight * STATUS_POINTS[item.status] for item in applicable) / denominator
            weighted_categories += score * category_weight
            applicable_category_weight += category_weight
        categories.append(CategoryScore(category_id, name, category_weight, score))
    evidence_score = weighted_categories / applicable_category_weight if applicable_category_weight else 0.0
    possible = sum(item.weight for item in results if item.weight > 0)
    applicable_weight = sum(item.weight for item in results if item.status != "na" and item.weight > 0)
    confidence = applicable_weight / possible if possible else 0.0
    return Score(
        evidence_score=evidence_score,
        slop_level=round((100 - evidence_score) / 10),
        confidence=confidence,
        verdict=label(evidence_score),
        maturity_note=maturity_note(commits, now),
        categories=tuple(categories),
    )

from __future__ import annotations

from dataclasses import dataclass

from slopmeter.checks.base import CHECKS

BROWSER_PROFILE_ID = "browser-reduced-v1"
BROWSER_UNAVAILABLE_REASON = "available in the complete CLI assessment"


@dataclass(frozen=True)
class AnalysisProfile:
    id: str
    run: tuple[str, ...]
    unavailable_reason: str

    @property
    def unavailable(self) -> tuple[str, ...]:
        run = set(self.run)
        return tuple(check.id for check in CHECKS if check.id not in run)


FULL_PROFILE = AnalysisProfile(
    "full",
    tuple(check.id for check in CHECKS),
    "evidence unavailable",
)

BROWSER_REDUCED_PROFILE = AnalysisProfile(
    BROWSER_PROFILE_ID,
    (
        "T1",
        "T2",
        "T3",
        "C1",
        "C2",
        "C3",
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "S1",
        "S3",
        "S4",
        "I1",
    ),
    BROWSER_UNAVAILABLE_REASON,
)

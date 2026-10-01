from __future__ import annotations

from slopmeter.checks.base import CHECKS


def metadata_table() -> str:
    lines = ["| ID | Check | Weight | Thresholds | Rationale |", "|---|---|---:|---|---|"]
    for check in CHECKS:
        lines.append(
            f"| {check.id} | {check.name} | {check.weight} | {check.thresholds} | {check.rationale} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(metadata_table())

#!/usr/bin/env python3
"""Codex Stop hook that requests one Slop Meeter evidence-review pass."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _warning(message: str) -> int:
    return _emit({"systemMessage": f"Slop Meeter hook: {message}"})


def _read_event() -> dict[str, Any]:
    try:
        value = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid hook input: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("hook input must be a JSON object")
    return value


def _repository_root(cwd: str) -> Path:
    completed = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError("the current directory is not inside a Git repository")
    return Path(completed.stdout.strip()).resolve()


def _executable() -> str | None:
    configured = os.environ.get("SLOPMETER_EXECUTABLE")
    if configured:
        candidate = Path(configured).expanduser()
        return str(candidate) if candidate.is_file() else None
    return shutil.which("slopmeter")


def _csv_environment(name: str, default: str) -> set[str]:
    return {item.strip().upper() for item in os.environ.get(name, default).split(",") if item.strip()}


def _scan_command(executable: str, root: Path) -> list[str]:
    command = [executable, str(root), "--format", "json"]
    configured = os.environ.get("SLOPMETER_CONFIG")
    config = root / configured if configured else root / ".slopmeter.toml"
    if configured or config.is_file():
        command.extend(["--config", str(config)])
    fail_under = os.environ.get("SLOPMETER_FAIL_UNDER")
    if fail_under:
        command.extend(["--fail-under", fail_under])
    return command


def _selected_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    statuses = _csv_environment("SLOPMETER_REVIEW_STATUSES", "fail,warn")
    required = _csv_environment("SLOPMETER_REQUIRED_CHECKS", "")
    checks = report.get("checks", [])
    if not isinstance(checks, list):
        return []
    return [
        check
        for check in checks
        if isinstance(check, dict)
        and str(check.get("status", "")).upper() in statuses
        and (not required or str(check.get("id", "")).upper() in required)
    ]


def _finding_summary(findings: list[dict[str, Any]]) -> str:
    rows = []
    for check in findings[:8]:
        check_id = str(check.get("id", "?"))
        status = str(check.get("status", "unknown")).upper()
        message = str(check.get("message", "No finding details"))
        rows.append(f"{check_id} {status}: {message}")
    if len(findings) > len(rows):
        rows.append(f"and {len(findings) - len(rows)} more")
    return "; ".join(rows)


def main() -> int:
    try:
        event = _read_event()
    except ValueError as exc:
        return _warning(str(exc))

    if event.get("stop_hook_active") is True:
        return _emit({})

    executable = _executable()
    if executable is None:
        return _warning("scan skipped because the slopmeter executable was not found")

    try:
        root = _repository_root(str(event.get("cwd") or os.getcwd()))
        completed = subprocess.run(
            _scan_command(executable, root),
            check=False,
            capture_output=True,
            text=True,
            timeout=110,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return _warning(f"scan could not run: {exc}")

    if completed.returncode not in {0, 1}:
        detail = completed.stderr.strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        return _warning(f"scan exited with status {completed.returncode}{suffix}")

    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _warning("scan did not produce a valid JSON report")
    if not isinstance(report, dict):
        return _warning("scan report was not a JSON object")

    score = report.get("evidence_score", "unknown")
    confidence = report.get("confidence", "unknown")
    findings = _selected_findings(report)
    summary = f"evidence score {score}, confidence {confidence}%"
    below_floor = completed.returncode == 1

    if findings or below_floor:
        details = _finding_summary(findings) if findings else "configured evidence floor was not met"
        reason = (
            f"Slop Meeter reported {summary}. Review these findings before finishing: {details}. "
            "Fix genuine regressions caused by the current work, but do not manufacture evidence or "
            "game the score. Report pre-existing, intentional, or unavailable findings explicitly."
        )
        if os.environ.get("SLOPMETER_HOOK_ADVISORY") == "1":
            return _warning(reason)
        return _emit({"decision": "block", "reason": reason})

    return _emit({"systemMessage": f"Slop Meeter review passed with {summary}."})


if __name__ == "__main__":
    raise SystemExit(main())

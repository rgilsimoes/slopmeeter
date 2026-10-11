from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "integrations" / "codex" / "hooks" / "slopmeter_stop.py"


def _run_hook(payload: dict[str, object], env: dict[str, str]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        check=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return json.loads(completed.stdout)


def test_stop_hook_does_not_continue_twice(tmp_path):
    env = os.environ.copy()
    env["SLOPMETER_EXECUTABLE"] = str(tmp_path / "missing")

    assert _run_hook({"stop_hook_active": True}, env) == {}


def test_stop_hook_requests_one_review_pass_for_findings(tmp_path):
    report = {
        "evidence_score": 52,
        "confidence": 81,
        "checks": [
            {"id": "T2", "status": "fail", "message": "tests contain no assertions"},
            {"id": "D1", "status": "warn", "message": "README lacks an example"},
            {"id": "S4", "status": "pass", "message": "no secrets found"},
        ],
    }
    executable = tmp_path / "slopmeter"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        f"print(json.dumps({report!r}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    env = os.environ.copy()
    env["SLOPMETER_EXECUTABLE"] = str(executable)

    output = _run_hook({"cwd": str(ROOT), "stop_hook_active": False}, env)

    assert output["decision"] == "block"
    assert "T2 FAIL" in output["reason"]
    assert "D1 WARN" in output["reason"]
    assert "S4" not in output["reason"]
    assert "evidence score 52" in output["reason"]


def test_stop_hook_can_restrict_review_to_required_checks(tmp_path):
    report = {
        "evidence_score": 70,
        "confidence": 75,
        "checks": [
            {"id": "D1", "status": "fail", "message": "README is incomplete"},
            {"id": "S4", "status": "pass", "message": "no secrets found"},
        ],
    }
    executable = tmp_path / "slopmeter"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        f"print(json.dumps({report!r}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    env = os.environ.copy()
    env["SLOPMETER_EXECUTABLE"] = str(executable)
    env["SLOPMETER_REQUIRED_CHECKS"] = "S4"

    output = _run_hook({"cwd": str(ROOT), "stop_hook_active": False}, env)

    assert "decision" not in output
    assert "review passed" in output["systemMessage"]


def test_codex_hook_configuration_is_valid_and_points_to_installed_helper():
    path = ROOT / "integrations" / "codex" / "hooks.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    handler = data["hooks"]["Stop"][0]["hooks"][0]
    assert handler["type"] == "command"
    assert ".codex/hooks/slopmeter_stop.py" in handler["command"]


def test_public_llms_file_links_the_agent_contract():
    content = (ROOT / "website" / "public" / "llms.txt").read_text(encoding="utf-8")

    assert "Complete methodology" in content
    assert "Agent and CI integration" in content
    assert "AGENTS.md template" in content
    assert "JSON report schema" in content


def test_website_exposes_a_visible_llms_link():
    content = (ROOT / "website" / "public" / "index.html").read_text(encoding="utf-8")

    assert '<a href="llms.txt">Agent docs (llms.txt)</a>' in content


def test_website_sample_report_uses_full_cli_output():
    index = (ROOT / "website" / "public" / "index.html").read_text(encoding="utf-8")
    report = (ROOT / "website" / "public" / "sample-report.html").read_text(encoding="utf-8")

    assert '<a id="sample-report-link" href="sample-report.html">Sample report</a>' in index
    assert "CLI sample report" in report
    assert "Online analysis" in report
    assert "History &amp; substance" in report

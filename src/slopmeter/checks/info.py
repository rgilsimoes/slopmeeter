from __future__ import annotations

import re

from slopmeter.checks.base import CheckResult, result
from slopmeter.repo import RepoContext

AI_FILES = {"agents.md", "claude.md", ".cursorrules", ".github/copilot-instructions.md"}


def run(repo: RepoContext) -> list[CheckResult]:
    files = [file.relative for file in repo.files if file.relative.lower() in AI_FILES]
    readme = next((file for file in repo.files if file.relative.lower() == "readme.md"), None)
    if readme and re.search(r"\b(?:AI[- ]assist|generated with|written with|Claude|ChatGPT|Codex)\b", repo.read_text(readme.relative), re.I):
        files.append(f"{readme.relative}: disclosure statement")
    message = "AI-assistance disclosure found" if files else "no AI-assistance disclosure found"
    return [result("I1", "na", message, files)]


from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path


class RepoBuilder:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir()
        self._git("init", "-b", "main")
        self._git("config", "user.name", "Test Author")
        self._git("config", "user.email", "test@example.com")

    def _git(self, *args: str, env: dict[str, str] | None = None) -> str:
        completed = subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", *args],
            cwd=self.path,
            text=True,
            capture_output=True,
            check=True,
            env={**os.environ, **(env or {})},
        )
        return completed.stdout

    def commit(
        self,
        files: dict[str, str],
        message: str,
        date: datetime,
        author: tuple[str, str] = ("Test Author", "test@example.com"),
    ) -> RepoBuilder:
        for relative, contents in files.items():
            target = self.path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding="utf-8")
        self._git("add", ".")
        stamp = date.isoformat()
        env = {
            "GIT_AUTHOR_NAME": author[0],
            "GIT_AUTHOR_EMAIL": author[1],
            "GIT_AUTHOR_DATE": stamp,
            "GIT_COMMITTER_NAME": author[0],
            "GIT_COMMITTER_EMAIL": author[1],
            "GIT_COMMITTER_DATE": stamp,
        }
        self._git("commit", "-m", message, env=env)
        return self

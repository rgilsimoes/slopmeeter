from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from slopmeter.repo import RepoError

GITHUB_URL = re.compile(r"^(?:https://github\.com/|git@github\.com:)([^/]+)/([^/#]+?)(?:\.git)?/?$")


def github_slug(value: str) -> tuple[str, str] | None:
    match = GITHUB_URL.match(value.strip())
    return (match.group(1), match.group(2)) if match else None


def origin_slug(path: Path) -> tuple[str, str] | None:
    try:
        completed = subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "remote", "get-url", "origin"],
            cwd=path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return github_slug(completed.stdout.strip()) if completed.returncode == 0 else None


@contextmanager
def materialize(target: str, online: bool) -> Iterator[tuple[Path, tuple[str, str] | None]]:
    if "://" not in target and not target.startswith("git@"):
        path = Path(target).expanduser().resolve()
        yield path, origin_slug(path)
        return
    if not online:
        raise RepoError("URL targets require --online because cloning uses the network")
    if not target.startswith("https://github.com/"):
        raise RepoError("only HTTPS GitHub URLs are supported")
    slug = github_slug(target)
    if slug is None:
        raise RepoError("invalid GitHub repository URL")
    with tempfile.TemporaryDirectory(prefix="slopmeter-") as temporary:
        destination = Path(temporary) / "repo"
        command = [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "protocol.file.allow=never",
            "-c", "filter.lfs.smudge=", "-c", "filter.lfs.required=false",
            "clone", "--no-recurse-submodules", "--quiet", target, str(destination),
        ]
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                env={
                    **os.environ,
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_TERMINAL_PROMPT": "0",
                },
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RepoError(f"clone failed safely: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "unknown error"
            raise RepoError(f"clone failed: {detail}")
        yield destination, slug


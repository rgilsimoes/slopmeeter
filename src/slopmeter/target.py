from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from slopmeter.repo import RepoError

GITHUB_URL = re.compile(r"^(?:https://github\.com/|git@github\.com:)([^/]+)/([^/#]+?)(?:\.git)?/?$")
CLONE_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class OriginResolution:
    slug: tuple[str, str] | None = None
    reason: str | None = None


def github_slug(value: str) -> tuple[str, str] | None:
    match = GITHUB_URL.match(value.strip())
    return (match.group(1), match.group(2)) if match else None


def origin_slug(path: Path) -> OriginResolution:
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
    except subprocess.TimeoutExpired:
        return OriginResolution(reason="git origin lookup timed out after 10 seconds")
    except OSError as exc:
        return OriginResolution(reason=f"git origin lookup failed: {exc}")
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        reason = detail[-1] if detail else "git command returned no origin"
        return OriginResolution(reason=f"git origin lookup failed: {reason}")
    value = completed.stdout.strip()
    slug = github_slug(value)
    if slug is None:
        return OriginResolution(reason="origin is not a supported GitHub URL")
    return OriginResolution(slug=slug)


@contextmanager
def materialize(
    target: str,
    online: bool,
    *,
    max_commits: int = 5000,
) -> Iterator[tuple[Path, OriginResolution]]:
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
            "clone", "--no-recurse-submodules", "--quiet", "--single-branch",
            f"--depth={max(1, max_commits)}", target, str(destination),
        ]
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=CLONE_TIMEOUT_SECONDS,
                check=False,
                env={
                    **os.environ,
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_TERMINAL_PROMPT": "0",
                },
            )
        except subprocess.TimeoutExpired as exc:
            raise RepoError(
                f"clone timed out after {CLONE_TIMEOUT_SECONDS} seconds"
            ) from exc
        except OSError as exc:
            raise RepoError(f"clone failed safely: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "unknown error"
            raise RepoError(f"clone failed: {detail}")
        yield destination, OriginResolution(slug=slug)

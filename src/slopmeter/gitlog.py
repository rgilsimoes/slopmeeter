from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from slopmeter.repo import LOCKFILE_NAMES, RepoContext


@dataclass(frozen=True)
class Commit:
    hash: str
    author_email: str
    author_name: str
    date: datetime
    message: str
    added_lines: int


def _excluded_numstat_path(path: str) -> bool:
    lowered = path.lower().replace("\\", "/")
    return (
        lowered.rsplit("/", 1)[-1] in LOCKFILE_NAMES
        or any(part in {"vendor", "node_modules", "dist", "build"} for part in lowered.split("/"))
    )


def parse_history(repo: RepoContext) -> tuple[Commit, ...]:
    if not repo.is_git_repo:
        return ()
    raw = repo.git(
        "log",
        f"--max-count={repo.max_commits}",
        "--format=%x1e%H%x1f%aE%x1f%aN%x1f%aI%x1f%s",
        "--numstat",
        "--no-renames",
    )
    commits: list[Commit] = []
    for block in raw.split("\x1e"):
        block = block.strip("\n")
        if not block:
            continue
        lines = block.splitlines()
        fields = lines[0].split("\x1f", 4)
        if len(fields) != 5:
            continue
        added = 0
        for line in lines[1:]:
            parts = line.split("\t", 2)
            if len(parts) == 3 and parts[0].isdigit() and not _excluded_numstat_path(parts[2]):
                added += int(parts[0])
        try:
            date = datetime.fromisoformat(fields[3].replace("Z", "+00:00"))
        except ValueError:
            continue
        commits.append(Commit(fields[0], fields[1].lower(), fields[2], date, fields[4], added))
    return tuple(commits)


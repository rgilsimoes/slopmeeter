from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from slopmeter.config import Config

if TYPE_CHECKING:
    from slopmeter.gitlog import Commit

CODE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js", ".jsx",
    ".kt", ".kts", ".lua", ".php", ".py", ".rb", ".rs", ".scala", ".sh", ".swift",
    ".ts", ".tsx", ".vue",
}
LOCKFILE_NAMES = {
    "cargo.lock", "composer.lock", "gemfile.lock", "package-lock.json", "pnpm-lock.yaml",
    "poetry.lock", "uv.lock", "yarn.lock",
}


@dataclass(frozen=True)
class FileRecord:
    relative: str
    size: int
    suffix: str
    is_code: bool
    is_binary: bool
    mode: str | None = None
    object_sha: str | None = None


T = TypeVar("T")


@dataclass(frozen=True)
class Evidence(Generic[T]):
    value: T | None
    reason: str | None = None

    @property
    def available(self) -> bool:
        return self.reason is None

    @classmethod
    def found(cls, value: T) -> Evidence[T]:
        return cls(value)

    @classmethod
    def unavailable(cls, reason: str) -> Evidence[T]:
        return cls(None, reason)


class RepositoryView(Protocol):
    config: Config
    files: tuple[FileRecord, ...]

    def exists(self, relative: str) -> bool: ...

    def matching_files(self, predicate) -> list[FileRecord]: ...

    def read_text(self, relative: str, limit: int | None = None) -> str: ...

    def history(self) -> Evidence[tuple[Commit, ...]]: ...

    def tags(self) -> Evidence[tuple[str, ...]]: ...


class RepoError(RuntimeError):
    pass


class RepoContext:
    def __init__(self, path: str | Path, config: Config | None = None, max_commits: int = 5000):
        candidate = Path(path).expanduser().resolve()
        if not candidate.is_dir():
            raise RepoError(f"repository path is not a directory: {path}")
        self.path = candidate
        self.config = config or Config()
        self.max_commits = max_commits
        self.files = self._inventory()
        self._by_relative = {item.relative: item for item in self.files}

    def _ignored(self, relative: Path) -> bool:
        parts = relative.parts
        return any(part in self.config.ignored_paths for part in parts)

    def _inventory(self) -> tuple[FileRecord, ...]:
        records: list[FileRecord] = []
        for root, dirs, files in os.walk(self.path, followlinks=False):
            root_path = Path(root)
            relative_root = root_path.relative_to(self.path)
            dirs[:] = sorted(
                name for name in dirs
                if not self._ignored(relative_root / name) and not (root_path / name).is_symlink()
            )
            for name in sorted(files):
                relative = relative_root / name
                if self._ignored(relative):
                    continue
                full_path = root_path / name
                if full_path.is_symlink():
                    continue
                try:
                    stat = full_path.stat()
                except OSError:
                    continue
                if stat.st_size > self.config.max_file_size:
                    continue
                try:
                    prefix = full_path.read_bytes()[:8192]
                except OSError:
                    continue
                is_binary = b"\0" in prefix
                suffix = full_path.suffix.lower()
                records.append(FileRecord(relative.as_posix(), stat.st_size, suffix, suffix in CODE_SUFFIXES, is_binary))
                if len(records) >= self.config.max_files:
                    return tuple(records)
        return tuple(records)

    def exists(self, relative: str) -> bool:
        return relative.replace("\\", "/") in self._by_relative

    def matching_files(self, predicate) -> list[FileRecord]:
        return [item for item in self.files if predicate(item)]

    def read_text(self, relative: str, limit: int | None = None) -> str:
        normalized = relative.replace("\\", "/")
        record = self._by_relative.get(normalized)
        if record is None or record.is_binary:
            return ""
        path = self.path / normalized
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(self.path)
        except (OSError, ValueError):
            return ""
        try:
            data = resolved.read_bytes()
        except OSError:
            return ""
        if limit is not None:
            data = data[:limit]
        return data.decode("utf-8", errors="replace")

    def git(self, *args: str, timeout: float = 20.0, check: bool = True) -> str:
        command = [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "core.attributesFile=/dev/null",
            "--no-pager", *args,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=self.path,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RepoError(f"git inspection failed: {exc}") from exc
        if check and completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "unknown error"
            raise RepoError(f"git inspection failed: {detail}")
        return completed.stdout

    @property
    def is_git_repo(self) -> bool:
        return self.git("rev-parse", "--is-inside-work-tree", check=False).strip() == "true"

    @property
    def source_loc(self) -> int:
        return sum(self.read_text(item.relative).count("\n") + 1 for item in self.files if item.is_code)

    def history(self) -> Evidence[tuple[Commit, ...]]:
        from slopmeter.gitlog import parse_history

        return Evidence.found(parse_history(self))

    def tags(self) -> Evidence[tuple[str, ...]]:
        if not self.is_git_repo:
            return Evidence.found(())
        return Evidence.found(tuple(self.git("tag", "--list", check=False).splitlines()))


def _safe_relative(relative: str) -> str:
    normalized = relative.replace("\\", "/")
    path = Path(normalized)
    if not normalized or normalized.startswith("/") or any(part in {"", ".", ".."} for part in path.parts):
        raise RepoError(f"unsafe repository path: {relative}")
    return path.as_posix()


class BrowserRepository:
    """An immutable repository view backed by bytes acquired by the browser worker."""

    def __init__(
        self,
        entries: list[tuple[str, int, str, str, bytes | bytearray | memoryview]],
        *,
        config: Config | None = None,
        tags: Evidence[tuple[str, ...]] | None = None,
    ):
        self.config = config or Config(max_files=3000)
        self._contents: dict[str, bytes] = {}
        records: list[FileRecord] = []
        for relative, declared_size, mode, object_sha, contents in entries:
            normalized = _safe_relative(relative)
            if normalized in self._contents:
                raise RepoError(f"duplicate repository path: {normalized}")
            data = bytes(contents)
            if len(data) != declared_size:
                raise RepoError(f"downloaded size mismatch for {normalized}")
            if len(data) > self.config.max_file_size:
                raise RepoError(f"browser file limit exceeded by {normalized}")
            suffix = Path(normalized).suffix.lower()
            records.append(
                FileRecord(
                    normalized,
                    len(data),
                    suffix,
                    suffix in CODE_SUFFIXES,
                    b"\0" in data[:8192],
                    mode,
                    object_sha,
                )
            )
            self._contents[normalized] = data
        if len(records) > self.config.max_files:
            raise RepoError("browser file-count limit exceeded")
        self.files = tuple(sorted(records, key=lambda item: item.relative))
        self._by_relative = {item.relative: item for item in self.files}
        self._tags = tags or Evidence.unavailable("release tag lookup was unavailable")

    def exists(self, relative: str) -> bool:
        try:
            normalized = _safe_relative(relative)
        except RepoError:
            return False
        return normalized in self._by_relative

    def matching_files(self, predicate) -> list[FileRecord]:
        return [item for item in self.files if predicate(item)]

    def read_text(self, relative: str, limit: int | None = None) -> str:
        try:
            normalized = _safe_relative(relative)
        except RepoError:
            return ""
        record = self._by_relative.get(normalized)
        if record is None or record.is_binary:
            return ""
        data = self._contents[normalized]
        if limit is not None:
            data = data[:limit]
        return data.decode("utf-8", errors="replace")

    def history(self) -> Evidence[tuple[Commit, ...]]:
        return Evidence.unavailable("available in the complete CLI assessment")

    def tags(self) -> Evidence[tuple[str, ...]]:
        return self._tags

    @property
    def source_loc(self) -> int:
        return sum(self.read_text(item.relative).count("\n") + 1 for item in self.files if item.is_code)

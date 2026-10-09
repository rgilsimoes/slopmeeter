from __future__ import annotations

import json
import re
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from slopmeter.checks.base import CheckResult, result
from slopmeter.config import Config
from slopmeter.repo import LOCKFILE_NAMES, RepositoryView


@dataclass(frozen=True)
class Dependency:
    ecosystem: str
    name: str
    specification: str
    pinned: bool
    source: str


class DependencyState(Enum):
    EXISTS = "exists"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DependencyLookupResult:
    state: DependencyState
    reason: str | None = None


class DependencyLookup(Protocol):
    def lookup(self, ecosystem: str, name: str) -> DependencyLookupResult: ...


class RegistryClient:
    def __init__(
        self,
        timeout: float = 5.0,
        request_cap: int = 25,
        total_timeout: float = 15.0,
    ):
        self.timeout = timeout
        self.request_cap = request_cap
        self.total_timeout = total_timeout
        self.requests = 0
        self._started_at: float | None = None

    def _available_timeout(self) -> float | None:
        now = time.monotonic()
        if self._started_at is None:
            self._started_at = now
        remaining = self.total_timeout - (now - self._started_at)
        if remaining <= 0:
            return None
        return min(self.timeout, remaining)

    def lookup(self, ecosystem: str, name: str) -> DependencyLookupResult:
        if self.requests >= self.request_cap:
            return DependencyLookupResult(DependencyState.UNKNOWN, "request limit reached")
        request_timeout = self._available_timeout()
        if request_timeout is None:
            return DependencyLookupResult(
                DependencyState.UNKNOWN,
                f"online lookup time budget of {self.total_timeout:g} seconds reached",
            )
        self.requests += 1
        quoted = urllib.parse.quote(name, safe="" if ecosystem == "pypi" else "@")
        url = f"https://pypi.org/pypi/{quoted}/json" if ecosystem == "pypi" else f"https://registry.npmjs.org/{quoted}"
        request = urllib.request.Request(url, headers={"User-Agent": "slopmeter/0.1 (+https://github.com/)"})
        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                if 200 <= response.status < 300:
                    return DependencyLookupResult(DependencyState.EXISTS)
                return DependencyLookupResult(DependencyState.UNKNOWN, f"HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return DependencyLookupResult(DependencyState.MISSING)
            return DependencyLookupResult(DependencyState.UNKNOWN, f"HTTP {exc.code}")
        except (OSError, urllib.error.URLError) as exc:
            detail = exc.reason if isinstance(exc, urllib.error.URLError) else str(exc)
            return DependencyLookupResult(DependencyState.UNKNOWN, f"network error: {detail}")


def _python_requirement(value: str, source: str) -> Dependency | None:
    value = value.strip()
    if not value or value.startswith(("#", "-", "http://", "https://", "git+")):
        return None
    match = re.match(r"([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)", value)
    if not match:
        return None
    name, specification = match.groups()
    pinned = bool(re.match(r"^===?\s*[^,;\s]+(?:\s*;.*)?$", specification))
    return Dependency("pypi", name, specification.strip(), pinned, source)


def dependencies(repo: RepositoryView) -> list[Dependency]:
    found: list[Dependency] = []
    for file in repo.files:
        basename = file.relative.lower().rsplit("/", 1)[-1]
        if basename.startswith("requirements") and basename.endswith(".txt"):
            for line in repo.read_text(file.relative).splitlines():
                item = _python_requirement(line.split("#", 1)[0], file.relative)
                if item:
                    found.append(item)
        elif basename == "pyproject.toml":
            try:
                data = tomllib.loads(repo.read_text(file.relative))
            except tomllib.TOMLDecodeError:
                continue
            for value in data.get("project", {}).get("dependencies", []):
                item = _python_requirement(str(value), file.relative)
                if item:
                    found.append(item)
        elif basename == "package.json":
            try:
                data = json.loads(repo.read_text(file.relative))
            except (json.JSONDecodeError, TypeError):
                continue
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                for name, specification in data.get(section, {}).items():
                    specification = str(specification)
                    pinned = bool(re.fullmatch(r"\d+(?:\.\d+){2}(?:-[A-Za-z0-9.-]+)?", specification))
                    found.append(Dependency("npm", name, specification, pinned, file.relative))
    unique: dict[tuple[str, str], Dependency] = {}
    for item in found:
        unique[(item.ecosystem, item.name.lower())] = item
    return sorted(unique.values(), key=lambda item: (item.ecosystem, item.name.lower()))


def check_s1(repo: RepositoryView, config: Config, declared: list[Dependency] | None = None) -> CheckResult:
    del config
    declared = dependencies(repo) if declared is None else declared
    locks = [file.relative for file in repo.files if file.relative.lower().rsplit("/", 1)[-1] in LOCKFILE_NAMES]
    if locks:
        return result("S1", "pass", "dependency lockfile found", locks)
    if not declared:
        return result("S1", "pass", "no third-party runtime dependencies declared")
    pinned = sum(item.pinned for item in declared)
    if pinned == len(declared):
        status = "pass"
    elif pinned:
        status = "warn"
    else:
        status = "fail"
    evidence = [f"{item.source}: {item.name} {item.specification or '(unpinned)'}" for item in declared if not item.pinned]
    return result("S1", status, f"{pinned} of {len(declared)} dependencies are exactly pinned", evidence[:20])


def check_s2(
    repo: RepositoryView,
    config: Config,
    client: DependencyLookup,
    declared: list[Dependency] | None = None,
) -> CheckResult:
    del config
    declared = dependencies(repo) if declared is None else declared
    if not declared:
        return result("S2", "pass", "no declared third-party dependencies to verify")
    missing: list[str] = []
    unknown: list[str] = []
    for item in declared:
        lookup = client.lookup(item.ecosystem, item.name)
        label = f"{item.ecosystem}:{item.name}"
        if lookup.state is DependencyState.MISSING:
            missing.append(label)
        elif lookup.state is DependencyState.UNKNOWN:
            unknown.append(f"{label}: {lookup.reason or 'unknown reason'}")
    if missing:
        return result("S2", "fail", f"{len(missing)} declared dependencies were not found", missing)
    if unknown:
        return result("S2", "warn", f"{len(unknown)} dependencies could not be verified", unknown)
    return result("S2", "pass", f"all {len(declared)} declared dependencies exist")


def check_s3(repo: RepositoryView, config: Config) -> CheckResult:
    del config
    risks: list[str] = []
    documented = True
    for file in repo.files:
        text = repo.read_text(file.relative)
        if file.relative.lower().endswith("package.json"):
            try:
                scripts = json.loads(text).get("scripts", {})
            except (json.JSONDecodeError, TypeError):
                scripts = {}
            for name in ("preinstall", "install", "postinstall"):
                if name in scripts:
                    risks.append(f"{file.relative}: scripts.{name}")
                    documented = False
        if file.relative.lower().rsplit("/", 1)[-1].startswith("readme"):
            for line_number, line in enumerate(text.splitlines(), 1):
                if re.search(r"\b(?:curl|wget)\b.+\|\s*(?:sh|bash)\b", line, re.I):
                    risks.append(f"{file.relative}:{line_number}: shell-pipe install command")
                    if not re.search(r"\b(?:warning|review|inspect|optional)\b", line, re.I):
                        documented = False
    if not risks:
        return result("S3", "pass", "no install-time execution patterns found")
    status = "warn" if documented else "fail"
    message = "install-time execution is explicitly documented" if documented else "install-time execution pattern found"
    return result("S3", status, message, risks)


SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
    "GitHub token": re.compile(r"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36,255}(?![A-Za-z0-9_])"),
    "Slack token": re.compile(r"(?<![A-Za-z0-9-])xox[baprs]-[A-Za-z0-9-]{20,}(?![A-Za-z0-9-])"),
}


def check_s4(repo: RepositoryView, config: Config) -> CheckResult:
    del config
    findings: list[str] = []
    for file in repo.files:
        if file.is_binary:
            continue
        for line_number, line in enumerate(repo.read_text(file.relative).splitlines(), 1):
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{file.relative}:{line_number}: {name} pattern")
    if findings:
        return result("S4", "fail", f"{len(findings)} high-confidence secret patterns found", findings[:50])
    return result("S4", "pass", "no high-confidence secret patterns found")


def run(repo: RepositoryView, config: Config, online: bool = False, client: DependencyLookup | None = None) -> list[CheckResult]:
    declared = dependencies(repo)
    results = [check_s1(repo, config, declared)]
    if online:
        results.append(check_s2(repo, config, client or RegistryClient(), declared))
    else:
        results.append(result("S2", "na", "online check disabled"))
    results.extend([check_s3(repo, config), check_s4(repo, config)])
    return results

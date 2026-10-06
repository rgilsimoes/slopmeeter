from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from statistics import median
from typing import Any, Protocol

from slopmeter.checks.base import CheckResult, result


class GitHubData(Protocol):
    def repository(self) -> dict[str, Any]: ...
    def issues(self) -> list[dict[str, Any]]: ...
    def pulls(self) -> list[dict[str, Any]]: ...
    def stargazers(self) -> list[dict[str, Any]]: ...
    def issue_comments(self, number: int) -> list[dict[str, Any]]: ...
    def user(self, login: str) -> dict[str, Any]: ...


class GitHubError(RuntimeError):
    pass


class RateLimitError(GitHubError):
    pass


class GitHubClient:
    def __init__(
        self,
        owner: str,
        repo: str,
        token: str | None = None,
        timeout: float = 5.0,
        request_cap: int = 30,
        total_timeout: float = 20.0,
    ):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.timeout = timeout
        self.request_cap = request_cap
        self.total_timeout = total_timeout
        self.requests = 0
        self._cache: dict[str, Any] = {}
        self._started_at: float | None = None

    def _available_timeout(self) -> float:
        now = time.monotonic()
        if self._started_at is None:
            self._started_at = now
        remaining = self.total_timeout - (now - self._started_at)
        if remaining <= 0:
            raise GitHubError(
                f"online lookup time budget of {self.total_timeout:g} seconds reached"
            )
        return min(self.timeout, remaining)

    def _get(self, path: str, accept: str = "application/vnd.github+json") -> Any:
        key = f"{accept}:{path}"
        if key in self._cache:
            return self._cache[key]
        if self.requests >= self.request_cap:
            raise RateLimitError(f"request cap of {self.request_cap} reached")
        request_timeout = self._available_timeout()
        self.requests += 1
        headers = {
            "Accept": accept,
            "User-Agent": "slopmeter/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                value = json.loads(response.read().decode("utf-8"))
                self._cache[key] = value
                return value
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 429}:
                raise RateLimitError("GitHub API rate limit reached") from exc
            raise GitHubError(f"GitHub API returned HTTP {exc.code}") from exc
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise GitHubError(f"GitHub API request failed: {exc}") from exc

    def repository(self) -> dict[str, Any]:
        return self._get(f"/repos/{self.owner}/{self.repo}")

    def issues(self) -> list[dict[str, Any]]:
        return self._get(f"/repos/{self.owner}/{self.repo}/issues?state=all&per_page=100")

    def pulls(self) -> list[dict[str, Any]]:
        return self._get(f"/repos/{self.owner}/{self.repo}/pulls?state=all&per_page=100")

    def stargazers(self) -> list[dict[str, Any]]:
        return self._get(
            f"/repos/{self.owner}/{self.repo}/stargazers?per_page=100",
            "application/vnd.github.star+json",
        )

    def issue_comments(self, number: int) -> list[dict[str, Any]]:
        return self._get(f"/repos/{self.owner}/{self.repo}/issues/{number}/comments?per_page=100")

    def user(self, login: str) -> dict[str, Any]:
        return self._get(f"/users/{urllib.parse.quote(login, safe='')}")


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def check_m1(client: GitHubData, now: datetime) -> CheckResult:
    data = client.repository()
    created = _date(data["created_at"])
    pushed = _date(data.get("pushed_at") or data.get("updated_at") or data["created_at"])
    age_days = max((now.astimezone(UTC) - created).days, 1)
    idle_days = max((now.astimezone(UTC) - pushed).days, 0)
    if idle_days <= max(30, age_days * 0.10):
        status = "pass"
        word = "recent"
    elif idle_days <= max(180, age_days * 0.50):
        status = "warn"
        word = "aging"
    else:
        status = "fail"
        word = "stale"
    return result("M1", status, f"last repository activity is {idle_days} days old ({word})", [f"repository age: {age_days} days", f"last push: {pushed.date()}"])


def check_m2(client: GitHubData) -> CheckResult:
    issues = [item for item in client.issues() if "pull_request" not in item]
    if len(issues) < 5:
        return result("M2", "na", f"only {len(issues)} issues available; at least 5 are required")
    response_hours: list[float] = []
    for issue in issues[:20]:
        comments = issue.get("comments_data")
        if comments is None and issue.get("comments", 0):
            comments = client.issue_comments(int(issue["number"]))
        if comments:
            first = min(_date(comment["created_at"]) for comment in comments)
            response_hours.append(max((first - _date(issue["created_at"])).total_seconds() / 3600, 0))
    pulls = client.pulls()
    merged = sum(bool(item.get("merged_at")) for item in pulls)
    merge_ratio = merged / len(pulls) if pulls else 0.0
    if not response_hours:
        return result("M2", "warn", "issue response time could not be established", [f"pull requests merged: {merged}/{len(pulls)}"])
    median_hours = median(response_hours)
    if median_hours <= 7 * 24 and merge_ratio >= 0.50:
        status = "pass"
        word = "healthy"
    elif median_hours <= 30 * 24 and merge_ratio >= 0.25:
        status = "warn"
        word = "mixed"
    else:
        status = "fail"
        word = "poor"
    return result(
        "M2",
        status,
        f"maintenance responsiveness is {word}",
        [f"median first response: {median_hours / 24:.1f} days", f"pull requests merged: {merged}/{len(pulls)} ({merge_ratio:.0%})"],
    )


def check_m3(client: GitHubData, now: datetime, deep_stars: bool = False) -> CheckResult:
    data = client.repository()
    stars = int(data.get("stargazers_count", 0))
    forks = int(data.get("forks_count", 0))
    issues = int(data.get("open_issues_count", 0))
    age_days = max((now.astimezone(UTC) - _date(data["created_at"])).days, 1)
    star_rate = stars / age_days
    sampled = client.stargazers() if stars else []
    by_week: dict[str, int] = {}
    for item in sampled:
        starred_at = item.get("starred_at")
        if starred_at:
            date = _date(starred_at)
            year, week, _ = date.isocalendar()
            key = f"{year}-W{week:02d}"
            by_week[key] = by_week.get(key, 0) + 1
    busiest_share = max(by_week.values(), default=0) / len(sampled) if sampled else 0.0
    signals: list[str] = []
    if stars >= 100 and star_rate > 25 and forks / max(stars, 1) < 0.01:
        signals.append("rapid star growth with very few forks")
    if len(sampled) >= 20 and busiest_share > 0.80:
        signals.append("more than 80% of sampled stars arrived in one week")
    if stars >= 500 and forks == 0 and issues == 0:
        signals.append("high star count without forks or open issues")
    if deep_stars and sampled:
        suspicious = 0
        inspected = sampled[: min(25, len(sampled))]
        for item in inspected:
            login = item.get("user", {}).get("login")
            if not login:
                continue
            user = client.user(login)
            account_age = (_date(item["starred_at"]) - _date(user["created_at"])).days
            if account_age < 30 and int(user.get("public_repos", 0)) == 0:
                suspicious += 1
        if inspected and suspicious / len(inspected) > 0.50:
            signals.append("most deeply sampled accounts were new and had no public repositories")
    status = "fail" if len(signals) >= 2 else "warn" if signals else "pass"
    wording = "anomalous" if status == "fail" else "unusual" if status == "warn" else "plausible"
    evidence = [f"stars/day: {star_rate:.2f}", f"stars/forks/open issues: {stars}/{forks}/{issues}"]
    if sampled:
        evidence.append(f"busiest sampled week: {busiest_share:.0%} of {len(sampled)} sampled stars")
    evidence.extend(signals)
    return result("M3", status, f"star pattern is {wording}", evidence)


def run(
    client: GitHubData | None,
    now: datetime,
    deep_stars: bool = False,
    unavailable_reason: str | None = None,
) -> list[CheckResult]:
    if client is None:
        message = (
            f"GitHub data unavailable: {unavailable_reason}"
            if unavailable_reason
            else "GitHub repository could not be identified"
        )
        return [
            result("M1", "na", message),
            result("M2", "na", message),
            result("M3", "na", message),
        ]
    checks = (("M1", lambda: check_m1(client, now)), ("M2", lambda: check_m2(client)), ("M3", lambda: check_m3(client, now, deep_stars)))
    results: list[CheckResult] = []
    for check_id, operation in checks:
        try:
            results.append(operation())
        except RateLimitError as exc:
            results.append(result(check_id, "na", str(exc)))
        except (GitHubError, KeyError, TypeError, ValueError) as exc:
            results.append(result(check_id, "na", f"online data unavailable: {exc}"))
    return results

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from slopmeter.checks import claims, deps, docs, history, info, tests
from slopmeter.checks import online as online_checks
from slopmeter.checks.base import CheckResult, result
from slopmeter.gitlog import Commit, parse_history
from slopmeter.repo import RepoContext
from slopmeter.scoring import Score, aggregate


def analyze(
    repo: RepoContext,
    now: datetime,
    online: bool = False,
    dependency_client: deps.DependencyLookup | None = None,
    github_client: online_checks.GitHubData | None = None,
    deep_stars: bool = False,
    github_unavailable_reason: str | None = None,
    progress: Callable[[int, str], None] | None = None,
) -> tuple[list[CheckResult], tuple[Commit, ...], Score]:
    report_progress = progress or (lambda _percent, _stage: None)
    report_progress(40, "Inspecting repository history")
    commits = parse_history(repo)
    report_progress(50, "Checking tests and CI")
    results = [*history.run(commits, repo.config), *tests.run(repo, repo.config)]
    report_progress(60, "Checking claims and documentation")
    results.extend([*claims.run(repo, repo.config), *docs.run(repo, repo.config)])
    report_progress(72, "Checking dependencies and secrets")
    results.extend(deps.run(repo, repo.config, online=online, client=dependency_client))
    report_progress(84, "Checking maintenance signals")
    if not online:
        results.extend(
            [
                result("M1", "na", "online check disabled", []),
                result("M2", "na", "online check disabled", []),
                result("M3", "na", "online check disabled", []),
            ]
        )
    else:
        results.extend(
            online_checks.run(
                github_client,
                now,
                deep_stars=deep_stars,
                unavailable_reason=github_unavailable_reason,
            )
        )
    report_progress(90, "Calculating score")
    results.extend(info.run(repo))
    results = [replace(item, weight=repo.config.weight(item.id, item.weight)) for item in results]
    return results, commits, aggregate(results, commits, now)

from __future__ import annotations

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
) -> tuple[list[CheckResult], tuple[Commit, ...], Score]:
    commits = parse_history(repo)
    results = [
        *history.run(commits, repo.config),
        *tests.run(repo, repo.config),
        *claims.run(repo, repo.config),
        *docs.run(repo, repo.config),
        *deps.run(repo, repo.config, online=online, client=dependency_client),
    ]
    if not online:
        results.extend(
            [
                result("M1", "na", "online check disabled", []),
                result("M2", "na", "online check disabled", []),
                result("M3", "na", "online check disabled", []),
            ]
        )
    else:
        results.extend(online_checks.run(github_client, now, deep_stars=deep_stars))
    results.extend(info.run(repo))
    results = [replace(item, weight=repo.config.weight(item.id, item.weight)) for item in results]
    return results, commits, aggregate(results, commits, now)

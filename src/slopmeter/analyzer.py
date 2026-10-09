from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from slopmeter.checks import claims, deps, docs, history, info, tests
from slopmeter.checks import online as online_checks
from slopmeter.checks.base import CheckResult, result
from slopmeter.gitlog import Commit
from slopmeter.profiles import BROWSER_REDUCED_PROFILE, FULL_PROFILE, AnalysisProfile
from slopmeter.repo import Evidence, RepoContext, RepositoryView
from slopmeter.scoring import Score, aggregate


def _unavailable(check_ids: tuple[str, ...], reason: str) -> list[CheckResult]:
    return [result(check_id, "na", reason, []) for check_id in check_ids]


def analyze_repository(
    repo: RepositoryView,
    *,
    profile: AnalysisProfile,
    now: datetime,
    online: bool = False,
    dependency_client: deps.DependencyLookup | None = None,
    github_client: online_checks.GitHubData | None = None,
    deep_stars: bool = False,
    github_unavailable_reason: str | None = None,
    progress: Callable[[int, str], None] | None = None,
) -> tuple[list[CheckResult], tuple[Commit, ...], Score]:
    report_progress = progress or (lambda _percent, _stage: None)
    browser_profile = profile.id == BROWSER_REDUCED_PROFILE.id

    report_progress(40, "Inspecting repository history")
    if browser_profile:
        history_evidence: Evidence[tuple[Commit, ...]] = Evidence.unavailable(
            profile.unavailable_reason
        )
    else:
        history_evidence = repo.history()
    commits = history_evidence.value or ()

    report_progress(50, "Checking tests and CI")
    results = (
        _unavailable(("H1", "H2", "H3", "H4", "H5"), profile.unavailable_reason)
        if not history_evidence.available
        else history.run(commits, repo.config)
    )
    results.extend(tests.run(repo, repo.config))

    report_progress(60, "Checking claims and documentation")
    results.extend(claims.run(repo, repo.config))
    results.extend(docs.run(repo, repo.config, repo.tags()))

    report_progress(72, "Checking dependencies and secrets")
    if browser_profile:
        declared = deps.dependencies(repo)
        results.extend(
            [
                deps.check_s1(repo, repo.config, declared),
                result("S2", "na", profile.unavailable_reason),
                deps.check_s3(repo, repo.config),
                deps.check_s4(repo, repo.config),
            ]
        )
    else:
        results.extend(deps.run(repo, repo.config, online=online, client=dependency_client))

    report_progress(84, "Checking maintenance signals")
    if browser_profile:
        results.extend(_unavailable(("M1", "M2", "M3"), profile.unavailable_reason))
    elif not online:
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
    return results, commits, aggregate(
        results,
        commits,
        now,
        history_available=history_evidence.available,
    )


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
    return analyze_repository(
        repo,
        profile=FULL_PROFILE,
        now=now,
        online=online,
        dependency_client=dependency_client,
        github_client=github_client,
        deep_stars=deep_stars,
        github_unavailable_reason=github_unavailable_reason,
        progress=progress,
    )

from __future__ import annotations

import re

from slopmeter.checks.base import CheckResult, result
from slopmeter.config import Config
from slopmeter.gitlog import Commit

GENERIC_MESSAGE = re.compile(r"^(update|fix|wip|initial commit|update readme(?:\.md)?)$", re.I)
BOT_PATTERN = re.compile(r"(?:\[bot\]|bot@|noreply.*bot)", re.I)


def check_h1(commits: tuple[Commit, ...], config: Config) -> CheckResult:
    count = len(commits)
    if count >= config.threshold("H1.pass_commits"):
        status = "pass"
    elif count >= config.threshold("H1.warn_commits"):
        status = "warn"
    else:
        status = "fail"
    return result("H1", status, f"{count} commit{'s' if count != 1 else ''} inspected", [f"commit count: {count}"])


def check_h2(commits: tuple[Commit, ...], config: Config) -> CheckResult:
    total = sum(commit.added_lines for commit in commits)
    if total == 0:
        return result("H2", "na", "no added source lines found")
    largest = max(commits, key=lambda commit: commit.added_lines)
    share = largest.added_lines / total
    if share < config.threshold("H2.pass_share"):
        status = "pass"
    elif share <= config.threshold("H2.warn_share"):
        status = "warn"
    else:
        status = "fail"
    return result(
        "H2",
        status,
        f"largest commit holds {share:.0%} of added lines",
        [f"{largest.hash[:12]}: {largest.added_lines} of {total} added lines"],
    )


def check_h3(commits: tuple[Commit, ...], config: Config) -> CheckResult:
    if not commits:
        return result("H3", "fail", "no commit dates found")
    days = {commit.date.date() for commit in commits}
    span = (max(days) - min(days)).days + 1
    if len(days) >= config.threshold("H3.pass_days") and span >= config.threshold("H3.pass_span"):
        status = "pass"
    elif len(days) >= config.threshold("H3.warn_days"):
        status = "warn"
    else:
        status = "fail"
    return result("H3", status, f"{len(days)} active days across a {span}-day span", [f"first: {min(days)}", f"last: {max(days)}"])


def check_h4(commits: tuple[Commit, ...], config: Config) -> CheckResult:
    if not commits:
        return result("H4", "na", "no commit messages found")
    generic = [commit for commit in commits if len(commit.message.strip()) < 10 or GENERIC_MESSAGE.fullmatch(commit.message.strip())]
    share = len(generic) / len(commits)
    if share < config.threshold("H4.pass_share"):
        status = "pass"
    elif share <= config.threshold("H4.warn_share"):
        status = "warn"
    else:
        status = "fail"
    evidence = [f"{commit.hash[:12]}: {commit.message[:60]}" for commit in generic[:10]]
    return result("H4", status, f"{len(generic)} of {len(commits)} messages are generic", evidence)


def check_h5(commits: tuple[Commit, ...], config: Config) -> CheckResult:
    del config
    authors = {commit.author_email for commit in commits if not BOT_PATTERN.search(f"{commit.author_name} {commit.author_email}")}
    count = len(authors)
    status = "pass" if count >= 3 else "warn"
    return result("H5", status, f"{count} non-bot contributor identit{'y' if count == 1 else 'ies'}", sorted(authors)[:10])


def run(commits: tuple[Commit, ...], config: Config) -> list[CheckResult]:
    return [check_h1(commits, config), check_h2(commits, config), check_h3(commits, config), check_h4(commits, config), check_h5(commits, config)]


from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

from slopmeter import __version__
from slopmeter.analyzer import analyze
from slopmeter.checks.base import CHECKS
from slopmeter.checks.online import GitHubClient
from slopmeter.config import load_config
from slopmeter.repo import RepoContext, RepoError
from slopmeter.report import render
from slopmeter.target import materialize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slopmeter", description="Score repository evidence, not vibes.")
    parser.add_argument("target", nargs="?", help="local repository path or GitHub URL")
    parser.add_argument("--online", action="store_true", help="enable explicit network checks")
    parser.add_argument("--deep-stars", action="store_true", help="sample a bounded number of stargazer accounts (online only)")
    parser.add_argument("--token", help="GitHub token (default: GITHUB_TOKEN)")
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--fail-under", type=float, metavar="N")
    parser.add_argument("--max-commits", type=int, default=5000)
    parser.add_argument("--config", metavar="FILE")
    parser.add_argument("--explain", metavar="CHECK_ID")
    parser.add_argument("--list-checks", action="store_true")
    parser.add_argument("--version", action="version", version=f"slopmeter {__version__}")
    return parser


def _list_checks() -> str:
    return "\n".join(f"{check.id}\t{check.name}" for check in CHECKS)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_checks:
        print(_list_checks())
        return 0
    if args.explain:
        check = next((item for item in CHECKS if item.id.upper() == args.explain.upper()), None)
        if check is None:
            print(f"unknown check: {args.explain}", file=sys.stderr)
            return 2
        print(f"{check.id} · {check.name}\n{check.description}\nThresholds: {check.thresholds}\nRationale: {check.rationale}")
        return 0
    if not args.target:
        build_parser().error("target is required unless --list-checks, --explain, or --version is used")
    if args.fail_under is not None and not 0 <= args.fail_under <= 100:
        print("--fail-under must be between 0 and 100", file=sys.stderr)
        return 2
    if args.max_commits < 1:
        print("--max-commits must be at least 1", file=sys.stderr)
        return 2
    if args.deep_stars and not args.online:
        print("--deep-stars requires --online", file=sys.stderr)
        return 2
    try:
        config = load_config(args.config)
        with materialize(args.target, args.online) as (target, slug):
            repo = RepoContext(target, config=config, max_commits=args.max_commits)
            github_client = GitHubClient(*slug, token=args.token or os.environ.get("GITHUB_TOKEN")) if args.online and slug else None
            results, _, score = analyze(
                repo,
                datetime.now(UTC),
                online=args.online,
                github_client=github_client,
                deep_stars=args.deep_stars,
            )
            print(render(args.format, args.target, results, score, args.online), end="")
    except (OSError, ValueError, RepoError) as exc:
        print(f"slopmeter: {exc}", file=sys.stderr)
        return 2
    if args.fail_under is not None and score.evidence_score < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

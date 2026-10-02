from __future__ import annotations

import argparse
import os
import sys
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from slopmeter import __version__
from slopmeter.analyzer import analyze
from slopmeter.checks.base import CHECKS
from slopmeter.checks.online import GitHubClient
from slopmeter.config import load_config
from slopmeter.progress import ProgressIndicator
from slopmeter.repo import RepoContext, RepoError
from slopmeter.report import render
from slopmeter.target import materialize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slopmeter", description="Score repository evidence, not vibes."
    )
    parser.add_argument("target", nargs="?", help="local repository path or GitHub URL")
    parser.add_argument("--online", action="store_true", help="enable explicit network checks")
    parser.add_argument(
        "--deep-stars",
        action="store_true",
        help="sample a bounded number of stargazer accounts (online only)",
    )
    parser.add_argument("--token", help="GitHub token (default: GITHUB_TOKEN)")
    parser.add_argument("--format", choices=("text", "json", "markdown", "html"), default="text")
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="colourise text output (default: auto)",
    )
    parser.add_argument("-o", "--output", metavar="FILE", help="write the report to FILE")
    parser.add_argument("--fail-under", type=float, metavar="N")
    parser.add_argument("--max-commits", type=int, default=5000)
    parser.add_argument("--config", metavar="FILE")
    parser.add_argument("--explain", metavar="CHECK_ID")
    parser.add_argument("--list-checks", action="store_true")
    parser.add_argument("--version", action="version", version=f"slopmeter {__version__}")
    return parser


def _list_checks() -> str:
    return "\n".join(f"{check.id}\t{check.name}" for check in CHECKS)


def _color_enabled(option: str, format_name: str, output: str | None) -> bool:
    if format_name != "text":
        return False
    if option == "always":
        return True
    if option == "never":
        return False
    return (
        output is None
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM") != "dumb"
        and sys.stdout.isatty()
    )


def _write_output(filename: str, content: str) -> None:
    destination = Path(filename)
    parent = destination.parent
    if not parent.is_dir():
        raise OSError(f"output directory does not exist: {parent}")

    descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(content)
        os.replace(temporary_name, destination)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


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
        print(
            f"{check.id} · {check.name}\n{check.description}\nThresholds: {check.thresholds}\nRationale: {check.rationale}"
        )
        return 0
    if not args.target:
        build_parser().error(
            "target is required unless --list-checks, --explain, or --version is used"
        )
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
        with ProgressIndicator():
            config = load_config(args.config)
            with materialize(args.target, args.online) as (target, slug):
                repo = RepoContext(target, config=config, max_commits=args.max_commits)
                github_client = (
                    GitHubClient(*slug, token=args.token or os.environ.get("GITHUB_TOKEN"))
                    if args.online and slug
                    else None
                )
                results, _, score = analyze(
                    repo,
                    datetime.now(UTC),
                    online=args.online,
                    github_client=github_client,
                    deep_stars=args.deep_stars,
                )
                report = render(
                    args.format,
                    args.target,
                    results,
                    score,
                    args.online,
                    color=_color_enabled(args.color, args.format, args.output),
                )
                if args.output:
                    _write_output(args.output, report)
        if not args.output:
            print(report, end="")
    except (OSError, ValueError, RepoError) as exc:
        print(f"slopmeter: {exc}", file=sys.stderr)
        return 2
    if args.fail_under is not None and score.evidence_score < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

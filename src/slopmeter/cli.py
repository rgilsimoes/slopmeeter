from __future__ import annotations

import argparse
import sys

from slopmeter import __version__
from slopmeter.checks.base import CHECKS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slopmeter", description="Score repository evidence, not vibes.")
    parser.add_argument("target", nargs="?", help="local repository path or GitHub URL")
    parser.add_argument("--online", action="store_true", help="enable explicit network checks")
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
    print("analysis engine is not yet wired", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


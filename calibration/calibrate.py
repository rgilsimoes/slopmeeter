from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path

LABELS = ("solid", "mixed", "slop")


def score_target(target: str, online: bool = False) -> float:
    command = [sys.executable, "-m", "slopmeter", target, "--format", "json"]
    if online:
        command.append("--online")
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "analysis failed"
        raise RuntimeError(detail)
    return float(json.loads(completed.stdout)["evidence_score"])


def read_labels(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"repo_url", "label", "notes"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must contain repo_url,label,notes columns")
        rows = []
        for row in reader:
            label = row["label"].strip().lower()
            target = row["repo_url"].strip()
            if not target:
                continue
            if label not in LABELS:
                raise ValueError(f"unsupported label {label!r}; expected solid, mixed, or slop")
            rows.append({"repo_url": target, "label": label, "notes": row["notes"]})
        return rows


def summarize(scores: dict[str, list[float]]) -> str:
    lines = ["label,count,mean,min,max"]
    means: dict[str, float] = {}
    for label in LABELS:
        values = scores[label]
        if values:
            mean = statistics.fmean(values)
            means[label] = mean
            lines.append(f"{label},{len(values)},{mean:.2f},{min(values):.2f},{max(values):.2f}")
        else:
            lines.append(f"{label},0,n/a,n/a,n/a")
    if all(label in means for label in LABELS):
        separation = min(means["solid"] - means["mixed"], means["mixed"] - means["slop"])
        lines.append(f"separation_min_adjacent_mean_gap,{separation:.2f}")
    else:
        lines.append("separation_min_adjacent_mean_gap,n/a")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Slop Meeter against owner-curated labels.")
    parser.add_argument("labels", type=Path, help="CSV with repo_url,label,notes columns")
    parser.add_argument("--online", action="store_true", help="allow URL targets and online checks")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = read_labels(args.labels)
    except (OSError, ValueError) as exc:
        print(f"calibrate: {exc}", file=sys.stderr)
        return 2
    scores = {label: [] for label in LABELS}
    failures = 0
    for row in rows:
        try:
            score = score_target(row["repo_url"], online=args.online)
        except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            failures += 1
            print(f"calibrate: {row['repo_url']}: {exc}", file=sys.stderr)
            continue
        scores[row["label"]].append(score)
        print(f"{row['label']:<5} {score:6.2f}  {row['repo_url']}")
    print(summarize(scores))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())


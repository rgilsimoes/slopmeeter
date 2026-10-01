from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

DEFAULT_BUZZWORDS = (
    "agentic",
    "ai-powered",
    "autonomous",
    "breakthrough",
    "cutting-edge",
    "game-changing",
    "next-generation",
    "production-ready",
    "revolutionary",
    "seamless",
    "state-of-the-art",
    "transformative",
)

DEFAULT_IGNORED = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
)

DEFAULT_THRESHOLDS: dict[str, float] = {
    "H1.pass_commits": 30,
    "H1.warn_commits": 10,
    "H2.pass_share": 0.40,
    "H2.warn_share": 0.70,
    "H3.pass_days": 10,
    "H3.pass_span": 14,
    "H3.warn_days": 4,
    "H4.pass_share": 0.20,
    "H4.warn_share": 0.50,
    "T1.pass_ratio": 0.15,
    "T2.pass_ratio": 0.90,
    "T2.warn_ratio": 0.60,
    "C1.pass_ratio": 0.80,
    "C1.warn_ratio": 0.40,
    "C3.pass_density": 8,
    "C3.warn_density": 20,
    "D4.pass_share": 0.25,
    "D4.warn_share": 0.10,
    "D5.pass_density": 0.05,
    "D5.warn_density": 0.15,
}


@dataclass(frozen=True)
class Config:
    weights: dict[str, int] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    ignored_paths: tuple[str, ...] = DEFAULT_IGNORED
    buzzwords: tuple[str, ...] = DEFAULT_BUZZWORDS
    max_file_size: int = 1_000_000
    max_files: int = 20_000

    def weight(self, check_id: str, default: int) -> int:
        return self.weights.get(check_id, default)

    def threshold(self, key: str) -> float:
        return self.thresholds[key]


def _flatten_thresholds(value: dict[str, Any]) -> dict[str, float]:
    flattened: dict[str, float] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            for nested_key, nested_value in item.items():
                flattened[f"{key}.{nested_key}"] = float(nested_value)
        else:
            flattened[key] = float(item)
    return flattened


def load_config(path: str | Path | None = None) -> Config:
    config = Config()
    if path is None:
        return config
    config_path = Path(path)
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds.update(_flatten_thresholds(data.get("thresholds", {})))
    return replace(
        config,
        weights={str(key).upper(): int(value) for key, value in data.get("weights", {}).items()},
        thresholds=thresholds,
        ignored_paths=tuple(data.get("ignored_paths", DEFAULT_IGNORED)),
        buzzwords=tuple(data.get("buzzwords", DEFAULT_BUZZWORDS)),
        max_file_size=int(data.get("max_file_size", config.max_file_size)),
        max_files=int(data.get("max_files", config.max_files)),
    )


from __future__ import annotations

import json
from datetime import datetime

from slopmeter.analyzer import analyze_repository
from slopmeter.config import Config
from slopmeter.profiles import BROWSER_REDUCED_PROFILE
from slopmeter.repo import BrowserRepository, Evidence
from slopmeter.report import report_data

BROWSER_MAX_FILES = 3000
BROWSER_MAX_BYTES = 60 * 1024 * 1024
BROWSER_MAX_FILE_BYTES = 1_000_000
BROWSER_LIMIT_VERSION = "browser-limits-v1"


def analyze_browser_snapshot(
    entries,
    tag_state,
    target: str,
    revision: str,
    now_iso: str,
    elapsed_ms: int = 0,
) -> str:
    """Pyodide entry point. Inputs are plain sequences so JS/Python transfer stays bounded."""

    converted = []
    downloaded_bytes = 0
    for entry in entries:
        relative, declared_size, mode, object_sha, contents = entry
        data = bytes(contents)
        downloaded_bytes += len(data)
        converted.append((str(relative), int(declared_size), str(mode), str(object_sha), data))

    state, values, reason = tag_state
    tags = (
        Evidence.found(tuple(str(value) for value in values))
        if state == "available"
        else Evidence.unavailable(str(reason or "release tag lookup was unavailable"))
    )
    config = Config(max_file_size=BROWSER_MAX_FILE_BYTES, max_files=BROWSER_MAX_FILES)
    repository = BrowserRepository(converted, config=config, tags=tags)
    now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    results, _, score = analyze_repository(
        repository,
        profile=BROWSER_REDUCED_PROFILE,
        now=now,
    )
    payload = report_data(
        target,
        results,
        score,
        False,
        profile=BROWSER_REDUCED_PROFILE,
        revision=revision,
        acquisition={
            "file_count": len(converted),
            "downloaded_bytes": downloaded_bytes,
            "elapsed_ms": int(elapsed_ms),
            "limit_version": BROWSER_LIMIT_VERSION,
            "limits": {
                "max_files": BROWSER_MAX_FILES,
                "max_total_bytes": BROWSER_MAX_BYTES,
                "max_file_bytes": BROWSER_MAX_FILE_BYTES,
            },
        },
    )
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

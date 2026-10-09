import json
from datetime import UTC, datetime

import pytest

from slopmeter.analyzer import analyze_repository
from slopmeter.checks.base import CHECKS
from slopmeter.checks.docs import check_d3
from slopmeter.config import Config
from slopmeter.profiles import BROWSER_REDUCED_PROFILE, BROWSER_UNAVAILABLE_REASON
from slopmeter.repo import BrowserRepository, Evidence, RepoError
from slopmeter.report import report_data

NOW = datetime(2026, 1, 1, tzinfo=UTC)
REVISION = "a" * 40


def _entry(path: str, contents: str):
    data = contents.encode()
    return (path, len(data), "100644", "b" * 40, data)


def _repository(tags: Evidence[tuple[str, ...]] | None = None) -> BrowserRepository:
    return BrowserRepository(
        [
            _entry(
                "README.md",
                "# Demo\n\nA small documented tool with local evidence and a "
                "[benchmark](benchmark/run.py) showing it is 100% faster.\n\n"
                "## Install\n\n`pip install demo`\n\n```sh\ndemo .\n```\n",
            ),
            _entry(
                "LICENSE",
                "MIT License\nPermission is hereby granted, free of charge, to any person obtaining a copy",
            ),
            _entry("src/demo.py", "def add(a, b):\n    return a + b\n"),
            _entry("tests/test_demo.py", "def test_add():\n    assert 1 + 1 == 2\n"),
            _entry(".github/workflows/ci.yml", "steps:\n  - run: pytest\n"),
            _entry("benchmark/run.py", "print('benchmark harness')\n"),
        ],
        tags=tags or Evidence.found(("v1.0.0",)),
    )


def test_browser_profile_runs_shared_checks_and_marks_cli_checks_unavailable():
    results, commits, score = analyze_repository(
        _repository(), profile=BROWSER_REDUCED_PROFILE, now=NOW
    )
    by_id = {item.id: item for item in results}

    assert commits == ()
    assert tuple(by_id) == tuple(check.id for check in CHECKS)
    assert all(by_id[check_id].status == "na" for check_id in BROWSER_REDUCED_PROFILE.unavailable)
    assert all(
        by_id[check_id].message == BROWSER_UNAVAILABLE_REASON
        for check_id in BROWSER_REDUCED_PROFILE.unavailable
    )
    assert score.maturity_note is None
    assert round(score.confidence * 100) == 63


def test_browser_report_has_versioned_profile_revision_and_coverage():
    results, _, score = analyze_repository(
        _repository(), profile=BROWSER_REDUCED_PROFILE, now=NOW
    )
    data = report_data(
        "owner/repository",
        results,
        score,
        False,
        profile=BROWSER_REDUCED_PROFILE,
        revision=REVISION,
        acquisition={"file_count": 5},
    )

    assert data["schema_version"] == 2
    assert data["analysis_profile"] == "browser-reduced-v1"
    assert data["revision"] == REVISION
    assert data["mode"] == "browser"
    assert data["coverage"] == {
        "run": list(BROWSER_REDUCED_PROFILE.run),
        "unavailable": list(BROWSER_REDUCED_PROFILE.unavailable),
        "maximum_confidence": 63.46,
    }
    json.dumps(data)


def test_release_tag_states_are_distinct_in_browser_profile():
    config = Config()
    tagged = check_d3(_repository(Evidence.found(("v1",))), config)
    empty = check_d3(_repository(Evidence.found(())), config)
    unavailable = check_d3(_repository(Evidence.unavailable("tag API unavailable")), config)
    changelog_repo = BrowserRepository(
        [_entry("CHANGELOG.md", "# Changes\n")],
        tags=Evidence.unavailable("tag API unavailable"),
    )
    fallback = check_d3(changelog_repo, config)

    assert tagged.status == "pass"
    assert empty.status == "fail"
    assert unavailable.status == "na"
    assert unavailable.message == "tag API unavailable"
    assert fallback.status == "warn"
    assert "could not be checked" in fallback.message


def test_browser_repository_rejects_unsafe_paths_and_size_mismatches():
    with pytest.raises(RepoError, match="unsafe"):
        BrowserRepository([_entry("../escape.py", "value = 1\n")])
    with pytest.raises(RepoError, match="size mismatch"):
        BrowserRepository([("safe.py", 99, "100644", "b" * 40, b"value = 1\n")])

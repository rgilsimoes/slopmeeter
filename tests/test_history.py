from datetime import UTC, datetime, timedelta

import pytest

from slopmeter.checks import history
from slopmeter.config import Config
from slopmeter.gitlog import parse_history
from slopmeter.repo import RepoContext
from tests.fixtures.builders import RepoBuilder

BASE = datetime(2025, 1, 1, tzinfo=UTC)


def make_commits(tmp_path, count, *, days=None, generic=0, authors=1, giant=False):
    builder = RepoBuilder(tmp_path / "repo")
    for index in range(count):
        day = days[index] if days else index
        message = "fix" if index < generic else f"Implement useful change {index:03d}"
        author_index = index % authors
        lines = 100 if giant and index == 0 else 2
        builder.commit(
            {f"src/file{index}.py": "\n".join(f"value_{n} = {n}" for n in range(lines))},
            message,
            BASE + timedelta(days=day),
            (f"Author {author_index}", f"author{author_index}@example.com"),
        )
    context = RepoContext(builder.path)
    return parse_history(context)


@pytest.mark.parametrize(("count", "expected"), [(30, "pass"), (10, "warn"), (9, "fail")])
def test_h1_thresholds(tmp_path, count, expected):
    assert history.check_h1(make_commits(tmp_path, count), Config()).status == expected


@pytest.mark.parametrize(("count", "giant", "expected"), [(10, False, "pass"), (2, False, "warn"), (5, True, "fail")])
def test_h2_thresholds(tmp_path, count, giant, expected):
    assert history.check_h2(make_commits(tmp_path, count, giant=giant), Config()).status == expected


@pytest.mark.parametrize(
    ("days", "expected"),
    [(list(range(0, 20, 2)), "pass"), ([0, 1, 2, 3], "warn"), ([0, 1, 2], "fail")],
)
def test_h3_thresholds(tmp_path, days, expected):
    assert history.check_h3(make_commits(tmp_path, len(days), days=days), Config()).status == expected


@pytest.mark.parametrize(("generic", "expected"), [(1, "pass"), (3, "warn"), (6, "fail")])
def test_h4_thresholds(tmp_path, generic, expected):
    assert history.check_h4(make_commits(tmp_path, 10, generic=generic), Config()).status == expected


@pytest.mark.parametrize(("authors", "expected"), [(3, "pass"), (2, "warn"), (1, "warn")])
def test_h5_thresholds(tmp_path, authors, expected):
    assert history.check_h5(make_commits(tmp_path, 6, authors=authors), Config()).status == expected


from pathlib import Path

import pytest

from slopmeter.repo import RepoError
from slopmeter.target import github_slug, materialize


def test_github_slug():
    assert github_slug("https://github.com/owner/project.git") == ("owner", "project")
    assert github_slug("git@github.com:owner/project.git") == ("owner", "project")


def test_local_materialize(tmp_path):
    with materialize(str(tmp_path), False) as (path, slug):
        assert path == Path(tmp_path).resolve()
        assert slug is None


def test_url_requires_explicit_online():
    with pytest.raises(RepoError, match="require --online"), materialize(
        "https://github.com/owner/project", False
    ):
        pass

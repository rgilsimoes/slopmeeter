import subprocess
from pathlib import Path

import pytest

from slopmeter.repo import RepoError
from slopmeter.target import github_slug, materialize, origin_slug


def test_github_slug():
    assert github_slug("https://github.com/owner/project.git") == ("owner", "project")
    assert github_slug("git@github.com:owner/project.git") == ("owner", "project")


def test_local_materialize(tmp_path):
    with materialize(str(tmp_path), False) as (path, origin):
        assert path == Path(tmp_path).resolve()
        assert origin.slug is None
        assert origin.reason is not None


def test_url_requires_explicit_online():
    with pytest.raises(RepoError, match="require --online"), materialize(
        "https://github.com/owner/project", False
    ):
        pass


def test_origin_timeout_preserves_the_failure_reason(tmp_path, monkeypatch):
    def time_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", 10)

    monkeypatch.setattr("slopmeter.target.subprocess.run", time_out)

    resolution = origin_slug(tmp_path)

    assert resolution.slug is None
    assert resolution.reason == "git origin lookup timed out after 10 seconds"


def test_remote_clone_is_bounded_and_limited_to_requested_history(monkeypatch):
    captured = {}

    def time_out(command, **kwargs):
        captured["command"] = command
        captured["timeout"] = kwargs["timeout"]
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr("slopmeter.target.subprocess.run", time_out)

    with pytest.raises(RepoError, match="clone timed out after 30 seconds"), materialize(
        "https://github.com/owner/project", True, max_commits=250
    ):
        pass

    assert captured["timeout"] == 30
    assert "--single-branch" in captured["command"]
    assert "--depth=250" in captured["command"]

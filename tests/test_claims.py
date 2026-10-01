from slopmeter.checks.claims import run
from slopmeter.config import Config
from slopmeter.repo import RepoContext


def make_repo(tmp_path, files):
    root = tmp_path / "repo"
    root.mkdir()
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return RepoContext(root)


def test_claims_with_and_without_receipts_have_evidence(tmp_path):
    repo = make_repo(
        tmp_path,
        {
            "README.md": (
                "# Claims\n\n"
                "The engine is 37% faster in our benchmark.\n"
                "See [the harness](bench/run.py).\n\n"
                "## More\n\n"
                + "Context line.\n" * 11
                + "It also outperforms every alternative.\n"
            ),
            "bench/run.py": "print('static fixture; never executed')\n",
        },
    )
    results = {item.id: item for item in run(repo, Config())}
    assert results["C1"].status == "warn"
    assert results["C1"].evidence == [
        "README.md:3 receipt — The engine is 37% faster in our benchmark.",
        "README.md:19 no receipt — It also outperforms every alternative.",
    ]
    assert results["C2"].status == "pass"


def test_unsupported_claims_fail(tmp_path):
    repo = make_repo(tmp_path, {"README.md": "# Big\n\nProduction-ready and state-of-the-art.\n"})
    results = {item.id: item for item in run(repo, Config())}
    assert results["C1"].status == "fail"
    assert "no receipt" in results["C1"].evidence[0]
    assert results["C2"].status == "fail"


def test_no_claims_pass_and_harness_is_na(tmp_path):
    repo = make_repo(tmp_path, {"README.md": "# Small tool\n\nIt reads local files.\n"})
    results = {item.id: item for item in run(repo, Config())}
    assert results["C1"].status == "pass"
    assert results["C2"].status == "na"


def test_claims_inside_code_fences_are_ignored(tmp_path):
    repo = make_repo(tmp_path, {"README.md": "# Output\n\n```text\n37% faster\n```\n"})
    results = {item.id: item for item in run(repo, Config())}
    assert results["C1"].status == "pass"
    assert results["C1"].evidence == []

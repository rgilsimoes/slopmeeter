from slopmeter.checks import docs, tests
from slopmeter.config import Config
from slopmeter.repo import RepoContext


def context(tmp_path, files):
    root = tmp_path / "repo"
    root.mkdir()
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return RepoContext(root)


def test_real_tests_pass(tmp_path):
    repo = context(
        tmp_path,
        {
            "src/app.py": "def add(a, b):\n    return a + b\n",
            "tests/test_app.py": "def test_add():\n    assert 1 + 1 == 2\n",
            ".github/workflows/ci.yml": "steps:\n  - run: pytest\n",
        },
    )
    results = {item.id: item for item in tests.run(repo, Config())}
    assert results["T1"].status == "pass"
    assert results["T2"].status == "pass"
    assert results["T3"].status == "pass"


def test_assertion_free_tests_fail(tmp_path):
    repo = context(tmp_path, {"app.py": "value = 1\n", "test_app.py": "def test_nothing():\n    value = 1\n"})
    results = {item.id: item for item in tests.run(repo, Config())}
    assert results["T1"].status in {"pass", "warn"}
    assert results["T2"].status == "fail"


def test_no_tests(tmp_path):
    repo = context(tmp_path, {"app.py": "value = 1\n"})
    results = {item.id: item for item in tests.run(repo, Config())}
    assert results["T1"].status == "fail"
    assert results["T2"].status == "na"


def test_readme_and_license(tmp_path):
    repo = context(
        tmp_path,
        {
            "README.md": "# Tool\n\nA useful local tool for checking repositories.\n\n## Install\n`pip install tool`\n\n```sh\ntool .\n```\n",
            "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy",
            "src/tool.py": "def useful(value):\n    result = value * 2\n    return result + 42\n\n\ndef explain():\n    return 'evidence-first repository checking'\n",
        },
    )
    results = {item.id: item for item in docs.run(repo, Config())}
    assert results["D1"].status == "pass"
    assert results["D2"].status == "pass"
    assert results["D4"].status == "pass"
    assert results["D5"].status == "pass"

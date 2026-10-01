import os
from datetime import UTC, datetime, timedelta

from slopmeter.analyzer import analyze
from slopmeter.repo import RepoContext
from tests.fixtures.builders import RepoBuilder

BASE = datetime(2025, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_solid_like_scores_above_slop_like(tmp_path):
    solid = RepoBuilder(tmp_path / "solid")
    initial = {
        "README.md": "# Solid\n\nA careful tool for local repository review.\n\n## Install\n`pip install solid`\n\n```sh\nsolid .\n```\n",
        "LICENSE": "MIT License\nPermission is hereby granted, free of charge, to any person obtaining a copy",
        "src/solid.py": "def add(a, b):\n    return a + b\n",
        "tests/test_solid.py": "def test_add():\n    assert 1 + 1 == 2\n",
        ".github/workflows/ci.yml": "steps:\n  - run: pytest\n",
        "CHANGELOG.md": "# Changelog\n",
    }
    solid.commit(initial, "Create documented implementation and tests", BASE)
    for index in range(1, 30):
        solid.commit(
            {f"src/part_{index}.py": f"def value_{index}():\n    return {index}\n"},
            f"Implement repository capability {index}",
            BASE + timedelta(days=index),
            (f"Author {index % 3}", f"author{index % 3}@example.com"),
        )
    solid._git("tag", "v1.0.0")

    slop = RepoBuilder(tmp_path / "slop")
    slop.commit(
        {
            "README.md": "# Huge\n\nProduction-ready and 100x faster than everything.\n",
            "main.py": "\n".join(f"value_{index} = {index}" for index in range(300)),
        },
        "initial commit",
        BASE,
    )

    solid_score = analyze(RepoContext(solid.path), NOW)[2].evidence_score
    slop_score = analyze(RepoContext(slop.path), NOW)[2].evidence_score
    assert solid_score > slop_score + 25


def test_malicious_hook_symlink_and_huge_file_are_never_used(tmp_path):
    builder = RepoBuilder(tmp_path / "target")
    builder.commit({"safe.py": "value = 1\n"}, "Add safe source file", BASE)
    sentinel = tmp_path / "hook-ran"
    hook = builder.path / ".git" / "hooks" / "post-checkout"
    hook.write_text(f"#!/bin/sh\ntouch '{sentinel}'\n", encoding="utf-8")
    hook.chmod(0o755)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside secret", encoding="utf-8")
    os.symlink(outside, builder.path / "escape.txt")
    (builder.path / "huge.bin").write_bytes(b"x" * 1_000_001)

    repo = RepoContext(builder.path)
    analyze(repo, NOW)
    assert not sentinel.exists()
    assert "escape.txt" not in {file.relative for file in repo.files}
    assert "huge.bin" not in {file.relative for file in repo.files}

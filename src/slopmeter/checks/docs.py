from __future__ import annotations

import ast
import re

from slopmeter.checks.base import CheckResult, result
from slopmeter.config import Config
from slopmeter.repo import LOCKFILE_NAMES, RepoContext

LICENSE_MARKERS = {
    "mit": "permission is hereby granted, free of charge",
    "apache-2.0": "apache license, version 2.0",
    "gpl": "gnu general public license",
    "bsd": "redistribution and use in source and binary forms",
    "mpl-2.0": "mozilla public license version 2.0",
    "isc": "permission to use, copy, modify, and/or distribute this software",
}


def _readme(repo: RepoContext) -> tuple[str, str]:
    record = next((file for file in repo.files if file.relative.lower() in {"readme", "readme.md", "readme.rst", "readme.txt"}), None)
    return (record.relative, repo.read_text(record.relative)) if record else ("README", "")


def check_d1(repo: RepoContext, config: Config) -> CheckResult:
    del config
    path, text = _readme(repo)
    if not text:
        return result("D1", "fail", "README is missing")
    prose = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("#", "[", "!"))]
    description = any(len(line.split()) >= 5 for line in prose[:12])
    install = bool(re.search(r"\b(?:install|pipx|pip install|npm install|cargo install|go install)\b", text, re.I))
    example = bool(re.search(r"```[^\n]*\n.+?```", text, re.S))
    count = sum((description, install, example))
    status = "pass" if count == 3 else "warn" if count == 2 else "fail"
    missing = [name for name, present in (("description", description), ("install step", install), ("usage code block", example)) if not present]
    return result("D1", status, f"README contains {count} of 3 essentials", [f"{path}: missing {item}" for item in missing])


def check_d2(repo: RepoContext, config: Config) -> CheckResult:
    del config
    licenses = [file for file in repo.files if file.relative.lower().rsplit("/", 1)[-1].startswith(("license", "licence", "copying"))]
    if not licenses:
        return result("D2", "fail", "no license file found")
    for file in licenses:
        text = repo.read_text(file.relative).lower()
        for name, marker in LICENSE_MARKERS.items():
            if marker in text:
                return result("D2", "pass", f"recognized {name} license", [file.relative])
    return result("D2", "warn", "license file text was not recognized", [file.relative for file in licenses])


def check_d3(repo: RepoContext, config: Config) -> CheckResult:
    del config
    tags = repo.git("tag", "--list", check=False).splitlines() if repo.is_git_repo else []
    changelogs = []
    for file in repo.files:
        basename = file.relative.lower().rsplit("/", 1)[-1]
        stem = basename.split(".", 1)[0]
        if stem in {"changelog", "changes", "history"} and (file.suffix in {"", ".md", ".rst", ".txt"}):
            changelogs.append(file.relative)
    if tags:
        return result("D3", "pass", f"{len(tags)} release tag{'s' if len(tags) != 1 else ''} found", tags[:10])
    if changelogs:
        return result("D3", "warn", "changelog found without a release tag", changelogs)
    return result("D3", "fail", "no release tags or changelog found")


def check_d4(repo: RepoContext, config: Config) -> CheckResult:
    eligible = [file for file in repo.files if file.relative.lower().rsplit("/", 1)[-1] not in LOCKFILE_NAMES]
    total = sum(file.size for file in eligible)
    code = sum(file.size for file in eligible if file.is_code)
    share = code / max(total, 1)
    if share >= config.threshold("D4.pass_share"):
        status = "pass"
    elif share >= config.threshold("D4.warn_share"):
        status = "warn"
    else:
        status = "fail"
    return result("D4", status, f"code is {share:.0%} of {total} tracked bytes", [f"code bytes: {code}", f"eligible bytes: {total}"])


def _python_placeholders(text: str) -> tuple[int, int]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0, 0
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    functions = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        parent = parents.get(node)
        protocol_method = isinstance(parent, ast.ClassDef) and any(
            isinstance(base, ast.Name) and base.id == "Protocol" for base in parent.bases
        )
        abstract_method = any(
            isinstance(decorator, ast.Name) and decorator.id == "abstractmethod"
            for decorator in node.decorator_list
        )
        if not protocol_method and not abstract_method:
            functions.append(node)
    placeholders = 0
    for function in functions:
        body = function.body
        if len(body) != 1:
            continue
        statement = body[0]
        if isinstance(statement, ast.Pass) or isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and statement.value.value is Ellipsis or isinstance(statement, ast.Raise) and isinstance(statement.exc, ast.Call) and isinstance(statement.exc.func, ast.Name) and statement.exc.func.id == "NotImplementedError":
            placeholders += 1
    return len(functions), placeholders


def check_d5(repo: RepoContext, config: Config) -> CheckResult:
    functions = placeholders = markers = 0
    for file in repo.files:
        if file.is_binary:
            continue
        text = repo.read_text(file.relative)
        markers += len(re.findall(r"\b(?:TODO|lorem ipsum)\b", text, re.I))
        if file.suffix == ".py":
            found, empty = _python_placeholders(text)
            functions += found
            placeholders += empty
    denominator = max(functions + markers, 1)
    density = (placeholders + markers) / denominator
    if density < config.threshold("D5.pass_density"):
        status = "pass"
    elif density <= config.threshold("D5.warn_density"):
        status = "warn"
    else:
        status = "fail"
    return result("D5", status, f"{placeholders} empty functions and {markers} placeholder markers", [f"density: {density:.1%}"])


def run(repo: RepoContext, config: Config) -> list[CheckResult]:
    return [check_d1(repo, config), check_d2(repo, config), check_d3(repo, config), check_d4(repo, config), check_d5(repo, config)]

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from slopmeter.checks.base import CheckResult, result
from slopmeter.config import Config
from slopmeter.repo import FileRecord, RepositoryView

TEST_SUFFIXES = (".test.js", ".test.jsx", ".test.ts", ".test.tsx", "_test.go")
TEST_DIRS = {"tests", "test", "__tests__", "spec"}
CI_PATHS = (".github/workflows/", ".gitlab-ci.yml", ".circleci/", "azure-pipelines.yml")
TEST_COMMAND = re.compile(r"(?:pytest|unittest|npm\s+(?:run\s+)?test|pnpm\s+test|yarn\s+test|go\s+test|cargo\s+test|mvn\s+test|gradle\s+test)", re.I)


@dataclass(frozen=True)
class PythonTestParse:
    functions: tuple[tuple[str, bool], ...] = ()
    error: str | None = None


def is_test_file(file: FileRecord) -> bool:
    path = file.relative.lower()
    name = path.rsplit("/", 1)[-1]
    return (
        any(part in TEST_DIRS for part in path.split("/")[:-1])
        or name.startswith("test_") and name.endswith(".py")
        or name.endswith(TEST_SUFFIXES)
        or name.endswith("_test.py")
    )


def _loc(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def check_t1(repo: RepositoryView, config: Config) -> CheckResult:
    test_files = [file for file in repo.files if file.is_code and is_test_file(file)]
    source_files = [file for file in repo.files if file.is_code and not is_test_file(file)]
    test_loc = sum(_loc(repo.read_text(file.relative)) for file in test_files)
    source_loc = sum(_loc(repo.read_text(file.relative)) for file in source_files)
    if not test_files or test_loc == 0:
        return result("T1", "fail", "no test code found")
    ratio = test_loc / max(source_loc, 1)
    status = "pass" if ratio >= config.threshold("T1.pass_ratio") else "warn"
    return result(
        "T1",
        status,
        f"{test_loc} test LOC / {source_loc} source LOC ({ratio:.0%})",
        [file.relative for file in test_files[:20]],
    )


def _is_trivial_assert(node: ast.Assert) -> bool:
    value = node.test
    return isinstance(value, ast.Constant) and bool(value.value)


def _python_test_functions(text: str) -> PythonTestParse:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno is not None else "unknown line"
        return PythonTestParse(error=f"{exc.msg} at {location}")
    found: list[tuple[str, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test"):
            continue
        meaningful = False
        for child in ast.walk(node):
            if isinstance(child, ast.Assert) and not _is_trivial_assert(child):
                meaningful = True
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute) and (
                    func.attr.startswith("assert") or func.attr == "raises"
                ):
                    meaningful = True
        found.append((node.name, meaningful))
    return PythonTestParse(tuple(found))


def _js_test_functions(text: str) -> list[tuple[str, bool]]:
    starts = list(re.finditer(r"\b(?:it|test)\s*\(", text))
    found: list[tuple[str, bool]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else min(len(text), match.start() + 4000)
        block = text[match.start():end]
        meaningful = bool(re.search(r"\b(?:expect|assert)\s*\(", block))
        if re.search(r"expect\s*\(\s*true\s*\)\.toBe\s*\(\s*true\s*\)", block, re.I):
            meaningful = False
        found.append((f"test at offset {match.start()}", meaningful))
    return found


def check_t2(repo: RepositoryView, config: Config) -> CheckResult:
    tests: list[tuple[str, str, bool]] = []
    parse_errors: list[str] = []
    supported_files = 0
    for file in repo.files:
        if not is_test_file(file):
            continue
        text = repo.read_text(file.relative)
        parsed: list[tuple[str, bool]] = []
        if file.suffix == ".py":
            supported_files += 1
            outcome = _python_test_functions(text)
            parsed = list(outcome.functions)
            if outcome.error:
                parse_errors.append(f"{file.relative}: {outcome.error}")
        elif file.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            supported_files += 1
            parsed = _js_test_functions(text)
        tests.extend((file.relative, name, assertion) for name, assertion in parsed)
    if supported_files == 0:
        return result("T2", "na", "no supported test functions found")
    if not tests:
        if parse_errors:
            count = len(parse_errors)
            noun = "file" if count == 1 else "files"
            return result("T2", "warn", f"{count} test {noun} could not be parsed", parse_errors[:20])
        return result("T2", "na", "no supported test functions found")
    asserted = sum(assertion for _, _, assertion in tests)
    share = asserted / len(tests)
    if share >= config.threshold("T2.pass_ratio"):
        status = "pass"
    elif share >= config.threshold("T2.warn_ratio"):
        status = "warn"
    else:
        status = "fail"
    missing = [f"{path}: {name}" for path, name, assertion in tests if not assertion]
    message = f"{asserted} of {len(tests)} test functions contain meaningful assertions"
    if parse_errors:
        count = len(parse_errors)
        noun = "file" if count == 1 else "files"
        message += f"; {count} test {noun} could not be parsed"
        if status == "pass":
            status = "warn"
    return result("T2", status, message, (parse_errors + missing)[:20])


def check_t3(repo: RepositoryView, config: Config) -> CheckResult:
    del config
    ci_files = [file for file in repo.files if file.relative.startswith(CI_PATHS) or file.relative in CI_PATHS]
    if not ci_files:
        return result("T3", "fail", "no CI configuration found")
    running = [file.relative for file in ci_files if TEST_COMMAND.search(repo.read_text(file.relative))]
    if running:
        return result("T3", "pass", "CI configuration runs tests", running)
    return result("T3", "warn", "CI exists but no test command was found", [file.relative for file in ci_files])


def run(repo: RepositoryView, config: Config) -> list[CheckResult]:
    return [check_t1(repo, config), check_t2(repo, config), check_t3(repo, config)]

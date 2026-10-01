from __future__ import annotations

import re
from dataclasses import dataclass

from slopmeter.checks.base import CheckResult, result
from slopmeter.config import Config
from slopmeter.repo import RepoContext

CLAIM_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s?(?:%|x|×)\b|\b(?:faster|improves?|reduces?|state[- ]of[- ]the[- ]art|SOTA|production[- ]ready|outperforms?)\b)",
    re.I,
)
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)|https?://[^\s)>]+", re.I)
EVIDENCE_PATH = re.compile(r"(?:^|/)(?:bench|benchmark|eval|evaluation|result|notebook|script)[^/]*", re.I)


@dataclass(frozen=True)
class Claim:
    path: str
    line: int
    text: str
    receipt: bool


def _documentation_files(repo: RepoContext) -> list[str]:
    return [
        file.relative
        for file in repo.files
        if "/" not in file.relative
        and file.suffix in {".md", ".rst", ".txt"}
        and "plan" not in file.relative.lower()
        and not file.relative.lower().startswith(("changelog", "license"))
    ]


def _link_has_receipt(repo: RepoContext, text: str) -> bool:
    for match in LINK_PATTERN.finditer(text):
        target = (match.group(1) or match.group(0)).strip().split("#", 1)[0]
        if target.startswith(("http://", "https://")):
            return True
        normalized = target.removeprefix("./").rstrip("/")
        if EVIDENCE_PATH.search(normalized) and (
            repo.exists(normalized) or any(file.relative.startswith(f"{normalized}/") for file in repo.files)
        ):
            return True
    return False


def extract_claims(repo: RepoContext) -> list[Claim]:
    claims: list[Claim] = []
    for path in _documentation_files(repo):
        lines = repo.read_text(path).splitlines()
        headings = [index for index, line in enumerate(lines) if re.match(r"^#{1,6}\s", line)]
        for index, line in enumerate(lines):
            if not CLAIM_PATTERN.search(line):
                continue
            section_start = max((heading for heading in headings if heading <= index), default=0)
            section_end = min((heading for heading in headings if heading > index), default=len(lines))
            nearby_start = max(section_start, index - 10)
            nearby_end = min(section_end, index + 11)
            receipt = _link_has_receipt(repo, "\n".join(lines[nearby_start:nearby_end]))
            excerpt = " ".join(line.strip().split())[:140]
            claims.append(Claim(path, index + 1, excerpt, receipt))
    return claims


def check_c1(repo: RepoContext, config: Config, claims: list[Claim] | None = None) -> CheckResult:
    claims = extract_claims(repo) if claims is None else claims
    if not claims:
        return result("C1", "pass", "no quantitative or superlative claims found")
    received = sum(claim.receipt for claim in claims)
    share = received / len(claims)
    if share >= config.threshold("C1.pass_ratio"):
        status = "pass"
    elif share >= config.threshold("C1.warn_ratio"):
        status = "warn"
    else:
        status = "fail"
    evidence = [
        f"{claim.path}:{claim.line} {'receipt' if claim.receipt else 'no receipt'} — {claim.text}"
        for claim in claims
    ]
    return result("C1", status, f"{received} of {len(claims)} claims link to evidence", evidence)


def check_c2(repo: RepoContext, config: Config, claims: list[Claim] | None = None) -> CheckResult:
    del config
    claims = extract_claims(repo) if claims is None else claims
    if not claims:
        return result("C2", "na", "no claims require an evaluation harness")
    candidates = [file for file in repo.files if re.search(r"(?:^|/)(?:bench|benchmark|eval|evaluation|results?)(?:/|[_.-])", file.relative, re.I)]
    scripts = [file.relative for file in candidates if file.is_code]
    if scripts:
        return result("C2", "pass", "benchmark or evaluation code found", scripts[:20])
    if candidates:
        return result("C2", "warn", "evaluation results found without a runnable harness", [file.relative for file in candidates[:20]])
    return result("C2", "fail", "claims found but no benchmark or evaluation harness found")


def check_c3(repo: RepoContext, config: Config) -> CheckResult:
    readme = next((file for file in repo.files if file.relative.lower() in {"readme.md", "readme.rst", "readme.txt", "readme"}), None)
    text = repo.read_text(readme.relative) if readme else ""
    words = re.findall(r"\b[\w-]+\b", text.lower())
    lowered = text.lower()
    hits = sum(len(re.findall(rf"(?<!\w){re.escape(word.lower())}(?!\w)", lowered)) for word in config.buzzwords)
    density = hits * 1000 / max(len(words), 1)
    if density < config.threshold("C3.pass_density"):
        status = "pass"
    elif density <= config.threshold("C3.warn_density"):
        status = "warn"
    else:
        status = "fail"
    return result("C3", status, f"{hits} buzzwords in {len(words)} README words ({density:.1f} per 1,000)")


def run(repo: RepoContext, config: Config) -> list[CheckResult]:
    claims = extract_claims(repo)
    return [check_c1(repo, config, claims), check_c2(repo, config, claims), check_c3(repo, config)]

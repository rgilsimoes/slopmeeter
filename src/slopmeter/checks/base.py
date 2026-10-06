from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Status = Literal["pass", "warn", "fail", "na"]


@dataclass(frozen=True)
class CheckDefinition:
    id: str
    name: str
    category: str
    weight: int
    description: str
    thresholds: str
    rationale: str
    requires_online: bool = False


@dataclass(frozen=True)
class CheckResult:
    id: str
    name: str
    category: str
    weight: int
    status: Status
    message: str
    evidence: list[str]
    requires_online: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


CATEGORIES = {
    "history": ("History & substance", 25),
    "tests": ("Tests & CI", 20),
    "claims": ("Claims vs. receipts", 20),
    "docs": ("Docs, release & composition", 10),
    "security": ("Dependencies & security", 10),
    "maintenance": ("Maintenance & attention", 15),
    "info": ("Information", 0),
}


CHECKS = [
    CheckDefinition("H1", "Commit depth", "history", 3, "Counts commits up to the configured cap.", ">=30 pass; 10-29 warn; <10 fail", "Sustained work is harder to stage in one dump."),
    CheckDefinition("H2", "Largest-commit share", "history", 3, "Measures the largest share of added lines, excluding generated paths.", "<40% pass; 40-70% warn; >70% fail", "Incremental history provides more evidence than a single code dump."),
    CheckDefinition("H3", "Time spread", "history", 2, "Measures active days and calendar span.", ">=10 active days and >=14 day span pass; 4-9 days warn; <=3 days fail", "Work distributed over time offers more observable history."),
    CheckDefinition("H4", "Commit messages", "history", 1, "Counts generic or very short commit messages.", "<20% pass; 20-50% warn; >50% fail", "Specific messages make history auditable."),
    CheckDefinition("H5", "Contributors", "history", 1, "Counts normalized non-bot author emails.", ">=3 pass; 2 warn; 1 warn", "Independent contributors are a mild corroborating signal."),
    CheckDefinition("T1", "Tests present", "tests", 4, "Finds conventional tests and compares test LOC with source LOC.", ">=15% pass; >0 warn; none fail", "Tests are reproducible evidence of behavior."),
    CheckDefinition("T2", "Tests assert", "tests", 4, "Checks whether Python and JS/TS tests contain meaningful assertions.", ">=90% pass; 60-89% warn; <60% fail; Python parse errors prevent pass", "Test-shaped files without assertions provide weak evidence."),
    CheckDefinition("T3", "CI runs tests", "tests", 2, "Looks for CI configuration with a test command.", "CI + tests pass; CI without tests warn; no CI fail", "Automated execution makes tests more credible."),
    CheckDefinition("C1", "Claims have receipts", "claims", 5, "Matches quantitative or superlative claims and nearby evidence links.", ">=80% or no claims pass; 40-79% warn; <40% fail", "Strong claims should point to reproducible evidence."),
    CheckDefinition("C2", "Eval harness present", "claims", 3, "Looks for benchmark or evaluation scripts when claims exist.", "runnable harness pass; results only warn; claims without either fail", "A harness makes performance claims reproducible."),
    CheckDefinition("C3", "Hype density", "claims", 1, "Counts configured buzzwords per 1,000 README words.", "<8 pass; 8-20 warn; >20 fail", "Dense promotional language can crowd out verifiable detail."),
    CheckDefinition("D1", "README essentials", "docs", 2, "Checks for description, installation and a code example.", "3 pass; 2 warn; <=1 fail", "Basic documentation lets users evaluate the project."),
    CheckDefinition("D2", "License", "docs", 2, "Looks for a recognizable license file.", "recognized pass; unrecognized warn; missing fail", "A clear license establishes reuse terms."),
    CheckDefinition("D3", "Release hygiene", "docs", 1, "Looks for tags, changelog, or version changes.", "release evidence pass; partial warn; none fail", "Release records provide a public change trail."),
    CheckDefinition("D4", "Substance vs. fluff", "docs", 2, "Measures code bytes as a share of tracked project bytes.", ">=25% pass; 10-25% warn; <10% fail", "Implementation substance should support project claims."),
    CheckDefinition("D5", "Placeholder density", "docs", 1, "Counts empty Python functions and TODO/lorem markers.", "<5% pass; 5-15% warn; >15% fail", "Placeholders weaken evidence of completion."),
    CheckDefinition("S1", "Lockfile / pinning", "security", 1, "Checks dependency locks and exact version pins.", "locked/pinned pass; partial warn; none fail", "Reproducible dependency resolution reduces ambiguity."),
    CheckDefinition("S2", "Dependencies exist", "security", 3, "Queries official package registries for declared dependencies.", "all exist pass; unverifiable warn; nonexistent fail", "Missing packages can reveal broken or mistaken manifests.", True),
    CheckDefinition("S3", "Install-time risk", "security", 2, "Finds lifecycle scripts and shell-pipe installation instructions.", "none pass; documented warn; undocumented fail", "Install-time execution deserves explicit scrutiny."),
    CheckDefinition("S4", "Secrets patterns", "security", 3, "Finds high-confidence credential patterns without printing values.", "none pass; any fail", "Published credentials create concrete risk."),
    CheckDefinition("M1", "Recency", "maintenance", 1, "Compares last activity with repository age.", "recent pass; aging warn; stale fail", "Recent maintenance is evidence of ongoing stewardship.", True),
    CheckDefinition("M2", "Responsiveness", "maintenance", 2, "Measures issue first-response time and pull-request merge ratio.", "healthy pass; mixed warn; poor fail", "Responsive maintenance supports real-world usability.", True),
    CheckDefinition("M3", "Star plausibility", "maintenance", 3, "Compares attention with age, forks, contributors, and issue activity.", "plausible pass; unusual warn; anomalous fail", "Attention patterns are context, not proof of wrongdoing.", True),
    CheckDefinition("I1", "AI-assistance disclosure", "info", 0, "Reports AI-assistance files or disclosures neutrally.", "informational only", "AI use is neither rewarded nor punished."),
]

CHECK_BY_ID = {check.id: check for check in CHECKS}


def result(check_id: str, status: Status, message: str, evidence: list[str] | None = None) -> CheckResult:
    definition = CHECK_BY_ID[check_id]
    return CheckResult(
        id=definition.id,
        name=definition.name,
        category=definition.category,
        weight=definition.weight,
        status=status,
        message=message,
        evidence=evidence or [],
        requires_online=definition.requires_online,
    )

# Slop Meeter methodology

Slop Meeter evaluates observable repository evidence. Each check returns `pass`, `warn`, `fail`, or
`na`, plus a neutral message and verifiable evidence. It never attempts to identify AI-written code.

## Scoring

Statuses contribute 1, 0.5, 0, or no points respectively. Within a category, points are weighted by
the check weights below. The evidence score is the weighted average of applicable category scores:
history 25, tests 20, claims 20, documentation 10, dependencies/security 10, and online maintenance 15.
Categories with no applicable checks are excluded. Confidence is the applicable check weight divided
by all possible check weight. The flavor-only slop level is `round((100 - evidence score) / 10)`.

Scores from 80 are “Solid. Receipts included.”, from 60 “Promising. Some receipts.”, from 40 “Mostly
vibes.”, and below 40 “Peak slop.” If the repository has fewer than 10 commits or is younger than 14
days, the report also says “Too early to tell” without hiding the score.

## History and substance (category weight 25)

| ID | Weight | Thresholds | Rationale |
|---|---:|---|---|
| H1 Commit depth | 3 | 30+ pass; 10–29 warn; under 10 fail | Sustained work is harder to stage in one dump. |
| H2 Largest-commit share | 3 | under 40% pass; 40–70% warn; over 70% fail | Incremental history provides more evidence than a single code dump. Lockfiles and vendored paths are excluded. |
| H3 Time spread | 2 | 10+ active days and 14+ day span pass; 4–9 active days warn; 3 or fewer fail | Work distributed over time offers more observable history. |
| H4 Commit messages | 1 | under 20% generic pass; 20–50% warn; over 50% fail | Specific messages make history auditable. Very short messages and a small explicit generic list are counted. |
| H5 Contributors | 1 | 3+ pass; 1–2 warn; never fail | Independent contributors are only a mild signal because solo projects are legitimate. Bot identities are excluded. |

## Tests and CI (category weight 20)

| ID | Weight | Thresholds | Rationale |
|---|---:|---|---|
| T1 Tests present | 4 | test/source LOC at least 15% pass; any lower nonzero ratio warn; none fail | Tests are reproducible evidence of behavior. Conventional test names and directories are recognized. |
| T2 Tests assert | 4 | at least 90% pass; 60–89% warn; under 60% fail | Test-shaped files without meaningful assertions provide weak evidence. Python uses `ast`; JS/TS uses bounded regex inspection. |
| T3 CI runs tests | 2 | CI with a test command pass; CI without one warn; no CI fail | Automated execution makes tests more credible. |

## Claims versus receipts (category weight 20)

| ID | Weight | Thresholds | Rationale |
|---|---:|---|---|
| C1 Claims have receipts | 5 | 80%+ or no claims pass; 40–79% warn; under 40% fail | Quantitative and superlative claims should link to in-repo evidence or an external source within 10 lines or the same section. Every claim is listed with path and line. |
| C2 Eval harness present | 3 | runnable benchmark/eval code pass; results only warn; claims without either fail; no claims `na` | A harness makes performance claims reproducible. |
| C3 Hype density | 1 | under 8 buzzwords/1,000 README words pass; 8–20 warn; over 20 fail | Dense promotional language can crowd out verifiable detail. The word list is configurable. |

## Documentation, release, and composition (category weight 10)

| ID | Weight | Thresholds | Rationale |
|---|---:|---|---|
| D1 README essentials | 2 | description + install + code example pass; two warn; one or none fail | Basic documentation lets users evaluate the project. |
| D2 License | 2 | recognized text pass; unrecognized license file warn; missing fail | A clear license establishes reuse terms. |
| D3 Release hygiene | 1 | Git tag pass; changelog without tag warn; neither fail | Release records provide a public change trail. |
| D4 Substance vs. fluff | 2 | code at least 25% of eligible bytes pass; 10–24% warn; under 10% fail | Implementation substance should support project claims. Locks and vendored paths are excluded. |
| D5 Placeholder density | 1 | under 5% pass; 5–15% warn; over 15% fail | Empty Python functions and TODO/lorem markers weaken evidence of completion. Protocol and abstract methods are excluded. |

## Dependencies and security (category weight 10)

| ID | Weight | Thresholds | Rationale |
|---|---:|---|---|
| S1 Lockfile / pinning | 1 | lockfile, all exact pins, or no dependencies pass; partial pins warn; no pins fail | Reproducible resolution reduces ambiguity. |
| S2 Dependencies exist | 3 | all exist pass; unavailable lookups warn; any registry 404 fail; offline `na` | Missing declared packages can reveal broken manifests. PyPI and npm are queried only with `--online`. |
| S3 Install-time risk | 2 | none pass; explicitly documented risk warn; lifecycle or shell-pipe execution fail | Install-time execution deserves explicit scrutiny. Nothing is executed. |
| S4 Secrets patterns | 3 | no high-confidence match pass; any match fail | Published credentials create concrete risk. Evidence contains only path, line, and pattern type—not the secret. |

## Online maintenance and attention (category weight 15)

| ID | Weight | Thresholds | Rationale |
|---|---:|---|---|
| M1 Recency | 1 | idle no more than max(30 days, 10% of age) pass; no more than max(180 days, 50% of age) warn; otherwise fail | Recent activity is evidence of stewardship while allowing older stable projects more time. |
| M2 Responsiveness | 2 | with 5+ issues: median response within 7 days and 50%+ PR merge ratio pass; within 30 days and 25%+ warn; otherwise fail | Responsive maintenance supports real-world usability. Fewer than five issues is `na`. |
| M3 Star plausibility | 3 | no triggered pattern pass; one warn; two or more fail | Stars/day, sampled weekly concentration, forks, and issues provide context only. Wording is “plausible”, “unusual”, or “anomalous”—never an accusation. |

## Informational

I1 reports files or README text disclosing AI assistance. Its weight is zero: AI use is neither rewarded
nor punished.

## Safety and determinism

Repository contents are static input. Files are bounded and symlinks are not followed. Target code,
hooks, imports, tests, and installers are never run. Git and HTTP operations have timeouts and request
caps. Online clients and the analysis clock are injectable, so the test suite uses no real network and
two runs against the same state and analysis time produce byte-identical JSON.

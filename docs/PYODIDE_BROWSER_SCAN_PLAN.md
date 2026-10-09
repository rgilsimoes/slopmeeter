# Reduced Pyodide browser scan implementation plan

## Status and relationship to the website plan

This is a proposed zero-compute-cost alternative to the server-side scan worker in
[`WEBSITE_IMPLEMENTATION_PLAN.md`](WEBSITE_IMPLEMENTATION_PLAN.md). It delivers a real but deliberately
reduced public-repository assessment in the visitor's browser. It does not replace the CLI as the
canonical complete assessment and does not promise browser/CLI score equivalence.

The server-side worker remains a possible later route to full hosted parity. This plan should be tested
with a short feasibility spike before that infrastructure is built.

## Product decision

Run the existing Python analysis implementation in a module Web Worker through a pinned, self-hosted
Pyodide build. Acquire an immutable public GitHub repository snapshot with browser `fetch`, then run only
the checks whose evidence can be obtained completely and safely within bounded browser resources.

Every browser result must identify itself as a **Reduced browser assessment**. The report must explain
which checks ran, which require the CLI, and why. Every result and every unsupported or oversized state
must include a prominent route to the complete CLI assessment.

The browser is not a second scoring implementation. File checks, scoring, and rendering remain Python
modules shared with the CLI. Only repository acquisition and environment-dependent evidence use a
browser adapter.

## User promise

The browser experience may promise:

- A real deterministic scan of an exact public GitHub commit, performed locally in the visitor's browser.
- No execution of repository code, tests, hooks, installers, imports, or scripts.
- No repository contents sent to Slop Meeter infrastructure.
- Complete coverage of the declared browser check set for repositories within published limits.
- Clear `na` results for checks that require the full CLI rather than simulated or inferred results.
- The same rule implementation and default thresholds as the matching CLI release.

It must not promise:

- The complete Slop Meeter assessment.
- A score directly interchangeable with a full CLI score.
- Commit-history, package-registry, or maintenance analysis.
- Private repository support, visitor-supplied tokens, or custom configuration in the first release.
- Partial sampling of oversized repositories presented as a complete browser scan.

## Browser check profile

The first browser profile is intentionally conservative. It downloads the exact commit's complete
eligible file set, checks release-tag presence with GitHub metadata, and marks all other unavailable
evidence `na`.

| Check | Browser | Evidence source | Notes |
|---|---|---|---|
| H1 Commit depth | `na` | CLI only | Requires bounded Git history. |
| H2 Largest-commit share | `na` | CLI only | Requires per-commit numstat-equivalent data. |
| H3 Time spread | `na` | CLI only | Requires bounded Git history. |
| H4 Commit messages | `na` | CLI only | Requires bounded Git history. |
| H5 Contributors | `na` | CLI only | Requires bounded Git history. |
| T1 Tests present | Run | Repository snapshot | Shared Python check. |
| T2 Tests assert | Run | Repository snapshot | Uses the existing Python `ast` implementation. |
| T3 CI runs tests | Run | Repository snapshot | Shared Python check. |
| C1 Claims have receipts | Run | Repository snapshot | Shared Python check. |
| C2 Eval harness present | Run | Repository snapshot | Shared Python check. |
| C3 Hype density | Run | Repository snapshot | Shared Python check. |
| D1 README essentials | Run | Repository snapshot | Shared Python check. |
| D2 License | Run | Repository snapshot | Shared Python check. |
| D3 Release hygiene | Run | Snapshot + GitHub tags | A failed tag lookup must not become a false failure. |
| D4 Substance vs. fluff | Run | Repository snapshot | Tree sizes and downloaded contents must represent the full eligible set. |
| D5 Placeholder density | Run | Repository snapshot | Uses the existing Python `ast` implementation. |
| S1 Lockfile / pinning | Run | Repository snapshot | Shared Python check. |
| S2 Dependencies exist | `na` | CLI only | Registry CORS and request volume are not part of v1. |
| S3 Install-time risk | Run | Repository snapshot | Inspection only; nothing is executed. |
| S4 Secret patterns | Run | Repository snapshot | Values remain redacted exactly as in the CLI. |
| M1 Recency | `na` | CLI only | Full maintenance profile remains an online CLI feature. |
| M2 Responsiveness | `na` | CLI only | Requires issues, comments, and pull-request requests. |
| M3 Star plausibility | `na` | CLI only | Requires bounded stargazer and repository metadata requests. |
| I1 AI-assistance disclosure | Run | Repository snapshot | Informational and weight zero. |

This runs 14 of 23 weighted checks plus I1. With default weights, the maximum browser confidence is
33/52, approximately 63%. The report must show this coverage rather than presenting 63% as a runtime
failure or lack of repository evidence.

## Scoring and report semantics

- Emit all defined checks in the report. CLI-only checks use `status: "na"` and a stable reason such as
  `available in the complete CLI assessment`.
- Continue excluding `na` checks and wholly unavailable categories from the score, as the current scorer
  does.
- Label the result **Browser evidence score**, not merely **Evidence score**.
- Label the verdict as applying to the reduced browser evidence set.
- Do not calculate the maturity note without history. Absence of browser history must not appear as
  `0 commits, 0 days old`.
- Show a coverage summary near the score: `14 of 23 checks run · maximum confidence 63%`.
- Keep the current score and verdict definitions so supported checks do not acquire browser-specific
  semantics.
- Treat tag lookup failure as unavailable evidence. If no tag data is available, D3 may report a
  changelog-only warning when a changelog is present; otherwise it must be `na`, never a false failure.
- A resource-limit rejection or failed required download produces no score. It is an unsupported or
  failed scan with a CLI route, not a partial success.

Add explicit report metadata rather than inferring mode from `na` checks:

```json
{
  "schema_version": 2,
  "analysis_profile": "browser-reduced-v1",
  "analyzer_version": "0.x.y",
  "target": "owner/repository",
  "revision": "full-commit-sha",
  "coverage": {
    "run": ["T1", "T2", "T3", "C1", "C2", "C3", "D1", "D2", "D3", "D4", "D5", "S1", "S3", "S4", "I1"],
    "unavailable": ["H1", "H2", "H3", "H4", "H5", "S2", "M1", "M2", "M3"]
  }
}
```

The exact schema belongs in a versioned contract and may add acquisition limits and notices. Existing
CLI fields should remain backward compatible where practical.

## Architecture

```text
Main browser thread
  ├── scan form, progress, report, filters, and CLI callouts
  └── postMessage
        │
        ▼
Module Web Worker
  ├── pinned self-hosted Pyodide runtime
  ├── slop-meeter pure-Python wheel
  ├── GitHub browser adapter
  │     ├── resolve ref to exact commit SHA
  │     ├── list the recursive Git tree
  │     ├── list release tags
  │     └── download bounded raw blobs at the SHA
  ├── in-memory browser repository adapter
  └── shared Python analysis and JSON rendering modules
        │
        ▼
Versioned reduced report
```

The browser adapter should use the same acquisition pattern proven by SlopCop: list the recursive tree
through GitHub's REST interface, filter it before downloading content, then fetch raw files at the
resolved SHA. It should not clone Git or reconstruct `.git` in the browser for v1.

## Shared analysis seam

Place the seam between evidence acquisition and analysis. The shared module should expose one small
interface and hide check ordering, unavailable-result construction, weighting, scoring, and report
metadata inside its implementation.

Conceptually:

```python
class RepositoryView(Protocol):
    config: Config
    files: tuple[FileRecord, ...]

    def read_text(self, relative: str, limit: int | None = None) -> str: ...
    def history(self) -> Evidence[tuple[Commit, ...]]: ...
    def tags(self) -> Evidence[tuple[str, ...]]: ...


def analyze_repository(
    repository: RepositoryView,
    *,
    profile: AnalysisProfile,
    now: datetime,
    dependency_client: DependencyLookup | None = None,
    github_client: GitHubData | None = None,
    progress: Progress | None = None,
) -> Report: ...
```

The exact types may differ, but these invariants matter:

- `RepoContext` becomes the native CLI adapter instead of being the analysis interface itself.
- A browser repository adapter stores already-downloaded bytes and implements the same read interface.
- History and tags return either evidence or a structured unavailable reason; they do not masquerade as
  empty repositories.
- Checks no longer invoke `repo.git(...)` directly. In particular, D3 consumes tag evidence supplied at
  the seam.
- The profile selects availability, not alternate scoring rules.
- Both adapters feed the same checks, aggregation, and renderer modules.

This is a real seam because it has two adapters: native Git/filesystem and browser GitHub/in-memory.

## Repository acquisition and limits

The first release accepts only canonical public GitHub HTTPS repository URLs. It does not accept
credentials, embedded tokens, arbitrary hosts, archives, local paths, or user-selected refs unless ref
support is separately specified and tested.

Acquisition stages:

1. Parse and normalize `owner/repository` locally.
2. Resolve the default branch to an exact commit SHA.
3. Fetch the recursive Git tree for that SHA, retaining path, type, mode, object SHA, and byte size.
4. Reject truncated trees because absence-based checks would be unreliable.
5. Exclude directories ignored by the default Slop Meeter configuration.
6. Reject symlinks and non-blob entries before downloading.
7. Reject any file over the configured per-file limit.
8. Calculate the complete candidate count and total bytes before download.
9. Reject repositories over the browser file-count or total-byte limit with a CLI callout.
10. Download every candidate at the exact SHA with bounded concurrency and cancellation.
11. Detect binary files from the same prefix rule as the CLI and build the in-memory repository adapter.
12. Fetch the first tag page because D3 needs only evidence that at least one release tag exists.
13. Run the shared reduced profile.

Initial limits should be conservative and calibrated during the spike. Starting candidates:

- 3,000 repository blobs after ignored-directory filtering.
- 60 MiB total candidate bytes.
- 1 MiB per file, matching the current default.
- 12 concurrent raw-file downloads.
- 30 seconds for acquisition and 15 seconds for analysis.

Limits are product behavior and must be shown before or during the scan. They must not be hidden inside
implementation constants.

## Pyodide packaging

- Build the existing project as a pure-Python wheel and test that wheel under a pinned Pyodide version.
- Self-host the Pyodide loader, WebAssembly runtime, standard-library archive, lockfile, and Slop Meeter
  wheel under versioned asset paths.
- Run Pyodide only inside a module Web Worker.
- Keep the main-thread protocol small: start, cancel, progress, complete, and error messages.
- Transfer file bytes rather than repository-controlled HTML. Render repository text only through the
  existing escaping rules.
- Cache immutable runtime assets with long-lived content hashes; do not cache mutable repository refs as
  if they were commits.
- Keep a restrictive Content Security Policy with explicit `script-src`, `worker-src`, and `connect-src`
  entries for self-hosted assets, GitHub REST, and raw GitHub content.

## Honest progress

Progress must report observable work rather than simulated percentages:

- Loading browser analyzer.
- Resolving default branch.
- Listing repository files.
- Checking browser limits.
- Downloading file `n` of `total`.
- Reading release tags.
- Running 14 browser checks.
- Building reduced report.

The collapsed run log should retain these events and finish with the resolved SHA, downloaded byte and
file counts, checks run, checks unavailable, and total elapsed time. Do not log repository contents,
tokens, or matched secret values.

## CLI callout

The complete-assessment route is part of the result, not a marketing footer. Show it:

- Beside the score and confidence summary.
- Above the list of CLI-only checks.
- In every resource-limit, unavailable, rate-limit, and acquisition-failure state.
- In downloaded browser HTML reports.
- At the bottom of successful browser reports.

Recommended successful-result copy:

> This browser assessment ran 14 of 23 checks against the selected commit. Commit history, dependency
> registry verification, and maintenance signals require the complete CLI assessment.

Primary action: **Run the complete assessment**.

The expanded instructions should be generated from the normalized target:

```sh
pipx install slop-meeter
slopmeter https://github.com/OWNER/REPOSITORY --online --format html --output slopmeeter-report.html
```

Also offer the equivalent `uv tool install slop-meeter` installation route already supported by project
documentation. Copy buttons must copy only commands visible to the visitor.

## Browser caching

Cache only complete successful reports in IndexedDB. Keep at most ten reports and key each entry by:

- Analyzer version and browser-profile version.
- Full commit SHA.
- Default-configuration hash.
- Acquisition-limit version.

When a visitor opens a cached branch result, show it immediately with its age, resolve the branch again,
and offer a rescan if the SHA moved. Never cache failures, truncated trees, incomplete downloads, or
cancelled scans as successful results.

## Safety and privacy

- Treat repository names, paths, configuration, source text, API responses, and error bodies as
  untrusted data.
- Never execute repository content or dynamically import from repository-controlled URLs.
- Fetch only GitHub REST and raw-content URLs constructed from validated owner, repository, SHA, and
  encoded path segments.
- Enforce limits before downloading and again while streaming responses.
- Abort the entire report if a required eligible file cannot be downloaded.
- Keep visitor tokens out of v1; anonymous API exhaustion should produce a clear retry-later state.
- Do not send repository contents, findings, or browsing history to analytics.
- Redact matched secrets exactly as the CLI does.
- Cancellation must terminate network requests and discard the worker's in-memory repository.

## Delivery milestones

### Milestone B1 — Contract and behavior lock

- Add `analysis_profile`, coverage, revision, and schema-version fields to the report contract.
- Define stable unavailable and browser-limit failure reasons.
- Add golden reports for full CLI, successful reduced browser, tag lookup unavailable, and unsupported
  repository states.
- Change maturity-note calculation so unavailable history is distinct from empty history.

**Accept when:** fixtures alone can render every reduced result, failure, and CLI-callout state.

### Milestone B2 — Shared evidence seam

- Introduce the repository interface and structured evidence availability.
- Adapt native `RepoContext`, history, and tags without changing CLI output.
- Remove direct Git invocation from checks.
- Add the browser-reduced profile and its explicit `na` results.

**Accept when:** all existing CLI snapshots remain byte-identical and the reduced-profile golden report
is produced entirely by shared Python checks.

### Milestone B3 — Pyodide feasibility spike

- Build and self-host a pure-Python wheel and pinned Pyodide runtime.
- Run the reduced profile in a module Web Worker against stored repository snapshots.
- Measure compressed runtime size, cold start, peak browser memory, analysis time, and JS/Python transfer
  overhead at small, medium, and limit-sized fixtures.
- Verify current Chrome, Firefox, and Safari releases.

**Accept when:** supported checks match native Python byte-for-byte after removing explicitly
environmental timing fields, the UI stays responsive, and the limit-sized fixture completes within the
provisional memory and time budgets. If this fails, stop before building live acquisition.

### Milestone B4 — GitHub browser adapter

- Implement URL normalization, revision resolution, recursive tree listing, tag lookup, raw downloads,
  cancellation, timeouts, and resource enforcement.
- Preserve Git modes so symlinks are rejected.
- Add real progress messages and the collapsed run log.
- Ensure no user token or Slop Meeter backend is involved.

**Accept when:** a reviewed matrix of public repositories either produces a complete reduced report or
an actionable unsupported/failure state; none produces a sampled report presented as complete.

### Milestone B5 — Reduced report and CLI route

- Replace representative website data with the real browser result.
- Add the reduced-assessment badge, browser score label, coverage summary, CLI-only check treatment, and
  CLI installation/run instructions.
- Add accessible loading, cancellation, rate-limit, unsupported, and failure states.
- Include the browser-profile metadata and CLI callout in downloaded HTML.

**Accept when:** a visitor cannot reasonably mistake the browser result for the full CLI assessment and
can copy a target-specific complete-assessment command from every terminal state.

### Milestone B6 — Cache, hardening, and launch

- Add IndexedDB caching and branch-staleness checks.
- Add CSP and dependency integrity checks for the self-hosted runtime.
- Exercise hostile paths, huge trees, oversized responses, malformed UTF-8, binary files, truncated
  trees, API exhaustion, cancellation, storage denial, and worker crashes.
- Publish browser limits, privacy behavior, methodology differences, and supported-browser policy.

**Accept when:** production traffic creates no scan-compute bill, unsupported inputs fail closed, cached
reports cannot cross versions or revisions, and the website's report claims match the actual browser
work.

## Tests that matter most

- Native CLI output remains unchanged after introducing the repository seam.
- Every supported browser check matches the CLI result for an identical snapshot and default config.
- Every excluded check is `na` with the documented stable reason.
- Browser confidence is approximately 63% with all 14 weighted checks applicable and never implies that
  CLI-only evidence was inspected.
- Tag success, empty tags, tag failure, and changelog fallback produce distinct D3 outcomes.
- A truncated tree, cap overflow, or failed eligible download cannot produce a successful report.
- The worker never fetches a branch-relative raw URL after revision resolution; every content request
  uses the full SHA.
- Repository paths cannot escape URL construction, the in-memory filesystem, or HTML escaping.
- Cancelling a scan aborts outstanding fetches and prevents a late report from replacing the next run.
- Cached reports are isolated by commit, analyzer version, profile, configuration, and limit version.
- The Web Worker survives unavailable IndexedDB and reports API rate exhaustion accurately.
- Desktop and mobile layouts expose the coverage and CLI callout without relying on the expanded log.

## Exit criteria and fallback

Proceed with the browser architecture only if the B3 spike demonstrates acceptable startup, memory,
cross-browser behavior, and output parity for the supported checks. If it does not, retain the static
report viewer and use the original isolated-worker plan for hosted scans.

Do not compensate for a failed spike by rewriting check logic in JavaScript. That would create a second
scoring implementation and remove the main reason to choose Pyodide.

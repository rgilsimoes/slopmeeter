# Slop Meeter website implementation plan

> **Architecture option under evaluation:**
> [`PYODIDE_BROWSER_SCAN_PLAN.md`](PYODIDE_BROWSER_SCAN_PLAN.md) defines a reduced assessment that runs
> the shared Python checks in the visitor's browser with no scan-compute infrastructure. The plan below
> remains the route to a hosted assessment with full CLI parity.

## Product decision

Build the website as a low-friction public demo and report viewer while keeping the CLI as the canonical
tool for private repositories, local analysis, CI, and custom configuration.

The first release should answer one job clearly: **paste a public GitHub repository and receive an
explainable Slop Meeter report without installing anything.** It should not add accounts, private
repository access, uploads, social scoring, or a public repository leaderboard.

## User flow

1. The visitor pastes a public GitHub repository URL.
2. The service validates and normalizes the owner/repository pair.
3. The API resolves the repository's default branch and exact commit SHA.
4. A disposable worker runs the released Slop Meeter CLI against that immutable revision.
5. The website shows bounded progress without claiming more precision than the worker provides.
6. The result page presents the score, confidence, maturity note, category scores, inspection priorities,
   and every evidence check.
7. A visitor can copy the result URL or install the CLI for a private or configurable scan.

The UI must always distinguish queued, running, complete, partial, rate-limited, unsupported, and failed
scans. A failed scan must never silently become a zero score.

## Recommended architecture

```text
Browser
  │
  ├── static website and report UI
  │
  └── HTTPS API
        ├── request validation and rate limiting
        ├── scan record / cache lookup
        ├── bounded job queue
        └── isolated scan worker
              ├── restricted GitHub clone at an exact SHA
              ├── released Slop Meeter package
              ├── optional bounded registry/GitHub lookups
              └── JSON result + self-contained HTML artifact
```

Use a static frontend backed by a small API and queue. Run the Python analyser in an isolated container
or micro-VM service designed for untrusted jobs; do not attempt to execute it inside the browser or a
general-purpose web request handler. The website and worker should consume the same versioned JSON
report schema already produced by the CLI.

## Repository and service boundaries

Keep the web surface separate from the analyser:

```text
web/
  app/                  website source
  public/               mascot and static assets
  tests/                UI and contract tests
service/
  api/                  scan requests, status, results
  worker/               isolated CLI runner
  tests/                validation, queue, abuse and failure tests
docs/
  WEBSITE_IMPLEMENTATION_PLAN.md
```

The analyser remains a versioned dependency of the worker. The service must call its public CLI or
Python seam and must not fork scoring logic into a second implementation.

## API contract

Start with three endpoints:

- `POST /api/scans` accepts a GitHub URL and optional branch, tag, or commit. It returns a scan ID,
  normalized target, resolved revision when available, status, and whether an existing result was reused.
- `GET /api/scans/{id}` returns status, bounded progress stage, failure reason, and the completed report.
- `GET /reports/{id}` renders the human-readable report for a completed scan.

Cache identity should include repository identity, resolved commit SHA, Slop Meeter version, effective
configuration hash, and online/offline mode. A repeated request for the same identity should reuse the
result rather than clone and scan again.

Persist only normalized scan metadata, structured results, and the optional HTML artifact. Repository
checkouts must be ephemeral. Establish and publish a retention window before launch.

## Security model

The existing “repository is untrusted input” rule becomes the service boundary, not merely an analyser
rule.

- Allow GitHub HTTPS repository URLs only in the first release. Reject arbitrary hosts, credentials,
  embedded tokens, local addresses, redirects to other hosts, and non-repository paths.
- Resolve DNS and outbound destinations through a restricted network policy to prevent SSRF.
- Run each scan as an unprivileged user in a fresh, read-only-root container with an ephemeral workspace.
- Disable hooks, submodules, credential helpers, global Git configuration, LFS smudge filters, and any
  executable target behavior.
- Apply hard limits for repository bytes, file count, individual file size, commit count, CPU, memory,
  wall time, network requests, redirects, and response bytes.
- Permit outbound requests only to approved GitHub and package-registry endpoints required by online
  checks.
- Never accept or store a visitor's GitHub token in the first release.
- Escape all repository-controlled text in the web UI and preserve the report's restrictive rendering
  rules.
- Delete the checkout after every terminal outcome, including cancellation and timeout.

Rate limits should exist per source IP and per repository. Add a global concurrency ceiling and queue
depth so a burst of large repositories cannot exhaust the service.

## Visual system

Use the existing HTML report as the structural baseline and the mascot logo as the color and personality
baseline.

The proposed website keeps the warm paper background, editorial serif headings, navy structure,
monospace evidence labels, compact status pills, and clear report hierarchy. It adjusts the semantic
colors toward the logo:

| Role | Direction |
|---|---|
| Structure | Deep navy and near-black |
| Pass / evidence | Brighter mascot green on a pale green surface |
| Warning | Warm meter amber on a pale yellow surface |
| Failure / weak evidence | Mascot coral on a pale coral surface |
| Informational | Existing blue/teal family |
| Canvas | Warm off-white paper |

Apply the same tokens to the website and HTML report, while preserving text labels and icons so color is
never the only status indicator. The self-contained HTML report should continue to ship without remote
fonts, scripts, assets, or network requests.

Before changing the report palette, add visual snapshots for pass, warn, fail, `na`, low/high scores,
and print mode. Contrast must meet WCAG AA for regular text, focus states must remain visible, and the
printed report must not depend on background color to communicate status.

## Delivery milestones

### Milestone 1 — Product and schema contract

- Freeze the public-scan scope and result-retention policy.
- Document the JSON fields required by the website.
- Add schema-version handling and a clear unsupported-version state.
- Define terminal failure codes such as invalid target, repository too large, timeout, upstream rate
  limit, unsupported repository, and internal error.

**Accept when:** a stored fixture can drive every website state without running a scan.

### Milestone 2 — Website shell and report viewer

- Turn the approved mockup into the production frontend.
- Implement responsive scan, progress, error, and report states.
- Render all current score, confidence, maturity, category, evidence, and information fields.
- Add keyboard navigation, screen-reader labels, reduced-motion behavior, and mobile table handling.
- Update the self-contained HTML report to the approved logo-aligned palette.

**Accept when:** the frontend passes accessibility checks and renders deterministic fixtures at mobile
and desktop widths.

### Milestone 3 — Scan API and isolated worker

- Implement strict GitHub URL validation and revision resolution.
- Add the queue, disposable worker, resource limits, cleanup, and outbound allowlist.
- Run the released Slop Meeter analyser and validate its JSON output before storage.
- Stream coarse, honest progress stages rather than invented percentages.

**Accept when:** hostile and oversized fixtures cannot execute code, escape the sandbox, reach forbidden
hosts, or leave checkouts behind.

### Milestone 4 — Caching, reliability, and abuse controls

- Cache by immutable scan identity.
- Add per-client, per-repository, queue-depth, and global concurrency limits.
- Record structured metrics for queue time, scan time, cache hit rate, failure class, resource use, and
  upstream rate-limit pressure.
- Add cancellation, timeout recovery, worker-health checks, and dead-job cleanup.

**Accept when:** repeated scans reuse results, overload fails predictably, and operators can diagnose a
failed scan without reading repository content.

### Milestone 5 — Private alpha

- Deploy behind owner-only or invite-only access.
- Test against a reviewed set of small, medium, large, young, archived, and intentionally hostile public
  repositories.
- Compare web results byte-for-byte with the same CLI version and analysis time.
- Calibrate quotas and progress messaging from observed runs.

**Accept when:** the web and CLI reports agree, the service stays within its resource budget, and no scan
requires manual cleanup.

### Milestone 6 — Public beta

- Publish the privacy, retention, methodology, limitations, and acceptable-use pages.
- Add a status page and an easy route from every report to the CLI.
- Roll out gradually with conservative concurrency and repository-size caps.
- Review false-positive feedback before changing any scoring threshold.

**Accept when:** public traffic remains bounded, failure messaging is actionable, and operational alerts
cover queue saturation, elevated failures, and cleanup errors.

## Tests that matter most

- URL parsing and SSRF rejection, including redirects and unusual GitHub URL forms.
- Analyzer-version and schema compatibility.
- Repository size, file, request, redirect, CPU, memory, and timeout enforcement.
- Hook, submodule, LFS, credential-helper, and global Git configuration isolation.
- Escaping of hostile repository names, messages, paths, and evidence.
- Web/CLI equivalence for identical commit, configuration, mode, and analysis time.
- Cache correctness and refusal to mix results across revisions or analyser versions.
- Keyboard, screen-reader, mobile, high-zoom, reduced-motion, and print behavior.

## Deliberate non-goals for the first release

- Private repositories or user-supplied access tokens.
- Arbitrary Git hosts or uploaded archives.
- Executing tests, builds, benchmarks, installers, or repository code.
- Accounts, comments, repository rankings, or public leaderboards.
- User-defined scoring configuration in the hosted scanner.
- Treating the website result as a security certification or author judgement.

These can be reconsidered only after the public-repository service is demonstrably safe, useful, and
operationally affordable.

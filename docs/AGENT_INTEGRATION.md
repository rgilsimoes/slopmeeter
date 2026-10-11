# Agent and CI integration

Slop Meeter can be used while a project is being built, not only after publication. The integration
kit in [`integrations/`](../integrations/) gives coding agents a repeatable evidence-review workflow
and gives CI an independent enforcement point.

The CLI remains the source of truth. The templates tell an agent when to run it and how to interpret
the result; they do not copy the rule definitions or thresholds from the
[methodology](METHODOLOGY.md).

## Choose the integration layers

| Layer | What it does | Strength |
|---|---|---|
| `AGENTS.md` | Makes evidence review part of normal agent work | Advisory |
| Audit prompt | Starts a focused, read-only review on demand | Advisory |
| Codex `Stop` hook | Requests one review pass before a Codex turn finishes | Automated review |
| GitHub Actions | Records a report and rejects scores below the chosen floor | Enforcement |
| `llms.txt` | Helps web agents discover Slop Meeter documentation | Discovery |

Use `AGENTS.md` plus CI for the smallest useful setup. Add the Codex hook when a review should happen
automatically during interactive agent work.

## Onboard from the CLI

Run the recommended setup from the root of a project:

```sh
slopmeter init .
```

This installs `AGENTS.md` and `.github/workflows/slopmeter.yml`. Add every available integration with
`slopmeter init . --all`, or select individual components by repeating `--component` with `agents`,
`prompt`, `codex`, or `github`:

```sh
slopmeter init . --component agents --component codex
```

The prompt is installed at `.slopmeter/prompts/slop-review.md`; the Codex files are installed at
`.codex/hooks.json` and `.codex/hooks/slopmeter_stop.py`. The command checks every destination before
writing, leaves identical files unchanged, and refuses to overwrite a different file. Use `--dry-run`
to inspect the plan or explicit `--force` after reviewing conflicts. It also rejects symlinked parent
directories so onboarding cannot write outside the selected project.

The templates below remain available for manual copying and review.

## Add the project instructions

Copy [`integrations/AGENTS.md`](../integrations/AGENTS.md) into the repository root, or merge its
“Slop Meeter evidence policy” section into an existing `AGENTS.md`.

The policy intentionally says not to manufacture commits, tests, benchmarks, or documentation merely
to raise the score. A warning can be honest and acceptable; the agent should report intentional or
pre-existing findings instead of gaming them.

Run this command to verify the setup manually:

```sh
slopmeter . --format json
```

If the project has a Slop Meeter configuration, append `--config .slopmeter.toml` to commands in the
template. Configuration is explicit in the current CLI and is not discovered automatically.

## Use the audit prompt

[`integrations/prompts/slop-review.md`](../integrations/prompts/slop-review.md) is a portable prompt
for agents that do not load `AGENTS.md`, or for an explicit audit before a release. It asks for a
read-only assessment by default. The user must separately ask the agent to fix findings.

## Install the Codex hook

Copy the hook definition and its Python helper into a project's `.codex` directory:

```sh
mkdir -p .codex/hooks
cp integrations/codex/hooks.json .codex/hooks.json
cp integrations/codex/hooks/slopmeter_stop.py .codex/hooks/slopmeter_stop.py
```

Restart Codex, open `/hooks`, inspect the project hook, and trust it. Project hooks are not run until
their current definition has been reviewed and trusted.

When Codex attempts to finish a turn, the helper runs an offline JSON scan. If configured findings
exist, it asks Codex to perform one more review pass. On the next completion attempt,
`stop_hook_active` prevents another continuation, so an existing or intentional warning cannot create
an infinite loop. The hook never enables network checks.

The helper recognizes these optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `SLOPMETER_EXECUTABLE` | `slopmeter` on `PATH` | Use a specific executable |
| `SLOPMETER_CONFIG` | `.slopmeter.toml` when present | Select a config file relative to the repository root |
| `SLOPMETER_REVIEW_STATUSES` | `fail,warn` | Statuses that request another review pass |
| `SLOPMETER_REQUIRED_CHECKS` | all checks | Restrict review to comma-separated check IDs |
| `SLOPMETER_FAIL_UNDER` | unset | Also request review when the evidence score is below this floor |
| `SLOPMETER_HOOK_ADVISORY` | unset | Set to `1` to show findings without continuing the turn |

The hook is a review aid, not a security boundary. A missing executable or failed scan is surfaced as
a warning instead of trapping the agent. Use CI for required enforcement.

## Add the GitHub Actions gate

Copy [`integrations/github/slopmeter.yml`](../integrations/github/slopmeter.yml) to
`.github/workflows/slopmeter.yml`. It checks out full history, installs a pinned Slop Meeter release,
runs an offline scan, uploads the JSON report even when the score gate fails, and enforces a score of
40 by default.

Choose the floor deliberately. New repositories naturally lack deep history, releases, contributor
diversity, and long-term maintenance evidence. Treat the maturity note and confidence as part of the
result, and raise the floor as the project matures.

## Interpret agent reports

An agent should report:

- evidence score and confidence;
- the maturity note, when present;
- each failed or warning check ID with its evidence;
- whether a finding was introduced by the current work, pre-existing, or intentionally accepted; and
- the exact command and analysis mode used.

Slop Meeter does not detect AI-written code, judge taste, or prove fraud. Its output is a set of static,
explainable review prompts.

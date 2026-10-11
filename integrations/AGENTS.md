# Project agent instructions

## Slop Meeter evidence policy

Treat Slop Meeter as an evidence review, not a score to game.

- After changes affecting tests, CI, documentation, dependencies, packaging, benchmarks, security, or
  releases, run `slopmeter . --format json` from the repository root. If this project has a
  `.slopmeter.toml`, append `--config .slopmeter.toml`.
- Before declaring a task complete, review every `fail` and `warn` result and its evidence. Run any
  repository-specific Slop Meeter score gate configured in CI.
- Fix findings caused by the current work when the fix represents genuine project evidence.
- Never add fake tests, meaningless commits, placeholder benchmarks, unsupported claims, or decorative
  documentation merely to increase the score.
- Do not treat `na` as a failure. Report the confidence and analysis mode so unavailable checks remain
  visible.
- In the final response, report the evidence score, confidence, maturity note, affected check IDs, and
  any intentionally unresolved findings.
- If Slop Meeter is unavailable, say so explicitly and suggest `pipx install slop-meeter` without
  installing it unless the user asks. Do not guess what the score would be.

Slop Meeter scores observable repository evidence. It does not detect AI-written code, judge taste,
or declare a project fraudulent.

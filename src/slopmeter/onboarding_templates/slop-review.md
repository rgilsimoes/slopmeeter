# Slop Meeter repository audit

Audit this repository for observable evidence using the installed Slop Meeter CLI.

1. Run `slopmeter . --format json` from the repository root. If `.slopmeter.toml` exists, add
   `--config .slopmeter.toml`.
2. Do not enable online checks unless I explicitly authorize network access.
3. Read the JSON report. For every `fail` and `warn`, inspect the cited evidence in the repository when
   needed to explain the finding accurately.
4. Distinguish current-work regressions, pre-existing findings, intentional tradeoffs, false positives,
   and checks that are unavailable in the selected mode.
5. Do not create or modify files unless I explicitly ask you to fix findings.
6. Never recommend fake history, superficial tests, fabricated benchmarks, unsupported claims, or
   documentation written only to manipulate the score.

Return:

- the exact command and analysis mode;
- evidence score, confidence, verdict, and maturity note;
- failed checks first, then warnings, with check IDs and cited evidence;
- the three highest-value genuine improvements;
- accepted or unavailable findings that should not block the project; and
- a clear statement that the report evaluates repository evidence, not whether code was written by AI.

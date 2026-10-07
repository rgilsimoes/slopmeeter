# Changelog

All notable changes to Slop Meeter are documented here.

## Unreleased

## 0.3.0 — 2026-10-07

- Aligned the coloured terminal report with the approved prototype using a block banner,
  three-column summary, segmented category bars, and reformatted complete evidence checks.
- Added and published a responsive Cloudflare Pages website prototype with repository input,
  representative scan progress, evidence filters, and an inspect-next report view.
- Added production-facing website metadata, security headers, cache rules, deployment configuration,
  and explicit messaging that the current website uses representative data.
- Added the Slop Meeter launch article, supporting research, banner artwork, and website implementation
  plan, together with the “Where slop meets its match” brand line.

## 0.2.0 — 2026-10-06

- Replaced the generation spinner with a stage-aware percentage bar while preserving the rotating
  Slop Meeter status messages; it stays quiet for pipes and redirected output.
- Bounded remote clones and online lookups with shorter deadlines and a total network time budget.
- Added accessible ANSI-coloured text reports with automatic TTY, `NO_COLOR`, and `TERM=dumb`
  handling plus explicit `--color` control.
- Added deterministic, responsive, printable, and self-contained HTML reports with escaped repository
  content and prioritized inspection guidance.
- Added atomic `-o/--output` file writing for every report format.

## 0.1.0 — 2026-10-01

- Added 24 explainable repository checks across history, tests, claims, documentation, dependencies,
  security, maintenance, attention, and neutral AI-assistance disclosure.
- Added deterministic text, JSON, and Markdown reports with scoring, confidence, maturity gating, and
  CI thresholds.
- Added safe local inspection and temporary HTTPS GitHub cloning without executing target code.
- Added bounded opt-in PyPI, npm, and GitHub API checks with injectable test clients.
- Added self-scoring CI, synthetic repository fixtures, safety tests, and an owner-curated calibration
  harness.

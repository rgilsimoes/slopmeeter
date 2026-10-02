# Changelog

All notable changes to Slop Meeter are documented here.

## Unreleased

- Added an interactive progress spinner with rotating Slop Meeter status messages; it stays quiet for
  pipes and redirected output.
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

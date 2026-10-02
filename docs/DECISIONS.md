# Decisions

## 2026-10-01: Distribution name

The `slopmeter` distribution name is already occupied on PyPI. The project uses the available
distribution name `slop-meeter` while preserving the planned `slopmeter` import package and CLI.

## 2026-10-01: License

Use the plan's default MIT license because no owner override was provided.

## 2026-10-01: Placeholder density denominator

`D5` divides empty Python functions plus TODO/lorem markers by the number of Python functions plus
markers. This deliberately makes explicit markers visible even in repositories with little Python.

## 2026-10-01: URL targets and offline mode

The plan says both that URL targets are cloned and that network access only occurs with `--online`.
The safety principle wins: URL targets require `--online`; local targets remain fully offline by
default.

## 2026-10-01: Remaining owner decisions

The GitHub owner/repository and real calibration labels remain unset because they require owner input.
No AI-disclosure footer was added; the neutral I1 check reports only disclosures that actually exist.

## 2026-10-01: Report rendering and dependencies

Text, JSON, Markdown, and HTML are adapters behind one rendering seam. The shared report view contains
only deterministic analysis results and deterministic presentation summaries; format-specific details
remain inside their adapters.

Coloured terminal output and HTML generation use only the Python standard library. This preserves the
zero-runtime-dependency installation and keeps text colour policy at the CLI, where TTY and environment
information is available.

## 2026-10-01: Self-contained HTML reports

HTML reports contain packaged templates with inline CSS and SVG but no JavaScript, remote resources,
or generated timestamp. Target-provided content is escaped, evidence is rendered as text rather than
as local links, and a restrictive Content Security Policy disables active and remote content. These
constraints keep reports portable, deterministic, and safe to open from untrusted repository scans.

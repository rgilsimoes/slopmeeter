# Coloured CLI and HTML report implementation plan

## Goal

Implement the two approved prototypes without changing how repositories are analyzed or scored:

1. A coloured, terminal-native text report that remains useful when colour is unavailable.
2. A self-contained, professional HTML report suitable for local inspection, CI artifacts, and sharing.

The approved visual references are:

- [`prototypes/coloured-cli-proposal.png`](prototypes/coloured-cli-proposal.png)
- [`prototypes/html-report-proposal.png`](prototypes/html-report-proposal.png)

## Product decisions

- Keep `text`, `json`, and `markdown` output backward compatible at the command-line level.
- Add `html` to `--format`.
- Add `--color auto|always|never`, defaulting to `auto`.
- Add `-o/--output FILE` for every format. Without it, output continues to go to stdout.
- Do not automatically open the HTML report in a browser.
- Keep all renderers deterministic. In particular, do not add the current time to a report.
- Add no runtime dependencies. ANSI styling, HTML escaping, templates, and resource loading can all use the standard library.
- Keep the HTML document self-contained: inline CSS and SVG, no remote fonts, JavaScript, images, trackers, or network requests.
- Treat target repository content as untrusted in every renderer.

## Architecture

The existing `render(format_name, target, results, score, online) -> str` function is the rendering
seam. Keep that small interface and move format-specific implementations behind it.

Suggested layout:

```text
src/slopmeter/
  report.py                 public rendering seam and shared report view
  renderers/
    __init__.py
    text.py                 plain and ANSI-coloured terminal adapter
    json.py                 existing deterministic JSON adapter
    markdown.py             existing Markdown adapter
    html.py                 self-contained HTML adapter
  templates/
    report.html             semantic document shell
    report.css              responsive and print styles
```

`report.py` should build one private, immutable report view containing the current report fields plus
derived presentation data such as status counts and inspection priorities. Every renderer receives
that same view. The JSON document and schema remain version 1 unless a JSON field actually changes.

The only renderer option initially needed at the seam is `color: bool`. The CLI owns terminal and
environment detection; renderers remain pure functions that return strings.

## Milestone 1: Lock down current behaviour

Before restructuring, add golden fixtures for the existing plain text, JSON, and Markdown output.
These tests make the renderer split mechanical and verify that JSON remains byte-identical.

Tasks:

- Add a compact, fixed report fixture with pass, warn, fail, `na`, evidence, and an informational check.
- Snapshot all three existing formats.
- Verify output ends with exactly one newline.
- Verify report generation does not mutate results or scoring data.
- Move the existing renderer implementations behind the new internal adapter layout.
- Run the full test suite before beginning visual changes.

Acceptance criteria:

- Existing CLI invocations still work.
- Existing JSON and Markdown output are byte-for-byte unchanged.
- Existing exit codes remain `0`, `1`, and `2` with their current meanings.

## Milestone 2: Coloured text CLI

### 2.1 Colour policy

Add this option:

```text
--color auto|always|never   colourise text output (default: auto)
```

Resolve the policy in `cli.py`, not in the renderer:

1. `--color always` enables colour.
2. `--color never` disables colour.
3. In `auto`, disable colour when `NO_COLOR` is present, `TERM=dumb`, stdout is not a TTY, an output
   file is selected, or the format is not `text`.
4. Otherwise enable colour.

Colour must never appear in JSON, Markdown, or HTML, and piped text must remain free of escape codes
by default.

### 2.2 Terminal theme

Create a small internal theme with semantic roles rather than scattering escape sequences:

- accent: cyan
- pass: green
- warn: amber/yellow
- fail: red/coral
- not applicable and secondary text: gray
- reset: always emitted after styled spans

Use standard 8/16-colour ANSI sequences for compatibility. Status words and symbols remain visible so
colour is never the sole carrier of meaning.

### 2.3 Text hierarchy

Adapt the approved proposal to a width-stable terminal layout:

1. Header: tool name, version, target, and the existing tagline.
2. Summary: evidence score, slop level, confidence/mode, verdict, and maturity note.
3. Category scores: aligned labels, a ten-segment bar, and numeric score.
4. Evidence checks: grouped by category, with coloured status label, check ID, message, and indented
   evidence.
5. Information checks: a separate muted section marked “not scored”.

Do not make output depend on the detected terminal width in the first version; fixed formatting is
more deterministic and easier to test. Very long messages and evidence should wrap through one shared
helper with predictable indentation and a conservative fixed width.

### 2.4 CLI tests

Add tests for:

- each explicit `--color` value;
- auto mode with TTY and non-TTY streams;
- `NO_COLOR` and `TERM=dumb`;
- no ANSI sequences in redirected output or non-text formats;
- exact status-to-style mapping and reset sequences;
- coloured and plain output becoming identical after ANSI sequences are stripped;
- invalid colour values returning argparse's usage error;
- `--fail-under` retaining its current exit behaviour.

Acceptance criteria:

- The normal interactive command resembles the approved terminal prototype.
- `slopmeter . | less` produces clean plain text unless colour is explicitly forced.
- Status remains understandable in monochrome and for colour-vision deficiencies.
- The feature introduces no runtime dependency.

## Milestone 3: Output files

Add `-o/--output FILE` before the HTML format so every renderer follows the same rule.

Tasks:

- Render fully before opening the destination, so analysis or rendering failures cannot truncate an
  existing report.
- Write UTF-8 with deterministic newlines.
- Write to a sibling temporary file and replace the destination only after a successful write.
- Do not create missing parent directories implicitly; report a clear usage/runtime error.
- Keep stdout unchanged when no output path is supplied.
- When a file is written, print no report body to stdout. A short confirmation may go to stderr only
  when stderr is interactive.

Tests cover stdout, successful file output, missing parents, write errors, and the guarantee that a
failed render leaves an existing destination untouched.

Acceptance criteria:

- `slopmeter . --format markdown -o report.md` works as expected.
- Existing stdout-based integrations need no changes.

## Milestone 4: Professional HTML report

### 4.1 Document structure

Implement the approved light report with semantic HTML in this order:

1. Header with Slop Meeter identity, target, analysis mode, and “Generated locally”.
2. Score summary with the evidence score visualization, slop level, confidence, verdict, and maturity
   note.
3. Category score panel with labels, numeric values, and accessible progress bars.
4. “What to inspect next” panel derived deterministically from scored failures and warnings.
5. Complete evidence-check table with status, finding, and evidence.
6. Separate informational-check section.
7. Methodology and safety footer, including “A score is a prompt for scrutiny, not a verdict on the
   authors.”

The first version is static. Status-count chips are summaries, not interactive filters; filtering can
be added later only if it materially improves large reports.

### 4.2 Inspection priorities

Generate up to three suggestions without AI or nondeterministic logic:

- consider scored `fail` results before `warn` results;
- within a status, sort by check weight descending and then by canonical check order;
- use the check name as the action title;
- combine the result message with the check rationale for the explanation;
- exclude informational and `na` checks;
- show a positive empty state when there are no failures or warnings.

Keep this derivation in the shared report implementation so it can be tested without parsing HTML.

### 4.3 Visual implementation

Translate the prototype into reusable CSS design tokens:

- warm paper background and white report surfaces;
- near-black text, navy structure, teal accent;
- green pass, amber warn, coral fail, and gray `na` roles;
- editorial display face using a local system serif stack;
- compact UI and code labels using system sans-serif and monospace stacks;
- subtle borders and shadows, with no gradients required for meaning.

Use CSS grid for the summary and two-column body, collapsing to one column below approximately 900 px.
Add print styles that remove decorative chrome, prevent row splitting where practical, expose full
evidence text, and preserve status labels in grayscale.

### 4.4 Security and portability

- Escape every target-derived value with `html.escape(..., quote=True)`.
- Never interpolate evidence into CSS, attributes, or raw HTML.
- Render paths and commit references as text initially. Do not construct `file://` links from untrusted
  evidence.
- Include a restrictive Content Security Policy meta tag: no scripts, forms, frames, remote resources,
  or base URL changes; allow only the document's inline style.
- Use accessible landmarks, table headings, labels, focus order, and ARIA text for visual scores.
- Ensure status is conveyed by text and icon as well as colour.
- Load packaged template assets with `importlib.resources` and verify they are present in the built
  wheel.

### 4.5 HTML tests

Add tests for:

- `--format html` selection and `--output` integration;
- one complete deterministic HTML golden file;
- escaping malicious target names, messages, and evidence;
- absence of scripts, remote URLs, inline event handlers, and raw untrusted markup;
- score, category, status-count, maturity, information, and evidence sections;
- deterministic inspection-priority ordering;
- the all-pass empty state;
- HTML5 document structure and required accessibility labels;
- packaged template/CSS resources in both an sdist and wheel.

Perform visual QA against the approved prototype at desktop, tablet, mobile, and print widths. Check
long repository names, all four statuses, absent maturity notes, offline-only `na` checks, and unusually
long evidence.

Acceptance criteria:

- `slopmeter . --format html -o slopmeter-report.html` creates one portable file that opens without a
  server or network connection.
- The report clearly matches the hierarchy and tone of the approved HTML prototype.
- Untrusted repository content cannot inject markup or active content.
- The document remains readable on mobile and when printed to PDF.

## Milestone 5: Documentation and release readiness

- Update CLI usage and examples in `README.md`.
- Document colour precedence, `NO_COLOR`, stdout versus file behaviour, and HTML's self-contained and
  local-only guarantees.
- Add screenshots from the approved prototypes or from the final implementation after visual QA.
- Add both features to `CHANGELOG.md`.
- Record the no-runtime-dependency and self-contained-HTML decisions in `docs/DECISIONS.md`.
- Regenerate any derived methodology or self-score artifacts only through their existing workflows.
- Run `ruff`, the complete pytest suite, package builds, and installed-wheel smoke tests.

## Recommended implementation order

1. Behaviour-locking golden tests.
2. Internal renderer split and shared report view.
3. Colour policy and terminal theme.
4. New text hierarchy and text snapshots.
5. Generic `--output` support.
6. HTML structure, escaping, and deterministic inspection priorities.
7. CSS responsiveness, print styles, and visual QA.
8. Packaging verification and documentation.

Keep the CLI and HTML work in separate reviewable commits after the shared renderer refactor. This
makes regressions easy to isolate and allows the coloured CLI to ship independently if desired.

## Definition of done

- Both approved designs are recognisable in the implemented output.
- Analysis, scoring, JSON schema, and exit-code semantics are unchanged.
- Plain text remains clean in pipes, files, CI logs, and colour-disabled terminals.
- HTML is deterministic, self-contained, responsive, printable, accessible, and safe for untrusted
  repository content.
- All automated checks and an installed-package smoke test pass.

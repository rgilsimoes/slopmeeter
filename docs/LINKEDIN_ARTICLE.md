# Why Slop Meeter Scores the Receipts, Not the Vibes

Software repositories have become very good at making a first impression. A polished README, a heroic benchmark chart, a lively star count and several appearances of the word “agentic” can make almost anything look inevitable.

But a repository is more than its launch outfit.

That is the idea behind [Slop Meeter](https://github.com/rgilsimoes/slopmeeter): a local tool that looks for observable evidence behind a project’s claims. It does **not** try to detect AI-written code, judge whether the code is elegant or accuse anyone of fraud. It asks a narrower and more useful question:

> How much verifiable evidence does this repository give us that the project is what it says it is?

That distinction shaped the entire assessment rubric.

## Why not score the code itself?

Because “code quality” is not one universal, context-free property. A complexity score, lint count or fashionable architecture pattern may be useful inside a particular ecosystem, but none can reliably tell us whether software is correct, maintainable or fit for its intended job. Apply one grand formula across Python libraries, JavaScript apps, command-line tools and experimental research code, and the precision quickly becomes decorative.

A meaningful code review also needs context: intended behaviour, design constraints, threat model and domain knowledge. Slop Meeter deliberately avoids pretending it has all of that. It does not execute target code, and its deterministic checks must remain safe across untrusted repositories.

Instead, it examines observable consequences around the code: is behaviour tested, are those tests run automatically, can performance claims be reproduced, are dependencies controlled, and can another person understand how the project evolved? That still leaves an important limitation: weak code can collect good receipts, and excellent code can arrive with very few. The score is a way to decide where scrutiny is needed, not a replacement for code review. No monocle or clipboard can change that.

For a complementary, code-facing check, [SlopCop](https://slopcop.me/) scans observable code and prose patterns such as swallowed exceptions, empty functions, trivial assertions and placeholder markers. In short: Slop Meeter asks whether a project brings receipts; SlopCop looks more closely at what is written on them.

## What the score actually means

Slop Meeter groups its checks into six areas: history and substance, tests and CI, claims and receipts, documentation and releases, dependencies and security, and online maintenance and attention.

Each applicable check returns pass, warning or fail, worth 1, 0.5 or 0 points. Checks that cannot fairly be applied are left out rather than quietly treated as failures. The category results are combined into a 0–100 evidence score, with greater weight given to history, testing and claim verification.

There is also a separate confidence figure. An offline scan, for example, cannot inspect registry availability or GitHub activity, so it can still produce a score while being honest about how much of the full rubric it covered. And if a repository is less than 14 days old or has fewer than 10 commits, Slop Meeter adds “Too early to tell.” A seedling should not lose a forestry contest simply because it has not yet become an oak.

The resulting “slop level” is intentionally the playful part. The evidence and confidence scores are the serious bits.

## 1. History and substance: was this built, or merely unveiled?

Commit depth, work spread over time, the share of the project arriving in one giant commit, the usefulness of commit messages and the number of contributors all help reveal how much development history is available for inspection.

None of these signals is proof of quality. A brilliant solo developer can publish an excellent project in a single import. But incremental history makes decisions, corrections and ownership easier to audit. Specific commit messages add context. Multiple contributors offer mild independent corroboration.

That is why contributor count is deliberately a weak signal and never an automatic failure. Slop Meeter is looking for evidence, not enforcing a corporate org chart on someone’s weekend project.

## 2. Tests and CI: do the tests test anything?

The rubric checks whether tests exist, whether test functions contain meaningful assertions and whether continuous integration actually runs the test suite.

This goes one step beyond spotting a directory named `tests`. Decorative tests are still decoration. Assertions provide executable evidence about expected behaviour, while CI shows that the evidence is checked repeatedly rather than only on the maintainer’s mysteriously well-behaved laptop. The [OpenSSF Scorecard](https://github.com/ossf/scorecard/blob/main/docs/checks.md#ci-tests) uses the same broad signal: tests that run before a change is merged help catch mistakes early.

Slop Meeter does not run repository code. It inspects test structure statically, with stronger analysis for Python and best-effort support for JavaScript and TypeScript. That safety choice limits what it can conclude, so the result remains a prompt for review rather than a certification stamp.

## 3. Claims versus receipts: extraordinary adjectives welcome evidence

Quantitative and superlative claims receive special attention. If a README says a tool is “3× faster,” “state of the art” or otherwise unusually magnificent, Slop Meeter looks nearby for a link to evidence. It also checks for a runnable benchmark or evaluation harness.

This reflects a simple norm: a result is more useful when another person can inspect how it was produced. [NIST’s guidance on software performance measurement](https://www.nist.gov/publications/ghost-machine-dont-let-it-haunt-your-software-performance-measurements) and [ACM SIGMOD’s reproducibility process](https://reproducibility.sigmodconf.hosting.acm.org/index.html) both emphasise measurement procedures and artifacts that let others examine or recreate reported results. Reproducibility does not guarantee that a benchmark is fair, but an unexplained chart guarantees even less.

The tool also measures hype density. One “revolutionary” will not summon the scoring police. A README saturated with promotional language, however, may be spending words that could have explained installation, limitations or methodology. Buzzwords are therefore a small signal, not the main event.

## 4. Documentation, releases and composition: can a stranger evaluate it?

A useful README should explain what the project does, how to install it and how to use it—very close to the role described in [GitHub’s README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes). A recognisable licence clarifies reuse rights; without one, [default copyright rules still apply](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository). Tags and changelogs create a public record of releases. The repository should also contain a plausible amount of implementation rather than mostly generated files, marketing material or placeholders.

These checks reward evaluability. They do not say that more code is automatically better—thank goodness—but they do ask whether the visible substance supports the visible promise.

## 5. Dependencies and security: can we reproduce it without stepping on a rake?

Slop Meeter looks for lockfiles or exact dependency pins, verifies declared packages against official registries when online mode is enabled, flags install-time execution and searches for high-confidence secret patterns without printing secret values.

The reasoning is practical. [npm’s lockfile documentation](https://docs.npmjs.com/files/package-lock.json/) describes capturing an exact dependency tree so later installations can reproduce it, while [pip’s guidance](https://pip.pypa.io/en/stable/topics/repeatable-installs/) recommends version pinning—and, for stronger integrity, hashes. A package name that does not exist can reveal a broken manifest or a dangerous assumption. Lifecycle scripts and shell-pipe installers may be legitimate, but they deserve explicit scrutiny because installation is a surprisingly exciting time to execute code. Published credentials, meanwhile, are not a matter of taste; [GitHub treats exposed secrets as security, compliance and financial risks](https://docs.github.com/en/code-security/concepts/secret-security).

Importantly, Slop Meeter never runs installers, hooks, tests or target code. The repository is treated as untrusted input from the start.

## 6. Maintenance and attention: popularity needs context

With online checks enabled, the rubric considers recent activity, response times on issues, pull-request merge ratios and whether stars look plausible alongside the repository’s age, forks, contributors and issue activity.

This is the most delicate category, so the wording is intentionally restrained. An unusual attention pattern is not proof of manipulation. [GitHub describes stars](https://docs.github.com/en/get-started/exploring-projects-on-github/saving-repositories-with-stars) as a way to save repositories and discover similar projects—not a unit test for quality. Research has found [large-scale suspicious starring patterns](https://doi.org/10.1145/3744916.3764531), but that supports contextual analysis, not drive-by accusations. Slop Meeter reports patterns as plausible, unusual or anomalous and leaves the conclusion to a human.

Likewise, “recent” is adjusted for project age. A mature, stable library should not fail merely because it did not receive a commit last Tuesday. Maintenance evidence must be interpreted in context.

## The thresholds are defaults, not commandments

The exact cut-offs—30 commits, a 15% test-to-source ratio, 80% of strong claims linked to receipts and so on—are starting values chosen to make the rubric concrete and predictable. They are not laws of software physics, and Slop Meeter does not pretend otherwise.

Weights, thresholds, ignored paths and buzzwords are configurable. The project also includes a calibration workflow based on human-reviewed repositories. This matters because a good heuristic should be inspectable and adjustable, especially across ecosystems with different conventions. Even the more established [OpenSSF Scorecard describes its checks and aggregate score as opinionated](https://github.com/ossf/scorecard#project-non-goals), with false positives and false negatives rather than a one-size-fits-all verdict.

The honest way to read a Slop Meeter result is therefore:

- the **evidence score** summarises the signals the tool observed;
- **confidence** says how much of the rubric could be applied;
- the detailed findings show exactly what produced the result;
- and the final judgement still belongs to you.

AI-assistance disclosure is informational only and carries zero weight. That is deliberate. AI can help produce solid, tested, well-documented software, just as humans have long demonstrated a remarkable ability to produce nonsense unassisted.

Slop Meeter’s position is pleasantly boring: do not score the author’s tools, intentions or aesthetic aura. Score the receipts.

That will not eliminate slop. It may, however, make slop work a little harder.

---

The complete rubric, including every weight, threshold and limitation, is available in the [Slop Meeter methodology](https://github.com/rgilsimoes/slopmeeter/blob/main/docs/METHODOLOGY.md).

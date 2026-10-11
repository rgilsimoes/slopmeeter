"""Safe project onboarding for Slop Meeter integrations."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


@dataclass(frozen=True)
class Template:
    component: str
    source: str
    destination: Path


@dataclass(frozen=True)
class PlannedFile:
    action: str
    destination: Path


TEMPLATES = (
    Template("agents", "AGENTS.md", Path("AGENTS.md")),
    Template("prompt", "slop-review.md", Path(".slopmeter/prompts/slop-review.md")),
    Template("codex", "hooks.json", Path(".codex/hooks.json")),
    Template("codex", "slopmeter_stop.py", Path(".codex/hooks/slopmeter_stop.py")),
    Template("github", "slopmeter.yml", Path(".github/workflows/slopmeter.yml")),
)
COMPONENTS = tuple(dict.fromkeys(template.component for template in TEMPLATES))
DEFAULT_COMPONENTS = ("agents", "github")


class OnboardingError(ValueError):
    """Raised when onboarding cannot safely update the target project."""


def build_init_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slopmeter init",
        description="Add Slop Meeter agent and CI integrations to a project.",
    )
    parser.add_argument("directory", nargs="?", default=".", help="project directory (default: .)")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--component",
        choices=COMPONENTS,
        action="append",
        dest="components",
        help="install one component; repeat to select more",
    )
    selection.add_argument("--all", action="store_true", help="install every integration component")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace conflicting integration files after a complete preflight",
    )
    parser.add_argument("--dry-run", action="store_true", help="show changes without writing files")
    return parser


def _template_bytes(template: Template) -> bytes:
    return files("slopmeter.onboarding_templates").joinpath(template.source).read_bytes()


def _validate_parent_path(root: Path, relative: Path) -> None:
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise OnboardingError(f"refusing to write through symlinked directory: {current}")
        if current.exists() and not current.is_dir():
            raise OnboardingError(f"onboarding path is not a directory: {current}")


def _selected_templates(components: tuple[str, ...]) -> tuple[Template, ...]:
    selected = set(components)
    return tuple(template for template in TEMPLATES if template.component in selected)


def plan_onboarding(
    directory: str | os.PathLike[str],
    components: tuple[str, ...],
    *,
    force: bool = False,
) -> tuple[Path, tuple[tuple[PlannedFile, bytes], ...]]:
    requested = set(components)
    unknown = requested.difference(COMPONENTS)
    if unknown:
        raise OnboardingError(f"unknown component: {sorted(unknown)[0]}")
    if not requested:
        raise OnboardingError("at least one onboarding component is required")

    root = Path(directory).expanduser()
    if not root.exists():
        raise OnboardingError(f"project directory does not exist: {root}")
    if not root.is_dir():
        raise OnboardingError(f"project path is not a directory: {root}")
    root = root.resolve()

    planned: list[tuple[PlannedFile, bytes]] = []
    conflicts: list[Path] = []
    for template in _selected_templates(components):
        _validate_parent_path(root, template.destination)
        destination = root / template.destination
        content = _template_bytes(template)
        if destination.is_symlink():
            action = "replace" if force else "conflict"
        elif destination.exists():
            if not destination.is_file():
                raise OnboardingError(f"onboarding destination is not a file: {destination}")
            action = "unchanged" if destination.read_bytes() == content else "replace" if force else "conflict"
        else:
            action = "create"
        if action == "conflict":
            conflicts.append(template.destination)
        planned.append((PlannedFile(action, template.destination), content))

    if conflicts:
        listed = ", ".join(str(path) for path in conflicts)
        raise OnboardingError(f"refusing to overwrite existing files: {listed}; use --force to replace them")
    return root, tuple(planned)


def _create_parents(root: Path, relative: Path) -> None:
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise OnboardingError(f"refusing to write through symlinked directory: {current}")
        if current.exists():
            if not current.is_dir():
                raise OnboardingError(f"onboarding path is not a directory: {current}")
        else:
            current.mkdir()


def _replace_file(destination: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
        os.replace(temporary_name, destination)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def apply_onboarding(
    root: Path,
    planned: tuple[tuple[PlannedFile, bytes], ...],
    *,
    dry_run: bool = False,
) -> tuple[PlannedFile, ...]:
    if not dry_run:
        for item, content in planned:
            if item.action == "unchanged":
                continue
            _create_parents(root, item.destination)
            _replace_file(root / item.destination, content)
    return tuple(item for item, _ in planned)


def run_init(argv: list[str]) -> int:
    args = build_init_parser().parse_args(argv)
    components = COMPONENTS if args.all else tuple(args.components or DEFAULT_COMPONENTS)
    try:
        root, planned = plan_onboarding(args.directory, components, force=args.force)
        results = apply_onboarding(root, planned, dry_run=args.dry_run)
    except (OSError, OnboardingError) as exc:
        print(f"slopmeter init: {exc}", file=sys.stderr)
        return 2

    prefix = "Would initialize" if args.dry_run else "Initialized"
    print(f"{prefix} Slop Meeter in {root}")
    for item in results:
        action = f"would {item.action}" if args.dry_run and item.action != "unchanged" else item.action
        print(f"  {action:13} {item.destination}")
    if not args.dry_run:
        print(f"Next: review the generated files, then run slopmeter {root} --format json")
    return 0

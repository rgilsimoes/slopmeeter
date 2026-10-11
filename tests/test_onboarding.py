from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

from slopmeter.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_init_installs_recommended_agent_and_ci_components(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()

    assert main(["init", str(project)]) == 0

    assert (project / "AGENTS.md").is_file()
    assert (project / ".github/workflows/slopmeter.yml").is_file()
    assert not (project / ".slopmeter/prompts/slop-review.md").exists()
    assert not (project / ".codex/hooks.json").exists()
    output = capsys.readouterr().out
    assert "Initialized Slop Meeter" in output
    assert "create        AGENTS.md" in output
    assert "review the generated files" in output


def test_init_all_installs_every_integration_component(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    assert main(["init", str(project), "--all"]) == 0

    assert (project / "AGENTS.md").is_file()
    assert (project / ".slopmeter/prompts/slop-review.md").is_file()
    assert (project / ".codex/hooks.json").is_file()
    assert (project / ".codex/hooks/slopmeter_stop.py").is_file()
    assert (project / ".github/workflows/slopmeter.yml").is_file()


def test_init_can_select_repeatable_components(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    assert (
        main(
            [
                "init",
                str(project),
                "--component",
                "prompt",
                "--component",
                "codex",
            ]
        )
        == 0
    )

    assert not (project / "AGENTS.md").exists()
    assert (project / ".slopmeter/prompts/slop-review.md").is_file()
    assert (project / ".codex/hooks.json").is_file()
    assert not (project / ".github/workflows/slopmeter.yml").exists()


def test_init_preflights_conflicts_before_writing_any_file(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    agents = project / "AGENTS.md"
    agents.write_text("keep these project instructions\n", encoding="utf-8")

    assert main(["init", str(project)]) == 2

    assert agents.read_text(encoding="utf-8") == "keep these project instructions\n"
    assert not (project / ".github").exists()
    error = capsys.readouterr().err
    assert "refusing to overwrite existing files: AGENTS.md" in error
    assert "--force" in error


def test_init_force_replaces_conflicts_and_keeps_identical_files(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("old instructions\n", encoding="utf-8")

    assert main(["init", str(project), "--force"]) == 0
    first = capsys.readouterr().out
    assert "replace       AGENTS.md" in first

    assert main(["init", str(project)]) == 0
    second = capsys.readouterr().out
    assert "unchanged     AGENTS.md" in second
    assert "unchanged     .github/workflows/slopmeter.yml" in second


def test_init_dry_run_reports_without_writing(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()

    assert main(["init", str(project), "--all", "--dry-run"]) == 0

    assert list(project.iterdir()) == []
    output = capsys.readouterr().out
    assert "Would initialize Slop Meeter" in output
    assert "would create" in output


def test_init_rejects_missing_directory_and_symlinked_parent(tmp_path, capsys):
    assert main(["init", str(tmp_path / "missing")]) == 2
    assert "project directory does not exist" in capsys.readouterr().err

    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    try:
        (project / ".github").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    assert main(["init", str(project), "--component", "github"]) == 2
    assert "symlinked directory" in capsys.readouterr().err
    assert list(outside.iterdir()) == []


def test_init_force_replaces_file_symlink_without_following_it(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside-agents.md"
    outside.write_text("outside content\n", encoding="utf-8")
    try:
        (project / "AGENTS.md").symlink_to(outside)
    except OSError:
        pytest.skip("file symlinks are unavailable")

    assert main(["init", str(project), "--component", "agents", "--force"]) == 0

    assert not (project / "AGENTS.md").is_symlink()
    assert "Slop Meeter evidence policy" in (project / "AGENTS.md").read_text(encoding="utf-8")
    assert outside.read_text(encoding="utf-8") == "outside content\n"


@pytest.mark.parametrize(
    ("resource", "integration"),
    [
        ("AGENTS.md", "integrations/AGENTS.md"),
        ("slop-review.md", "integrations/prompts/slop-review.md"),
        ("hooks.json", "integrations/codex/hooks.json"),
        ("slopmeter_stop.py", "integrations/codex/hooks/slopmeter_stop.py"),
        ("slopmeter.yml", "integrations/github/slopmeter.yml"),
    ],
)
def test_bundled_onboarding_templates_match_public_integrations(resource, integration):
    bundled = files("slopmeter.onboarding_templates").joinpath(resource).read_bytes()
    assert bundled == (ROOT / integration).read_bytes()

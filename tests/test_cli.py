import io
import sys

import pytest

from slopmeter import cli
from slopmeter.cli import main


class TtyBuffer(io.StringIO):
    def isatty(self):
        return True


def test_version_and_list_checks(capsys):
    assert main(["--list-checks"]) == 0
    output = capsys.readouterr().out
    assert "H1\tCommit depth" in output
    assert "I1\tAI-assistance disclosure" in output


def test_explain(capsys):
    assert main(["--explain", "C1"]) == 0
    assert "Claims have receipts" in capsys.readouterr().out


def test_local_analysis_json_and_fail_under(tmp_path, capsys):
    (tmp_path / "README.md").write_text("# Tiny\n\nA small local project.\n", encoding="utf-8")
    assert main([str(tmp_path), "--format", "json", "--fail-under", "100"]) == 1
    output = capsys.readouterr().out
    assert '"schema_version": 1' in output


def test_text_colour_can_be_forced_but_is_off_for_captured_auto_output(tmp_path, capsys):
    (tmp_path / "README.md").write_text("# Tiny\n\nA small local project.\n", encoding="utf-8")

    assert main([str(tmp_path)]) == 0
    assert "\x1b[" not in capsys.readouterr().out

    assert main([str(tmp_path), "--color", "always"]) == 0
    assert "\x1b[" in capsys.readouterr().out

    assert main([str(tmp_path), "--color", "never"]) == 0
    assert "\x1b[" not in capsys.readouterr().out


def test_auto_colour_respects_tty_no_color_and_dumb_terminal(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("# Tiny\n\nA small local project.\n", encoding="utf-8")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    terminal = TtyBuffer()
    monkeypatch.setattr(sys, "stdout", terminal)
    assert main([str(tmp_path)]) == 0
    assert "\x1b[" in terminal.getvalue()

    no_color_terminal = TtyBuffer()
    monkeypatch.setattr(sys, "stdout", no_color_terminal)
    monkeypatch.setenv("NO_COLOR", "")
    assert main([str(tmp_path)]) == 0
    assert "\x1b[" not in no_color_terminal.getvalue()

    dumb_terminal = TtyBuffer()
    monkeypatch.setattr(sys, "stdout", dumb_terminal)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert main([str(tmp_path)]) == 0
    assert "\x1b[" not in dumb_terminal.getvalue()


@pytest.mark.parametrize("format_name", ["json", "markdown", "html"])
def test_colour_is_never_added_to_non_text_formats(tmp_path, capsys, format_name):
    (tmp_path / "README.md").write_text("# Tiny\n\nA small local project.\n", encoding="utf-8")

    assert main([str(tmp_path), "--format", format_name, "--color", "always"]) == 0
    assert "\x1b[" not in capsys.readouterr().out


def test_invalid_colour_mode_is_a_usage_error():
    with pytest.raises(SystemExit) as error:
        main([".", "--color", "sometimes"])
    assert error.value.code == 2


def test_output_writes_the_selected_format_without_printing_the_report(tmp_path, capsys):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "README.md").write_text("# Tiny\n\nA small local project.\n", encoding="utf-8")
    destination = tmp_path / "report.md"

    assert main([str(repository), "--format", "markdown", "--output", str(destination)]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert destination.read_text(encoding="utf-8").startswith("# Slop Meeter report\n")


def test_output_rejects_a_missing_parent_directory(tmp_path, capsys):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "README.md").write_text("# Tiny\n", encoding="utf-8")
    destination = tmp_path / "missing" / "report.txt"

    assert main([str(repository), "--output", str(destination)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "output directory does not exist" in captured.err
    assert not destination.exists()


def test_render_failure_does_not_replace_an_existing_output(tmp_path, capsys, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "README.md").write_text("# Tiny\n", encoding="utf-8")
    destination = tmp_path / "report.txt"
    destination.write_text("keep me\n", encoding="utf-8")

    def fail_render(*args, **kwargs):
        raise ValueError("render failed")

    monkeypatch.setattr(cli, "render", fail_render)

    assert cli.main([str(repository), "--output", str(destination)]) == 2
    assert capsys.readouterr().out == ""
    assert destination.read_text(encoding="utf-8") == "keep me\n"


def test_html_report_can_be_written_from_the_cli(tmp_path, capsys):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "README.md").write_text("# Tiny\n\nA small local project.\n", encoding="utf-8")
    destination = tmp_path / "report.html"

    assert main([str(repository), "--format", "html", "-o", str(destination)]) == 0

    assert capsys.readouterr().out == ""
    document = destination.read_text(encoding="utf-8")
    assert document.startswith("<!doctype html>\n")
    assert "Repository evidence report" in document


def test_cli_reports_generation_stages_and_completion(tmp_path, capsys, monkeypatch):
    (tmp_path / "README.md").write_text("# Tiny\n", encoding="utf-8")
    updates = []

    class RecordingProgress:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def update(self, percent, stage):
            updates.append((percent, stage))

    monkeypatch.setattr(cli, "ProgressIndicator", RecordingProgress)

    assert main([str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert updates[0] == (5, "Loading configuration")
    assert (15, "Preparing local repository") in updates
    assert (25, "Indexing repository files") in updates
    assert (95, "Rendering report") in updates
    assert updates[-1] == (100, "Complete")
    assert [percent for percent, _ in updates] == sorted(percent for percent, _ in updates)

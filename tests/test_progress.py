import io
import time

import pytest

from slopmeter.progress import STATUS_MESSAGES, ProgressIndicator


class TtyBuffer(io.StringIO):
    def isatty(self):
        return True


def test_progress_animates_with_a_playful_status_and_clears_the_line(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    terminal = TtyBuffer()

    with ProgressIndicator(stream=terminal, interval=0.001, message_interval=0.002):
        time.sleep(0.01)

    output = terminal.getvalue()
    assert any(message in output for message in STATUS_MESSAGES)
    assert any(frame in output for frame in "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
    assert output.endswith("\r\x1b[2K")


def test_progress_reports_real_percentage_and_stage(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    terminal = TtyBuffer()

    with ProgressIndicator(stream=terminal, interval=0.001) as progress:
        progress.update(35, "Inspecting repository history")
        time.sleep(0.005)

    output = terminal.getvalue()
    assert "35%" in output
    assert "Inspecting repository history" in output
    assert "[" in output and "]" in output


@pytest.mark.parametrize("term", ["dumb", "xterm-256color"])
def test_progress_is_quiet_when_the_terminal_cannot_animate(monkeypatch, term):
    monkeypatch.setenv("TERM", term)
    stream = io.StringIO()

    with ProgressIndicator(stream=stream, interval=0.001):
        pass

    assert stream.getvalue() == ""


def test_progress_clears_the_line_when_the_operation_fails(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    terminal = TtyBuffer()

    with pytest.raises(RuntimeError), ProgressIndicator(stream=terminal, interval=0.001):
        raise RuntimeError("analysis failed")

    assert terminal.getvalue().endswith("\r\x1b[2K")

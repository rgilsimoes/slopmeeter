from __future__ import annotations

import os
import random
import sys
import threading
from collections.abc import Sequence
from types import TracebackType
from typing import TextIO

STATUS_MESSAGES = (
    "Deslopifying",
    "Unsloptastic",
    "Checking the receipts",
    "Interrogating the README",
    "Counting suspicious buzzwords",
    "Auditing the vibes",
    "Separating signal from slop",
    "Looking for actual tests",
)

SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


class ProgressIndicator:
    """A transient terminal spinner that stays out of redirected output."""

    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        interval: float = 0.08,
        message_interval: float = 1.6,
        messages: Sequence[str] = STATUS_MESSAGES,
    ) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.interval = interval
        self.message_interval = message_interval
        self.messages = tuple(messages)
        self.enabled = (
            bool(self.messages)
            and os.environ.get("TERM") != "dumb"
            and self.stream.isatty()
        )
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> ProgressIndicator:
        if not self.enabled:
            return self

        self._thread = threading.Thread(
            target=self._animate,
            name="slopmeter-progress",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self.enabled:
            return

        self._stopped.set()
        if self._thread is not None:
            self._thread.join()
        self._write("\r\x1b[2K")

    def _animate(self) -> None:
        messages = list(self.messages)
        random.shuffle(messages)
        message_index = 0
        frame_index = 0
        elapsed = 0.0

        while not self._stopped.is_set():
            self._write(f"\r\x1b[2K{SPINNER_FRAMES[frame_index]} {messages[message_index]}…")
            frame_index = (frame_index + 1) % len(SPINNER_FRAMES)

            if self._stopped.wait(self.interval):
                break
            elapsed += self.interval
            if elapsed >= self.message_interval:
                message_index = (message_index + 1) % len(messages)
                elapsed = 0.0

    def _write(self, content: str) -> None:
        try:
            self.stream.write(content)
            self.stream.flush()
        except (OSError, ValueError):
            self._stopped.set()

"""`log_capture`: the app's own log records, without third-party noise."""

import json
import logging
from dataclasses import dataclass

import pytest

APP_LOGGER = "language_lab"
REQUEST_LOGGER = f"{APP_LOGGER}.request"  # AD-15: one JSON line per request


@dataclass
class LogCapture:
    caplog: pytest.LogCaptureFixture

    @property
    def records(self) -> list[logging.LogRecord]:
        return [
            r
            for r in self.caplog.records
            if r.name == APP_LOGGER or r.name.startswith(f"{APP_LOGGER}.")
        ]

    @property
    def messages(self) -> list[str]:
        return [r.getMessage() for r in self.records]

    @property
    def request_lines(self) -> list[dict]:
        """The per-request lines, parsed from JSON, in order."""
        return [json.loads(r.getMessage()) for r in self.records if r.name == REQUEST_LOGGER]

    @property
    def all_text(self) -> str:
        """Every captured record from every logger, for leak checks (R-02)."""
        return self.caplog.text

    def clear(self) -> None:
        self.caplog.clear()


@pytest.fixture
def log_capture(caplog: pytest.LogCaptureFixture) -> LogCapture:
    """Capture `language_lab.*` records at INFO and above. For stdout/stderr use `capsys`."""
    caplog.set_level(logging.INFO, logger=APP_LOGGER)
    return LogCapture(caplog)

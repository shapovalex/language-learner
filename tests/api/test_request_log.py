"""Story 1.3: one content-free log line per request, and no uvicorn access log (AD-15).

Skipped until the request-id middleware lands. Un-skip one per task, watch it fail, then implement.
"""

import pytest
from fastapi.testclient import TestClient

from language_lab import app as app_module
from tests.support.app_env import config_values
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import ConfigFiles
from tests.support.probes import (
    BOOM_ROUTE,
    PROBE_PREFIX,
    VALIDATE_ROUTE,
    error_envelope,
    sentinel,
)

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 1.3: un-skip with the request log")

LINE_KEYS = {"requestId", "method", "route", "status", "code", "durationMs"}


@RED_PHASE
@pytest.mark.p0
def test_one_line_per_request_with_ad15_fields(
    probe_client: TestClient, log_capture: LogCapture
) -> None:
    """AC-4: exactly one line per request: id, method, route template, status, code, duration."""
    response = probe_client.get(f"{PROBE_PREFIX}/boom/42")

    lines = log_capture.request_lines
    assert len(lines) == 1
    [line] = lines
    assert set(line) == LINE_KEYS
    assert line["requestId"] == error_envelope(response).get("requestId")
    assert (line["method"], line["route"], line["status"], line["code"]) == (
        "GET",
        BOOM_ROUTE,
        500,
        "internal_error",
    )
    assert isinstance(line["durationMs"], int | float) and line["durationMs"] >= 0


@RED_PHASE
@pytest.mark.p0
def test_log_line_carries_no_request_content(
    probe_client: TestClient, log_capture: LogCapture, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5: the line holds the route template, never the path, query, body or headers (R-02)."""
    secret = sentinel()

    probe_client.post(
        f"{PROBE_PREFIX}/validate/{secret}",
        params={"limit": secret},
        json={"word": secret, "count": secret},
        headers={"X-Probe": secret},
    )

    assert [line["route"] for line in log_capture.request_lines] == [VALIDATE_ROUTE]
    assert secret not in log_capture.all_text
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err


@RED_PHASE
@pytest.mark.p1
def test_main_turns_off_uvicorn_access_log(
    monkeypatch: pytest.MonkeyPatch, config_files: ConfigFiles
) -> None:
    """AC-6: the uvicorn access log is off; the request log replaces it."""
    config_files.write_home(config_values())
    calls: list[dict] = []
    monkeypatch.setattr(app_module.uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))

    app_module.main()

    assert calls[0].get("access_log") is False

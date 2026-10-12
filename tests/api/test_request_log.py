"""Story 1.3: one content-free log line per request, and no uvicorn access log (AD-15)."""

import json
import logging
import subprocess
import sys
import threading
from pathlib import Path

import httpx
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from language_lab import app as app_module
from language_lab.app import create_app
from tests.support.app_env import HOME_ENV_RELATIVE, config_values, isolated_environ, write_dotenv
from tests.support.fixtures.logs import APP_LOGGER, LogCapture
from tests.support.fixtures.settings import ConfigFiles, SettingsFactory
from tests.support.hosts import app_client
from tests.support.live_server import bind_free_port
from tests.support.probes import (
    BOOM_ROUTE,
    PROBE_PREFIX,
    VALIDATE_ROUTE,
    error_envelope,
    sentinel,
)

SERVER_START_TIMEOUT_S = 15.0
LINE_KEYS = {"requestId", "method", "route", "status", "code", "durationMs"}


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


@pytest.mark.p0
@pytest.mark.parametrize(
    ("path", "route"),
    [
        ("/api/no-such-route/{secret}", "/{path:path}"),
        (f"{PROBE_PREFIX}/boom/{{secret}}", BOOM_ROUTE),
    ],
    ids=["unknown-route", "unhandled"],
)
def test_failure_logs_carry_no_request_content(
    probe_client: TestClient,
    log_capture: LogCapture,
    capsys: pytest.CaptureFixture[str],
    path: str,
    route: str,
) -> None:
    """AC-5: no path, query or traceback text in any log or on stdout/stderr (R-02)."""
    secret = sentinel()

    probe_client.get(path.format(secret=secret), params={"q": secret})

    assert [line["route"] for line in log_capture.request_lines] == [route]
    assert secret not in log_capture.all_text
    assert "Traceback" not in log_capture.all_text
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "Traceback" not in captured.out + captured.err


@pytest.mark.p1
def test_success_line_has_null_code(probe_client: TestClient, log_capture: LogCapture) -> None:
    """AC-4: a 2xx request logs status 200 and code null."""
    probe_client.get("/api/health")

    [line] = log_capture.request_lines
    assert (line["method"], line["route"], line["status"], line["code"]) == (
        "GET",
        "/api/health",
        200,
        None,
    )


@pytest.mark.p1
def test_each_request_gets_its_own_id(probe_client: TestClient, log_capture: LogCapture) -> None:
    """AC-4: two requests, two lines, two distinct request ids."""
    probe_client.get("/api/health")
    probe_client.get("/api/no-such-route")

    ids = [line["requestId"] for line in log_capture.request_lines]
    assert len(ids) == 2
    assert ids[0] != ids[1]


@pytest.mark.p2
def test_shell_request_is_logged_too(probe_client: TestClient, log_capture: LogCapture) -> None:
    """AC-4: non-/api requests get the request line, under the catch-all template."""
    probe_client.get("/captures")

    [line] = log_capture.request_lines
    assert (line["route"], line["status"], line["code"]) == ("/{path:path}", 200, None)


@pytest.mark.p1
def test_real_server_logs_json_lines_and_no_access_line(tmp_path: Path) -> None:
    """AC-6: `language-lab` prints one JSON line per request and no uvicorn access line."""
    home = tmp_path / "home"
    write_dotenv(home / HOME_ENV_RELATIVE, config_values())
    with bind_free_port() as sock:
        port = sock.getsockname()[1]
    secret = sentinel()
    proc = subprocess.Popen(
        [sys.executable, "-c", "from language_lab.app import main; main()"],
        env=isolated_environ(home, {"LANGUAGE_LAB_PORT": str(port)}),
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output: list[str] = []
    listening = threading.Event()

    def read_output() -> None:
        assert proc.stdout is not None
        for text in proc.stdout:
            output.append(text)
            if "Uvicorn running on" in text:  # uvicorn's own line, printed once the port is bound
                listening.set()
        listening.set()  # the process ended: stop waiting either way

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        assert listening.wait(SERVER_START_TIMEOUT_S), "server did not start"
        assert proc.poll() is None, "".join(output)
        base = f"http://127.0.0.1:{port}"
        health = httpx.get(f"{base}/api/health", timeout=5.0)
        missing = httpx.get(f"{base}/api/nope", params={"x": secret}, timeout=5.0)
    finally:
        proc.terminate()
        proc.wait(timeout=SERVER_START_TIMEOUT_S)
        reader.join(timeout=SERVER_START_TIMEOUT_S)
    text = "".join(output)

    assert (health.status_code, missing.status_code) == (200, 404)
    lines = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
    assert [(line["route"], line["status"]) for line in lines] == [
        ("/api/health", 200),
        ("/{path:path}", 404),
    ]
    assert secret not in text
    assert "/api/nope" not in text
    assert "HTTP/1.1" not in text


@pytest.mark.p1
def test_main_twice_attaches_one_stdout_handler(
    monkeypatch: pytest.MonkeyPatch, config_files: ConfigFiles
) -> None:
    """NFR-9: main() adds one stdout handler to the app logger, never a duplicate."""
    config_files.write_home(config_values())
    monkeypatch.setattr(app_module.uvicorn, "run", lambda app, **kwargs: None)

    app_module.main()
    app_module.main()

    handlers = logging.getLogger(APP_LOGGER).handlers
    assert sum(isinstance(h, app_module._StdoutHandler) for h in handlers) == 1


@pytest.mark.p1
def test_non_api_crash_stays_plain_text_500(
    settings_factory: SettingsFactory,
    log_capture: LogCapture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R-07: outside /api a crash is a plain 500, not the envelope, and still leaks nothing."""
    secret = sentinel()
    settings = settings_factory()
    app = create_app(settings)

    async def crash() -> None:
        raise RuntimeError(f"shell failure for {secret}")

    app.router.routes.insert(0, APIRoute("/_probe-shell-crash", crash))
    client = app_client(app, settings, raise_server_exceptions=False)

    response = client.get("/_probe-shell-crash", params={"q": secret})

    assert (response.status_code, response.text) == (500, "Internal Server Error")
    assert response.headers["content-type"].startswith("text/plain")
    assert [line["code"] for line in log_capture.request_lines] == ["internal_error"]
    assert secret not in log_capture.all_text
    assert "Traceback" not in log_capture.all_text
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "Traceback" not in captured.out + captured.err

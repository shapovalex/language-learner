"""Story 1.4: the AD-16 Host and Origin allow-list.

Q1 (decided 2026-10-11): `Host` must be on the allow-list, and `X-Forwarded-Host`, when present,
must be on it too. A DNS-rebinding page has a foreign `Host`, so no XFH it sets can rescue it,
and the rule holds whether Tailscale Serve keeps the public `Host` or rewrites it to loopback.

Skipped until the allow-list middleware lands. Un-skip one per task, watch it fail, then implement.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from language_lab import __version__
from language_lab.app import create_app
from language_lab.domain.errors import MESSAGES, ErrorCode
from language_lab.settings import Settings
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import (
    FOREIGN_HOST,
    TAILNET_HOST,
    app_client,
    local_hosts,
    serve_headers,
)
from tests.support.probes import VALIDATE_ROUTE, add_probe_routes, error_envelope

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.4: un-skip with the AD-16 allow-list middleware"
)

FORBIDDEN = 403
HEALTH = "/api/health"
# A non-GET /api route that accepts this body, so only the Origin check can turn it away
WRITE_PATH = VALIDATE_ROUTE.format(item_id=1)
WRITE_BODY = {"word": "bonjour", "count": 1}


@pytest.fixture
def settings(settings_factory: SettingsFactory) -> Settings:
    return settings_factory(public_host=TAILNET_HOST)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    """No default Origin, so each test sends exactly the Origin it is about."""
    app = add_probe_routes(create_app(settings))
    return app_client(app, settings, same_origin=False, raise_server_exceptions=False)


def _with_port(headers: dict[str, str], settings: Settings) -> dict[str, str]:
    return {name: value.format(port=settings.port) for name, value in headers.items()}


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize("path", [HEALTH, "/captures", f"/static/{__version__}/main.js"])
def test_foreign_host_is_rejected_on_every_path(
    client: TestClient, settings: Settings, path: str
) -> None:
    """AC-1: only 127.0.0.1:<port>, localhost:<port> and the tailnet host are allowed."""
    foreign = f"{FOREIGN_HOST}:{settings.port}"

    assert client.get(path, headers={"host": foreign}).status_code == FORBIDDEN
    wrong_port = f"127.0.0.1:{settings.port + 1}"
    allowed = [*local_hosts(settings), TAILNET_HOST]
    statuses = {host: client.get(path, headers={"host": host}).status_code for host in allowed}
    statuses[wrong_port] = client.get(path, headers={"host": wrong_port}).status_code
    assert statuses == {**dict.fromkeys(allowed, 200), wrong_port: FORBIDDEN}


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(
    "headers",
    [
        pytest.param(
            {"host": f"{FOREIGN_HOST}:{{port}}", "x-forwarded-host": TAILNET_HOST},
            id="rebinding-page-claims-the-tailnet",
        ),
        pytest.param(
            {"host": "127.0.0.1:{port}", "x-forwarded-host": f"{FOREIGN_HOST}:{{port}}"},
            id="loopback-with-a-foreign-forwarded-host",
        ),
    ],
)
def test_forwarded_host_can_neither_rescue_nor_spoof(
    client: TestClient, settings: Settings, headers: dict[str, str]
) -> None:
    """AC-5: Host and X-Forwarded-Host must both be allowed (Q1); the tailnet via XFH passes."""
    assert client.get(HEALTH, headers=_with_port(headers, settings)).status_code == FORBIDDEN
    assert client.get(HEALTH, headers=serve_headers()).status_code == 200


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="missing"),
        pytest.param({"origin": f"http://{FOREIGN_HOST}:{{port}}"}, id="foreign"),
        pytest.param({"origin": "null"}, id="opaque"),
    ],
)
def test_write_without_an_allowed_origin_is_rejected(
    client: TestClient, settings: Settings, headers: dict[str, str]
) -> None:
    """AC-6: a non-GET /api request needs an Origin whose host[:port] is on the allow-list."""
    response = client.post(WRITE_PATH, json=WRITE_BODY, headers=_with_port(headers, settings))

    assert response.status_code == FORBIDDEN
    # The scheme isn't compared: Tailscale Serve's Origin is https in front of an http app
    loopback_https = {"origin": f"https://127.0.0.1:{settings.port}"}
    assert client.post(WRITE_PATH, json=WRITE_BODY, headers=loopback_https).status_code == 200
    assert client.post(WRITE_PATH, json=WRITE_BODY, headers=serve_headers()).status_code == 200


type Send = Callable[[TestClient, Settings], Response]

REJECTED: dict[str, Send] = {
    "foreign-host": lambda c, s: c.get(HEALTH, headers={"host": f"{FOREIGN_HOST}:{s.port}"}),
    "missing-origin": lambda c, s: c.post(WRITE_PATH, json=WRITE_BODY),
}


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize("send", REJECTED.values(), ids=REJECTED.keys())
def test_rejection_is_the_forbidden_origin_envelope_with_one_log_line(
    client: TestClient, settings: Settings, log_capture: LogCapture, send: Send
) -> None:
    """AC-7: a rejection is 403 forbidden_origin in the envelope, with one content-free line."""
    response = send(client, settings)

    error = error_envelope(response)
    assert error.get("code") == ErrorCode.FORBIDDEN_ORIGIN.value
    assert response.status_code == FORBIDDEN
    assert error["message"] == MESSAGES[ErrorCode.FORBIDDEN_ORIGIN]
    lines = log_capture.request_lines
    assert [(line["status"], line["code"]) for line in lines] == [(403, "forbidden_origin")]
    assert lines[0]["requestId"] == error["requestId"]
    assert FOREIGN_HOST not in log_capture.all_text  # header values stay out of the log (R-02)

"""Story 1.4: the AD-16 Host and Origin allow-list.

Q1 (decided 2026-10-11): `Host` must be on the allow-list, and `X-Forwarded-Host`, when present,
must be on it too. A DNS-rebinding page has a foreign `Host`, so no XFH it sets can rescue it,
and the rule holds whether Tailscale Serve keeps the public `Host` or rewrites it to loopback.
"""

import asyncio
import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from starlette.types import ASGIApp

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
from tests.support.probes import VALIDATE_ROUTE, add_probe_routes, error_envelope, sentinel

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


# --- Green-phase backlog: the secondary branches of AC-1, AC-6 and AC-7 ---

OTHER_WRITE_PATH = "/api/_probe/write"


@pytest.fixture
def write_client(settings: Settings) -> TestClient:
    """`client`, plus a test-local /api route answering PUT, PATCH and DELETE."""
    app = add_probe_routes(create_app(settings))

    async def write() -> dict[str, bool]:
        return {"ok": True}

    app.add_api_route(OTHER_WRITE_PATH, write, methods=["PUT", "PATCH", "DELETE"])
    return app_client(app, settings, same_origin=False, raise_server_exceptions=False)


@pytest.mark.p1
@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_every_non_get_method_needs_an_allowed_origin(
    write_client: TestClient, settings: Settings, method: str
) -> None:
    """AC-6: PUT, PATCH and DELETE without an Origin are rejected like POST."""
    assert write_client.request(method, OTHER_WRITE_PATH).status_code == FORBIDDEN
    same_origin = {"origin": f"http://127.0.0.1:{settings.port}"}
    response = write_client.request(method, OTHER_WRITE_PATH, headers=same_origin)
    assert response.status_code == 200


@pytest.mark.p2
def test_get_api_with_a_foreign_origin_passes(client: TestClient, settings: Settings) -> None:
    """AC-6: AD-16 checks Origin on non-GET /api only; an allowed Host is enough for a GET."""
    foreign = {"origin": f"http://{FOREIGN_HOST}:{settings.port}"}
    assert client.get(HEALTH, headers=foreign).status_code == 200


@pytest.mark.p3
@pytest.mark.parametrize(
    "host",
    [
        pytest.param("LOCALHOST:{port}", id="upper-case-loopback"),
        pytest.param("Mac-Mini.tail1234.ts.net", id="mixed-case-tailnet"),
        pytest.param(f"{TAILNET_HOST}:443", id="explicit-default-https-port"),
    ],
)
def test_host_is_normalised_before_comparison(
    client: TestClient, settings: Settings, host: str
) -> None:
    """AC-1: Host is compared case-insensitively, and an explicit :443 equals no port."""
    headers = _with_port({"host": host}, settings)
    assert client.get(HEALTH, headers=headers).status_code == 200


@pytest.mark.p2
@pytest.mark.parametrize("path", ["/captures", f"/static/{__version__}/main.js"])
def test_rejection_outside_api_is_plain_text(
    client: TestClient, settings: Settings, path: str
) -> None:
    """AC-1: a shell or static 403 is plain text, not the /api envelope (R-07 convention)."""
    response = client.get(path, headers={"host": f"{FOREIGN_HOST}:{settings.port}"})

    assert response.status_code == FORBIDDEN
    assert response.headers["content-type"].startswith("text/plain")
    assert error_envelope(response) == {}


@pytest.mark.p1
def test_rejection_carries_no_header_value(
    client: TestClient, settings: Settings, log_capture: LogCapture
) -> None:
    """AC-7: sentinel Host, X-Forwarded-Host and Origin values reach neither body nor log."""
    marker = sentinel()
    rejected = [
        client.get(HEALTH, headers={"host": f"{marker}.example"}),
        client.get(HEALTH, headers={"host": local_hosts(settings)[0], "x-forwarded-host": marker}),
        client.post(WRITE_PATH, json=WRITE_BODY, headers={"origin": f"http://{marker}"}),
    ]

    assert [r.status_code for r in rejected] == [FORBIDDEN] * 3
    assert all(marker not in r.text for r in rejected)
    assert marker not in log_capture.all_text


async def _raw_status(app: ASGIApp, method: str, path: str, headers: list[tuple[str, str]]) -> int:
    """Drive the app with a raw ASGI scope, so repeated headers reach it unmerged."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(name.encode("latin-1"), value.encode("latin-1")) for name, value in headers],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 80),
    }
    body = json.dumps(WRITE_BODY).encode() if method != "GET" else b""
    sent: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    await app(scope, receive, send)
    return next(m["status"] for m in sent if m["type"] == "http.response.start")


@pytest.mark.p0
@pytest.mark.parametrize(
    ("method", "path", "header"),
    [
        pytest.param("GET", HEALTH, "host", id="repeated-host"),
        pytest.param("GET", HEALTH, "x-forwarded-host", id="repeated-forwarded-host"),
        pytest.param("POST", WRITE_PATH, "origin", id="repeated-origin"),
    ],
)
def test_a_foreign_second_copy_of_a_header_is_rejected(
    settings: Settings, method: str, path: str, header: str
) -> None:
    """AC-5/AC-6: every copy of Host, X-Forwarded-Host and Origin must be allowed."""
    app = add_probe_routes(create_app(settings))
    loopback = local_hosts(settings)[0]
    allowed = {
        "host": loopback,
        "x-forwarded-host": TAILNET_HOST,
        "origin": f"http://{loopback}",
    }
    foreign = f"http://{FOREIGN_HOST}" if header == "origin" else FOREIGN_HOST
    base = [(name, value) for name, value in allowed.items() if name != header]
    base.append(("content-type", "application/json"))
    repeated = [*base, (header, allowed[header]), (header, foreign)]

    assert asyncio.run(_raw_status(app, method, path, repeated)) == FORBIDDEN
    single = [*base, (header, allowed[header])]
    assert asyncio.run(_raw_status(app, method, path, single)) == 200

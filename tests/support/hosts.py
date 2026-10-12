"""Hosts and Origins as the AD-16 allow-list sees them, and the recorded Tailscale inputs."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from language_lab.settings import Settings

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TAILSCALE_STATUS = FIXTURES / "tailscale-status.json"
TAILSCALE_SERVE_HEADERS = FIXTURES / "tailscale-serve-headers.json"

# The tailnet name in both recorded fixtures: Self.DNSName without its trailing dot
TAILNET_HOST = "mac-mini.tail1234.ts.net"
# A DNS-rebinding name: it resolves to 127.0.0.1, so a page on it reaches the app's own port
FOREIGN_HOST = "evil.example"

# Tailscale discovery waits this long before giving up (Q2, decided 2026-10-11)
DISCOVERY_TIMEOUT_S = 2.0


def local_hosts(settings: Settings) -> list[str]:
    """The loopback entries of the allow-list: `127.0.0.1:<port>` and `localhost:<port>`."""
    return [f"127.0.0.1:{settings.port}", f"localhost:{settings.port}"]


def local_url(settings: Settings) -> str:
    return f"http://127.0.0.1:{settings.port}"


def app_client(
    app: FastAPI,
    settings: Settings,
    *,
    same_origin: bool = True,
    raise_server_exceptions: bool = True,
) -> TestClient:
    """A TestClient that talks to the app the way the shell does, so AD-16 lets it through.

    It sends an allowed Host (TestClient's default, `testserver`, is foreign) and, unless
    `same_origin` is off, the same-origin `Origin` a browser puts on every non-GET request.
    """
    return TestClient(
        app,
        base_url=local_url(settings),
        headers={"origin": local_url(settings)} if same_origin else None,
        raise_server_exceptions=raise_server_exceptions,
    )


def tailscale_status_text() -> str:
    """`tailscale status --json` stdout, as the discovery runner returns it."""
    return TAILSCALE_STATUS.read_text(encoding="utf-8")


def tailscale_status(**overrides: object) -> str:
    """The recorded status JSON with top-level keys replaced, e.g. `BackendState="Stopped"`."""
    return json.dumps({**json.loads(tailscale_status_text()), **overrides})


def serve_headers() -> dict[str, str]:
    """The headers Tailscale Serve forwarded for a tailnet browser's POST."""
    return json.loads(TAILSCALE_SERVE_HEADERS.read_text(encoding="utf-8"))["headers"]

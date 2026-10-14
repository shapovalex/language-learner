"""Story 1.10: the Tailscale fixture recorder publishes nothing private (R-05).

`language-lab-record-fixtures` ships in the wheel, because the host machine runs wheels only,
and runs there during device acceptance. Its output replaces the synthetic fixtures in this
public repo, so the tailnet name, login, display name and addresses it receives must never
reach the file, while the header names and status keys, which are what the recording is for,
must.
"""

import json
import socket
import subprocess
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from language_lab.adapters import tailscale
from language_lab.app import create_app
from language_lab.tools.record_tailscale_fixtures import sanitise_headers
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import TAILNET_HOST, app_client, serve_headers, tailscale_status_text
from tests.support.probes import VALIDATE_ROUTE, add_probe_routes
from tests.support.recorder import run_recorder, run_recorder_status
from tests.support.release import non_loopback_address

REAL_HOST = "oleksiis-mac-mini.tail9f3e2.ts.net"
REAL_LOGIN = "someone@gmail.com"
REAL_NAME = "Some One"
REAL_PEER_IP = "100.97.12.34"
REAL_SELF_IPV6 = "fd7a:115c:a1e0::9a01:c22"
SESSION = "sessionid=4f1c9e"
PRIVATE = [
    "oleksiis-mac-mini",
    "tail9f3e2",
    REAL_LOGIN,
    REAL_NAME,
    REAL_PEER_IP,
    REAL_SELF_IPV6,
    "4f1c9e",
    "Macintosh",
]

# What Tailscale Serve forwards for a tailnet browser's POST, with values that must not leak
FORWARDED = {
    "Host": REAL_HOST,
    "X-Forwarded-Host": REAL_HOST,
    "X-Forwarded-Proto": "https",
    "X-Forwarded-For": REAL_PEER_IP,
    "Origin": f"https://{REAL_HOST}",
    "Referer": f"https://{REAL_HOST}/",
    "Sec-Fetch-Site": "same-origin",
    "Content-Type": "application/json",
    "Tailscale-User-Login": REAL_LOGIN,
    "Tailscale-User-Name": REAL_NAME,
    "Tailscale-User-Profile-Pic": "https://lh3.googleusercontent.com/a/4f1c9e",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/129.0.0.0",
    "Cookie": SESSION,
}

WRITE_PATH = VALIDATE_ROUTE.format(item_id=1)
WRITE_BODY = {"word": "bonjour", "count": 1}


def _real_status() -> str:
    """The status fixture as a real machine would print it, private values included."""
    status = json.loads(tailscale_status_text())
    status["Self"] |= {
        "HostName": "oleksiis-mac-mini",
        "DNSName": f"{REAL_HOST}.",
        "TailscaleIPs": [REAL_PEER_IP, REAL_SELF_IPV6],
        "CurAddr": "192.168.1.20:41641",
    }
    status["TailscaleIPs"] = [REAL_PEER_IP, REAL_SELF_IPV6]
    status["MagicDNSSuffix"] = "tail9f3e2.ts.net"
    status["CurrentTailnet"] |= {"Name": REAL_LOGIN, "MagicDNSSuffix": "tail9f3e2.ts.net"}
    status["CertDomains"] = [REAL_HOST]
    status["Peer"] = {
        "nodekey:abc": {"HostName": "Some One's iPhone", "DNSName": "iphone.tail9f3e2.ts.net."}
    }
    status["User"] = {"42": {"ID": 42, "LoginName": REAL_LOGIN, "DisplayName": REAL_NAME}}
    return json.dumps(status)


def _assert_nothing_private(text: str) -> None:
    assert [value for value in PRIVATE if value in text] == []


@pytest.mark.p1
def test_sanitised_headers_keep_every_name_and_no_private_value() -> None:
    clean = sanitise_headers(FORWARDED)

    assert set(clean) == {name.lower() for name in FORWARDED}
    _assert_nothing_private(json.dumps(clean))
    assert clean["host"] == clean["x-forwarded-host"] == TAILNET_HOST
    assert clean["origin"] == f"https://{TAILNET_HOST}"
    assert clean["sec-fetch-site"] == "same-origin"


@pytest.mark.p1
def test_recorded_post_passes_the_allow_list(
    tmp_path: Path, settings_factory: SettingsFactory
) -> None:
    """The file `serve` writes is the fixture the allow-list tests replay."""
    out = tmp_path / "tailscale-serve-headers.json"
    with run_recorder(out) as recorder:
        page = httpx.get(recorder.url)
        reply = httpx.post(f"{recorder.url}/api/_echo", headers=FORWARDED, json={})

    assert "isSecureContext" in page.text
    assert reply.json()["recorded"] is True
    text = out.read_text(encoding="utf-8")
    _assert_nothing_private(text)
    assert json.loads(text)["upstream"] == f"http://127.0.0.1:{recorder.port}"

    settings = settings_factory(public_host=TAILNET_HOST)
    app = add_probe_routes(create_app(settings))
    client: TestClient = app_client(app, settings, same_origin=False)
    recorded = serve_headers(out)
    assert client.get("/api/health", headers=recorded).status_code == 200
    assert client.post(WRITE_PATH, json=WRITE_BODY, headers=recorded).status_code == 200


@pytest.mark.p2
def test_recorder_is_not_reachable_from_the_network(tmp_path: Path) -> None:
    """It stands in for the app, so it binds loopback only, as the app does (NFR-5)."""
    address = non_loopback_address()
    if address is None:
        pytest.skip("this machine has only a loopback interface")
    with run_recorder(tmp_path / "headers.json") as recorder:
        with pytest.raises(OSError):
            socket.create_connection((address, recorder.port), timeout=2).close()


@pytest.mark.p1
def test_sanitised_status_keeps_its_shape_and_passes_discovery() -> None:
    real = _real_status()

    run = run_recorder_status(real)

    assert run.returncode == 0, run.stderr
    _assert_nothing_private(run.stdout)
    clean = json.loads(run.stdout)
    assert clean.keys() == json.loads(real).keys()
    assert clean["Self"].keys() == json.loads(real)["Self"].keys()
    assert clean["BackendState"] == "Running"
    assert clean["Self"]["DNSName"] == f"{TAILNET_HOST}."

    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["tailscale", "status", "--json"], 0, run.stdout, "")

    assert tailscale.discover_tailnet_host(run=runner) == TAILNET_HOST


@pytest.mark.p2
@pytest.mark.parametrize("stdin", ["", "not json", "[]"], ids=["empty", "not-json", "not-object"])
def test_status_rejects_input_that_is_not_a_status(stdin: str) -> None:
    run = run_recorder_status(stdin)

    assert run.returncode == 1
    assert run.stdout == ""
    assert "tailscale status --json" in run.stderr

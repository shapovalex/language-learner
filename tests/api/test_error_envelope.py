"""Story 1.3: every /api failure returns the AD-15 envelope, without echoing input."""

import pytest
from fastapi.testclient import TestClient

from tests.support.probes import PROBE_PREFIX, error_envelope, sentinel

ENVELOPE_KEYS = {"code", "message", "requestId", "details"}


@pytest.mark.p0
@pytest.mark.parametrize(
    ("method", "path", "json", "status", "code"),
    [
        (
            "POST",
            f"{PROBE_PREFIX}/validate/not-a-number",
            {"word": "chat"},
            422,
            "validation_failed",
        ),
        ("GET", "/api/no-such-route", None, 404, "not_found"),
        ("GET", f"{PROBE_PREFIX}/boom/42", None, 500, "internal_error"),
    ],
    ids=["validation", "unknown-route", "unhandled"],
)
def test_api_failure_returns_envelope(
    probe_client: TestClient, method: str, path: str, json: dict | None, status: int, code: str
) -> None:
    """AC-2: a validation error, an unknown /api path and a raised exception get the envelope."""
    response = probe_client.request(method, path, json=json)

    envelope = error_envelope(response)
    assert envelope.get("code") == code
    assert response.status_code == status
    assert set(response.json()) == {"error"}
    assert set(envelope) <= ENVELOPE_KEYS
    assert isinstance(envelope["message"], str) and envelope["message"]
    assert isinstance(envelope["requestId"], str) and envelope["requestId"]


@pytest.mark.p0
def test_validation_envelope_does_not_echo_input(probe_client: TestClient) -> None:
    """AC-3: the envelope never echoes input values (R-02)."""
    secret = sentinel()

    response = probe_client.post(
        f"{PROBE_PREFIX}/validate/{secret}",
        params={"limit": secret},
        json={"word": secret, "count": secret},
        headers={"X-Probe": secret},
    )

    assert secret not in response.text
    assert error_envelope(response).get("code") == "validation_failed"


@pytest.mark.p0
@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/api/no-such-route/{secret}", 404, "not_found"),
        (f"{PROBE_PREFIX}/boom/{{secret}}", 500, "internal_error"),
    ],
    ids=["unknown-route", "unhandled"],
)
def test_failure_envelope_does_not_echo_input(
    probe_client: TestClient, path: str, status: int, code: str
) -> None:
    """AC-3: the unknown-route and crash envelopes carry no path, query or exception text."""
    secret = sentinel()

    response = probe_client.get(path.format(secret=secret), params={"q": secret})

    assert secret not in response.text
    assert "probe failure" not in response.text
    assert (response.status_code, error_envelope(response).get("code")) == (status, code)


@pytest.mark.p0
def test_malformed_json_gives_validation_failed_without_echo(probe_client: TestClient) -> None:
    """AC-3: a body that isn't JSON is a validation failure, and the body isn't echoed."""
    secret = sentinel()

    response = probe_client.post(
        f"{PROBE_PREFIX}/validate/1",
        content=b"{" + secret.encode(),
        headers={"Content-Type": "application/json"},
    )

    assert error_envelope(response).get("code") == "validation_failed"
    assert response.status_code == 422
    assert secret not in response.text


@pytest.mark.p1
def test_wrong_method_gets_envelope(probe_client: TestClient) -> None:
    """AC-2: a 405 from the router is an envelope too, with the Allow header kept."""
    response = probe_client.post("/api/health")

    assert error_envelope(response).get("code") == "not_found"
    assert response.status_code == 405
    assert set(response.json()) == {"error"}
    assert "GET" in response.headers.get("allow", "")


@pytest.mark.p2
def test_missing_static_file_stays_a_plain_404(probe_client: TestClient) -> None:
    """R-07: outside /api the envelope doesn't apply, and /static/... never serves the shell."""
    from language_lab import __version__

    response = probe_client.get(f"/static/{__version__}/missing.js")

    assert response.status_code == 404
    assert error_envelope(response) == {}
    assert "<html" not in response.text

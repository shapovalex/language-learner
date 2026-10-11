"""Story 1.3: every /api failure returns the AD-15 envelope, without echoing input.

Skipped until the exception handlers land. Un-skip one per task, watch it fail, then implement.
"""

import pytest
from fastapi.testclient import TestClient

from tests.support.probes import PROBE_PREFIX, error_envelope, sentinel

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 1.3: un-skip with the envelope handlers")

ENVELOPE_KEYS = {"code", "message", "requestId", "details"}


@RED_PHASE
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


@RED_PHASE
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

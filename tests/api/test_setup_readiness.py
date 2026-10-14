"""Story 2.1: GET /api/setup/readiness reports each check on its own (FR-5).

Decided 2026-10-14: the body is {"prefix", "checks": [{"id", "ok"}]}, with the checks in tile
order (ankiConnect, azure, openrouter), and the Setup screen owns the copy. Azure counts as
configured only when both its key and its region are set. Keys are checked as configured, with
no live call (epic decision 2026-10-08).

`create_app(settings, anki_store=...)` takes the AnkiStore, so these tests pass the in-memory
fake from tests/fakes/ and never reach Anki.
"""

import uuid

import pytest

from language_lab.app import create_app
from language_lab.domain.errors import MESSAGES, ErrorCode
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client
from tests.support.live_server import closed_port

READINESS = "/api/setup/readiness"


def configured_keys() -> dict[str, str]:
    """Every key the readiness checks look at, set. Unique per call; never sent anywhere."""
    return {
        "azure_speech_key": f"az-{uuid.uuid4().hex}",
        "azure_speech_region": "canadacentral",
        "openrouter_api_key": f"sk-or-v1-{uuid.uuid4().hex}",
    }


def checks(*, anki: bool = True, azure: bool = True, openrouter: bool = True) -> list:
    """The expected `(id, ok)` pairs, in tile order."""
    return [("ankiConnect", anki), ("azure", azure), ("openrouter", openrouter)]


@pytest.mark.p0
@pytest.mark.parametrize(
    ("anki_available", "unset", "expected"),
    [
        (True, {}, checks()),
        (False, {}, checks(anki=False)),
        (True, {"azure_speech_key": ""}, checks(azure=False)),
        (True, {"azure_speech_region": ""}, checks(azure=False)),
        (True, {"openrouter_api_key": ""}, checks(openrouter=False)),
    ],
    ids=["all-pass", "anki-closed", "azure-key-unset", "azure-region-unset", "openrouter-unset"],
)
def test_readiness_reports_each_check_on_its_own(
    settings_factory: SettingsFactory,
    anki_available: bool,
    unset: dict[str, str],
    expected: list,
) -> None:
    """AC-5: one failing dependency fails its own check only, and the Prefix is reported."""
    prefix = f"Ll{uuid.uuid4().hex}"
    settings = settings_factory(anki_prefix=prefix, **(configured_keys() | unset))
    app = create_app(settings, anki_store=FakeAnkiStore(available=anki_available))

    response = app_client(app, settings).get(READINESS)

    assert response.status_code == 200
    body = response.json()
    assert [(check["id"], check["ok"]) for check in body["checks"]] == expected
    assert body["prefix"] == prefix


@pytest.mark.p1
def test_readiness_while_anki_is_busy_is_the_503_anki_busy_envelope(
    settings_factory: SettingsFactory,
) -> None:
    """AC-5: when the Anki lock wait runs out, readiness is the AD-15 `anki_busy` envelope."""
    settings = settings_factory(**configured_keys())
    app = create_app(settings, anki_store=FakeAnkiStore(busy=True))

    response = app_client(app, settings).get(READINESS)

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "anki_busy"
    assert error["message"] == MESSAGES[ErrorCode.ANKI_BUSY]
    assert error["requestId"]


@pytest.mark.p1
def test_readiness_never_shows_a_key_in_its_body_or_log(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """AC-5: keys are checked as configured; their values reach neither the body nor the log."""
    keys = configured_keys()
    settings = settings_factory(**keys)
    app = create_app(settings, anki_store=FakeAnkiStore())

    response = app_client(app, settings).get(READINESS)

    assert response.status_code == 200
    for name in ("azure_speech_key", "openrouter_api_key"):
        assert keys[name] not in response.text
        assert keys[name] not in log_capture.all_text
    [line] = log_capture.request_lines
    assert (line["route"], line["status"]) == (READINESS, 200)


@pytest.mark.p1
def test_default_wiring_reports_anki_not_reachable_when_nothing_listens(
    settings_factory: SettingsFactory,
) -> None:
    """AC-5: without injection, the real adapter on a closed loopback port reports false."""
    port = closed_port()
    settings = settings_factory(anki_connect_url=f"http://127.0.0.1:{port}", **configured_keys())
    with app_client(create_app(settings), settings) as client:  # runs the lifespan
        response = client.get(READINESS)

    assert response.status_code == 200
    assert [(c["id"], c["ok"]) for c in response.json()["checks"]] == checks(anki=False)

"""Story 2.1: GET /api/setup/readiness reports each check on its own (FR-5).

Decided 2026-10-14: the body is {"prefix", "checks": [{"id", "ok"}]}, with the checks in tile
order (ankiConnect, azure, openrouter), and the Setup screen owns the copy. Azure counts as
configured only when both its key and its region are set. Keys are checked as configured, with
no live call (epic decision 2026-10-08).

`create_app(settings, anki_store=...)` takes the AnkiStore, so these tests pass the in-memory
fake from tests/fakes/ and never reach Anki.

Skipped until features/setup exists. Un-skip it, watch it fail, then implement.
"""

import uuid

import pytest

from language_lab.app import create_app
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.1: un-skip with features/setup and FakeAnkiStore"
)

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


@RED_PHASE
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
    from tests.fakes.anki_store import FakeAnkiStore

    prefix = f"Ll{uuid.uuid4().hex}"
    settings = settings_factory(anki_prefix=prefix, **(configured_keys() | unset))
    app = create_app(settings, anki_store=FakeAnkiStore(available=anki_available))

    response = app_client(app, settings).get(READINESS)

    assert response.status_code == 200
    body = response.json()
    assert [(check["id"], check["ok"]) for check in body["checks"]] == expected
    assert body["prefix"] == prefix

"""Story 3.3: DELETE /api/captures/{captureId} (FR-13, AD-15, Consistency Conventions).

- **Delete.** 204 with no body, and the Capture is gone from Anki.
- **Already gone (decided 2026-10-21).** A CaptureId that no Capture holds is 204 too, so a
  retried delete succeeds.

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/, whose `captures`
holds each Capture by CaptureId. The adapter itself is in
tests/integration/test_anki_capture_delete.py.
"""

import uuid
from datetime import UTC, datetime

import pytest

from language_lab.app import create_app
from language_lab.domain.captures import Capture
from language_lab.domain.errors import AppError, ErrorCode
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client, client_over
from tests.support.live_server import closed_port

CAPTURES = "/api/captures"

TARGET = Capture(
    str(uuid.uuid4()),
    "I'd rather not jump to conclusions.",
    datetime(2026, 10, 22, 21, 14, 5, tzinfo=UTC),
)
OTHER = Capture(
    str(uuid.uuid4()), "Il fait un temps de chien.", datetime(2026, 10, 22, 8, 2, tzinfo=UTC)
)


def store_with(*captures: Capture) -> FakeAnkiStore:
    store = FakeAnkiStore()
    for capture in captures:
        store.captures[capture.capture_id] = capture
    return store


@pytest.mark.p0
def test_delete_removes_the_capture_and_answers_204(settings_factory: SettingsFactory) -> None:
    """AC-4: DELETE /api/captures/{captureId} is 204 with no body; that Capture is gone and the
    others stay.
    """
    store = store_with(TARGET, OTHER)
    client = client_over(settings_factory, store)

    response = client.delete(f"{CAPTURES}/{TARGET.capture_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert list(store.captures) == [OTHER.capture_id]


@pytest.mark.p0
def test_a_retried_delete_of_a_capture_already_gone_is_204(
    settings_factory: SettingsFactory,
) -> None:
    """AC-5: DELETE for a CaptureId no Capture holds (one already deleted) is 204 as well."""
    store = store_with(OTHER)
    client = client_over(settings_factory, store)

    response = client.delete(f"{CAPTURES}/{TARGET.capture_id}")

    assert response.status_code == 204
    assert list(store.captures) == [OTHER.capture_id]


# Secondary cases (green phase)


@pytest.mark.p1
def test_an_unreachable_anki_is_503_and_keeps_the_capture(
    settings_factory: SettingsFactory,
) -> None:
    """AC-4: with Anki unreachable DELETE is 503 `anki_unavailable`."""
    store = store_with(TARGET)
    store.available = False
    client = client_over(settings_factory, store)

    response = client.delete(f"{CAPTURES}/{TARGET.capture_id}")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "anki_unavailable"
    assert list(store.captures) == [TARGET.capture_id]


@pytest.mark.p1
def test_a_malformed_capture_id_is_404_and_never_reaches_the_store(
    settings_factory: SettingsFactory,
) -> None:
    """AC-5: `capture-1` names no Capture and was never one, so it is 404 `not_found` before
    the store is asked (an unreachable store would answer 503).
    """
    store = store_with(TARGET)
    store.available = False
    client = client_over(settings_factory, store)

    response = client.delete(f"{CAPTURES}/capture-1")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.p1
def test_the_app_built_without_an_injected_store_has_the_delete_route(
    settings_factory: SettingsFactory,
) -> None:
    """AC-4: `create_app(settings)` wires DELETE over the AnkiConnect store: with no Anki
    listening, it reaches the store and is 503 `anki_unavailable`.
    """
    settings = settings_factory(env={"ANKI_CONNECT_URL": f"http://127.0.0.1:{closed_port()}"})
    client = app_client(create_app(settings), settings)

    response = client.delete(f"{CAPTURES}/{TARGET.capture_id}")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "anki_unavailable"


@pytest.mark.p1
def test_a_deleted_capture_reads_as_not_found(settings_factory: SettingsFactory) -> None:
    """AC-4: after DELETE, GET of that Capture is 404 `not_found` and the list leaves it out."""
    store = store_with(TARGET, OTHER)
    client = client_over(settings_factory, store)
    client.delete(f"{CAPTURES}/{TARGET.capture_id}")

    response = client.get(f"{CAPTURES}/{TARGET.capture_id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    listed = client.get(CAPTURES).json()["captures"]
    assert [c["captureId"] for c in listed] == [OTHER.capture_id]


@pytest.mark.p1
def test_a_gated_anki_is_409_setup_required(
    settings_factory: SettingsFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-4: a store refusing the delete while Setup isn't ready is 409 `setup_required`
    (AD-19).
    """
    store = store_with(TARGET)

    async def gated(*_: object) -> None:
        raise AppError(ErrorCode.SETUP_REQUIRED)

    monkeypatch.setattr(store, "delete_capture", gated)
    client = client_over(settings_factory, store)

    response = client.delete(f"{CAPTURES}/{TARGET.capture_id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "setup_required"
    assert list(store.captures) == [TARGET.capture_id]

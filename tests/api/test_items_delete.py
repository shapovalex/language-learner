"""Story 5.3 HTTP contract; the real adapter is injected over a replay collection.

DELETE /api/items/{lang}/{itemId} returns 204 with an empty body after cleanup.
"""

import pytest

from tests.support.anki_state import managed_collection
from tests.support.captures import MANIFEST
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over
from tests.support.item_delete import media_names, put_item, wired_delete


@pytest.mark.p0
def test_delete_item_answers_204_and_subsequent_reads_leave_it_out(
    settings_factory: SettingsFactory,
) -> None:
    """[P0] AC-12 DELETE answers 204, then detail is absent and the list keeps other Items."""
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    other_id, other_note = put_item(collection)
    store, _ = wired_delete(collection)
    client = client_over(settings_factory, store)

    response = client.delete(f"/api/items/en/{item_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert note_id not in collection.notes
    assert other_note in collection.notes
    gone = client.get(f"/api/items/en/{item_id}")
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "not_found"
    listed = client.get("/api/items/en").json()["items"]
    assert [row["itemId"] for row in listed] == [other_id]


@pytest.mark.parametrize("item_id", ["not-an-id", "00000000-0000-1000-8000-000000000000"])
def test_malformed_id_is_not_found_before_anki_is_called(settings_factory, item_id) -> None:
    collection = managed_collection(MANIFEST)
    store, replay = wired_delete(collection)
    response = client_over(settings_factory, store).delete(f"/api/items/en/{item_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert replay.sent == []


def test_unknown_language_is_422_without_anki_calls(settings_factory) -> None:
    import uuid

    store, replay = wired_delete(managed_collection(MANIFEST))
    response = client_over(settings_factory, store).delete(f"/api/items/de/{uuid.uuid4()}")
    assert response.status_code == 422
    assert replay.sent == []


@pytest.mark.parametrize(
    ("state", "replies", "status", "code"),
    [
        ("needs_migration", None, 409, "setup_required"),
        (
            "ready",
            {"deleteNotes": {"result": None, "error": "secret upstream content"}},
            503,
            "anki_unavailable",
        ),
    ],
)
def test_delete_uses_the_existing_safe_error_envelope(
    settings_factory, state, replies, status, code
) -> None:
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    store, _ = wired_delete(collection, state=state, replies=replies)
    response = client_over(settings_factory, store).delete(f"/api/items/en/{item_id}")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "requestId" in response.json()["error"]
    assert "secret upstream content" not in response.text
    assert note_id in collection.notes


def test_french_delete_and_repeated_delete_are_empty_204(settings_factory) -> None:
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection, language="fr")
    collection.media.update(media_names(item_id))
    store, _ = wired_delete(collection)
    client = client_over(settings_factory, store)
    assert client.delete(f"/api/items/en/{item_id}").status_code == 204
    assert note_id in collection.notes
    assert collection.media == set(media_names(item_id))
    for _ in range(2):
        response = client.delete(f"/api/items/fr/{item_id}")
        assert (response.status_code, response.content) == (204, b"")
    assert note_id not in collection.notes
    assert collection.media == set()

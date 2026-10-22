"""Story 4.1: POST /api/items/<lang>, Save with the `keep` audio intent (AD-6, AD-8, AD-11,
AD-15, AD-20, Consistency Conventions).

- **The request.** `multipart/form-data` with an `item` JSON part: `ItemContent` (camelCase,
  discriminated by `category`) plus `itemId` and `audio` (Consistency Conventions, Binary
  payloads). The Language is the path segment, `en` or `fr`. Only `audio: "keep"` is built here;
  epic-reference-audio adds `replace` and `remove` with the `audioFile` part.
- **The answer.** 200 `{itemId}` (a default this story takes), for a new Item and for a retry
  with the same ItemId alike: Save is create-or-update by ItemId (AD-20).
- **Refused.** An alternative with a comma (AD-10), a blank Target or Russian meaning, an
  unknown category, an `itemId` that isn't a lowercase canonical UUIDv4, and a missing or
  malformed `item` part are 422 `validation_failed`, and the AnkiStore is never called.

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/. Its `items` holds
each saved Item by ItemId as `(Language, ItemContent)`, create-or-update like the adapter's.
The adapter itself is in tests/integration/test_anki_item_save.py.
"""

import json
import uuid
from typing import Any

import pytest

from language_lab.app import create_app
from language_lab.domain.catalog import Language
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client, client_over
from tests.support.items import SENTENCE, VOCABULARY, content
from tests.support.live_server import closed_port


def items_path(language: str) -> str:
    return f"/api/items/{language}"


def item_part(wire: dict[str, Any], item_id: str, audio: str = "keep") -> dict[str, Any]:
    """The multipart `item` part of a Save: `wire` plus `itemId` and `audio`."""
    payload = {**wire, "itemId": item_id, "audio": audio}
    return {"item": (None, json.dumps(payload), "application/json")}


SAVES = {
    "en-vocabulary": ("en", VOCABULARY),
    "fr-sentence": ("fr", SENTENCE),
}


@pytest.mark.p0
@pytest.mark.parametrize(("language", "wire"), SAVES.values(), ids=SAVES.keys())
def test_save_stores_the_item_under_its_item_id(
    settings_factory: SettingsFactory, language: str, wire: dict[str, Any]
) -> None:
    """AC-10: POST /api/items/<lang> with the `item` part is 200 `{itemId}`, and the Item is
    saved under that ItemId with its Language and content.
    """
    store = FakeAnkiStore()
    client = client_over(settings_factory, store)
    item_id = str(uuid.uuid4())

    response = client.post(items_path(language), files=item_part(wire, item_id))

    assert response.status_code == 200
    assert response.json() == {"itemId": item_id}
    assert store.items[item_id] == (Language(language), content(wire))


def _part(**changes: Any) -> dict[str, Any]:
    return item_part({**VOCABULARY, **changes}, str(uuid.uuid4()))


INVALID: dict[str, dict[str, Any]] = {
    "comma-in-an-alternative": _part(russianAlternatives=["торопиться, спешить"]),
    "blank-target": _part(target="  "),
    "blank-russian": _part(russian=""),
    "unknown-category": _part(category="idiom"),
    "uppercase-item-id": item_part(VOCABULARY, str(uuid.uuid4()).upper()),
    "item-id-not-a-uuid": item_part(VOCABULARY, "item-1"),
    "item-id-uuid-version-1": item_part(VOCABULARY, str(uuid.uuid1())),
    "item-part-not-json": {"item": (None, "{not json", "application/json")},
    "no-item-part": {"other": (None, "x", "text/plain")},
}


@pytest.mark.p0
@pytest.mark.parametrize("files", INVALID.values(), ids=INVALID.keys())
def test_an_invalid_item_is_validation_failed_and_nothing_is_saved(
    settings_factory: SettingsFactory, files: dict[str, Any]
) -> None:
    """AC-11: a comma in an alternative, a blank Target or Russian meaning, an unknown
    category, a non-canonical `itemId`, or a missing or malformed `item` part is 422
    `validation_failed`, and nothing is saved.
    """
    store = FakeAnkiStore()
    client = client_over(settings_factory, store)

    response = client.post(items_path("en"), files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert store.items == {}


@pytest.mark.p1
def test_a_json_body_instead_of_multipart_is_validation_failed(
    settings_factory: SettingsFactory,
) -> None:
    """AC-11: Save takes `multipart/form-data` only; a JSON body is 422 `validation_failed`."""
    store = FakeAnkiStore()
    client = client_over(settings_factory, store)
    payload = {**VOCABULARY, "itemId": str(uuid.uuid4()), "audio": "keep"}

    response = client.post(items_path("en"), json=payload)

    assert response.status_code == 422
    assert store.items == {}


@pytest.mark.p1
def test_a_retried_save_with_the_same_item_id_replaces_the_content(
    settings_factory: SettingsFactory,
) -> None:
    """AC-10: a Save retried with the same ItemId and edited content is 200, and the one Item
    under that ItemId holds the edit (AD-20).
    """
    store = FakeAnkiStore()
    client = client_over(settings_factory, store)
    item_id = str(uuid.uuid4())
    client.post(items_path("en"), files=item_part(VOCABULARY, item_id))
    edited = {**VOCABULARY, "russian": "поспешить с выводами"}

    response = client.post(items_path("en"), files=item_part(edited, item_id))

    assert response.status_code == 200
    assert list(store.items) == [item_id]
    assert store.items[item_id] == (Language.EN, content(edited))


@pytest.mark.p1
def test_the_app_built_without_an_injected_store_has_the_route(
    settings_factory: SettingsFactory,
) -> None:
    """AC-10: `create_app(settings)` wires Save over the AnkiConnect store: with no Anki
    listening, a valid Save reaches the store and is 503 `anki_unavailable`.
    """
    settings = settings_factory(env={"ANKI_CONNECT_URL": f"http://127.0.0.1:{closed_port()}"})
    client = app_client(create_app(settings), settings)

    response = client.post(items_path("en"), files=item_part(VOCABULARY, str(uuid.uuid4())))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "anki_unavailable"


@pytest.mark.p1
def test_an_unreachable_anki_is_503_anki_unavailable(settings_factory: SettingsFactory) -> None:
    """AC-10: an Anki that doesn't answer is 503 `anki_unavailable`, and nothing is saved."""
    store = FakeAnkiStore(available=False)
    client = client_over(settings_factory, store)

    response = client.post(items_path("en"), files=item_part(VOCABULARY, str(uuid.uuid4())))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "anki_unavailable"
    assert store.items == {}

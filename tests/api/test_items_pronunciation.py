"""Excluding an Item from Pronunciation over HTTP (AD-13, AD-15).

PUT /api/items/<lang>/<itemId>/pronunciation with the strict body `{excluded: bool}` is 204:
`true` suspends the Item's Pronounce Card in Anki, `false` unsuspends it, and a flag that already
matches writes nothing. An ItemId that isn't a UUIDv4, or that no Item of the Language holds, is
404 `not_found`; a body that isn't exactly `{excluded: <bool>}` is 422 `validation_failed`.
GET /api/items/<lang>/<itemId> carries the flag as `pronunciationExcluded`.

Most tests pass the fake from tests/fakes/; the first runs the real adapter over the in-memory
collection, so the HTTP surface and the Anki write are seen together.
"""

import uuid
from typing import Any

import pytest

from language_lab.domain.catalog import Category, Language
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.anki_state import managed_collection, sent_writes
from tests.support.captures import MANIFEST
from tests.support.duplicates import store_with_items, vocabulary
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over
from tests.support.pronunciation import ReviewRig, due


def flag_path(language: str, item_id: str) -> str:
    return f"/api/items/{language}/{item_id}/pronunciation"


@pytest.mark.p0
def test_exclude_then_include_through_the_adapter_flips_only_the_pronounce_card(
    settings_factory: SettingsFactory,
) -> None:
    rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
    card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))
    client = client_over(settings_factory, rig.store)

    excluded = client.put(flag_path("en", card.item_id), json={"excluded": True})
    read_excluded = client.get(f"/api/items/en/{card.item_id}").json()
    queue = client.get("/api/pronunciation/en/queue").json()
    included = client.put(flag_path("en", card.item_id), json={"excluded": False})
    read_included = client.get(f"/api/items/en/{card.item_id}").json()

    assert (excluded.status_code, excluded.content) == (204, b"")
    assert (included.status_code, included.content) == (204, b"")
    assert read_excluded["pronunciationExcluded"] is True
    assert queue["cards"] == []
    assert read_included["pronunciationExcluded"] is False
    assert sent_writes(rig.replay.sent) == ["suspend", "unsuspend"]
    study = [c for c in rig.collection.cards.values() if c.note == card.note_id and c.ord != 3]
    assert [c.suspended for c in study] == [False, False, False]


@pytest.mark.p0
@pytest.mark.parametrize("excluded", [True, False])
def test_the_flag_is_written_and_read_back(
    settings_factory: SettingsFactory, excluded: bool
) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "fr", vocabulary()))
    store.excluded = set() if excluded else {item_id}
    client = client_over(settings_factory, store)

    response = client.put(flag_path("fr", item_id), json={"excluded": excluded})

    assert response.status_code == 204
    assert store.exclusions == [(item_id, excluded)]
    read = client.get(f"/api/items/fr/{item_id}").json()
    assert read["pronunciationExcluded"] is excluded


@pytest.mark.p0
def test_a_flag_that_already_matches_is_204_and_writes_nothing(
    settings_factory: SettingsFactory,
) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "en", vocabulary()))
    client = client_over(settings_factory, store)

    response = client.put(flag_path("en", item_id), json={"excluded": False})

    assert response.status_code == 204
    assert store.exclusions == []


NOT_FOUND = {
    "absent": lambda french: str(uuid.uuid4()),
    "in-the-other-language": lambda french: french,
    "not-a-uuid": lambda french: "item-1",
    "not-a-uuid4": lambda french: "00000000-0000-1000-8000-000000000000",
}


@pytest.mark.p0
@pytest.mark.parametrize("asked", NOT_FOUND.values(), ids=NOT_FOUND.keys())
def test_an_item_id_no_item_of_the_language_holds_is_not_found(
    settings_factory: SettingsFactory, asked: Any
) -> None:
    french = str(uuid.uuid4())
    store = store_with_items((french, "fr", vocabulary()))
    client = client_over(settings_factory, store)

    response = client.put(flag_path("en", asked(french)), json={"excluded": True})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert store.exclusions == []


BAD_BODIES = {
    "missing": {},
    "string": {"excluded": "true"},
    "number": {"excluded": 1},
    "null": {"excluded": None},
    "extra-key": {"excluded": True, "cardId": 5},
}


@pytest.mark.p0
@pytest.mark.parametrize("body", BAD_BODIES.values(), ids=BAD_BODIES.keys())
def test_a_body_that_isnt_exactly_the_flag_is_validation_failed(
    settings_factory: SettingsFactory, body: dict[str, Any]
) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "en", vocabulary()))
    client = client_over(settings_factory, store)

    response = client.put(flag_path("en", item_id), json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert store.exclusions == []


@pytest.mark.p1
@pytest.mark.parametrize(
    ("store", "status", "code"),
    [
        (FakeAnkiStore(available=False), 503, "anki_unavailable"),
        (FakeAnkiStore(busy=True), 503, "anki_busy"),
    ],
    ids=["anki-down", "anki-busy"],
)
def test_anki_down_or_busy_is_its_error(
    settings_factory: SettingsFactory, store: FakeAnkiStore, status: int, code: str
) -> None:
    item_id = str(uuid.uuid4())
    store.items[item_id] = store_with_items((item_id, "en", vocabulary())).items[item_id]
    client = client_over(settings_factory, store)

    response = client.put(flag_path("en", item_id), json={"excluded": True})

    assert response.json()["error"]["code"] == code
    assert response.status_code == status

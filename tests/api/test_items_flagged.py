"""Flagged Items over HTTP (AD-4, AD-13, AD-15).

GET /api/items/<lang> gives every row `flagged: bool` (any of its cards carries an Anki flag);
`?flagged=true` keeps only the flagged ones, combined with `q`, and `flagged=false` or no
`flagged` lists them all. Any other value is 422 `validation_failed` before Anki is read.
GET /api/items/<lang>/<itemId> carries `flagged` too. DELETE /api/items/<lang>/<itemId>/flag
clears the flag of every flagged card of the Item in Anki and is 204, writing nothing when none
is flagged; an ItemId that isn't a UUIDv4, or that no Item of the Language holds, is 404
`not_found`.

Most tests pass the fake from tests/fakes/; the first runs the real adapter over the in-memory
collection, so the HTTP surface and the Anki reads and writes are seen together.
"""

import uuid

import pytest

from language_lab.domain.catalog import Category, Language
from tests.support.anki_state import flag_card, managed_collection, sent_writes
from tests.support.captures import MANIFEST
from tests.support.duplicates import sentence, store_with_items, vocabulary
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over
from tests.support.pronunciation import ReviewRig, due


def flag_path(language: str, item_id: str) -> str:
    return f"/api/items/{language}/{item_id}/flag"


@pytest.mark.p0
def test_flag_listed_read_and_cleared_through_the_adapter(
    settings_factory: SettingsFactory,
) -> None:
    rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
    flagged = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))
    plain = rig.pronounce(Language.EN, Category.SENTENCE, due(2))
    flag_card(rig.collection, flagged.note_id, 3, flags=3)  # only the Pronounce card
    client = client_over(settings_factory, rig.store)

    every = client.get("/api/items/en").json()["items"]
    only = client.get("/api/items/en", params={"flagged": "true"}).json()["items"]
    detail = client.get(f"/api/items/en/{flagged.item_id}").json()
    cleared = client.delete(flag_path("en", flagged.item_id))
    after = client.get("/api/items/en", params={"flagged": "true"}).json()["items"]

    assert {row["itemId"]: row["flagged"] for row in every} == {
        flagged.item_id: True,
        plain.item_id: False,
    }
    assert [row["itemId"] for row in only] == [flagged.item_id]
    assert detail["flagged"] is True
    assert (cleared.status_code, cleared.content) == (204, b"")
    assert after == []
    assert sent_writes(rig.replay.sent) == ["setSpecificValueOfCard"]
    assert {c.flags for c in rig.collection.cards.values()} == {0}


@pytest.mark.p0
@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({}, ["flagged-jump", "plain-jump", "flagged-other"]),
        ({"flagged": "false"}, ["flagged-jump", "plain-jump", "flagged-other"]),
        ({"flagged": "true"}, ["flagged-jump", "flagged-other"]),
        ({"flagged": "true", "q": "jump"}, ["flagged-jump"]),
        ({"flagged": "false", "q": "jump"}, ["flagged-jump", "plain-jump"]),
    ],
    ids=["none", "false", "true", "true-with-q", "false-with-q"],
)
def test_the_flagged_filter_combines_with_the_search(
    settings_factory: SettingsFactory, params: dict[str, str], expected: list[str]
) -> None:
    ids = {name: str(uuid.uuid4()) for name in ("flagged-jump", "plain-jump", "flagged-other")}
    store = store_with_items(
        (ids["flagged-jump"], "en", vocabulary("jump")),
        (ids["plain-jump"], "en", vocabulary("jump ahead")),
        (ids["flagged-other"], "en", sentence("Something else.")),
    )
    store.flagged = {ids["flagged-jump"], ids["flagged-other"]}
    client = client_over(settings_factory, store)

    response = client.get("/api/items/en", params=params)

    assert response.status_code == 200
    rows = response.json()["items"]
    assert [row["itemId"] for row in rows] == [ids[name] for name in expected]
    assert all(row["flagged"] is (row["itemId"] in store.flagged) for row in rows)


@pytest.mark.p1
def test_no_flagged_item_is_an_empty_list(settings_factory: SettingsFactory) -> None:
    store = store_with_items((str(uuid.uuid4()), "en", vocabulary()))
    client = client_over(settings_factory, store)

    response = client.get("/api/items/en", params={"flagged": "true"})

    assert response.status_code == 200
    assert response.json() == {"items": []}


@pytest.mark.p1
@pytest.mark.parametrize("value", ["maybe", "1", "True", ""])
def test_a_bad_flagged_value_is_validation_failed_before_any_read(
    settings_factory: SettingsFactory, value: str
) -> None:
    store = store_with_items((str(uuid.uuid4()), "en", vocabulary()))
    store.available = False  # a read would be anki_unavailable
    client = client_over(settings_factory, store)

    response = client.get("/api/items/en", params={"flagged": value})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


@pytest.mark.p0
def test_get_item_reports_the_flag(settings_factory: SettingsFactory) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "fr", vocabulary()))
    store.flagged = {item_id}
    client = client_over(settings_factory, store)

    assert client.get(f"/api/items/fr/{item_id}").json()["flagged"] is True


@pytest.mark.p0
def test_clear_is_204_and_unflags_the_item(settings_factory: SettingsFactory) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "en", vocabulary()))
    store.flagged = {item_id}
    client = client_over(settings_factory, store)

    response = client.delete(flag_path("en", item_id))

    assert (response.status_code, response.content) == (204, b"")
    assert store.cleared_flags == [item_id]
    assert client.get(f"/api/items/en/{item_id}").json()["flagged"] is False


@pytest.mark.p1
def test_clearing_an_unflagged_item_is_204_and_writes_nothing(
    settings_factory: SettingsFactory,
) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "en", vocabulary()))
    client = client_over(settings_factory, store)

    response = client.delete(flag_path("en", item_id))

    assert response.status_code == 204
    assert store.cleared_flags == []


@pytest.mark.p0
@pytest.mark.parametrize("which", ["absent", "other-language", "not-a-uuid"])
def test_clearing_an_item_the_language_doesnt_hold_is_not_found(
    settings_factory: SettingsFactory, which: str
) -> None:
    french = str(uuid.uuid4())
    store = store_with_items((french, "fr", vocabulary()))
    store.flagged = {french}
    client = client_over(settings_factory, store)
    item_id = {"absent": str(uuid.uuid4()), "other-language": french, "not-a-uuid": "item-1"}[which]

    response = client.delete(flag_path("en", item_id))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert store.cleared_flags == []
    assert store.flagged == {french}


@pytest.mark.p1
@pytest.mark.parametrize(
    ("arrange", "code", "status"),
    [("busy", "anki_busy", 503), ("available", "anki_unavailable", 503)],
    ids=["busy", "unavailable"],
)
def test_clearing_while_anki_cant_answer_is_its_error(
    settings_factory: SettingsFactory, arrange: str, code: str, status: int
) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "en", vocabulary()))
    store.flagged = {item_id}
    setattr(store, arrange, arrange == "busy")
    client = client_over(settings_factory, store)

    response = client.delete(flag_path("en", item_id))

    assert response.json()["error"]["code"] == code
    assert store.flagged == {item_id}


@pytest.mark.p0
def test_only_the_items_list_asks_for_flags_not_the_duplicate_check(
    settings_factory: SettingsFactory,
) -> None:
    item_id = str(uuid.uuid4())
    store = store_with_items((item_id, "en", vocabulary("jump")))
    store.flagged = {item_id}
    client = client_over(settings_factory, store)

    listed = client.get("/api/items/en")
    assert store.flag_reads and all(store.flag_reads)
    store.flag_reads.clear()
    checked = client.get(
        "/api/items/en/duplicates", params={"category": "vocabulary", "target": "jump"}
    )

    assert listed.status_code == checked.status_code == 200
    assert store.flag_reads and not any(store.flag_reads)

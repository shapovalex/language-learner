"""Story 5.1: read-only, Language-scoped Item search (FR-22, AD-4, AD-12).

Proposed list wire contract: GET /api/items/<lang>?q= returns
{items: [{itemId, ...ItemContent, hasAudio: bool}]}. Empty or missing q lists all
Items of that Language. hasAudio is list metadata, not an editable content field.

Activate only the current task's skip marker to observe RED before implementation.
The first four cases use the port fake; the last two drive the real Anki adapter
through HTTP over the recorded-shape collection replay, without contacting Anki.
"""

import copy
import uuid

import pytest

from language_lab.adapters.anki.query import note_query
from tests.support.anki_state import (
    apply_manifest,
    item_note,
    managed_collection,
    sent_queries,
    sent_writes,
)
from tests.support.captures import DEV_MANIFEST, MANIFEST, wired
from tests.support.duplicates import sentence, store_with_items, vocabulary
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over
from tests.support.items import note_type_of, stored_fields

pytestmark = pytest.mark.skip(reason="ATDD 5.1: Item search and list metadata are not implemented")


@pytest.mark.p0
def test_search_normalizes_target_substrings(settings_factory: SettingsFactory) -> None:
    """[P0] AC-1 Target search applies AD-12 and keeps diacritics significant."""
    # Given a substring needing every normalization rule and an unaccented near match.
    matched, unaccented, unrelated = (str(uuid.uuid4()) for _ in range(3))
    target = "Please café don’t   jump to conclusions."
    store = store_with_items(
        (matched, "en", vocabulary(target)),
        (unaccented, "en", vocabulary("Please cafe don't jump to conclusions.")),
        (unrelated, "en", vocabulary("notwithstanding")),
    )
    client = client_over(settings_factory, store)

    # When NFC composition, case, punctuation, whitespace and apostrophe differ.
    response = client.get("/api/items/en", params={"q": " «CAFE\u0301  DONʼT\tJUMP» "})

    # Then the new list route is successful and only the normalized substring matches.
    assert response.status_code == 200
    assert [row["itemId"] for row in response.json()["items"]] == [matched]
    assert response.json()["items"][0]["target"] == target


@pytest.mark.p0
def test_search_matches_the_russian_meaning(settings_factory: SettingsFactory) -> None:
    """[P0] AC-2 Search normalizes and matches a Russian meaning substring."""
    # Given Target and alternatives that do not contain the requested Russian words.
    matched, other = str(uuid.uuid4()), str(uuid.uuid4())
    store = store_with_items(
        (matched, "en", vocabulary("arrive", russian="ДЕЛАТЬ   ПОСПЕШНЫЕ выводы!")),
        (other, "en", vocabulary("depart", russian="уходить", russianAlternatives=[])),
    )
    client = client_over(settings_factory, store)

    # When only a middle part of the Russian meaning is searched.
    response = client.get("/api/items/en", params={"q": "«делать поспешные»"})

    # Then the Item is returned through the successful search endpoint.
    assert response.status_code == 200
    assert [row["itemId"] for row in response.json()["items"]] == [matched]


@pytest.mark.p0
def test_search_matches_a_russian_alternative(settings_factory: SettingsFactory) -> None:
    """[P0] AC-3 Search normalizes and matches an individual Russian alternative."""
    # Given the query occurs only inside an alternative, not Target or Russian.
    matched, other = str(uuid.uuid4()), str(uuid.uuid4())
    store = store_with_items(
        (
            matched,
            "en",
            vocabulary(
                "take your time",
                russian="не спеши",
                russianAlternatives=["НЕ ТОРОПИТЬСЯ   С выводами", "подождать"],
            ),
        ),
        (other, "en", vocabulary("depart", russian="уходить", russianAlternatives=[])),
    )
    client = client_over(settings_factory, store)

    # When a normalized substring of one alternative is searched.
    response = client.get("/api/items/en", params={"q": "«торопиться с»"})

    # Then alternatives participate in search rather than being display-only data.
    assert response.status_code == 200
    assert [row["itemId"] for row in response.json()["items"]] == [matched]


@pytest.mark.p0
def test_search_includes_both_categories_only_in_the_requested_language(
    settings_factory: SettingsFactory,
) -> None:
    """[P0] AC-4 Search spans both Categories of one Language; blank q lists all."""
    # Given matching English Items in both Categories, another English Item and French matches.
    vocab, phrase, another, french_vocab, french_phrase = (str(uuid.uuid4()) for _ in range(5))
    store = store_with_items(
        (vocab, "en", vocabulary("jump to conclusions")),
        (phrase, "en", sentence("Don't jump to conclusions.")),
        (another, "en", vocabulary("notwithstanding")),
        (french_vocab, "fr", vocabulary("jump to conclusions")),
        (french_phrase, "fr", sentence("Don't jump to conclusions.")),
    )
    client = client_over(settings_factory, store)

    # When searching within English rather than one Category or the entire collection.
    response = client.get("/api/items/en", params={"q": "conclu"})

    # Then both English Categories match and French is excluded.
    assert response.status_code == 200
    assert {row["itemId"] for row in response.json()["items"]} == {vocab, phrase}
    blank = client.get("/api/items/en", params={"q": ""})
    assert blank.status_code == 200
    assert {row["itemId"] for row in blank.json()["items"]} == {vocab, phrase, another}


@pytest.mark.p0
def test_search_uses_read_only_exact_prefix_scopes(settings_factory: SettingsFactory) -> None:
    """[P0] AC-5 Search never interpolates user text into Anki queries or writes data."""
    # Given query syntax stored as ordinary Target text, and a different Prefix with that text.
    collection = managed_collection(MANIFEST)
    apply_manifest(collection, DEV_MANIFEST)
    item_id, dev_id = str(uuid.uuid4()), str(uuid.uuid4())
    query_text = 'scope" OR note:"LanguageLabDev English Vocabulary"'
    wire = vocabulary(query_text)
    item_note(
        collection,
        MANIFEST,
        note_type_of("en", wire),
        item_id,
        stored_fields(wire, item_id),
    )
    item_note(
        collection,
        DEV_MANIFEST,
        f"{DEV_MANIFEST.prefix} English Vocabulary",
        dev_id,
        stored_fields(wire, dev_id),
    )
    before = copy.deepcopy(collection)
    store, replay = wired(collection)
    client = client_over(settings_factory, store)

    # When the real service and adapter execute the user-controlled search.
    response = client.get("/api/items/en", params={"q": query_text})

    # Then only the exact two English note-type queries reach Anki, never user text.
    assert set(sent_queries(replay.sent)) == {
        note_query(MANIFEST, f"{MANIFEST.prefix} English Vocabulary"),
        note_query(MANIFEST, f"{MANIFEST.prefix} English Sentence"),
    }
    assert response.status_code == 200
    assert [row["itemId"] for row in response.json()["items"]] == [item_id]
    assert sent_writes(replay.sent) == []
    assert collection == before

    # A later Anki read failure is propagated through the existing envelope, not an empty list.
    failing_store, _ = wired(
        collection,
        replies={"findNotes": {"result": None, "error": "collection is not available"}},
    )
    failed = client_over(settings_factory, failing_store).get("/api/items/en", params={"q": "x"})
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "anki_unavailable"


@pytest.mark.p1
def test_item_list_reports_stored_audio_presence_without_writing(
    settings_factory: SettingsFactory,
) -> None:
    """[P1] AC-6 hasAudio reflects Audio on each row without changing editable content."""
    # Given one Vocabulary with Reference audio and one Sentence without it.
    collection = managed_collection(MANIFEST)
    voiced, silent = str(uuid.uuid4()), str(uuid.uuid4())
    voiced_wire, silent_wire = vocabulary(), sentence()
    media = f"{MANIFEST.prefix}_{voiced}_reference.mp3"
    item_note(
        collection,
        MANIFEST,
        note_type_of("en", voiced_wire),
        voiced,
        {**stored_fields(voiced_wire, voiced), "Audio": f"[sound:{media}]"},
    )
    item_note(
        collection,
        MANIFEST,
        note_type_of("en", silent_wire),
        silent,
        stored_fields(silent_wire, silent),
    )
    collection.media.add(media)
    before = copy.deepcopy(collection)
    store, replay = wired(collection)
    client = client_over(settings_factory, store)

    # When the list is read through the real adapter, without downloading or generating audio.
    response = client.get("/api/items/en")

    # Then list metadata distinguishes the stored Audio fields.
    assert response.status_code == 200
    rows = {row["itemId"]: row for row in response.json()["items"]}
    assert rows[voiced]["hasAudio"] is True
    assert rows[silent]["hasAudio"] is False
    assert {k: v for k, v in rows[voiced].items() if k not in ("itemId", "hasAudio")} == voiced_wire
    assert {k: v for k, v in rows[silent].items() if k not in ("itemId", "hasAudio")} == silent_wire
    assert sent_writes(replay.sent) == []
    assert collection == before

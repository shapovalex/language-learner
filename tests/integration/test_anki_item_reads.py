"""Story 4.3: read Items in the Anki adapter, for the duplicate check and Item detail (AD-4,
AD-9, AD-10, AD-12, AD-19).

- **`item_candidates(language, category)`.** `findNotes` on the exact note type scope of that
  Language and Category (`note_query`), then `notesInfo`: every Item of the note type, in note
  order, as an `Item(item_id, content)`. Each field is decoded through the codec, so markup from
  Anki's editor is gone, and `RussianAlternatives` is split by the adapter (AD-10). The
  matching on the Target is the service's (AD-12): the adapter returns the scoped candidates.
- **`get_item(language, item_id)`.** The exact scopes of both Categories of that Language, with
  the ItemId matched in Python on the decoded field, as Save does (AD-4). An ItemId no Item of
  that Language holds is `not_found`.

Neither the Target nor the ItemId ever enters a query. Both are reads, so the setup gate doesn't
apply to them (AD-19), as for the Capture reads. Anki is the in-memory collection in
tests/support/anki_state.py.
"""

import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.query import note_query
from language_lab.domain.catalog import Category, Language
from tests.support.aio import settle
from tests.support.anki_connect import refused
from tests.support.anki_state import (
    Collection,
    apply_manifest,
    collection_replies,
    item_note,
    managed_collection,
    sent_queries,
    sent_writes,
)
from tests.support.captures import DEV_MANIFEST, GATED_STATES, MANIFEST, code_of, wired
from tests.support.duplicates import sentence, vocabulary
from tests.support.items import content, note_type_of, stored_fields

# Stored in Anki's editor: inline markup and an NBSP in the Target, alternatives hand-joined
EDITED_FIELDS = {
    "Target": "<b>Jump</b>&nbsp;to conclusions",
    "Russian": "делать поспешные&nbsp;выводы",
    "RussianAlternatives": "торопиться с выводами,спешить с выводами",
}
EDITED = vocabulary(
    "Jump to conclusions",
    russian="делать поспешные выводы",
    russianAlternatives=["торопиться с выводами", "спешить с выводами"],
    hint="",
    partOfSpeech="",
    grammar="",
    example="",
    exampleRussian="",
    mnemonic="",
)


def put(collection: Collection, language: str, wire: dict[str, Any]) -> str:
    """An Item of `wire` in `language`, its fields as Save leaves them; returns its ItemId."""
    item_id = str(uuid.uuid4())
    note_type = note_type_of(language, wire)
    item_note(collection, MANIFEST, note_type, item_id, stored_fields(wire, item_id))
    return item_id


def put_dev(collection: Collection, wire: dict[str, Any], item_id: str | None = None) -> str:
    """A `LanguageLabDev` English Item: another Prefix, never read."""
    apply_manifest(collection, DEV_MANIFEST)
    item_id = item_id or str(uuid.uuid4())
    dev_type = f"{DEV_MANIFEST.prefix} English {wire['category'].capitalize()}"
    item_note(collection, DEV_MANIFEST, dev_type, item_id, stored_fields(wire, item_id))
    return item_id


@pytest.mark.p0
def test_item_candidates_returns_every_item_of_the_language_and_category_decoded() -> None:
    """AC-1: item_candidates(en, vocabulary) returns every English Vocabulary Item, in note
    order, with its ItemId and its fields decoded through the codec (editor markup gone,
    alternatives split); the English Sentence, French Vocabulary and LanguageLabDev Items are
    left out.
    """
    collection = managed_collection(MANIFEST)
    first = put(collection, "en", vocabulary())
    edited = str(uuid.uuid4())
    item_note(collection, MANIFEST, note_type_of("en", EDITED), edited, EDITED_FIELDS)
    put(collection, "en", sentence("jump to conclusions"))
    put(collection, "fr", vocabulary())
    put_dev(collection, vocabulary())
    store, _ = wired(collection)

    candidates = settle(store.item_candidates(Language.EN, Category.VOCABULARY))

    assert [c.item_id for c in candidates] == [first, edited]
    assert candidates[0].content == content(vocabulary())
    assert candidates[1].content == content(EDITED)


def _candidates(store: Any, item_id: str) -> Any:
    return store.item_candidates(Language.EN, Category.VOCABULARY)


def _one_item(store: Any, item_id: str) -> Any:
    return store.get_item(Language.EN, item_id)


READS = {"item-candidates": _candidates, "get-item": _one_item}

# The note types each read searches: one Category, or both of the Language
READ_SCOPES = {
    "item-candidates": [note_type_of("en", vocabulary())],
    "get-item": [note_type_of("en", vocabulary()), note_type_of("en", sentence())],
}


@pytest.mark.p0
@pytest.mark.parametrize("read", READS.keys())
def test_the_item_reads_send_only_exact_note_type_queries_and_no_user_text(read: str) -> None:
    """AC-2: each read sends only the exact `note:"<note type>"` queries of query.py for its
    scope, and no request carries the stored Target or the ItemId asked for (AD-4).
    """
    collection = managed_collection(MANIFEST)
    item_id = put(collection, "en", vocabulary())
    store, replay = wired(collection)

    settle(READS[read](store, item_id))

    assert set(sent_queries(replay.sent)) == {note_query(MANIFEST, t) for t in READ_SCOPES[read]}
    bodies = repr([r.body for r in replay.sent])
    assert item_id not in bodies
    assert vocabulary()["target"] not in bodies


ONE_OF_EACH = {"vocabulary": vocabulary(), "sentence": sentence("I'd rather not.")}


@pytest.mark.p0
@pytest.mark.parametrize("wire", ONE_OF_EACH.values(), ids=ONE_OF_EACH.keys())
def test_get_item_returns_the_item_matched_in_python_in_either_category(
    wire: dict[str, Any],
) -> None:
    """AC-3: get_item(en, item_id) returns the English Item whose decoded ItemId is `item_id`,
    Vocabulary or Sentence, with its fields decoded; other Items are not it.
    """
    collection = managed_collection(MANIFEST)
    put(collection, "en", vocabulary("another"))
    item_id = put(collection, "en", wire)
    put(collection, "en", sentence("yet another"))
    store, _ = wired(collection)

    got = settle(store.get_item(Language.EN, item_id))

    assert got.item_id == item_id
    assert got.content == content(wire)


def _absent(collection: Collection) -> str:
    put(collection, "en", vocabulary())
    return str(uuid.uuid4())


def _in_french(collection: Collection) -> str:
    return put(collection, "fr", vocabulary())


def _under_the_dev_prefix(collection: Collection) -> str:
    return put_dev(collection, vocabulary())


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [_absent, _in_french, _under_the_dev_prefix],
    ids=["absent", "in-the-other-language", "under-the-dev-prefix"],
)
def test_get_item_of_an_item_id_no_item_of_the_language_holds_is_not_found(arrange: Any) -> None:
    """AC-3: an ItemId held by no English Item of the Prefix is `not_found`, even when a French
    or a LanguageLabDev Item holds it.
    """
    collection = managed_collection(MANIFEST)
    item_id = arrange(collection)
    store, _ = wired(collection)

    outcome = settle(store.get_item(Language.EN, item_id))

    assert code_of(outcome) == "not_found"


@pytest.mark.p1
@pytest.mark.parametrize("state", GATED_STATES)
@pytest.mark.parametrize("read", READS.keys())
def test_the_item_reads_write_nothing_and_answer_when_anki_is_gated(state: str, read: str) -> None:
    """AC-4: under every gated SetupState each read writes nothing and still answers: the reads
    aren't gated (AD-19), as for the Capture reads.
    """
    collection = managed_collection(MANIFEST)
    item_id = put(collection, "en", vocabulary())
    store, replay = wired(collection, state=state)

    outcome = settle(READS[read](store, item_id))

    assert sent_writes(replay.sent) == []
    assert code_of(outcome) is None


@pytest.mark.p1
@pytest.mark.parametrize("read", READS.keys())
def test_anki_down_is_anki_unavailable_for_both_item_reads(read: str) -> None:
    """AC-3: an unreachable Anki is `anki_unavailable` for both reads."""
    store, _ = wired(managed_collection(MANIFEST), failure=refused)

    outcome = settle(READS[read](store, str(uuid.uuid4())))

    assert code_of(outcome) == "anki_unavailable"


@pytest.mark.p1
def test_a_note_deleted_since_find_notes_is_skipped_by_item_candidates() -> None:
    """AC-1: a note `notesInfo` answers as `{}` (deleted since `findNotes`) is left out."""
    collection = managed_collection(MANIFEST)
    kept = put(collection, "en", vocabulary())
    gone = put(collection, "en", vocabulary("gone"))
    gone_id = next(i for i, n in collection.notes.items() if n.fields["ItemId"] == gone)
    answers = collection_replies(collection, writes=True)

    def notes_info(body: Any) -> Any:
        reply = answers["notesInfo"]
        result = reply(body) if callable(reply) else reply
        notes = body["params"]["notes"]
        infos = zip(notes, result["result"], strict=True)
        result["result"] = [{} if n == gone_id else info for n, info in infos]
        return result

    store, _ = wired(collection, replies={"notesInfo": notes_info})

    candidates = settle(store.item_candidates(Language.EN, Category.VOCABULARY))

    assert [c.item_id for c in candidates] == [kept]

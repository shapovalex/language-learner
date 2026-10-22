"""Story 3.3: Delete Capture in the Anki adapter (AD-4, AD-5, AD-19).

`AnkiStore.delete_capture(capture_id)` is one use case under the Anki lock:

1. **Lookup by CaptureId (AD-4).** `findNotes` on the exact Capture note type scope
   (`note_query`), then `notesInfo`, and the CaptureId is matched in Python on the decoded
   field, as Create and Get Capture do. The CaptureId never enters a query.
2. **Found: `deleteNotes` on that note only.** Other Captures, other managed notes and another
   Prefix's Capture with the same CaptureId stay. The note's card goes with it.
3. **Not found: nothing to do (decided 2026-10-21).** A retried delete of a Capture that is
   already gone succeeds, and no `deleteNotes` is sent.

The write goes through `client.invoke`, so the AD-4 Prefix guard and the AD-19 setup gate both
apply: a gated Anki is `setup_required` and the note stays.

Anki is the in-memory collection in tests/support/anki_state.py. Its `deleteNotes` reply is
hand-built; the acceptance run (story 3.4) did not record it, so checking it is in deferred-work.md.
"""

import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import build_manifest
from language_lab.adapters.anki.query import note_query
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.errors import AppError
from language_lab.domain.setup import SetupState
from tests.support.aio import settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay, refused
from tests.support.anki_state import (
    Collection,
    apply_manifest,
    capture_note,
    collection_replies,
    managed_collection,
    managed_note,
    sent_queries,
    sent_writes,
)

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)
DEV_MANIFEST = build_manifest(DEV)

CAPTURE_QUERY = note_query(MANIFEST, f"{PREFIX} Capture")
VOCABULARY = f"{PREFIX} English Vocabulary"
CREATED_AT_FIELD = "2026-10-22T21:14:05Z"

GATED_STATES = ("needs_setup", "needs_migration", "newer_schema")


def wired(
    collection: Collection,
    *,
    state: str = "ready",
    replies: dict[str, Any] | None = None,
    failure: Any = None,
) -> tuple[Any, AnkiConnectReplay]:
    """The real client and store over `collection`, sharing a `SetupGate` set to `state`
    (`ready` by default); `replies` replaces some of the collection's replies; `failure` fails
    every request. Returns (store, replay).
    """
    gate = SetupGate(MANIFEST)
    gate.set(SetupState(state))
    answers = collection_replies(collection, writes=True) | (replies or {})
    replay = AnkiConnectReplay(answers, failure=failure)
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    return AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST, gate=gate), replay


def code_of(outcome: Any) -> str | None:
    return str(outcome.code) if isinstance(outcome, AppError) else None


def sent_bodies(replay: AnkiConnectReplay) -> str:
    return repr([r.body for r in replay.sent])


def notes_info_with(collection: Collection, note_id: int, entry: Any) -> Any:
    """A `notesInfo` reply over `collection` whose entry for `note_id` is `entry`."""
    answers = collection_replies(collection, writes=True)

    def notes_info(body: Any) -> Any:
        reply = answers["notesInfo"]
        result = reply(body) if callable(reply) else reply
        infos = zip(body["params"]["notes"], result["result"], strict=True)
        result["result"] = [entry(info) if n == note_id else info for n, info in infos]
        return result

    return notes_info


@pytest.mark.p0
def test_delete_capture_deletes_only_the_note_with_that_capture_id() -> None:
    """AC-1: delete_capture deletes the note with that CaptureId, and its card, and nothing
    else: other Captures, other managed notes and another Prefix's Capture with the same
    CaptureId stay. The CaptureId is matched in Python, never sent in a query (AD-4).
    """
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    edited_id = f"<div>{capture_id}</div>"  # as Anki's editor leaves it
    target = capture_note(collection, MANIFEST, edited_id, "gone", CREATED_AT_FIELD)
    others = [
        capture_note(collection, MANIFEST, str(uuid.uuid4()), "kept", CREATED_AT_FIELD)
        for _ in range(2)
    ]
    others.append(managed_note(collection, MANIFEST, VOCABULARY, str(MANIFEST.schema_version)))
    apply_manifest(collection, DEV_MANIFEST)
    others.append(capture_note(collection, DEV_MANIFEST, capture_id, "dev", CREATED_AT_FIELD))
    store, replay = wired(collection)

    settle(store.delete_capture(capture_id))

    assert sorted(collection.notes) == sorted(others)
    assert all(card.note != target for card in collection.cards.values())
    assert set(sent_queries(replay.sent)) == {CAPTURE_QUERY}
    assert capture_id not in sent_bodies(replay)


@pytest.mark.p0
def test_a_repeated_delete_succeeds_and_sends_no_write() -> None:
    """AC-2: deleting a Capture that is already gone succeeds (a retried delete), sends no
    `deleteNotes`, and leaves every other note.
    """
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    capture_note(collection, MANIFEST, capture_id, "gone", CREATED_AT_FIELD)
    kept = capture_note(collection, MANIFEST, str(uuid.uuid4()), "kept", CREATED_AT_FIELD)
    store, replay = wired(collection)
    settle(store.delete_capture(capture_id))
    before = len(replay.sent)

    outcome = settle(store.delete_capture(capture_id))

    assert (outcome, sent_writes(replay.sent[before:])) == (None, [])
    assert list(collection.notes) == [kept]


@pytest.mark.p0
@pytest.mark.parametrize("state", GATED_STATES)
def test_a_gated_anki_refuses_delete_capture_and_keeps_the_note(state: str) -> None:
    """AC-3: unless the SetupState is `ready`, delete_capture is `setup_required`, no write is
    sent and the Capture stays (AD-19).
    """
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    note_id = capture_note(collection, MANIFEST, capture_id, "kept", CREATED_AT_FIELD)
    store, replay = wired(collection, state=state)

    outcome = settle(store.delete_capture(capture_id))

    assert code_of(outcome) == "setup_required"
    assert sent_writes(replay.sent) == []
    assert list(collection.notes) == [note_id]


# Secondary cases (green phase)


@pytest.mark.p1
def test_anki_down_is_anki_unavailable_for_delete() -> None:
    """AC-1: an unreachable Anki is `anki_unavailable`."""
    store, _ = wired(managed_collection(MANIFEST), failure=refused)

    outcome = settle(store.delete_capture(str(uuid.uuid4())))

    assert code_of(outcome) == "anki_unavailable"


@pytest.mark.p1
@pytest.mark.parametrize("state", GATED_STATES)
def test_a_gated_anki_with_nothing_to_delete_succeeds(state: str) -> None:
    """AC-3: with no such Capture there is nothing to write, so a gated Anki succeeds too."""
    collection = managed_collection(MANIFEST)
    kept = capture_note(collection, MANIFEST, str(uuid.uuid4()), "kept", CREATED_AT_FIELD)
    store, replay = wired(collection, state=state)

    outcome = settle(store.delete_capture(str(uuid.uuid4())))

    assert (outcome, sent_writes(replay.sent)) == (None, [])
    assert list(collection.notes) == [kept]


@pytest.mark.p1
def test_a_capture_deleted_since_find_notes_is_skipped() -> None:
    """AC-2: a `{}` notesInfo entry (the note deleted since `findNotes`) is already gone, so
    nothing is written.
    """
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    note_id = capture_note(collection, MANIFEST, capture_id, "gone", CREATED_AT_FIELD)
    notes_info = notes_info_with(collection, note_id, lambda _: {})
    store, replay = wired(collection, replies={"notesInfo": notes_info})

    outcome = settle(store.delete_capture(capture_id))

    assert (outcome, sent_writes(replay.sent)) == (None, [])


@pytest.mark.p1
def test_a_malformed_note_id_is_anki_unavailable() -> None:
    """AC-1: a matching entry without an integer `noteId` is `anki_unavailable`, with no write."""
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    note_id = capture_note(collection, MANIFEST, capture_id, "kept", CREATED_AT_FIELD)
    notes_info = notes_info_with(collection, note_id, lambda info: info | {"noteId": "1"})
    store, replay = wired(collection, replies={"notesInfo": notes_info})

    outcome = settle(store.delete_capture(capture_id))

    assert code_of(outcome) == "anki_unavailable"
    assert sent_writes(replay.sent) == []
    assert list(collection.notes) == [note_id]

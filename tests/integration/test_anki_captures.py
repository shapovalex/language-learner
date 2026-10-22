"""Story 3.1: Create Capture in the Anki adapter (AD-4, AD-6, AD-8, AD-9, AD-19, AD-20).

`AnkiStore.create_capture(capture_id, text, created_at)` is one use case under the Anki lock:

1. **Lookup by CaptureId (AD-4, decided 2026-10-21).** `findNotes` on the exact Capture note
   type scope (`note_query`), then `notesInfo`, and the CaptureId is matched in Python on the
   decoded field. Neither the CaptureId nor the text ever enters a query.
2. **Found: create-or-noop (AD-20).** The stored Capture comes back unchanged, and nothing is
   written.
3. **Not found: add, then suspend (AD-6).** `addNote` into `<Prefix>::Captures` with `Text`,
   `CreatedAt` (`YYYY-MM-DDTHH:MM:SSZ`, UTC), `CaptureId` and `SchemaVersion`, each written
   through the codec, with `allowDuplicate: true`. Then `suspend` on its card.

The write goes through `client.invoke`, so the AD-4 Prefix guard and the AD-19 setup gate both
apply: a gated Anki is `setup_required` before any write is sent. A failing Anki is
`anki_unavailable`, and a failed `addNote` sends no `suspend`.

Anki is the in-memory collection in tests/support/anki_state.py: `addNote` gives the note its
card, and refuses a duplicate first field unless `allowDuplicate` is set. The real Anki's
`suspend` and `deleteNotes` replies are hand-built until the acceptance run (entry 4).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.codec import encode_field
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import SCHEMA_VERSION, build_manifest
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
    sent_queries,
    sent_writes,
)

pytestmark = pytest.mark.skip(reason="ATDD red phase: until story 3.1 adds create_capture")

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)
DEV_MANIFEST = build_manifest(DEV)

CAPTURE = f"{PREFIX} Capture"
CAPTURES_DECK = f"{PREFIX}::Captures"
CAPTURE_QUERY = note_query(MANIFEST, CAPTURE)

# Characters the codec escapes, and a newline it turns into <br> (AD-9)
TEXT = "I'd rather <not> jump & leap\nto conclusions."
CREATED_AT = datetime(2026, 10, 22, 21, 14, 5, tzinfo=UTC)
CREATED_AT_FIELD = "2026-10-22T21:14:05Z"
EARLIER_FIELD = "2026-10-01T08:02:00Z"
EARLIER = datetime(2026, 10, 1, 8, 2, tzinfo=UTC)

GATED_STATES = ("needs_setup", "needs_migration", "newer_schema")


def wired(
    collection: Collection,
    *,
    state: str = "ready",
    replies: dict[str, Any] | None = None,
    failure: Any = None,
) -> tuple[Any, Any]:
    """The real client and store over `collection`, sharing a `SetupGate` set to `state`.
    `replies` replaces some of the collection's replies; `failure` fails every request.
    Returns (store, replay).
    """
    gate = SetupGate(MANIFEST)
    gate.set(SetupState(state))
    answers = collection_replies(collection, writes=True) | (replies or {})
    replay = AnkiConnectReplay(answers, failure=failure)
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    return AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST, gate=gate), replay


def create(store: Any, capture_id: str, text: str = TEXT, created_at: datetime = CREATED_AT) -> Any:
    """`store.create_capture(...)`'s Capture, or the exception it raised."""
    return settle(store.create_capture(capture_id, text, created_at))


def captures_in(collection: Collection) -> dict[int, Any]:
    return {i: note for i, note in collection.notes.items() if note.model == CAPTURE}


def code_of(outcome: Any) -> str | None:
    return str(outcome.code) if isinstance(outcome, AppError) else None


def sent_note(replay: AnkiConnectReplay) -> dict[str, Any]:
    """The `note` param of the one `addNote` sent."""
    (body,) = [r.body for r in replay.sent if r.body.get("action") == "addNote"]
    return body["params"]["note"]


def _empty(collection: Collection) -> None:
    pass


def _same_text_as_another(collection: Collection) -> None:
    capture_note(collection, MANIFEST, str(uuid.uuid4()), encode_field(TEXT), EARLIER_FIELD)


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [_empty, _same_text_as_another],
    ids=["first-capture", "same-text-as-another-capture"],
)
def test_a_new_capture_is_added_then_its_card_suspended(arrange: Any) -> None:
    """AC-1: a new CaptureId adds a Capture note to `<Prefix>::Captures` with its four fields
    written through the codec and `allowDuplicate`, then suspends its card.
    """
    from language_lab.domain.captures import Capture

    collection = managed_collection(MANIFEST)
    arrange(collection)
    before = set(captures_in(collection))
    store, replay = wired(collection)
    capture_id = str(uuid.uuid4())

    outcome = create(store, capture_id)

    assert sent_writes(replay.sent) == ["addNote", "suspend"]
    (new_id,) = set(captures_in(collection)) - before
    assert collection.notes[new_id].fields == {
        "Text": encode_field(TEXT),
        "CreatedAt": CREATED_AT_FIELD,
        "CaptureId": capture_id,
        "SchemaVersion": str(SCHEMA_VERSION),
    }
    note = sent_note(replay)
    assert (note["deckName"], note["options"]["allowDuplicate"]) == (CAPTURES_DECK, True)
    cards = [c for c in collection.cards.values() if c.note == new_id]
    assert [(c.deck, c.suspended) for c in cards] == [(CAPTURES_DECK, True)]
    assert outcome == Capture(capture_id, TEXT, CREATED_AT)


def _other_captures(collection: Collection) -> None:
    for _ in range(3):
        capture_note(collection, MANIFEST, str(uuid.uuid4()), "other", EARLIER_FIELD)


def _dev_capture_with_the_id(collection: Collection, capture_id: str) -> None:
    """A `LanguageLabDev` Capture carrying the same CaptureId: another Prefix, never a match."""
    apply_manifest(collection, DEV_MANIFEST)
    capture_note(collection, DEV_MANIFEST, capture_id, "dev", EARLIER_FIELD)


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [
        lambda collection, _: None,
        lambda collection, _: _other_captures(collection),
        _dev_capture_with_the_id,
    ],
    ids=["no-captures", "other-captures", "dev-prefix-capture-with-the-same-id"],
)
def test_the_capture_id_lookup_queries_only_the_exact_capture_scope(arrange: Any) -> None:
    """AC-2: the CaptureId lookup sends only the exact Capture note type query; neither the
    CaptureId nor the text is ever in a query, and another Prefix's Capture never matches.
    """
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    arrange(collection, capture_id)
    store, replay = wired(collection)

    create(store, capture_id)

    assert set(sent_queries(replay.sent)) == {CAPTURE_QUERY}
    bodies = repr([r.body for r in replay.sent if r.body.get("action") != "addNote"])
    assert capture_id not in bodies
    assert "conclusions" not in bodies
    assert sent_writes(replay.sent) == ["addNote", "suspend"]


def _stored_plain(collection: Collection, capture_id: str) -> None:
    capture_note(collection, MANIFEST, capture_id, "un rendez-vous", EARLIER_FIELD)


def _stored_in_editor_markup(collection: Collection, capture_id: str) -> None:
    """Edited in Anki's editor: the hidden fields wrapped in markup the codec strips."""
    capture_note(
        collection,
        MANIFEST,
        f"<div>{capture_id}</div>",
        "un <b>rendez-vous</b>",
        f"<div>{EARLIER_FIELD}&nbsp;</div>",
    )


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [_stored_plain, _stored_in_editor_markup],
    ids=["stored-plain", "stored-in-editor-markup"],
)
def test_an_existing_capture_id_returns_the_stored_capture_and_writes_nothing(
    arrange: Any,
) -> None:
    """AC-3: a CaptureId already in Anki comes back as the stored Capture, unchanged, and
    nothing is written: a retried Save makes no second note (AD-20).
    """
    from language_lab.domain.captures import Capture

    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    arrange(collection, capture_id)
    before = {i: dict(n.fields) for i, n in captures_in(collection).items()}
    store, replay = wired(collection)

    outcome = create(store, capture_id, "a different text", CREATED_AT)

    assert sent_writes(replay.sent) == []
    assert {i: dict(n.fields) for i, n in captures_in(collection).items()} == before
    assert outcome == Capture(capture_id, "un rendez-vous", EARLIER)


@pytest.mark.p0
@pytest.mark.parametrize("state", GATED_STATES)
def test_a_gated_anki_refuses_create_capture_before_any_write(state: str) -> None:
    """AC-4: unless the SetupState is `ready`, create_capture is `setup_required` and no note
    is written (AD-19).
    """
    collection = managed_collection(MANIFEST)
    store, replay = wired(collection, state=state)

    outcome = create(store, str(uuid.uuid4()))

    assert code_of(outcome) == "setup_required"
    assert sent_writes(replay.sent) == []
    assert captures_in(collection) == {}


def _add_note_error(body: Any) -> dict[str, Any]:
    return {"result": None, "error": "collection is not available"}


@pytest.mark.p0
@pytest.mark.parametrize("failure", ["anki-down", "add-note-fails"])
def test_a_failing_anki_returns_anki_unavailable_with_no_note(failure: str) -> None:
    """AC-5: Anki down, or an `addNote` that fails, is `anki_unavailable`; no note is made and
    no `suspend` is sent.
    """
    collection = managed_collection(MANIFEST)
    if failure == "anki-down":
        store, replay = wired(collection, failure=refused)
    else:
        store, replay = wired(collection, replies={"addNote": _add_note_error})

    outcome = create(store, str(uuid.uuid4()))

    assert code_of(outcome) == "anki_unavailable"
    assert "suspend" not in sent_writes(replay.sent)
    assert captures_in(collection) == {}

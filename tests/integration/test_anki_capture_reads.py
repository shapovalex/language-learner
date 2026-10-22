"""Story 3.2: list and read Captures in the Anki adapter (AD-4, AD-5, AD-9).

- **`list_captures()`.** `findNotes` on the exact Capture note type scope (`note_query`), then
  `notesInfo`. Every field is decoded through the codec, so markup from Anki's editor is gone.
  The Captures come back newest first by CreatedAt, never by note id. Anki ids stay in the
  adapter: a `Capture` has none.
- **`get_capture(capture_id)`.** The same scope and reads, with the CaptureId matched in Python
  on the decoded field, as Create Capture does (AD-4). It is never in a query. An unknown
  CaptureId is `not_found`.

Both are reads, so the setup gate doesn't apply to them (AD-19). Anki is the in-memory
collection in tests/support/anki_state.py.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.codec import encode_field
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import build_manifest
from language_lab.adapters.anki.query import note_query
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.captures import Capture
from language_lab.domain.errors import AppError
from language_lab.domain.setup import SetupState
from tests.support.aio import settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import (
    Collection,
    apply_manifest,
    capture_note,
    collection_replies,
    managed_collection,
    managed_note,
    sent_queries,
)

pytestmark = pytest.mark.skip(
    reason="ATDD red phase: AnkiStore.list_captures and get_capture are not built until story 3.2"
)

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)
DEV_MANIFEST = build_manifest(DEV)

CAPTURE_QUERY = note_query(MANIFEST, f"{PREFIX} Capture")
VOCABULARY = f"{PREFIX} English Vocabulary"

# Characters the codec escapes, and a newline it turns into <br> (AD-9)
TEXT = "I'd rather <not> jump & leap\nto conclusions."
OCT_22 = datetime(2026, 10, 22, 21, 14, 5, tzinfo=UTC)
OCT_22_FIELD = "2026-10-22T21:14:05Z"
OCT_01 = datetime(2026, 10, 1, 8, 2, tzinfo=UTC)
OCT_01_FIELD = "2026-10-01T08:02:00Z"
LAST_YEAR = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
LAST_YEAR_FIELD = "2025-12-31T23:59:59Z"


def wired(collection: Collection) -> tuple[Any, AnkiConnectReplay]:
    """The real client and store over `collection`, gate `ready`. Returns (store, replay)."""
    gate = SetupGate(MANIFEST)
    gate.set(SetupState.READY)
    replay = AnkiConnectReplay(collection_replies(collection, writes=True))
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    return AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST, gate=gate), replay


def code_of(outcome: Any) -> str | None:
    return str(outcome.code) if isinstance(outcome, AppError) else None


def sent_bodies(replay: AnkiConnectReplay) -> str:
    return repr([r.body for r in replay.sent])


@pytest.mark.p0
def test_list_captures_returns_every_capture_decoded_from_the_exact_scope() -> None:
    """AC-1: list_captures returns every Capture of the Prefix with its fields decoded through
    the codec, from the exact Capture note type scope only; another Prefix's Captures and other
    managed notes are left out.
    """
    collection = managed_collection(MANIFEST)
    plain, edited = str(uuid.uuid4()), str(uuid.uuid4())
    capture_note(collection, MANIFEST, plain, encode_field(TEXT), OCT_22_FIELD)
    capture_note(
        collection,
        MANIFEST,
        f"<div>{edited}</div>",
        "un <b>rendez-vous</b>",
        f"<div>{OCT_01_FIELD}&nbsp;</div>",
    )
    managed_note(collection, MANIFEST, VOCABULARY, str(MANIFEST.schema_version))
    apply_manifest(collection, DEV_MANIFEST)
    capture_note(collection, DEV_MANIFEST, str(uuid.uuid4()), "dev", OCT_22_FIELD)
    store, replay = wired(collection)

    outcome = settle(store.list_captures())

    assert set(outcome) == {
        Capture(plain, TEXT, OCT_22),
        Capture(edited, "un rendez-vous", OCT_01),
    }
    assert set(sent_queries(replay.sent)) == {CAPTURE_QUERY}


@pytest.mark.p0
def test_list_captures_is_newest_first_by_created_at() -> None:
    """AC-2: list_captures orders the Captures newest first by CreatedAt, not by note id."""
    collection = managed_collection(MANIFEST)
    middle, oldest, newest = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    capture_note(collection, MANIFEST, middle, "middle", OCT_01_FIELD)
    capture_note(collection, MANIFEST, oldest, "oldest", LAST_YEAR_FIELD)
    capture_note(collection, MANIFEST, newest, "newest", OCT_22_FIELD)
    store, _ = wired(collection)

    outcome = settle(store.list_captures())

    assert [c.capture_id for c in outcome] == [newest, middle, oldest]


@pytest.mark.p0
def test_get_capture_returns_the_capture_matched_in_python() -> None:
    """AC-3: get_capture returns the Capture with that CaptureId, decoded through the codec; the
    CaptureId is matched in Python and never sent in a query (AD-4).
    """
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    for _ in range(2):
        capture_note(collection, MANIFEST, str(uuid.uuid4()), "other", OCT_22_FIELD)
    capture_note(
        collection,
        MANIFEST,
        f"<div>{capture_id}</div>",
        "un <b>rendez-vous</b>",
        f"<div>{OCT_01_FIELD}&nbsp;</div>",
    )
    store, replay = wired(collection)

    outcome = settle(store.get_capture(capture_id))

    assert outcome == Capture(capture_id, "un rendez-vous", OCT_01)
    assert set(sent_queries(replay.sent)) == {CAPTURE_QUERY}
    assert capture_id not in sent_bodies(replay)


def _no_captures(collection: Collection, capture_id: str) -> None:
    pass


def _other_captures(collection: Collection, capture_id: str) -> None:
    for _ in range(3):
        capture_note(collection, MANIFEST, str(uuid.uuid4()), "other", OCT_22_FIELD)


def _dev_capture_with_the_id(collection: Collection, capture_id: str) -> None:
    """A `LanguageLabDev` Capture carrying the same CaptureId: another Prefix, never a match."""
    apply_manifest(collection, DEV_MANIFEST)
    capture_note(collection, DEV_MANIFEST, capture_id, "dev", OCT_22_FIELD)


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [_no_captures, _other_captures, _dev_capture_with_the_id],
    ids=["no-captures", "other-captures", "dev-prefix-capture-with-the-same-id"],
)
def test_get_capture_of_an_unknown_capture_id_is_not_found(arrange: Any) -> None:
    """AC-4: get_capture of a CaptureId that no Capture of the Prefix holds is `not_found`."""
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    arrange(collection, capture_id)
    store, _ = wired(collection)

    outcome = settle(store.get_capture(capture_id))

    assert code_of(outcome) == "not_found"

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

from language_lab.adapters.anki.codec import encode_field
from language_lab.domain.captures import Capture
from tests.support.aio import settle
from tests.support.anki_connect import refused
from tests.support.anki_state import (
    Collection,
    apply_manifest,
    capture_note,
    collection_replies,
    managed_collection,
    managed_note,
    sent_actions,
    sent_queries,
)
from tests.support.captures import (
    CAPTURE_QUERY,
    DEV_MANIFEST,
    MANIFEST,
    TEXT,
    VOCABULARY,
    code_of,
    dev_capture_with_the_id,
    other_captures,
    sent_bodies,
    wired,
)

OCT_22 = datetime(2026, 10, 22, 21, 14, 5, tzinfo=UTC)
OCT_22_FIELD = "2026-10-22T21:14:05Z"
OCT_01 = datetime(2026, 10, 1, 8, 2, tzinfo=UTC)
OCT_01_FIELD = "2026-10-01T08:02:00Z"
LAST_YEAR = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
LAST_YEAR_FIELD = "2025-12-31T23:59:59Z"


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
    other_captures(collection, OCT_22_FIELD)


def _dev_capture_with_the_id(collection: Collection, capture_id: str) -> None:
    dev_capture_with_the_id(collection, capture_id, OCT_22_FIELD)


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


# Secondary cases (green phase)


@pytest.mark.p1
def test_an_empty_capture_scope_lists_nothing_and_sends_no_notes_info() -> None:
    """AC-1: with no Captures, list_captures is `[]` and no `notesInfo` is sent."""
    collection = managed_collection(MANIFEST)
    store, replay = wired(collection)

    outcome = settle(store.list_captures())

    assert outcome == []
    assert "notesInfo" not in sent_actions(replay.sent)


@pytest.mark.p1
def test_a_note_deleted_since_find_notes_is_skipped() -> None:
    """AC-1: a `{}` notesInfo entry (a note deleted since `findNotes`) is skipped."""
    collection = managed_collection(MANIFEST)
    kept, gone = str(uuid.uuid4()), str(uuid.uuid4())
    capture_note(collection, MANIFEST, kept, "kept", OCT_22_FIELD)
    gone_id = capture_note(collection, MANIFEST, gone, "gone", OCT_01_FIELD)
    answers = collection_replies(collection, writes=True)

    def notes_info(body: Any) -> Any:
        reply = answers["notesInfo"]
        result = reply(body) if callable(reply) else reply
        notes = body["params"]["notes"]
        infos = zip(notes, result["result"], strict=True)
        result["result"] = [{} if n == gone_id else info for n, info in infos]
        return result

    store, _ = wired(collection, replies={"notesInfo": notes_info})

    outcome = settle(store.list_captures())

    assert outcome == [Capture(kept, "kept", OCT_22)]


@pytest.mark.p1
def test_a_malformed_created_at_is_anki_unavailable() -> None:
    """AC-1: a CreatedAt that isn't `YYYY-MM-DDTHH:MM:SSZ` is `anki_unavailable`."""
    collection = managed_collection(MANIFEST)
    capture_note(collection, MANIFEST, str(uuid.uuid4()), "bad", "yesterday")
    store, _ = wired(collection)

    outcome = settle(store.list_captures())

    assert code_of(outcome) == "anki_unavailable"


@pytest.mark.p1
def test_anki_down_is_anki_unavailable_for_both_reads() -> None:
    """AC-1 / AC-3: an unreachable Anki is `anki_unavailable`."""
    store, _ = wired(managed_collection(MANIFEST), failure=refused)

    outcomes = [settle(store.list_captures()), settle(store.get_capture(str(uuid.uuid4())))]

    assert [code_of(o) for o in outcomes] == ["anki_unavailable", "anki_unavailable"]


@pytest.mark.p1
def test_a_gated_anki_still_lists_and_reads_captures() -> None:
    """AC-1 / AC-3: the reads aren't gated (AD-19), so `needs_setup` still lists and reads."""
    collection = managed_collection(MANIFEST)
    capture_id = str(uuid.uuid4())
    capture_note(collection, MANIFEST, capture_id, "kept", OCT_22_FIELD)
    store, _ = wired(collection, state="needs_setup")

    listed = settle(store.list_captures())
    got = settle(store.get_capture(capture_id))

    assert listed == [Capture(capture_id, "kept", OCT_22)]
    assert got == Capture(capture_id, "kept", OCT_22)


@pytest.mark.p1
def test_equal_created_at_values_keep_a_stable_order() -> None:
    """AC-2: Captures with the same CreatedAt come back in one order, CaptureId descending."""
    collection = managed_collection(MANIFEST)
    ids = [str(uuid.uuid4()) for _ in range(3)]
    for capture_id in ids:
        capture_note(collection, MANIFEST, capture_id, "same time", OCT_22_FIELD)
    store, _ = wired(collection)

    outcome = settle(store.list_captures())

    assert [c.capture_id for c in outcome] == sorted(ids, reverse=True)

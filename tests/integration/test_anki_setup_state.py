"""Story 2.8: SetupState and the write gate in the Anki adapter (AD-19, AD-3, AD-4, AD-9).

`SetupState` is `ready`, `needs_setup`, `needs_migration` or `newer_schema`. The adapter
computes it from the same reads as the preview plus each managed note's `SchemaVersion` field,
read through the codec (`decode_field`), so editor markup around the number doesn't count:

- `newer_schema`: any managed note stores a version above the manifest's. It wins over the rest.
- `needs_migration`: a Migrate item (fields differ), or a note below the manifest's version or
  with one that isn't an integer once decoded. Decided with the user (2026-10-21): an empty or
  non-integer version is an older note, so a migration (entry 9) can rewrite it.
- `needs_setup`: any other plan item.
- `ready`: no plan item, and every managed note at the manifest's version.

Notes of another Prefix (`LanguageLabDev` beside `LanguageLab`) never count (AD-4).

The gate (decided with the user, 2026-10-21) sits in the client, like the Prefix guard: a
`SetupGate(manifest)` shared by `AnkiConnectClient(..., gate=)` and `AnkiConnectStore(...,
gate=)`. `client.invoke` refuses every write with `AppError(SETUP_REQUIRED)`, before it is sent,
unless the gate's state is `ready`. Reads always pass. Setup's own apply writes through an
ungated path. The store sets the gate's state at each preview (a Setup visit), after each apply,
and from `setup_state()` (startup). While the state is unknown (`None`, e.g. Anki was down at
startup), the first gated write computes it under the call. `updateNoteFields` is refused when
the note's stored `SchemaVersion` isn't the manifest's, even when `ready`.

Anki is the in-memory collection in tests/support/anki_state.py. The gate, `SetupState` and
`setup_state()` don't exist yet, so they're imported inside the tests.

Skipped until the gate exists. Un-skip a test, watch it fail, then implement.
"""

from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import SCHEMA_VERSION, build_manifest
from language_lab.adapters.anki.query import note_query
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.errors import AppError
from language_lab.domain.setup import plan_hash
from tests.support.aio import settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import (
    Collection,
    apply_manifest,
    collection_replies,
    managed_collection,
    managed_note,
    sent_writes,
    stock_collection,
)

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.8: un-skip with SetupState and the SetupGate"
)

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)
DEV_MANIFEST = build_manifest(DEV)

VOCABULARY = f"{PREFIX} English Vocabulary"
SENTENCE = f"{PREFIX} French Sentence"
CAPTURE = f"{PREFIX} Capture"
UNDERSTAND_DECK = f"{PREFIX}::Study::English::Vocabulary::Understand"

CURRENT = str(SCHEMA_VERSION)
OLDER = str(SCHEMA_VERSION - 1)
NEWER = str(SCHEMA_VERSION + 1)

GATED_STATES = ("needs_setup", "needs_migration", "newer_schema")


def wired(collection: Collection, state: str | None = None) -> tuple[Any, Any, Any, Any]:
    """The real client and store over `collection`, sharing one `SetupGate` set to `state`
    (unknown when None). Returns (client, store, gate, replay).
    """
    from language_lab.adapters.anki.setup_gate import SetupGate

    from language_lab.domain.setup import SetupState

    gate = SetupGate(MANIFEST)
    if state is not None:
        gate.set(SetupState(state))
    replay = AnkiConnectReplay(collection_replies(collection, writes=True))
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    store = AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST, gate=gate)
    return client, store, gate, replay


def add_vocabulary(client: Any) -> Any:
    """What Items (a later epic) sends to add a note: a non-Setup write."""
    note = {
        "deckName": UNDERSTAND_DECK,
        "modelName": VOCABULARY,
        "fields": {"Target": "chat", "SchemaVersion": CURRENT},
    }
    return settle(client.invoke("addNote", note=note))


def code_of(outcome: Any) -> str | None:
    """The `AppError` code of an outcome, or None when it isn't one."""
    return str(outcome.code) if isinstance(outcome, AppError) else None


# ---- the states, from fixtures (AC-1) ----------------------------------------------------


def _set_up_with(*versions: str, note_type: str = VOCABULARY) -> Collection:
    collection = managed_collection(MANIFEST)
    for version in versions:
        managed_note(collection, MANIFEST, note_type, version)
    return collection


def _every_type_current() -> Collection:
    collection = managed_collection(MANIFEST)
    for note_type in MANIFEST.note_types:
        managed_note(collection, MANIFEST, note_type.name, CURRENT)
    return collection


def _missing_deck(*versions: str) -> Collection:
    collection = _set_up_with(*versions)
    del collection.decks[UNDERSTAND_DECK]
    return collection


def _field_change() -> Collection:
    collection = _set_up_with(CURRENT)
    collection.models[SENTENCE].fields.append("Extra")
    return collection


def _dev_newer_beside() -> Collection:
    collection = apply_manifest(_set_up_with(CURRENT), DEV_MANIFEST)
    managed_note(collection, DEV_MANIFEST, f"{DEV} English Vocabulary", NEWER)
    return collection


STATE_CASES = {
    "set-up-no-notes": (lambda: managed_collection(MANIFEST), "ready"),
    "set-up-every-type-current": (_every_type_current, "ready"),
    "version-in-editor-markup": (lambda: _set_up_with(f"<div>{CURRENT}</div>"), "ready"),
    "version-with-nbsp": (lambda: _set_up_with(f"{CURRENT}&nbsp;"), "ready"),
    "dev-prefix-newer-beside": (_dev_newer_beside, "ready"),
    "empty-prefix": (stock_collection, "needs_setup"),
    "missing-deck": (_missing_deck, "needs_setup"),
    "older-note": (lambda: _set_up_with(CURRENT, OLDER), "needs_migration"),
    "empty-version": (lambda: _set_up_with(""), "needs_migration"),
    "non-integer-version": (lambda: _set_up_with("one"), "needs_migration"),
    "field-change": (_field_change, "needs_migration"),
    "missing-deck-and-older-note": (lambda: _missing_deck(OLDER), "needs_migration"),
    "newer-note": (lambda: _set_up_with(NEWER, note_type=CAPTURE), "newer_schema"),
    "newer-beside-older": (lambda: _set_up_with(OLDER, NEWER), "newer_schema"),
    "newer-and-missing-deck": (lambda: _missing_deck(NEWER), "newer_schema"),
}


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(("build", "expected"), STATE_CASES.values(), ids=STATE_CASES.keys())
def test_setup_state_is_computed_from_the_plan_and_each_notes_schema_version(
    build: Any, expected: str
) -> None:
    """AC-1: each state from fixtures, every note's SchemaVersion read through the codec."""
    _, store, _, replay = wired(build())

    outcome = settle(store.setup_state())

    assert str(outcome) == expected
    assert sent_writes(replay.sent) == []


# ---- when it's computed (AC-3) -----------------------------------------------------------


@RED_PHASE
@pytest.mark.p0
def test_the_gate_follows_each_setup_visit_and_each_apply() -> None:
    """AC-3: a preview (a Setup visit) and an apply each leave their fresh state in the gate."""
    collection = stock_collection()
    _, store, gate, _ = wired(collection, "ready")
    states: list[str] = []

    async def visit_then_apply() -> None:
        preview = await store.setup_preview()
        states.append(str(gate.state))
        await store.setup_apply(plan_hash(preview.items))
        states.append(str(gate.state))

    settle(visit_then_apply())

    assert states == ["needs_setup", "ready"]


# ---- the gate (AC-4 to AC-8) -------------------------------------------------------------


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(
    ("state", "expected"),
    [*((s, "setup_required") for s in GATED_STATES), ("ready", None)],
    ids=[*GATED_STATES, "ready"],
)
def test_a_non_setup_write_is_refused_unless_setup_state_is_ready(
    state: str, expected: str | None
) -> None:
    """AC-4: `addNote` is `setup_required` before it's sent in every state but `ready`."""
    client, _, _, replay = wired(managed_collection(MANIFEST), state)

    outcome = add_vocabulary(client)

    assert code_of(outcome) == expected
    assert sent_writes(replay.sent) == ([] if expected else ["addNote"])


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize("state", [*GATED_STATES, "ready"])
def test_reads_stay_allowed_in_every_setup_state(state: str) -> None:
    """AC-5: a read answers in every state, the gated ones included."""
    collection = managed_collection(MANIFEST)
    note_id = managed_note(collection, MANIFEST, VOCABULARY, CURRENT)
    client, _, _, _ = wired(collection, state)

    outcome = settle(client.invoke("findNotes", query=note_query(MANIFEST, VOCABULARY)))

    assert outcome == [note_id]


@RED_PHASE
@pytest.mark.p1
@pytest.mark.parametrize(
    ("build", "expected", "state"),
    [
        (lambda: managed_collection(MANIFEST), None, "ready"),
        (stock_collection, "setup_required", "needs_setup"),
        (lambda: _set_up_with(NEWER), "setup_required", "newer_schema"),
    ],
    ids=["ready", "needs-setup", "newer-schema"],
)
def test_an_unknown_state_is_computed_by_the_first_gated_write(
    build: Any, expected: str | None, state: str
) -> None:
    """AC-6: with no state yet (Anki was down at startup), a write computes it, then decides."""
    client, _, gate, _ = wired(build())

    outcome = add_vocabulary(client)

    assert code_of(outcome) == expected
    assert str(gate.state) == state


@RED_PHASE
@pytest.mark.p0
def test_setups_own_apply_is_not_gated() -> None:
    """AC-7: Setup's apply writes while the state is `needs_setup`, and verifies clean."""
    _, store, _, replay = wired(stock_collection(), "needs_setup")

    async def visit_then_apply() -> Any:
        preview = await store.setup_preview()
        return await store.setup_apply(plan_hash(preview.items))

    outcome = settle(visit_then_apply())

    assert code_of(outcome) is None
    assert outcome.items == ()
    assert sent_writes(replay.sent) != []


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(
    ("stored", "expected"),
    [(OLDER, "setup_required"), (NEWER, "setup_required"), ("", "setup_required"), (CURRENT, None)],
    ids=["older", "newer", "empty", "current"],
)
def test_a_note_update_is_refused_when_its_schema_version_differs(
    stored: str, expected: str | None
) -> None:
    """AC-8: `updateNoteFields` on a note whose stored SchemaVersion isn't the manifest's is
    refused before it's sent, even while the state is `ready`.
    """
    collection = managed_collection(MANIFEST)
    note_id = managed_note(collection, MANIFEST, VOCABULARY, stored)
    client, _, _, replay = wired(collection, "ready")

    note = {"id": note_id, "fields": {"Hint": "a hint"}}
    outcome = settle(client.invoke("updateNoteFields", note=note))

    assert code_of(outcome) == expected
    assert sent_writes(replay.sent) == ([] if expected else ["updateNoteFields"])
    assert collection.notes[note_id].fields["Hint"] == ("" if expected else "a hint")


@RED_PHASE
@pytest.mark.p0
def test_apply_refuses_a_newer_schema_before_any_write() -> None:
    """AC-11: an older release never writes over a newer schema: apply is `setup_required`."""
    collection = _missing_deck(NEWER)
    _, store, _, replay = wired(collection)

    async def visit_then_apply() -> Any:
        preview = await store.setup_preview()
        return await store.setup_apply(plan_hash(preview.items))

    outcome = settle(visit_then_apply())

    assert code_of(outcome) == "setup_required"
    assert sent_writes(replay.sent) == []
    assert UNDERSTAND_DECK not in collection.decks

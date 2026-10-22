"""Capture test wiring, shared by the Capture integration tests (tests/integration/
test_anki_capture*.py) and API tests (tests/api/test_captures_*.py).

`wired(collection, ...)` is the real client and store over an in-memory collection
(tests/support/anki_state.py), under the `LanguageLab` Prefix. `other_captures` and
`dev_capture_with_the_id` arrange the Captures a CaptureId lookup must never match.
`store_with(*captures)` is the fake store holding them, for the API tests.
"""

import uuid
from typing import Any

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import build_manifest
from language_lab.adapters.anki.query import note_query
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.captures import Capture
from language_lab.domain.errors import AppError
from language_lab.domain.setup import SetupState
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import Collection, apply_manifest, capture_note, collection_replies

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)
DEV_MANIFEST = build_manifest(DEV)

CAPTURE_QUERY = note_query(MANIFEST, f"{PREFIX} Capture")
VOCABULARY = f"{PREFIX} English Vocabulary"

# Characters the codec escapes, and a newline it turns into <br> (AD-9)
TEXT = "I'd rather <not> jump & leap\nto conclusions."

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


def other_captures(collection: Collection, created_at: str) -> None:
    """Three Captures under fresh CaptureIds, created at the CreatedAt field `created_at`."""
    for _ in range(3):
        capture_note(collection, MANIFEST, str(uuid.uuid4()), "other", created_at)


def dev_capture_with_the_id(collection: Collection, capture_id: str, created_at: str) -> None:
    """A `LanguageLabDev` Capture carrying the same CaptureId: another Prefix, never a match."""
    apply_manifest(collection, DEV_MANIFEST)
    capture_note(collection, DEV_MANIFEST, capture_id, "dev", created_at)


def store_with(*captures: Capture) -> FakeAnkiStore:
    store = FakeAnkiStore()
    for capture in captures:
        store.captures[capture.capture_id] = capture
    return store

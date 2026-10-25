"""Story 5.3 delete setup: a real guarded adapter over the existing collection replay.

Media fixtures intentionally have valid AD-7 names. Reviews are outside the in-memory
collection model, so real review-history removal belongs to released-wheel acceptance.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.catalog import Language
from language_lab.domain.setup import SetupState
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import Collection, collection_replies, item_note
from tests.support.captures import MANIFEST
from tests.support.duplicates import vocabulary
from tests.support.items import note_type_of, stored_fields


def put_item(collection: Collection, *, language: str = "en") -> tuple[str, int]:
    item_id = str(uuid.uuid4())
    wire = vocabulary()
    note_id = item_note(
        collection,
        MANIFEST,
        note_type_of(language, wire),
        item_id,
        stored_fields(wire, item_id),
    )
    return item_id, note_id


def media_names(item_id: str, *, prefix: str = MANIFEST.prefix) -> list[str]:
    """Three AD-7 names of the Item: the Prefix lowercased (spike 2.2)."""
    return [f"{prefix.lower()}_{item_id}_{digit * 12}.mp3" for digit in ("1", "2", "3")]


async def delete_item(store: Any, item_id: str) -> None:
    """Resolve the future method inside the coroutine so settle returns missing-method RED."""
    await store.delete_item(Language.EN, item_id)


class ObservedLock(AnkiLock):
    """The real shared lock, recording holds and whether transport calls are inside it."""

    def __init__(self) -> None:
        super().__init__()
        self.holds = 0
        self.depth = 0
        self.request_depths: list[int] = []

    @asynccontextmanager
    async def hold(self) -> AsyncIterator[None]:
        async with super().hold():
            self.holds += 1
            self.depth += 1
            try:
                yield
            finally:
                self.depth -= 1


def wired_delete(
    collection: Collection,
    *,
    state: str = "ready",
    replies: dict[str, Any] | None = None,
    lock: ObservedLock | None = None,
    manifest: Manifest = MANIFEST,
) -> tuple[AnkiConnectStore, AnkiConnectReplay]:
    gate = SetupGate(manifest)
    gate.set(SetupState(state))
    answers = collection_replies(collection, writes=True) | (replies or {})

    def observe(reply: Any) -> Any:
        def answer(body: Any) -> Any:
            if lock is not None:
                lock.request_depths.append(lock.depth)
            return reply(body) if callable(reply) else reply

        return answer

    replay = AnkiConnectReplay({action: observe(reply) for action, reply in answers.items()})
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(manifest), gate=gate
    )
    store = AnkiConnectStore(client, lock or AnkiLock(), manifest=manifest, gate=gate)
    return store, replay


def action_bodies(replay: AnkiConnectReplay) -> list[dict[str, Any]]:
    bodies: list[dict[str, Any]] = []
    for sent in replay.sent:
        body = sent.body
        if body.get("action") == "multi":
            bodies.extend(body["params"]["actions"])
        else:
            bodies.append(body)
    return bodies

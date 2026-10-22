"""`AnkiConnectStore`: the AnkiStore port over AnkiConnect. Each method is one use case, run
entirely under the Anki lock (AD-5).

With a `SetupGate` shared with the client (AD-19), every SetupState the store computes (the
startup `setup_state()`, each preview, each apply's verification) is set in the gate.

`migrations` (adapters/anki/migrations.py) run only inside a confirmed apply whose plan has a
Migrate item, after its Create and Repair items (FR-7, AD-3). The opt-in repairs the user
checked (entry 11) run last, under the same lock hold.

Create Capture (story 3.1) writes through `client.invoke`, so the Prefix guard and the setup gate
both apply to it (AD-4, AD-19).

List Captures and Get Capture (story 3.2) are reads through `client.invoke`, under one lock hold
each, and not gated (AD-19). Their only query is the exact Capture note type scope; the
CaptureId is matched in Python and never sent (AD-4). Anki ids stay here: a `Capture` has none.

Delete Capture (story 3.3) finds the note the same way and deletes it through `client.invoke`,
so the guard and the gate apply; a CaptureId no Capture holds writes nothing and succeeds.
"""

import asyncio
from collections.abc import Collection, Iterator
from datetime import UTC, datetime
from typing import Any

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.codec import decode_field, encode_field
from language_lab.adapters.anki.guard import is_int
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.migrations import Migration, run_migrations
from language_lab.adapters.anki.query import note_query
from language_lab.adapters.anki.setup_apply import run_plan, run_repairs
from language_lab.adapters.anki.setup_gate import SCHEMA_VERSION_FIELD, SetupGate, read_preview
from language_lab.domain.captures import Capture
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanAction, SetupPreview, SetupState, checked_repairs
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome

POLL_INTERVAL_S = 1.0
SYNC_BUDGET_S = 120.0  # a Sync with AnkiWeb can take far longer than any other action

# API v1 operation states (spike 2.2, Q7)
_SUCCEEDED = "succeeded"
_FAILED = "failed"
# Decided 2026-10-21: a dialog in Anki or a cancelled Sync ends the Sync at once
_GAVE_UP = frozenset({"waitingForUser", "cancelled"})
_AUTH_REQUIRED_TYPE = "authenticationRequired"

# The Capture note type's fields (manifest.py) and the stored CreatedAt format (AD-9)
_TEXT, _CREATED_AT, _CAPTURE_ID = "Text", "CreatedAt", "CaptureId"
_CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _field(info: dict[str, Any], name: str) -> str:
    """Field `name` of one `notesInfo` entry, decoded; `ANKI_UNAVAILABLE` when malformed."""
    fields = info.get("fields")
    field = fields.get(name) if isinstance(fields, dict) else None
    value = field.get("value") if isinstance(field, dict) else None
    if not isinstance(value, str):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return decode_field(value)


def _stored_capture(capture_id: str, info: dict[str, Any]) -> Capture:
    """The Capture a `notesInfo` entry holds, its fields decoded through the codec."""
    try:
        created_at = datetime.strptime(_field(info, _CREATED_AT).strip(), _CREATED_AT_FORMAT)
    except ValueError:
        raise AppError(ErrorCode.ANKI_UNAVAILABLE) from None
    return Capture(capture_id, _field(info, _TEXT), created_at.replace(tzinfo=UTC))


def _capture_model(manifest: Manifest) -> str:
    """The Prefix's Capture note type (manifest.py)."""
    return f"{manifest.prefix} Capture"


def _matching(infos: list[dict[str, Any]], capture_id: str) -> Iterator[dict[str, Any]]:
    """The `notesInfo` entries whose decoded CaptureId is `capture_id` (AD-4)."""
    return (info for info in infos if _field(info, _CAPTURE_ID).strip() == capture_id)


def _failure_outcome(poll: dict[str, Any]) -> SyncOutcome:
    """A failed operation's outcome, from its `error.data.type` (spike 2.2, Q3/Q4)."""
    error = poll.get("error")
    data = error.get("data") if isinstance(error, dict) else None
    kind = data.get("type") if isinstance(data, dict) else None
    if kind == _AUTH_REQUIRED_TYPE:
        return SyncOutcome.AUTH_REQUIRED
    return SyncOutcome.ANKIWEB_UNREACHABLE


class AnkiConnectStore:
    def __init__(
        self,
        client: AnkiConnectClient,
        lock: AnkiLock,
        *,
        manifest: Manifest | None = None,
        gate: SetupGate | None = None,
        migrations: tuple[Migration, ...] = (),
        poll_interval_s: float = POLL_INTERVAL_S,
        sync_budget_s: float = SYNC_BUDGET_S,
    ) -> None:
        self._client = client
        self._lock = lock
        self._manifest = manifest
        self._gate = gate
        self._migrations = migrations
        self._poll_interval_s = poll_interval_s
        self._sync_budget_s = sync_budget_s

    async def reachable(self) -> bool:
        async with self._lock.hold():
            try:
                await self._client.invoke("version")
            except AppError as exc:
                if exc.code is ErrorCode.ANKI_UNAVAILABLE:
                    return False
                raise
            return True

    async def setup_state(self) -> SetupState:
        """The SetupState, from reads only under the lock (AD-19), set in the gate. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        return (await self.setup_preview()).state

    async def setup_preview(self) -> SetupPreview:
        """Read the managed state and diff it against the manifest, with reads only, under one
        lock hold (AD-3, AD-5), with its SetupState, which is set in the gate. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            _, preview = await read_preview(self._client.invoke, manifest)
        self._set_gate(preview)
        return preview

    async def setup_apply(self, plan_hash: str, repairs: Collection[str] = ()) -> SetupPreview:
        """Re-diff, refuse a stale `plan_hash` and then a `newer_schema` Anki before any write,
        run the plan's Create and Repair items, then, when it has a Migrate item, the migrations
        and the SchemaVersion rewrite, then each checked opt-in repair, through the client's
        guarded, ungated path, and verify by a fresh diff, all under one lock hold (AD-3, AD-4,
        AD-5, AD-19). The hash covers the items plus the offered repair rows whose key is in
        `repairs`. Each fresh SetupState is set in the gate. Raises
        `AppError(PLAN_CHANGED | SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            state, before = await read_preview(self._client.invoke, manifest)
            self._set_gate(before)
            checked = checked_repairs(before, repairs)
            if _plan_hash((*before.items, *checked)) != plan_hash:
                raise AppError(ErrorCode.PLAN_CHANGED)
            if before.state is SetupState.NEWER_SCHEMA:
                raise AppError(ErrorCode.SETUP_REQUIRED)
            await run_plan(self._client.invoke_setup, manifest, state, before.items)
            if any(i.action is PlanAction.MIGRATE for i in before.items):
                await run_migrations(self._client.invoke_setup, manifest, self._migrations, state)
            await run_repairs(self._client.invoke_setup, checked)
            _, verified = await read_preview(self._client.invoke, manifest)
            self._set_gate(verified)
        return verified

    async def create_capture(self, capture_id: str, text: str, created_at: datetime) -> Capture:
        """Find the Capture by CaptureId (matched in Python, AD-4) and return it unchanged, or
        add it to `<Prefix>::Captures` and suspend its card (AD-6, AD-20), under one lock hold.
        Raises `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        model = _capture_model(manifest)
        created_at = created_at.astimezone(UTC).replace(microsecond=0)
        async with self._lock.hold():
            stored = await self._find_capture(manifest, capture_id)
            if stored is not None:
                return stored
            fields = {
                _TEXT: text,
                _CREATED_AT: created_at.strftime(_CREATED_AT_FORMAT),
                _CAPTURE_ID: capture_id,
                SCHEMA_VERSION_FIELD: str(manifest.schema_version),
            }
            note_id = await self._client.invoke(
                "addNote",
                note={
                    "deckName": manifest.card_deck(model, 0),
                    "modelName": model,
                    "fields": {name: encode_field(value) for name, value in fields.items()},
                    "options": {"allowDuplicate": True},
                },
            )
            if not is_int(note_id):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            infos = await self._client.invoke("notesInfo", notes=[note_id])
            if not isinstance(infos, list) or len(infos) != 1 or not isinstance(infos[0], dict):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            cards = infos[0].get("cards")
            if not isinstance(cards, list) or not cards:
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            await self._client.invoke("suspend", cards=cards)
        return Capture(capture_id, text, created_at)

    async def list_captures(self) -> list[Capture]:
        """Every Capture of the Prefix, decoded through the codec, newest first by CreatedAt
        (ties by CaptureId), under one lock hold. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            infos = await self._capture_infos(manifest)
        captures = [_stored_capture(_field(info, _CAPTURE_ID).strip(), info) for info in infos]
        captures.sort(key=lambda c: (c.created_at, c.capture_id), reverse=True)
        return captures

    async def get_capture(self, capture_id: str) -> Capture:
        """The Capture whose CaptureId is `capture_id`, matched in Python (AD-4), under one lock
        hold. Raises `AppError(NOT_FOUND | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            stored = await self._find_capture(manifest, capture_id)
        if stored is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return stored

    async def delete_capture(self, capture_id: str) -> None:
        """Delete every note whose CaptureId is `capture_id` (matched in Python, AD-4) with one
        `deleteNotes`, under one lock hold; with none, nothing is written. Raises
        `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            infos = await self._capture_infos(manifest)
            note_ids: list[int] = []
            for info in _matching(infos, capture_id):
                note_id = info.get("noteId")
                if not is_int(note_id):
                    raise AppError(ErrorCode.ANKI_UNAVAILABLE)
                note_ids.append(note_id)
            if note_ids:
                await self._client.invoke("deleteNotes", notes=note_ids)

    async def _capture_infos(self, manifest: Manifest) -> list[dict[str, Any]]:
        """The `notesInfo` entries of the exact Capture scope's `findNotes`, skipping notes
        deleted in between; `ANKI_UNAVAILABLE` on a malformed reply.
        """
        query = note_query(manifest, _capture_model(manifest))
        ids = await self._client.invoke("findNotes", query=query)
        if not isinstance(ids, list):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        if not ids:
            return []
        infos = await self._client.invoke("notesInfo", notes=ids)
        if not isinstance(infos, list) or len(infos) != len(ids):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        entries: list[dict[str, Any]] = []
        for info in infos:
            if info == {}:  # a note deleted since `findNotes`
                continue
            if not isinstance(info, dict):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            entries.append(info)
        return entries

    async def _find_capture(self, manifest: Manifest, capture_id: str) -> Capture | None:
        """The stored Capture whose decoded CaptureId is `capture_id`, from the exact Capture
        scope's `findNotes` and `notesInfo`; None when there is none.
        """
        info = next(_matching(await self._capture_infos(manifest), capture_id), None)
        return None if info is None else _stored_capture(capture_id, info)

    def _set_gate(self, preview: SetupPreview) -> None:
        if self._gate is not None:
            self._gate.set(preview.state)

    def _require_manifest(self) -> Manifest:
        if self._manifest is None:
            raise RuntimeError("AnkiConnectStore was built without a manifest")
        return self._manifest

    async def sync(self) -> SyncOutcome:
        async with self._lock.hold():
            try:
                async with asyncio.timeout(self._sync_budget_s):
                    return await self._sync_to_end()
            except TimeoutError:
                return SyncOutcome.ANKIWEB_UNREACHABLE

    async def _sync_to_end(self) -> SyncOutcome:
        started = await self._client.invoke_v1("collection.sync")
        operation_id = started.get("operationId") if isinstance(started, dict) else None
        if not isinstance(operation_id, str):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        while True:
            poll = await self._client.invoke_v1("operations.get", operationId=operation_id)
            if not isinstance(poll, dict):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            state = poll.get("state")
            if state == _SUCCEEDED:
                return SyncOutcome.OK
            if state == _FAILED:
                return _failure_outcome(poll)
            if state in _GAVE_UP:
                return SyncOutcome.ANKIWEB_UNREACHABLE
            await asyncio.sleep(self._poll_interval_s)

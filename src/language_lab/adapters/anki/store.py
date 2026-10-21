"""`AnkiConnectStore`: the AnkiStore port over AnkiConnect. Each method is one use case, run
entirely under the Anki lock (AD-5).

With a `SetupGate` shared with the client (AD-19), every SetupState the store computes (the
startup `setup_state()`, each preview, each apply's verification) is set in the gate.

`migrations` (adapters/anki/migrations.py) run only inside a confirmed apply whose plan has a
Migrate item, after its Create and Repair items (FR-7, AD-3). The opt-in repairs the user
checked (entry 11) run last, under the same lock hold.
"""

import asyncio
from collections.abc import Collection
from typing import Any

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.migrations import Migration, run_migrations
from language_lab.adapters.anki.setup_apply import run_plan, run_repairs
from language_lab.adapters.anki.setup_gate import SetupGate, read_preview
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanAction, SetupPreview, SetupState
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
            wanted = set(repairs)
            checked = tuple(r for r in before.repairs if r.key in wanted)
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

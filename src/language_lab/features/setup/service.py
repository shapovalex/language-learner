"""Setup readiness (FR-5), preview, and confirmed apply with verify (FR-6).

Readiness: AnkiConnect reachable, Azure and OpenRouter configured, the Prefix. The keys are
checked as configured only, with no live call. The plan: what Setup would change in Anki, with
its hash (AD-3), read without touching Anki. Apply: the plan the user confirmed by its hash,
run to its end and verified (AD-3). The run is a task the service keeps; a request only awaits
it, shielded, so a client that disconnects doesn't cancel it, and a second request while it
runs awaits the same run. `apply_status()` reports it for a screen coming back. Responses
carry ids and names; the Setup screen owns the copy.

Full sync (entry 9, AD-3, AD-17): a plan with a field-changing row (`requiresFullSync`) first
awaits a Sync through the SyncRequester, outside the Anki lock, and is refused with
`sync_required` unless it ends OK (or Sync is disabled, in dev mode). After the run the
SyncRequester is told a full sync is required; readiness reports it as the `fullSync` check
until the user says they uploaded (`full_sync_uploaded()`).

Opt-in repairs (entry 11): the plan lists every leftover the preview offers under `repairs`,
unchecked. `plan(repairs=keys)` re-plans with those rows checked, and its `planHash` covers the
required items plus the checked rows; `apply(plan_hash, repairs)` hands the same keys to the
store, which re-hashes them before any write.

The plan carries the SetupState (AD-19). `start_refresh()` computes it once at startup, in a
task the lifespan doesn't wait for: a failure (Anki down) is logged without its text and the
adapter's gate computes it on demand later. `aclose()` cancels it if it still runs.
"""

import asyncio
import contextlib
import logging
from collections.abc import Collection
from typing import Literal, NotRequired, TypedDict

from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanItem, SetupPreview, SetupState, plan_hash
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome
from language_lab.ports.anki_store import AnkiStore
from language_lab.ports.sync_requester import SyncRequester

_log = logging.getLogger("language_lab.setup")

type CheckId = Literal["ankiConnect", "azure", "openrouter", "fullSync"]

# A Sync before a field change may end so, and the plan goes on (dev mode never Syncs)
_SYNCED = frozenset({SyncOutcome.OK, SyncOutcome.DISABLED})
# What the store's apply refuses with before its first write
_REFUSED_BEFORE_WRITES = frozenset({ErrorCode.PLAN_CHANGED, ErrorCode.SETUP_REQUIRED})


class Check(TypedDict):
    id: CheckId
    ok: bool


class Readiness(TypedDict):
    prefix: str
    checks: list[Check]


class PlanRow(TypedDict):
    action: str
    kind: str
    name: str
    requiresFullSync: bool  # a field change: a one-way full sync follows (AD-3)


class RepairRow(TypedDict):
    key: str  # "<kind>:<name>": what the screen checks and sends back
    action: str
    kind: str
    name: str
    checked: bool
    # Display detail of a card row
    noteType: NotRequired[str]
    card: NotRequired[str]
    deck: NotRequired[str]
    expectedDeck: NotRequired[str]  # a misplaced card's


class UnmanagedRow(TypedDict):
    kind: str
    name: str


class Plan(TypedDict):
    prefix: str
    planHash: str  # camelCase on the wire (Consistency Conventions)
    state: str  # the SetupState
    items: list[PlanRow]
    repairs: list[RepairRow]  # every opt-in repair row offered
    unmanaged: list[UnmanagedRow]


class ApplyResult(TypedDict):
    verified: bool
    # What a fresh preview, with the checked repairs still offered, hashes to while Anki stays
    # as verify found it
    planHash: str
    discrepancies: list[PlanRow]
    fullSyncRequired: bool  # the run's plan changed fields: upload in Anki Desktop


class ApplyStatus(TypedDict):
    state: Literal["idle", "running", "finished"]
    result: ApplyResult | None


def _rows(items: tuple[PlanItem, ...]) -> list[PlanRow]:
    return [
        {
            "action": str(i.action),
            "kind": str(i.kind),
            "name": i.name,
            "requiresFullSync": i.requires_full_sync,
        }
        for i in items
    ]


def _checked(preview: SetupPreview, repairs: Collection[str]) -> tuple[PlanItem, ...]:
    """The offered repair rows whose key is in `repairs`; a key no longer offered drops out."""
    wanted = set(repairs)
    return tuple(r for r in preview.repairs if r.key in wanted)


def _repair_rows(preview: SetupPreview, checked: tuple[PlanItem, ...]) -> list[RepairRow]:
    keys = {r.key for r in checked}
    rows: list[RepairRow] = []
    for r in preview.repairs:
        row: RepairRow = {
            "key": r.key,
            "action": str(r.action),
            "kind": str(r.kind),
            "name": r.name,
            "checked": r.key in keys,
        }
        rows.append({**row, **r.detail})  # type: ignore[typeddict-item]
    return rows


def _result(
    verification: SetupPreview, repairs: Collection[str], *, full_sync_required: bool
) -> ApplyResult:
    """The checked rows still offered are discrepancies too; unchecked ones aren't."""
    still = _checked(verification, repairs)
    discrepancies = (*verification.items, *still)
    return {
        "verified": not discrepancies,
        "planHash": plan_hash(discrepancies),  # a retry re-checks the repairs still offered
        "discrepancies": _rows(discrepancies),
        "fullSyncRequired": full_sync_required,
    }


def _retrieve(task: asyncio.Task[ApplyResult]) -> None:
    """Mark a run's exception as seen: its requests may all have gone away."""
    if not task.cancelled():
        task.exception()


class SetupService:
    def __init__(
        self,
        anki: AnkiStore,
        *,
        sync: SyncRequester,
        prefix: str,
        azure_configured: bool,
        openrouter_configured: bool,
    ) -> None:
        self._anki = anki
        self._sync = sync
        self._prefix = prefix
        self._azure = azure_configured
        self._openrouter = openrouter_configured
        self._run: asyncio.Task[ApplyResult] | None = None
        self._last: ApplyResult | None = None  # the last run that finished
        self._refresh: asyncio.Task[None] | None = None

    async def readiness(self) -> Readiness:
        """Each check on its own, in tile order. `anki_busy` propagates as an `AppError`.
        `fullSync` fails while the last Sync status says a full sync is required.
        """
        status = self._sync.last_status()
        return {
            "prefix": self._prefix,
            "checks": [
                {"id": "ankiConnect", "ok": await self._anki.reachable()},
                {"id": "azure", "ok": self._azure},
                {"id": "openrouter", "ok": self._openrouter},
                {"id": "fullSync", "ok": not (status and status.full_sync_required)},
            ],
        }

    async def plan(self, repairs: Collection[str] = ()) -> Plan:
        """The preview, items in the store's order, with the opt-in repair rows whose key is in
        `repairs` checked and in the hash. `anki_busy`/`anki_unavailable` propagate.
        """
        preview = await self._anki.setup_preview()
        checked = _checked(preview, repairs)
        return {
            "prefix": self._prefix,
            "planHash": plan_hash((*preview.items, *checked)),
            "state": str(preview.state),
            "items": _rows(preview.items),
            "repairs": _repair_rows(preview, checked),
            "unmanaged": [{"kind": str(u.kind), "name": u.name} for u in preview.unmanaged],
        }

    async def apply(self, plan_hash: str, repairs: Collection[str] = ()) -> ApplyResult:
        """Run the confirmed plan, with the checked opt-in `repairs` keys, to its end and return
        the verification. `sync_required` (the
        Sync before a field change didn't end OK), `plan_changed`, `setup_required` (a
        `newer_schema` Anki), `anki_busy` and `anki_unavailable` propagate.
        A cancelled caller leaves the run going.
        """
        if self._run is None or self._run.done():
            self._run = asyncio.create_task(self._apply(plan_hash, tuple(repairs)))
            self._run.add_done_callback(_retrieve)
        return await asyncio.shield(self._run)

    def apply_status(self) -> ApplyStatus:
        if self._run is not None and not self._run.done():
            return {"state": "running", "result": None}
        if self._last is not None:
            return {"state": "finished", "result": self._last}
        return {"state": "idle", "result": None}

    def full_sync_uploaded(self) -> None:
        """The user uploaded in Anki Desktop: the `fullSync` check passes again."""
        self._sync.set_full_sync_required(False)

    def start_refresh(self) -> None:
        """Compute the SetupState in the background (startup); never fails or waits."""
        self._refresh = asyncio.create_task(self.refresh_state())

    async def refresh_state(self) -> None:
        """Ask the AnkiStore for the SetupState, which the adapter's gate keeps. A failure is
        logged without its text (AD-15); the gate then computes the state on demand.
        """
        try:
            await self._anki.setup_state()
        except AppError as exc:
            _log.warning("setup state not computed at startup: %s", exc.code.value)
        except Exception:  # noqa: BLE001 -- startup goes on; the text may carry content (AD-15)
            _log.warning("setup state not computed at startup")

    async def aclose(self) -> None:
        """Cancel a startup refresh or a run still going (shutdown)."""
        refresh, self._refresh = self._refresh, None
        if refresh is not None and not refresh.done():
            refresh.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await refresh
        run, self._run = self._run, None
        if run is not None and not run.done():
            run.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await run

    async def _apply(self, plan_hash: str, repairs: Collection[str]) -> ApplyResult:
        preview = await self._anki.setup_preview()
        field_change = any(i.requires_full_sync for i in preview.items)
        # A stale hash or a newer-schema Anki goes straight to the store, which refuses it
        fresh = _plan_hash((*preview.items, *_checked(preview, repairs)))
        applicable = fresh == plan_hash and preview.state is not SetupState.NEWER_SCHEMA
        if field_change and applicable:
            # Before the Anki lock is taken: the Sync holds it itself (AD-5, AD-17)
            status = await self._sync.request_and_wait()
            if status.outcome not in _SYNCED:
                raise AppError(ErrorCode.SYNC_REQUIRED)
        try:
            verification = await self._anki.setup_apply(plan_hash, repairs)
        except AppError as exc:
            # Those two refuse before any write; any other may follow a field already added
            if field_change and exc.code not in _REFUSED_BEFORE_WRITES:
                self._sync.set_full_sync_required(True)
            raise
        if field_change:
            self._sync.set_full_sync_required(True)
        result = _result(verification, repairs, full_sync_required=field_change)
        self._last = result  # a run that raised isn't recorded
        return result

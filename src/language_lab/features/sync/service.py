"""`SyncService`: the SyncRequester port, coalescing every request into at most one running and
one pending Sync (AD-17). Each Sync goes through `AnkiStore.sync`, which holds the Anki lock.

A failure is logged as one line and kept as the last status. It is never raised, so a failing
or hung AnkiConnect fails no request. The status lives in memory only (AD-2).

Full sync required (entry 9): Sync never reports it (spike 2.2, Q2), so Setup sets it with
`set_full_sync_required()` after a field change. Every status recorded or returned from then on
carries it, across later Syncs that end OK, until it is set again (the user says they uploaded).
"""

import asyncio
import dataclasses
import logging

from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.sync import SyncOutcome, SyncStatus
from language_lab.ports.anki_store import AnkiStore

_log = logging.getLogger("language_lab.sync")

_DISABLED = SyncStatus(SyncOutcome.DISABLED)
_CANCELLED = SyncStatus(SyncOutcome.ANKI_UNAVAILABLE)  # a Sync cut short by shutdown
_STORE_FAILURES = {
    ErrorCode.ANKI_UNAVAILABLE: SyncOutcome.ANKI_UNAVAILABLE,
    ErrorCode.ANKI_BUSY: SyncOutcome.ANKI_BUSY,
}


class SyncService:
    """With `enabled=False` (dev mode) it never calls the store."""

    def __init__(self, anki: AnkiStore, *, enabled: bool) -> None:
        self._anki = anki
        self._enabled = enabled
        self._last: SyncStatus | None = None
        self._full_sync_required = False
        self._running: asyncio.Task[None] | None = None
        # Resolved with the status of the Sync that starts when the running one ends
        self._pending: asyncio.Future[SyncStatus] | None = None

    async def request(self) -> None:
        if self._enabled:
            self._submit()

    async def request_and_wait(self) -> SyncStatus:
        if not self._enabled:
            return self._flagged(_DISABLED)
        # Shielded: a cancelled caller must not cancel a Sync other callers share
        return self._flagged(await asyncio.shield(self._submit()))

    def last_status(self) -> SyncStatus | None:
        """The last Sync's status; with no Sync yet (dev mode), `DISABLED` while a full sync is
        required, else None.
        """
        if self._last is None:
            return SyncStatus(SyncOutcome.DISABLED, True) if self._full_sync_required else None
        return self._flagged(self._last)

    def set_full_sync_required(self, required: bool) -> None:
        self._full_sync_required = required

    def _flagged(self, status: SyncStatus) -> SyncStatus:
        return dataclasses.replace(status, full_sync_required=self._full_sync_required)

    async def aclose(self) -> None:
        """Cancel the running Sync and drop the pending one (shutdown, after its capped wait).

        Their waiters get `ANKI_UNAVAILABLE`.
        """
        pending, self._pending = self._pending, None
        if pending is not None and not pending.done():
            pending.set_result(_CANCELLED)  # its waiters get a status, never an exception
        running, self._running = self._running, None
        if running is not None and not running.done():
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)

    def _submit(self) -> asyncio.Future[SyncStatus]:
        """The future of a Sync that starts now if none is running, else of the pending one."""
        if self._running is None:
            waiter: asyncio.Future[SyncStatus] = asyncio.get_running_loop().create_future()
            self._start(waiter)
            return waiter
        if self._pending is None:
            self._pending = asyncio.get_running_loop().create_future()
        return self._pending

    def _start(self, waiter: asyncio.Future[SyncStatus]) -> None:
        self._running = asyncio.create_task(self._run(waiter))

    async def _run(self, waiter: asyncio.Future[SyncStatus]) -> None:
        try:
            status = await self._sync_once()
        except asyncio.CancelledError:
            if not waiter.done():  # every waiter gets a status, even at shutdown
                waiter.set_result(_CANCELLED)
            raise
        if not waiter.done():
            waiter.set_result(status)
        pending, self._pending = self._pending, None
        if pending is None:
            self._running = None
        else:
            self._start(pending)

    async def _sync_once(self) -> SyncStatus:
        try:
            outcome = await self._anki.sync()
        except AppError as exc:
            outcome = _STORE_FAILURES.get(exc.code, SyncOutcome.ANKI_UNAVAILABLE)
        except Exception:  # noqa: BLE001 -- a bug must not kill the pending chain
            outcome = SyncOutcome.ANKI_UNAVAILABLE
        status = SyncStatus(outcome, self._full_sync_required)
        self._last = status
        if outcome is SyncOutcome.OK:
            _log.info("Sync with AnkiWeb: %s", outcome.value)
        else:
            _log.warning("Sync with AnkiWeb failed: %s", outcome.value)
        return status

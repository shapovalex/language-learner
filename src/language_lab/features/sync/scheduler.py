"""`SyncScheduler`: the lifespan's Syncs (AD-17, FR-36). One at startup, not awaited; one every
five minutes; one at graceful shutdown, awaited for at most 30 s so a hung AnkiConnect can't
hold the process. Disabled (dev mode), it schedules nothing.
"""

import asyncio
import contextlib
import logging
from typing import Protocol

from language_lab.ports.sync_requester import SyncRequester

INTERVAL_S = 300.0
SHUTDOWN_CAP_S = 30.0

_log = logging.getLogger("language_lab.sync")


class Clock(Protocol):
    async def sleep(self, seconds: float) -> None: ...


class AsyncioClock:
    """Real time."""

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class SyncScheduler:
    def __init__(
        self, requester: SyncRequester, clock: Clock | None = None, *, enabled: bool
    ) -> None:
        self._requester = requester
        self._clock = clock or AsyncioClock()
        self._enabled = enabled
        self._interval: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Request the startup Sync without waiting for it, then one every `INTERVAL_S`."""
        if not self._enabled:
            return
        await self._requester.request()
        self._interval = asyncio.create_task(self._every_interval())

    async def stop(self) -> None:
        """Stop the interval, then request a Sync and wait for it, at most `SHUTDOWN_CAP_S`."""
        if not self._enabled:
            return
        if self._interval is not None:
            self._interval.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._interval
            self._interval = None
        synced = asyncio.create_task(self._requester.request_and_wait())
        capped = asyncio.create_task(self._clock.sleep(SHUTDOWN_CAP_S))
        await asyncio.wait({synced, capped}, return_when=asyncio.FIRST_COMPLETED)
        if not synced.done():
            _log.warning(
                "Shutdown Sync still running after %g s; not waiting for it", SHUTDOWN_CAP_S
            )
        for task in (synced, capped):
            task.cancel()
        await asyncio.gather(synced, capped, return_exceptions=True)

    async def _every_interval(self) -> None:
        while True:
            await self._clock.sleep(INTERVAL_S)
            await self._requester.request()

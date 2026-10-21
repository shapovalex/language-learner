"""Fake AnkiStore: the port in memory, kept in step with `ports/anki_store.py` (AD-1)."""

import asyncio

from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.sync import SyncOutcome


class FakeAnkiStore:
    """`available` says whether AnkiConnect answers; `busy` makes every call wait out the lock.

    `sync()` returns `outcome`. With `gated=True` each `sync()` stays in flight until
    `finish()` ends it, oldest first. Counts every `sync()` call (`sync_calls`), the ones that
    returned an outcome (`syncs`), and how many run at once (`in_flight`, `max_in_flight`).
    """

    def __init__(
        self,
        *,
        available: bool = True,
        busy: bool = False,
        gated: bool = False,
        outcome: SyncOutcome = SyncOutcome.OK,
    ) -> None:
        self.available = available
        self.busy = busy
        self.gated = gated
        self.outcome = outcome
        self.sync_calls = 0
        self.syncs = 0
        self.in_flight = 0
        self.max_in_flight = 0
        self._gates: list[asyncio.Future[SyncOutcome | ErrorCode]] = []

    async def reachable(self) -> bool:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        return self.available

    async def sync(self) -> SyncOutcome:
        self.sync_calls += 1
        if not self.gated:
            if self.busy:
                raise AppError(ErrorCode.ANKI_BUSY)
            if not self.available:
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            self.syncs += 1
            return self.outcome
        gate: asyncio.Future[SyncOutcome | ErrorCode] = asyncio.get_running_loop().create_future()
        self._gates.append(gate)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            end = await gate
        finally:
            self.in_flight -= 1
            if gate in self._gates:
                self._gates.remove(gate)
        if isinstance(end, ErrorCode):
            raise AppError(end)
        self.syncs += 1
        return end

    def finish(self, end: SyncOutcome | ErrorCode = SyncOutcome.OK) -> None:
        """End the oldest in-flight gated `sync()`: return a `SyncOutcome`, raise an `ErrorCode`."""
        gate = self._gates.pop(0)
        gate.set_result(end)

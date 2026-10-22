"""Fake AnkiStore: the port in memory, kept in step with `ports/anki_store.py` (AD-1)."""

import asyncio
from collections.abc import Collection
from datetime import datetime

from language_lab.domain.captures import Capture
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import SetupPreview, SetupState
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome


class FakeAnkiStore:
    """`available` says whether AnkiConnect answers; `busy` makes every call wait out the lock.

    `setup_preview()` returns `preview` (an empty one by default). `setup_state()` returns its
    `state`, raises as `setup_preview()` does, and counts every call (`state_calls`).

    `setup_apply(plan_hash, repairs)` raises `plan_changed` unless the hash is the preview's
    items plus its offered `repairs` rows whose key is in `repairs` (as the adapter's), then makes
    `verified` (empty by default) the preview and returns it. With `apply_gated=True` each one
    stays in flight until `finish_apply()` ends it, oldest first. Counts every call
    (`apply_calls`) and the ones that returned a verification (`applies`).

    `sync()` returns `outcome`. With `gated=True` each `sync()` stays in flight until
    `finish()` ends it, oldest first. Counts every `sync()` call (`sync_calls`), the ones that
    returned an outcome (`syncs`), and how many run at once (`in_flight`, `max_in_flight`).

    `create_capture()` is create-or-noop by CaptureId over `captures` (AD-20): a known CaptureId
    returns the stored Capture unchanged. It raises `anki_busy` or `anki_unavailable` as the
    other methods do.
    """

    def __init__(
        self,
        *,
        available: bool = True,
        busy: bool = False,
        gated: bool = False,
        outcome: SyncOutcome = SyncOutcome.OK,
        preview: SetupPreview | None = None,
        verified: SetupPreview | None = None,
        apply_gated: bool = False,
    ) -> None:
        self.available = available
        self.busy = busy
        self.gated = gated
        self.outcome = outcome
        self.preview = preview if preview is not None else SetupPreview()
        self.state_calls = 0
        self.sync_calls = 0
        self.syncs = 0
        self.in_flight = 0
        self.max_in_flight = 0
        self._gates: list[asyncio.Future[SyncOutcome | ErrorCode]] = []
        self.verified = verified if verified is not None else SetupPreview()
        self.apply_gated = apply_gated
        self.apply_calls = 0
        self.applies = 0
        self._apply_gates: list[asyncio.Future[ErrorCode | None]] = []
        self.captures: dict[str, Capture] = {}

    async def reachable(self) -> bool:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        return self.available

    async def setup_state(self) -> SetupState:
        self.state_calls += 1
        return (await self.setup_preview()).state

    async def setup_preview(self) -> SetupPreview:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return self.preview

    async def setup_apply(self, plan_hash: str, repairs: Collection[str] = ()) -> SetupPreview:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        wanted = set(repairs)
        checked = tuple(r for r in self.preview.repairs if r.key in wanted)
        if plan_hash != _plan_hash((*self.preview.items, *checked)):
            raise AppError(ErrorCode.PLAN_CHANGED)
        self.apply_calls += 1
        if self.apply_gated:
            gate: asyncio.Future[ErrorCode | None] = asyncio.get_running_loop().create_future()
            self._apply_gates.append(gate)
            try:
                end = await gate
            finally:
                if gate in self._apply_gates:
                    self._apply_gates.remove(gate)
            if end is not None:
                raise AppError(end)
        self.preview = self.verified
        self.applies += 1
        return self.verified

    def finish_apply(self, end: ErrorCode | None = None) -> None:
        """End the oldest in-flight gated `setup_apply()`: verify, or raise an `ErrorCode`."""
        gate = self._apply_gates.pop(0)
        gate.set_result(end)

    async def create_capture(self, capture_id: str, text: str, created_at: datetime) -> Capture:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return self.captures.setdefault(capture_id, Capture(capture_id, text, created_at))

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

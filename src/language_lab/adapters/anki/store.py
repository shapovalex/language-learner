"""`AnkiConnectStore`: the AnkiStore port over AnkiConnect. Each method is one use case, run
entirely under the Anki lock (AD-5).
"""

import asyncio
from typing import Any

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.domain.errors import AppError, ErrorCode
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
        poll_interval_s: float = POLL_INTERVAL_S,
        sync_budget_s: float = SYNC_BUDGET_S,
    ) -> None:
        self._client = client
        self._lock = lock
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

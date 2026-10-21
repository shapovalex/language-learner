"""Fake SyncRequester: the port in memory, kept in step with `ports/sync_requester.py` (AD-1)."""

import dataclasses

from language_lab.domain.sync import SyncOutcome, SyncStatus


class FakeSyncRequester:
    """Counts `request()` and `request_and_wait()` calls; both make no Sync.

    `request_and_wait()` returns `status` and records it as the last status. Set `status`
    to the status the next awaited Sync should end with. `set_full_sync_required()` marks every
    status from then on, as `SyncService` does.
    """

    def __init__(self, status: SyncStatus | None = None) -> None:
        self.status = status or SyncStatus(SyncOutcome.OK)
        self.requests = 0
        self.waited_requests = 0
        self._last: SyncStatus | None = None
        self.full_sync_required = False

    async def request(self) -> None:
        self.requests += 1

    async def request_and_wait(self) -> SyncStatus:
        self.waited_requests += 1
        self._last = dataclasses.replace(self.status, full_sync_required=self.full_sync_required)
        return self._last

    def last_status(self) -> SyncStatus | None:
        if self._last is None and self.full_sync_required:
            return SyncStatus(SyncOutcome.DISABLED, True)
        if self._last is None:
            return None
        return dataclasses.replace(self._last, full_sync_required=self.full_sync_required)

    def set_full_sync_required(self, required: bool) -> None:
        self.full_sync_required = required

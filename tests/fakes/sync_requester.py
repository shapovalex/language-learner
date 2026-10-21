"""Fake SyncRequester: the port in memory, kept in step with `ports/sync_requester.py` (AD-1)."""

from language_lab.domain.sync import SyncOutcome, SyncStatus


class FakeSyncRequester:
    """Counts `request()` and `request_and_wait()` calls; both make no Sync.

    `request_and_wait()` returns `status` and records it as the last status. Set `status`
    to the status the next awaited Sync should end with.
    """

    def __init__(self, status: SyncStatus | None = None) -> None:
        self.status = status or SyncStatus(SyncOutcome.OK)
        self.requests = 0
        self.waited_requests = 0
        self._last: SyncStatus | None = None

    async def request(self) -> None:
        self.requests += 1

    async def request_and_wait(self) -> SyncStatus:
        self.waited_requests += 1
        self._last = self.status
        return self.status

    def last_status(self) -> SyncStatus | None:
        return self._last

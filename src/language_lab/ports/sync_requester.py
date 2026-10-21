"""The SyncRequester port (AD-1, AD-17): how a feature asks for a Sync with AnkiWeb.

`features/sync` implements it and `app.py` injects it; no feature imports `features/sync`.
"""

from typing import Protocol

from language_lab.domain.sync import SyncStatus


class SyncRequester(Protocol):
    async def request(self) -> None:
        """Ask for a Sync and return at once. Never raises."""
        ...

    async def request_and_wait(self) -> SyncStatus:
        """The status of a Sync that started after this call. Never raises."""
        ...

    def last_status(self) -> SyncStatus | None:
        """The latest finished Sync's status, from memory; None before the first one."""
        ...

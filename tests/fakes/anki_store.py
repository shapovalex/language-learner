"""Fake AnkiStore: the port in memory, kept in step with `ports/anki_store.py` (AD-1)."""

from language_lab.domain.errors import AppError, ErrorCode


class FakeAnkiStore:
    """`available` says whether AnkiConnect answers; `busy` makes every call wait out the lock.

    Counts `sync()` calls that succeeded.
    """

    def __init__(self, *, available: bool = True, busy: bool = False) -> None:
        self.available = available
        self.busy = busy
        self.syncs = 0

    async def reachable(self) -> bool:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        return self.available

    async def sync(self) -> None:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        self.syncs += 1

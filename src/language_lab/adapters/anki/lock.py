"""The one global Anki lock (AD-5): waiting longer than 15 s for it is `anki_busy`."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from language_lab.domain.errors import AppError, ErrorCode

LOCK_WAIT_S = 15.0


class AnkiLock:
    def __init__(self, wait_seconds: float = LOCK_WAIT_S) -> None:
        self.wait_seconds = wait_seconds
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def hold(self) -> AsyncIterator[None]:
        """Hold the lock for the block. Raises `AppError(ANKI_BUSY)` if the wait runs out."""
        try:
            async with asyncio.timeout(self.wait_seconds):
                await self._lock.acquire()
        except TimeoutError:
            raise AppError(ErrorCode.ANKI_BUSY) from None
        try:
            yield
        finally:
            self._lock.release()

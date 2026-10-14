"""`AnkiConnectStore`: the AnkiStore port over AnkiConnect. Each method is one use case, run
entirely under the Anki lock (AD-5).
"""

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.domain.errors import AppError, ErrorCode


class AnkiConnectStore:
    def __init__(self, client: AnkiConnectClient, lock: AnkiLock) -> None:
        self._client = client
        self._lock = lock

    async def reachable(self) -> bool:
        async with self._lock.hold():
            try:
                await self._client.invoke("version")
            except AppError as exc:
                if exc.code is ErrorCode.ANKI_UNAVAILABLE:
                    return False
                raise
            return True

    async def sync(self) -> None:
        async with self._lock.hold():
            await self._client.invoke("sync")

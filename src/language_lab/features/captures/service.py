"""Create Capture: the server stamps CreatedAt, and the AnkiStore does the rest (AD-20)."""

from datetime import UTC, datetime

from language_lab.domain.captures import Capture
from language_lab.ports.anki_store import AnkiStore


class CaptureService:
    def __init__(self, anki: AnkiStore) -> None:
        self._anki = anki

    async def create(self, capture_id: str, text: str) -> Capture:
        """The stored Capture: the new one, or on a retry the one already in Anki, unchanged.
        Raises `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        created_at = datetime.now(UTC).replace(microsecond=0)
        return await self._anki.create_capture(capture_id, text, created_at)

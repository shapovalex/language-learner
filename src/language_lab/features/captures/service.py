"""Captures: Create Capture, where the server stamps CreatedAt and the AnkiStore does the rest
(AD-20), the reads, List and Get Capture, and Delete Capture.
"""

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

    async def list_all(self) -> list[Capture]:
        """Every Capture, newest first. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`."""
        return await self._anki.list_captures()

    async def get(self, capture_id: str) -> Capture:
        """The Capture `capture_id`. Raises `AppError(NOT_FOUND | ANKI_UNAVAILABLE | ANKI_BUSY)`."""
        return await self._anki.get_capture(capture_id)

    async def delete(self, capture_id: str) -> None:
        """Delete the Capture `capture_id`; one already gone is no error. Raises
        `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        await self._anki.delete_capture(capture_id)

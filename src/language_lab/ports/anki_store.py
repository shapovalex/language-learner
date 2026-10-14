"""The AnkiStore port (AD-1, AD-5): every Anki use case a feature can ask for.

Each method is one complete use case that the adapter runs under the Anki lock. This tracer
declares readiness and sync only; later entries add methods here, to the AnkiConnect adapter and
to the fake in tests/fakes/ together.
"""

from typing import Protocol


class AnkiStore(Protocol):
    async def reachable(self) -> bool:
        """Whether AnkiConnect answers. Raises `AppError(ANKI_BUSY)` when the lock wait runs out."""
        ...

    async def sync(self) -> None:
        """Ask Anki to Sync with AnkiWeb. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`."""
        ...

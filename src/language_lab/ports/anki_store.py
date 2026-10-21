"""The AnkiStore port (AD-1, AD-5): every Anki use case a feature can ask for.

Each method is one complete use case that the adapter runs under the Anki lock: readiness, sync
and the Setup preview so far. Later entries add methods here, to the AnkiConnect adapter and to
the fake in tests/fakes/ together.
"""

from typing import Protocol

from language_lab.domain.setup import SetupPreview
from language_lab.domain.sync import SyncOutcome


class AnkiStore(Protocol):
    async def reachable(self) -> bool:
        """Whether AnkiConnect answers. Raises `AppError(ANKI_BUSY)` when the lock wait runs out."""
        ...

    async def setup_preview(self) -> SetupPreview:
        """What Setup would change in Anki, from reads only (FR-6, AD-3): the plan items and the
        unrecognized content under the Prefix. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def sync(self) -> SyncOutcome:
        """Sync Anki with AnkiWeb to its end and return how it ended (`OK`, `AUTH_REQUIRED` or
        `ANKIWEB_UNREACHABLE`). Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

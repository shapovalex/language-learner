"""The AnkiStore port (AD-1, AD-5): every Anki use case a feature can ask for.

Each method is one complete use case that the adapter runs under the Anki lock: readiness, sync,
the SetupState, and the Setup preview and apply so far. Later entries add methods here, to the
AnkiConnect adapter and to the fake in tests/fakes/ together.
"""

from typing import Protocol

from language_lab.domain.setup import SetupPreview, SetupState
from language_lab.domain.sync import SyncOutcome


class AnkiStore(Protocol):
    async def reachable(self) -> bool:
        """Whether AnkiConnect answers. Raises `AppError(ANKI_BUSY)` when the lock wait runs out."""
        ...

    async def setup_state(self) -> SetupState:
        """Whether Anki is ready for feature writes (AD-19), from reads only under the lock.
        Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def setup_preview(self) -> SetupPreview:
        """What Setup would change in Anki, from reads only (FR-6, AD-3): the plan items, the
        unrecognized content under the Prefix, and the SetupState (AD-19). Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def setup_apply(self, plan_hash: str) -> SetupPreview:
        """Apply the confirmed plan and verify it (FR-6, AD-3), under one lock hold.

        Re-reads and diffs Anki, and raises `AppError(PLAN_CHANGED)` before any write when
        `plan_hash` isn't the fresh plan's, then `AppError(SETUP_REQUIRED)` when Anki was set
        up by a newer release (`newer_schema`). Runs every Create and Repair item, then, for a
        Migrate item, the migrations and the SchemaVersion rewrite of older notes; a write that
        fails doesn't end the run. Returns a fresh diff as the
        verification: its items are the discrepancies, with its fresh SetupState. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def sync(self) -> SyncOutcome:
        """Sync Anki with AnkiWeb to its end and return how it ended (`OK`, `AUTH_REQUIRED` or
        `ANKIWEB_UNREACHABLE`). Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

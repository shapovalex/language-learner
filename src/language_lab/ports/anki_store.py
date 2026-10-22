"""The AnkiStore port (AD-1, AD-5): every Anki use case a feature can ask for.

Each method is one complete use case that the adapter runs under the Anki lock: readiness, sync,
the SetupState, the Setup preview and apply, Create Capture, and List and Get Capture so far.
Later entries add methods here, to the AnkiConnect adapter and to the fake in tests/fakes/ together.
"""

from collections.abc import Collection
from datetime import datetime
from typing import Protocol

from language_lab.domain.captures import Capture
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
        unrecognized content under the Prefix, the opt-in repair rows (`repairs`, entry 11),
        and the SetupState (AD-19), which only the items decide. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def setup_apply(self, plan_hash: str, repairs: Collection[str] = ()) -> SetupPreview:
        """Apply the confirmed plan and verify it (FR-6, AD-3), under one lock hold.

        Re-reads and diffs Anki, and raises `AppError(PLAN_CHANGED)` before any write when
        `plan_hash` isn't the fresh plan's: its items plus the offered repair rows whose key is
        in `repairs` (a key no longer offered drops out, so the hash differs). Then raises
        `AppError(SETUP_REQUIRED)` when Anki was set up by a newer release (`newer_schema`).
        Runs every Create and Repair item, then, for a Migrate item, the migrations and the
        SchemaVersion rewrite of older notes, then each checked repair; a write that fails
        doesn't end the run. Returns a fresh diff as the verification: its items are the
        discrepancies, its repairs every row still offered, with its fresh SetupState. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def sync(self) -> SyncOutcome:
        """Sync Anki with AnkiWeb to its end and return how it ended (`OK`, `AUTH_REQUIRED` or
        `ANKIWEB_UNREACHABLE`). Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def create_capture(self, capture_id: str, text: str, created_at: datetime) -> Capture:
        """Create the Capture `capture_id`, or return the one already stored (AD-20), under one
        lock hold. A new one is added to `<Prefix>::Captures` with `text` and `created_at` and
        its card suspended (AD-6); a stored one comes back unchanged and nothing is written. The
        CaptureId is matched in Python, never in a query (AD-4). Raises
        `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def list_captures(self) -> list[Capture]:
        """Every Capture of the Prefix, its fields decoded through the codec, newest first by
        CreatedAt (equal times by CaptureId, descending), from reads only under one lock hold;
        not gated (AD-19). Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

    async def get_capture(self, capture_id: str) -> Capture:
        """The Capture `capture_id`, matched in Python and never in a query (AD-4), from reads
        only under one lock hold; not gated (AD-19). Raises
        `AppError(NOT_FOUND | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        ...

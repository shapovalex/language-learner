"""What a Sync with AnkiWeb ended as (AD-17): the outcome and the status kept in memory."""

from dataclasses import dataclass
from enum import StrEnum

from language_lab.domain.errors import ErrorCode


class SyncOutcome(StrEnum):
    OK = "ok"
    AUTH_REQUIRED = "auth_required"
    ANKIWEB_UNREACHABLE = "ankiweb_unreachable"
    ANKI_UNAVAILABLE = ErrorCode.ANKI_UNAVAILABLE.value
    ANKI_BUSY = ErrorCode.ANKI_BUSY.value
    DISABLED = "disabled"


@dataclass(frozen=True)
class SyncStatus:
    """The latest Sync's outcome. `full_sync_required` is set by Setup (entry 9), not by a Sync."""

    outcome: SyncOutcome
    full_sync_required: bool = False

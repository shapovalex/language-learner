"""A Capture (FR-9): a free-text note saved for later, under a client-generated CaptureId."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Capture:
    """`capture_id` is a lowercase UUIDv4 (AD-8); `created_at` is aware UTC, to the second."""

    capture_id: str
    text: str
    created_at: datetime

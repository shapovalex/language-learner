"""Pronunciation review (FR-30, FR-34): the Rating, a queued Pronounce Card and the queue.

A card id is an opaque Anki int to features and the client: the Rating must address one Card
and carry its `reps` (AD-20). Story 7.1 amends AD-8 for this one id; nothing else leaves the
adapter.
"""

from dataclasses import dataclass
from enum import StrEnum

from language_lab.domain.catalog import Category


class Rating(StrEnum):
    """The learner's Rating of a Card; the Anki adapter alone maps it to an ease."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


@dataclass(frozen=True)
class PronounceCard:
    """One queued Pronounce Card: `audio` is the managed Reference clip's name, or None."""

    card_id: int
    item_id: str
    reps: int
    category: Category
    target: str
    audio: str | None

    def wire(self) -> dict[str, object]:
        return {
            "cardId": self.card_id,
            "itemId": self.item_id,
            "reps": self.reps,
            "category": self.category.value,
            "target": self.target,
            "audio": self.audio,
        }


@dataclass(frozen=True)
class PronunciationQueue:
    """The Language's queue in FR-30 order (due first, then new) and its counts."""

    due: int
    new: int
    cards: tuple[PronounceCard, ...]

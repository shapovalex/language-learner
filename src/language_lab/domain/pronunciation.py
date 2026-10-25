"""Pronunciation review (FR-30, FR-34): the Rating, a queued Pronounce Card and the queue.

A card id is an opaque Anki int to features and the client: the Rating must address one Card
and carry its `reps` (AD-20). Story 7.1 amends AD-8 for this one id; nothing else leaves the
adapter.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from language_lab.domain.catalog import Category, Language


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


AssessmentLocale = Literal["en-US", "fr-CA"]

ASSESSMENT_LOCALE: dict[Language, AssessmentLocale] = {Language.EN: "en-US", Language.FR: "fr-CA"}
"""The one assessment locale per Language (not the Voice locales in `catalog.LOCALES`)."""

Score = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]


class _Feedback(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, frozen=True)

    def wire(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True)


class Phoneme(_Feedback):
    symbol: str
    score: Score


class Positions(_Feedback):
    start: Score | None = None
    middle: Score | None = None
    end: Score | None = None

    @classmethod
    def from_scores(cls, scores: list[float]) -> Self:
        buckets: list[list[float]] = [[], [], []]
        for i, score in enumerate(scores):
            buckets[min(2, 3 * i // len(scores))].append(score)
        return cls(
            **{
                name: min(bucket) if bucket else None
                for name, bucket in zip(("start", "middle", "end"), buckets, strict=True)
            }
        )


class AssessedWord(_Feedback):
    text: Annotated[str, Field(min_length=1)]
    score: Score
    error_type: Annotated[str, Field(alias="errorType", min_length=1)]
    phonemes: tuple[Phoneme, ...] = ()
    positions: Positions | None = None


class Assessment(_Feedback):
    """Validated, ephemeral feedback. Locale policy lives here, outside the provider/UI."""

    locale: AssessmentLocale
    overall: Score
    accuracy: Score
    fluency: Score
    completeness: Score
    prosody: Score | None = None
    words: Annotated[tuple[AssessedWord, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def locale_feedback(self) -> Self:
        if self.locale == "fr-CA":
            object.__setattr__(self, "prosody", None)
            object.__setattr__(
                self,
                "words",
                tuple(
                    word.model_copy(
                        update={
                            "positions": word.positions
                            or Positions.from_scores([p.score for p in word.phonemes]),
                            "phonemes": (),
                        }
                    )
                    for word in self.words
                ),
            )
        else:
            object.__setattr__(
                self,
                "words",
                tuple(word.model_copy(update={"positions": None}) for word in self.words),
            )
        return self

    @classmethod
    def from_azure(cls, locale: str, reply: object) -> Self | None:
        """Parse the REST flat NBest form; malformed replies fail closed at the adapter."""
        if not isinstance(reply, dict) or reply.get("RecognitionStatus") != "Success":
            raise ValueError
        best = reply["NBest"][0]
        words = tuple(
            AssessedWord(
                text=word["Word"],
                score=word["AccuracyScore"],
                errorType=word["ErrorType"],
                phonemes=tuple(
                    Phoneme(symbol=p["Phoneme"], score=p["AccuracyScore"])
                    for p in word.get("Phonemes", [])
                ),
            )
            for word in best["Words"]
        )
        if not words:
            raise ValueError
        if all(word.error_type == "Omission" for word in words):
            return None
        return cls(
            locale=locale,
            overall=best["PronScore"],
            accuracy=best["AccuracyScore"],
            fluency=best["FluencyScore"],
            completeness=best["CompletenessScore"],
            # Before validation: a French ProsodyScore is never read, so it can't fail the reply
            prosody=best.get("ProsodyScore") if locale == "en-US" else None,
            words=words,
        )

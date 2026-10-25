"""The shared vocabulary of Items (Consistency Conventions): Language, Category, Exercise, and the
form of an ItemId or CaptureId (AD-8).
"""

from enum import StrEnum

# A UUIDv4 in lowercase canonical form: every ItemId and CaptureId (AD-8)
UUID4 = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


class Language(StrEnum):
    EN = "en"
    FR = "fr"


class Category(StrEnum):
    VOCABULARY = "vocabulary"
    SENTENCE = "sentence"


class Exercise(StrEnum):
    UNDERSTAND = "understand"
    PRODUCE = "produce"
    WRITE = "write"
    PRONOUNCE = "pronounce"


# The Voice locales of each Language, in list order: one French list holds Canada then France
LOCALES: dict[Language, tuple[str, ...]] = {
    Language.EN: ("en-US",),
    Language.FR: ("fr-CA", "fr-FR"),
}

"""The shared vocabulary of Items (Consistency Conventions): Language, Category, Exercise."""

from enum import StrEnum


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

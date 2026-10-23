"""Fake Llm: the port in memory, kept in step with `ports/llm.py` (AD-1)."""

from typing import Any

from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import GeneratedFields, generated_model

# A valid answer per Category, on the wire, when no `reply` is given
_REPLIES: dict[Category, dict[str, Any]] = {
    Category.VOCABULARY: {
        "russian": "делать поспешные выводы",
        "russianAlternatives": [],
        "hint": None,
        "partOfSpeech": "phrase",
        "grammar": None,
        "example": "Let's not jump to conclusions.",
        "exampleRussian": "Давай не будем делать поспешных выводов.",
    },
    Category.SENTENCE: {
        "russian": "Не будем делать поспешных выводов.",
        "russianAlternatives": [],
        "hint": None,
        "note": None,
    },
}


class FakeLlm:
    """Records each `generate()` as `(language, category, target, generation_context)` in
    `requests`, then raises `AppError(error)` or answers `reply` (generated fields on the wire),
    validated with the Category's generated model.
    """

    def __init__(self, reply: dict[str, Any] | None = None, *, error: ErrorCode | None = None):
        self.reply = reply
        self.error = error
        self.requests: list[tuple[Language, Category, str, str]] = []

    async def generate(
        self, language: Language, category: Category, target: str, generation_context: str
    ) -> GeneratedFields:
        self.requests.append((language, category, target, generation_context))
        if self.error is not None:
            raise AppError(self.error)
        reply = _REPLIES[category] if self.reply is None else self.reply
        return generated_model(category).model_validate(reply)

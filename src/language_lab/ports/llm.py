"""The Llm port (AD-1, AD-11): how drafts asks a language model for a Category's generated fields.

`adapters/openrouter` implements it and `app.py` injects it. Epic-maintain-items reuses it for
per-field regeneration, taking the one field it needs from the full generated model.
"""

from typing import Protocol

from language_lab.domain.catalog import Category, Language
from language_lab.domain.items import GeneratedFields


class Llm(Protocol):
    async def generate(
        self, language: Language, category: Category, target: str, generation_context: str
    ) -> GeneratedFields:
        """The generated fields of `target` in `language` and `category`, with the Generation
        context as a hint that is used once and never kept.

        Raises `AppError(LLM_FAILED)` when the model can't be reached, and
        `AppError(LLM_INVALID_OUTPUT)` when its answer fails validation twice.
        """
        ...

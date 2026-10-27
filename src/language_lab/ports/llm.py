"""The Llm port (AD-1, AD-11): how drafts asks a language model for a Category's generated fields,
and how the Target helpers ask it for a grammar verdict and CEFR example sentences.

`adapters/openrouter` implements it and `app.py` injects it. Epic-maintain-items reuses it for
per-field regeneration, taking the one field it needs from the full generated model.
"""

from typing import Protocol

from language_lab.domain.catalog import Category, Language
from language_lab.domain.helpers import ExampleSet, GrammarCheck
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

    async def check_grammar(
        self, language: Language, category: Category, target: str
    ) -> GrammarCheck:
        """Whether `target` is grammatical in `language`, its corrected form when it isn't, and
        a short explanation in Russian. Same errors as `generate`.
        """
        ...

    async def examples(self, language: Language, target: str, context: str) -> ExampleSet:
        """Five example sentences using `target` in `language` for each CEFR level A1 to C2,
        each with its Russian translation. `context` is a hint used once and never kept.
        Same errors as `generate`.
        """
        ...

"""The Target helpers: the grammar verdict of a Target, the CEFR example sentences of a word
or phrase and the Russian translation of a Capture, asked of the same Llm port as Draft
generation (AD-1, AD-11).

Neither touches Anki or stores anything. The examples context is passed to the model and
dropped: it is never kept, returned or logged (AD-15).
"""

from language_lab.domain.catalog import Category, Language
from language_lab.domain.helpers import ExampleSet, GrammarCheck, Translation
from language_lab.ports.llm import Llm


class HelperService:
    def __init__(self, llm: Llm) -> None:
        self._llm = llm

    async def check_grammar(
        self, language: Language, category: Category, target: str
    ) -> GrammarCheck:
        """The model's verdict on `target`. Raises `AppError(LLM_FAILED | LLM_INVALID_OUTPUT)`."""
        return await self._llm.check_grammar(language, category, target)

    async def examples(self, language: Language, target: str, context: str = "") -> ExampleSet:
        """Five sentences per CEFR level A1..C2 using `target`, each with its Russian.

        Raises `AppError(LLM_FAILED | LLM_INVALID_OUTPUT)` from the model.
        """
        return await self._llm.examples(language, target, context)

    async def translate(self, language: Language, text: str) -> Translation:
        """The Russian translation of `text`, written in `language`.

        Raises `AppError(LLM_FAILED | LLM_INVALID_OUTPUT)` from the model.
        """
        return await self._llm.translate(language, text)

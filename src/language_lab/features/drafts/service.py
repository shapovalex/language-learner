"""Drafts: the blank Draft, which only issues the ItemId the Draft carries until Save (AD-8), and
the generated one, which also asks the Llm port for the Category's fields (AD-11).

Neither touches Anki (FR-18). The Generation context is passed to the model and dropped: it is
never kept, returned or logged (FR-16, AD-15).
"""

import uuid

from language_lab.domain.catalog import Category, Language
from language_lab.domain.items import Item
from language_lab.ports.llm import Llm


class DraftService:
    def __init__(self, llm: Llm) -> None:
        self._llm = llm

    def blank(self) -> str:
        """A fresh ItemId, a UUIDv4 in lowercase canonical form. Touches no Anki."""
        return str(uuid.uuid4())

    async def generate(
        self, language: Language, category: Category, target: str, generation_context: str
    ) -> Item:
        """The Draft: a fresh ItemId and the model's fields, with `target` as given.

        Raises `AppError(LLM_FAILED | LLM_INVALID_OUTPUT)` from the model.
        """
        fields = await self._llm.generate(language, category, target, generation_context)
        return Item(self.blank(), fields.to_content(target))

"""Items: Save, create-or-update by ItemId in the AnkiStore (AD-6, AD-20), and the Item reads:
the duplicate check, matched on the normalized Target here (AD-12), and one Item by ItemId.
"""

from language_lab.domain.catalog import Category, Language
from language_lab.domain.items import AudioIntent, Item, ItemContent, normalize_text
from language_lab.ports.anki_store import AnkiStore


class ItemService:
    def __init__(self, anki: AnkiStore) -> None:
        self._anki = anki

    async def save(
        self, item_id: str, language: Language, content: ItemContent, audio: AudioIntent
    ) -> None:
        """Save the Item `item_id`; a retry with the same ItemId updates it. Raises
        `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        await self._anki.save_item(item_id, language, content, audio)

    async def duplicates(
        self, language: Language, category: Category, target: str, item_id: str | None = None
    ) -> list[Item]:
        """The Items of `language` and `category` whose normalized Target equals `target`'s,
        leaving out `item_id`'s own, in the store's order (FR-19, AD-12). Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        wanted = normalize_text(target)
        return [
            item
            for item in await self._anki.item_candidates(language, category)
            if item.item_id != item_id and normalize_text(item.content.target) == wanted
        ]

    async def get(self, language: Language, item_id: str) -> Item:
        """The Item `item_id` of `language`. Raises
        `AppError(NOT_FOUND | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        return await self._anki.get_item(language, item_id)

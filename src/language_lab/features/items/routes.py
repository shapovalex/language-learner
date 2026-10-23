"""Items' HTTP routes, under /api/items: Save, the list/search, the duplicate read and the Item
read."""

import json
import re
from typing import Annotated, Any, Literal, TypedDict

from fastapi import APIRouter, Form, Query
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from language_lab.domain.catalog import UUID4, Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import AudioIntent, ItemContent
from language_lab.features.items.service import ItemService

_CONTENT = TypeAdapter(ItemContent)


class _SaveIntent(BaseModel):
    """The `item` part's keys beside ItemContent (Consistency Conventions, Binary payloads)."""

    item_id: str = Field(alias="itemId", pattern=UUID4)
    audio: Literal[AudioIntent.KEEP]  # epic-reference-audio adds replace and remove


class SavedBody(TypedDict):
    itemId: str


def _parse(item: str) -> tuple[_SaveIntent, ItemContent]:
    """The `item` JSON part as its save intent and content; `VALIDATION_FAILED` when it isn't."""
    try:
        payload: Any = json.loads(item)
        if not isinstance(payload, dict):
            raise ValueError("not an object")
        intent = _SaveIntent.model_validate(payload)
        rest = {k: v for k, v in payload.items() if k not in ("itemId", "audio")}
        return intent, _CONTENT.validate_python(rest)
    except ValueError, ValidationError:  # json.JSONDecodeError is a ValueError
        raise AppError(ErrorCode.VALIDATION_FAILED) from None


class ItemsBody(TypedDict):
    items: list[dict[str, Any]]


class MatchesBody(TypedDict):
    matches: list[dict[str, Any]]


def _duplicate_query(
    category: str | None, target: str | None, item_id: str | None
) -> tuple[Category, str, str | None]:
    """The duplicate read's query as its Category, Target and ItemId (`itemId=` empty is none);
    `VALIDATION_FAILED` when it isn't valid. No value is echoed (AD-15).
    """
    try:
        parsed = Category(category or "")
    except ValueError:
        raise AppError(ErrorCode.VALIDATION_FAILED) from None
    if target is None or not target.strip():
        raise AppError(ErrorCode.VALIDATION_FAILED)
    if item_id and re.fullmatch(UUID4, item_id) is None:
        raise AppError(ErrorCode.VALIDATION_FAILED)
    return parsed, target, item_id or None


def items_router(service: ItemService) -> APIRouter:
    router = APIRouter(prefix="/api/items")

    @router.post("/{lang}")
    async def save(lang: Language, item: Annotated[str, Form()]) -> SavedBody:
        intent, content = _parse(item)
        await service.save(intent.item_id, lang, content, intent.audio)
        return {"itemId": intent.item_id}

    @router.get("/{lang}")
    async def search(lang: Language, q: str | None = None) -> ItemsBody:
        items = await service.search(lang, q or "")
        return {"items": [{**item.wire(), "hasAudio": item.has_audio} for item in items]}

    # Declared before /{item_id}, which would otherwise take "duplicates" as an ItemId
    @router.get("/{lang}/duplicates")
    async def duplicates(
        lang: Language,
        category: str | None = None,
        target: str | None = None,
        item_id: Annotated[str | None, Query(alias="itemId")] = None,
    ) -> MatchesBody:
        parsed, text, own = _duplicate_query(category, target, item_id)
        matches = await service.duplicates(lang, parsed, text, own)
        return {"matches": [item.wire() for item in matches]}

    @router.get("/{lang}/{item_id}")
    async def get_item(lang: Language, item_id: str) -> dict[str, Any]:
        # A malformed ItemId names no Item, so it never reaches the store
        if re.fullmatch(UUID4, item_id) is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return (await service.get(lang, item_id)).wire()

    return router

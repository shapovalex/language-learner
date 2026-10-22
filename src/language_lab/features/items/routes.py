"""Items' HTTP routes, under /api/items."""

import json
from typing import Annotated, Any, Literal, TypedDict

from fastapi import APIRouter, Form
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from language_lab.domain.catalog import UUID4, Language
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


def items_router(service: ItemService) -> APIRouter:
    router = APIRouter(prefix="/api/items")

    @router.post("/{lang}")
    async def save(lang: Language, item: Annotated[str, Form()]) -> SavedBody:
        intent, content = _parse(item)
        await service.save(intent.item_id, lang, content, intent.audio)
        return {"itemId": intent.item_id}

    return router

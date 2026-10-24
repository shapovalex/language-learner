"""Drafts' HTTP routes, under /api/drafts."""

from typing import Any, TypedDict

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from language_lab.domain.catalog import Category, Language
from language_lab.domain.items import NonBlank
from language_lab.features.drafts.service import DraftService


class BlankBody(TypedDict):
    itemId: str


class GenerateRequest(BaseModel):
    """What the Make an Item pane sends: the chosen text, its Language and Category, and the
    optional Generation context.
    """

    model_config = ConfigDict(strict=True)

    language: Language = Field(strict=False)  # enums arrive as their JSON strings
    category: Category = Field(strict=False)
    target: NonBlank
    generation_context: str = Field("", alias="generationContext")


def drafts_router(service: DraftService) -> APIRouter:
    router = APIRouter(prefix="/api/drafts")

    @router.post("/blank", status_code=201)
    async def blank() -> BlankBody:
        # The client builds the empty form itself from the pane's choices
        return {"itemId": service.blank()}

    @router.post("/generate", status_code=201)
    async def generate(body: GenerateRequest) -> dict[str, Any]:
        draft = await service.generate(
            body.language, body.category, body.target, body.generation_context
        )
        # Flat like the Save's `item` part: the ItemId beside ItemContent
        return draft.wire()

    @router.post("/regenerate")
    async def regenerate(body: GenerateRequest) -> dict[str, Any]:
        # An Item's Preview (FR-24, AD-11): nothing is created, so 200 and no ItemId
        content = await service.regenerate(
            body.language, body.category, body.target, body.generation_context
        )
        return content.model_dump(by_alias=True, mode="json")

    return router

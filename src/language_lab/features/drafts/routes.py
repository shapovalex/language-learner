"""Drafts' HTTP routes, under /api/drafts."""

from typing import Annotated, Any, TypedDict

from fastapi import APIRouter
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from language_lab.domain.catalog import Category, Language
from language_lab.features.drafts.service import DraftService


class BlankBody(TypedDict):
    itemId: str


def _not_blank(text: str) -> str:
    if not text.strip():
        raise ValueError("blank")
    return text


class GenerateRequest(BaseModel):
    """What the Make an Item pane sends: the chosen text, its Language and Category, and the
    optional Generation context.
    """

    model_config = ConfigDict(strict=True)

    language: Language = Field(strict=False)  # enums arrive as their JSON strings
    category: Category = Field(strict=False)
    target: Annotated[str, AfterValidator(_not_blank)]
    generation_context: str = Field("", alias="generationContext")


def drafts_router(service: DraftService) -> APIRouter:
    router = APIRouter(prefix="/api/drafts")

    @router.post("/blank", status_code=201)
    async def blank() -> BlankBody:
        # The client builds the empty form itself from the pane's choices
        return {"itemId": service.blank()}

    @router.post("/generate", status_code=201)
    async def generate(body: GenerateRequest) -> dict[str, Any]:
        item_id, content = await service.generate(
            body.language, body.category, body.target, body.generation_context
        )
        # Flat like the Save's `item` part: the ItemId beside ItemContent
        return {"itemId": item_id, **content.model_dump(by_alias=True)}

    return router

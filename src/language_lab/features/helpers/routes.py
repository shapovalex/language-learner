"""The Target helpers' HTTP routes, under /api/helpers. Both answer 200: nothing is created."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from language_lab.domain.catalog import Category, Language
from language_lab.domain.items import NonBlank
from language_lab.features.helpers.service import HelperService


class GrammarRequest(BaseModel):
    """The Target field's Check grammar: the Target with its Language and Category."""

    model_config = ConfigDict(strict=True)

    language: Language = Field(strict=False)  # enums arrive as their JSON strings
    category: Category = Field(strict=False)
    target: NonBlank


class ExamplesRequest(BaseModel):
    """The Captures screen's Example sentences: the compose text, its Language and an optional
    context, used once.
    """

    model_config = ConfigDict(strict=True)

    language: Language = Field(strict=False)
    target: NonBlank
    context: str = ""


def helpers_router(service: HelperService) -> APIRouter:
    router = APIRouter(prefix="/api/helpers")

    @router.post("/grammar")
    async def grammar(body: GrammarRequest) -> dict[str, Any]:
        check = await service.check_grammar(body.language, body.category, body.target)
        return check.model_dump(by_alias=True, mode="json")

    @router.post("/examples")
    async def examples(body: ExamplesRequest) -> dict[str, Any]:
        example_set = await service.examples(body.language, body.target, body.context)
        return example_set.model_dump(by_alias=True, mode="json")

    return router

"""The Target helpers' HTTP routes, under /api/helpers. All answer 200: nothing is created."""

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


class ExampleChoicesRequest(BaseModel):
    """The Item detail's Regenerate example: the Item's Target and Language, an optional
    context, used once, and the Item's current Russian meaning, when it has one.
    """

    model_config = ConfigDict(strict=True)

    language: Language = Field(strict=False)
    target: NonBlank
    context: str = ""
    meaning: str = ""


class TranslateRequest(BaseModel):
    """The Captures screen's Capture and translate: the saved text and its Language."""

    model_config = ConfigDict(strict=True)

    language: Language = Field(strict=False)
    target: NonBlank


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

    @router.post("/example-choices")
    async def example_choices(body: ExampleChoicesRequest) -> dict[str, Any]:
        choices = await service.example_choices(
            body.language, body.target, body.context, body.meaning
        )
        return choices.model_dump(by_alias=True, mode="json")

    @router.post("/translate")
    async def translate(body: TranslateRequest) -> dict[str, Any]:
        translation = await service.translate(body.language, body.target)
        return translation.model_dump(by_alias=True, mode="json")

    return router

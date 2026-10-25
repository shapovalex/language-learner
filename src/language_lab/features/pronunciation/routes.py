"""Pronunciation's HTTP routes, under /api/pronunciation/<lang>: the queue, a Rating and the
session signals (AD-17: each signal answers 204 at once, whatever the Sync does).
"""

from typing import Annotated, Any, TypedDict

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from language_lab.domain.catalog import Language
from language_lab.domain.pronunciation import Rating
from language_lab.features.pronunciation.service import PronunciationService


class _RatingBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: StrictInt = Field(alias="cardId")
    reps: Annotated[StrictInt, Field(ge=0)]
    rating: Rating


class QueueBody(TypedDict):
    due: int
    new: int
    cards: list[dict[str, Any]]


class RatedBody(TypedDict):
    alreadyAnswered: bool


def pronunciation_router(service: PronunciationService) -> APIRouter:
    router = APIRouter(prefix="/api/pronunciation/{lang}")

    @router.get("/queue")
    async def queue(lang: Language) -> QueueBody:
        found = await service.queue(lang)
        return {"due": found.due, "new": found.new, "cards": [c.wire() for c in found.cards]}

    @router.post("/rating")
    async def rating(lang: Language, body: _RatingBody) -> RatedBody:
        already = await service.rate(lang, body.card_id, body.reps, body.rating)
        return {"alreadyAnswered": already}

    @router.post("/session/start", status_code=204)
    async def session_start(lang: Language) -> Response:
        await service.session_signal()
        return Response(status_code=204)

    @router.post("/session/end", status_code=204)
    async def session_end(lang: Language) -> Response:
        await service.session_signal()
        return Response(status_code=204)

    return router

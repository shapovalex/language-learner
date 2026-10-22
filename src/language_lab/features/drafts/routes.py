"""Drafts' HTTP routes, under /api/drafts."""

from typing import TypedDict

from fastapi import APIRouter

from language_lab.features.drafts.service import DraftService


class BlankBody(TypedDict):
    itemId: str


def drafts_router(service: DraftService) -> APIRouter:
    router = APIRouter(prefix="/api/drafts")

    @router.post("/blank", status_code=201)
    async def blank() -> BlankBody:
        # The client builds the empty form itself from the pane's choices
        return {"itemId": service.blank()}

    return router

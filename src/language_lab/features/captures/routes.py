"""Captures' HTTP routes, under /api/captures."""

from typing import Annotated, TypedDict

from fastapi import APIRouter
from pydantic import AfterValidator, BaseModel, Field

from language_lab.features.captures.service import CaptureService

# A UUIDv4 in lowercase canonical form, as the Prefix guard's media pattern takes it (AD-8)
_UUID4 = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
_CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _not_blank(text: str) -> str:
    if not text.strip():
        raise ValueError("blank")
    return text  # stored exactly as typed


class CreateRequest(BaseModel):
    capture_id: str = Field(alias="captureId", pattern=_UUID4)  # camelCase on the wire
    text: Annotated[str, AfterValidator(_not_blank)]


class CaptureBody(TypedDict):
    captureId: str
    text: str
    createdAt: str


def captures_router(service: CaptureService) -> APIRouter:
    router = APIRouter(prefix="/api/captures")

    @router.post("", status_code=201)
    async def create(body: CreateRequest) -> CaptureBody:
        capture = await service.create(body.capture_id, body.text)
        return {
            "captureId": capture.capture_id,
            "text": capture.text,
            "createdAt": capture.created_at.strftime(_CREATED_AT_FORMAT),
        }

    return router

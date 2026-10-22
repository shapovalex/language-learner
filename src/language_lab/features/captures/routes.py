"""Captures' HTTP routes, under /api/captures."""

import re
from typing import Annotated, TypedDict

from fastapi import APIRouter
from pydantic import AfterValidator, BaseModel, Field

from language_lab.domain.captures import Capture
from language_lab.domain.errors import AppError, ErrorCode
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


class CapturesBody(TypedDict):
    captures: list[CaptureBody]


def _body(capture: Capture) -> CaptureBody:
    return {
        "captureId": capture.capture_id,
        "text": capture.text,
        "createdAt": capture.created_at.strftime(_CREATED_AT_FORMAT),
    }


def captures_router(service: CaptureService) -> APIRouter:
    router = APIRouter(prefix="/api/captures")

    @router.post("", status_code=201)
    async def create(body: CreateRequest) -> CaptureBody:
        return _body(await service.create(body.capture_id, body.text))

    @router.get("")
    async def list_captures() -> CapturesBody:
        return {"captures": [_body(c) for c in await service.list_all()]}

    @router.get("/{capture_id}")
    async def get_capture(capture_id: str) -> CaptureBody:
        # A malformed CaptureId names no Capture, so it never reaches the store
        if re.fullmatch(_UUID4, capture_id) is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return _body(await service.get(capture_id))

    return router

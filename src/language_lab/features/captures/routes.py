"""Captures' HTTP routes, under /api/captures."""

import re
from typing import Annotated, TypedDict

from fastapi import APIRouter, Response
from pydantic import AfterValidator, BaseModel, Field

from language_lab.domain.captures import Capture
from language_lab.domain.catalog import UUID4
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.features.captures.service import CaptureService

_CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _not_blank(text: str) -> str:
    if not text.strip():
        raise ValueError("blank")
    return text  # stored exactly as typed


class CreateRequest(BaseModel):
    capture_id: str = Field(alias="captureId", pattern=UUID4)  # camelCase on the wire
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


def _require_capture_id(capture_id: str) -> None:
    # A malformed CaptureId names no Capture, so it never reaches the store
    if re.fullmatch(UUID4, capture_id) is None:
        raise AppError(ErrorCode.NOT_FOUND)


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
        _require_capture_id(capture_id)
        return _body(await service.get(capture_id))

    @router.delete("/{capture_id}", status_code=204)
    async def delete_capture(capture_id: str) -> Response:
        _require_capture_id(capture_id)
        await service.delete(capture_id)  # one already gone is deleted too: a retry succeeds
        return Response(status_code=204)

    return router

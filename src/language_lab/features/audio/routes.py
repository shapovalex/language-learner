"""Reference audio catalog and explicit binary preview routes."""

from fastapi import APIRouter, Response
from pydantic import BaseModel

from language_lab.domain.catalog import Language
from language_lab.features.audio.service import AudioService


class PreviewBody(BaseModel):
    language: Language
    voice: str
    target: str


def audio_router(service: AudioService) -> APIRouter:
    router = APIRouter(prefix="/api/audio")

    @router.get("/voices")
    async def voices(locale: str) -> dict:
        return {
            "voices": [
                {"name": v.name, "locale": v.locale, "displayName": v.display_name}
                for v in await service.voices(locale)
            ]
        }

    @router.post("/preview")
    async def preview(body: PreviewBody) -> Response:
        return Response(
            await service.preview(body.language, body.voice, body.target),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-store"},
        )

    return router

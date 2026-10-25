"""Azure Speech REST; backend credentials, escaped SSML and bounded requests."""

import asyncio
import json
import re
from xml.sax.saxutils import escape, quoteattr

import httpx

from language_lab.domain.audio import MAX_AUDIO_BYTES, Voice, validate_mp3
from language_lab.domain.errors import AppError, ErrorCode


class AzureSpeech:
    def __init__(self, key: str, region: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self._configured = bool(key and re.fullmatch(r"[a-z0-9-]+", region))
        host_region = region if self._configured else "unconfigured"
        self._client = httpx.AsyncClient(
            base_url=f"https://{host_region}.tts.speech.microsoft.com",
            headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": "LanguageLab"},
            timeout=httpx.Timeout(30, connect=5),
            transport=transport,
        )

    async def _request(self, method: str, path: str, **kwargs) -> bytes:
        if not self._configured:
            raise AppError(ErrorCode.TTS_FAILED)
        try:
            async with asyncio.timeout(30), self._client.stream(method, path, **kwargs) as response:
                response.raise_for_status()
                result = bytearray()
                async for chunk in response.aiter_bytes():
                    result.extend(chunk)
                    if len(result) > MAX_AUDIO_BYTES:
                        raise AppError(ErrorCode.TTS_FAILED)
                return bytes(result)
        except httpx.HTTPError, TimeoutError:
            raise AppError(ErrorCode.TTS_FAILED) from None

    async def voices(self, locales: tuple[str, ...]) -> list[Voice]:
        try:
            rows = json.loads(await self._request("GET", "/cognitiveservices/voices/list"))
            if not isinstance(rows, list):
                raise ValueError
            found = [
                Voice(row["ShortName"], row["Locale"], row["DisplayName"])
                for row in rows
                if row.get("Locale") in locales
                and row.get("VoiceType") == "Neural"
                and all(
                    isinstance(row.get(key), str) and row[key]
                    for key in ("ShortName", "Locale", "DisplayName")
                )
            ]
            # Stable: each locale keeps the provider's order within it
            return sorted(found, key=lambda voice: locales.index(voice.locale))
        except ValueError, KeyError, TypeError, AttributeError:
            raise AppError(ErrorCode.TTS_FAILED) from None

    async def synthesize(self, locale: str, voice: str, target: str) -> bytes:
        body = (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f"xml:lang={quoteattr(locale)}><voice name={quoteattr(voice)}>"
            f"{escape(target)}</voice></speak>"
        )
        data = await self._request(
            "POST",
            "/cognitiveservices/v1",
            content=body.encode(),
            headers={
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            },
        )
        try:
            validate_mp3(data)
        except AppError:
            raise AppError(ErrorCode.TTS_FAILED) from None
        return data

    async def aclose(self) -> None:
        await self._client.aclose()

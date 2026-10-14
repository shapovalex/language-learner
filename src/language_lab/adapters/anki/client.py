"""AnkiConnect API v6 over one httpx.AsyncClient (AD-5); every failure is `anki_unavailable`."""

from typing import Any

import httpx

from language_lab.domain.errors import AppError, ErrorCode

API_VERSION = 6
DEFAULT_TIMEOUT_S = 10.0
SYNC_TIMEOUT_S = 120.0  # a Sync with AnkiWeb can take far longer than any other action

_TIMEOUTS_S = {"sync": SYNC_TIMEOUT_S}


class AnkiConnectClient:
    def __init__(self, url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._url = url
        self._http = httpx.AsyncClient(transport=transport, timeout=DEFAULT_TIMEOUT_S)

    async def invoke(self, action: str, **params: Any) -> Any:
        """POST one action and return its `result`.

        Raises `AppError(ANKI_UNAVAILABLE)` for an httpx error, a non-2xx status, a body that
        isn't a JSON object, or a non-null `error`. No upstream text is carried (AD-15).
        """
        body: dict[str, Any] = {"action": action, "version": API_VERSION}
        if params:
            body["params"] = params
        timeout = _TIMEOUTS_S.get(action, DEFAULT_TIMEOUT_S)
        try:
            response = await self._http.post(self._url, json=body, timeout=timeout)
            response.raise_for_status()
            reply = response.json()
        except httpx.HTTPError, ValueError:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE) from None
        if not isinstance(reply, dict) or reply.get("error") is not None:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return reply.get("result")

    async def aclose(self) -> None:
        await self._http.aclose()

"""AnkiConnect over one httpx.AsyncClient (AD-5); every failure is `anki_unavailable`.

Every action speaks API v6, except Sync, which speaks API v1 (JSON-RPC on `/api/v1`) so it can
be polled to its end (spike 2.2, Q7).
"""

import itertools
from typing import Any

import httpx

from language_lab.domain.errors import AppError, ErrorCode

API_VERSION = 6
API_V1_PATH = "/api/v1"
DEFAULT_TIMEOUT_S = 10.0


class AnkiConnectClient:
    def __init__(self, url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._url = url
        self._v1_url = url.rstrip("/") + API_V1_PATH
        self._v1_ids = itertools.count(1)
        self._http = httpx.AsyncClient(transport=transport, timeout=DEFAULT_TIMEOUT_S)

    async def invoke(self, action: str, **params: Any) -> Any:
        """POST one v6 action and return its `result`.

        Raises `AppError(ANKI_UNAVAILABLE)` for an httpx error, a non-2xx status, a body that
        isn't a JSON object, or a non-null `error`. No upstream text is carried (AD-15).
        """
        body: dict[str, Any] = {"action": action, "version": API_VERSION}
        if params:
            body["params"] = params
        reply = await self._post(self._url, body)
        if reply.get("error") is not None:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return reply.get("result")

    async def invoke_v1(self, method: str, **params: Any) -> Any:
        """POST one API v1 (JSON-RPC 2.0) call and return its `result`.

        Raises `AppError(ANKI_UNAVAILABLE)` for an httpx error, a non-2xx status, a body that
        isn't a JSON object, or a JSON-RPC `error`. No upstream text is carried (AD-15).
        """
        body = {"jsonrpc": "2.0", "id": next(self._v1_ids), "method": method, "params": params}
        reply = await self._post(self._v1_url, body)
        if reply.get("error") is not None:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return reply.get("result")

    async def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._http.post(url, json=body)
            response.raise_for_status()
            reply = response.json()
        except httpx.HTTPError, ValueError:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE) from None
        if not isinstance(reply, dict):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return reply

    async def aclose(self) -> None:
        await self._http.aclose()

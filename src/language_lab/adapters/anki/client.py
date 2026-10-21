"""AnkiConnect over one httpx.AsyncClient (AD-5); every failure is `anki_unavailable`.

Every action speaks API v6, except Sync, which speaks API v1 (JSON-RPC on `/api/v1`) so it can
be polled to its end (spike 2.2, Q7).

Every v6 request passes the AD-4 Prefix guard first (adapters/anki/guard.py). Without a guard
the client sends reads only. v1 Sync is not a resource write and is not guarded.

With a `SetupGate` (adapters/anki/setup_gate.py, AD-19), `invoke` then refuses every write with
`AppError(SETUP_REQUIRED)` unless the SetupState is `ready`. `invoke_setup` is Setup's own
write path: guarded, ungated. Without a gate the client behaves as `invoke_setup`.
"""

import itertools
from typing import Any

import httpx

from language_lab.adapters.anki.guard import PrefixGuard, check_read_only
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.domain.errors import AppError, ErrorCode

API_VERSION = 6
API_V1_PATH = "/api/v1"
DEFAULT_TIMEOUT_S = 10.0


class AnkiConnectClient:
    def __init__(
        self,
        url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        guard: PrefixGuard | None = None,
        gate: SetupGate | None = None,
    ) -> None:
        self._url = url
        self._guard = guard
        self._gate = gate
        self._v1_url = url.rstrip("/") + API_V1_PATH
        self._v1_ids = itertools.count(1)
        self._http = httpx.AsyncClient(transport=transport, timeout=DEFAULT_TIMEOUT_S)

    async def invoke(self, action: str, **params: Any) -> Any:
        """POST one v6 action and return its `result`, once the guard and the gate allow it.

        Raises `PrefixViolation` before anything is sent for a request outside the Prefix (with
        no guard: anything but a read), then `AppError(SETUP_REQUIRED)` for a write the gate
        refuses. Raises `AppError(ANKI_UNAVAILABLE)` for an httpx error, a non-2xx status, a
        body that isn't a JSON object, or a non-null `error`. No upstream text is carried
        (AD-15).
        """
        await self._check_guard(action, params)
        if self._gate is not None:
            await self._gate.check(action, params, self._invoke_raw)
        return await self._invoke_raw(action, **params)

    async def invoke_setup(self, action: str, **params: Any) -> Any:
        """`invoke` without the gate: Setup's own apply, which writes while not `ready`."""
        await self._check_guard(action, params)
        return await self._invoke_raw(action, **params)

    async def _check_guard(self, action: str, params: dict[str, Any]) -> None:
        if self._guard is None:
            check_read_only(action, params)
        else:
            await self._guard.check(action, params, self._invoke_raw)

    async def _invoke_raw(self, action: str, **params: Any) -> Any:
        """`invoke` without the guard or the gate: for their own lookups only."""
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

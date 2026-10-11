"""Test-only /api routes that reach the failure paths no product route has yet (AD-15).

They're inserted ahead of the shell catch-all, so they behave like any real /api route.
"""

import uuid

from fastapi import APIRouter, FastAPI
from httpx import Response
from pydantic import BaseModel

PROBE_PREFIX = "/api/_probe"
VALIDATE_ROUTE = f"{PROBE_PREFIX}/validate/{{item_id}}"  # POST: typed path, query and body
BOOM_ROUTE = f"{PROBE_PREFIX}/boom/{{item_id}}"  # GET: raises with item_id in the message


class ProbeBody(BaseModel):
    word: str
    count: int


def add_probe_routes(app: FastAPI) -> FastAPI:
    router = APIRouter()

    @router.post(VALIDATE_ROUTE)
    async def validate(item_id: int, body: ProbeBody, limit: int = 10) -> dict[str, bool]:
        return {"ok": True}

    @router.get(BOOM_ROUTE)
    async def boom(item_id: str) -> None:
        # The traceback carries item_id, so a leaked traceback leaks the input (R-02)
        raise RuntimeError(f"probe failure for {item_id}")

    first_new = len(app.router.routes)
    app.include_router(router)
    added = app.router.routes[first_new:]
    del app.router.routes[first_new:]
    app.router.routes[:0] = added
    return app


def sentinel() -> str:
    """A unique value that must never show up in a response or a log line."""
    return f"sentinel-{uuid.uuid4().hex}"


def error_envelope(response: Response) -> dict:
    """The `error` object of an AD-15 envelope, or `{}` when the body isn't one."""
    try:
        body = response.json()
    except ValueError:
        return {}
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, dict) else {}

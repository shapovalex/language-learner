"""Composition root: the only place routes are wired (AD-13)."""

import json
import logging
import sys
import time
import uuid
from importlib.resources import files
from typing import TextIO

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from language_lab import __version__
from language_lab.domain.errors import ErrorCode, error_envelope
from language_lab.settings import ConfigError, Settings, describe_errors, load_settings

_STATIC = files("language_lab") / "static"
_RESERVED_PREFIXES = ("api/", "static/")

_APP_LOGGER = "language_lab"
_request_log = logging.getLogger(f"{_APP_LOGGER}.request")

# Keys in the ASGI scope's "state" dict, shared by the middleware and the handlers
_REQUEST_ID = "request_id"
_ERROR_CODE = "error_code"


def _is_api(path: str) -> bool:
    return path == "/api" or path.startswith("/api/")


def _code_for_status(status: int) -> ErrorCode:
    if status in (404, 405):
        return ErrorCode.NOT_FOUND
    if status == 413:
        return ErrorCode.PAYLOAD_TOO_LARGE
    if status >= 500:
        return ErrorCode.INTERNAL_ERROR
    return ErrorCode.VALIDATION_FAILED


def _envelope_response(
    request: Request, status: int, code: ErrorCode, headers: dict[str, str] | None = None
) -> JSONResponse:
    request_id = getattr(request.state, _REQUEST_ID, None) or uuid.uuid4().hex
    return JSONResponse(error_envelope(code, request_id), status_code=status, headers=headers)


async def _on_validation_error(request: Request, exc: Exception) -> Response:
    setattr(request.state, _ERROR_CODE, ErrorCode.VALIDATION_FAILED.value)
    if not _is_api(request.url.path):
        return await request_validation_exception_handler(request, exc)  # type: ignore[arg-type]
    # No details: FastAPI's errors carry the input values (AD-15)
    return _envelope_response(request, 422, ErrorCode.VALIDATION_FAILED)


async def _on_http_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, StarletteHTTPException)
    code = _code_for_status(exc.status_code)
    setattr(request.state, _ERROR_CODE, code.value)
    if not _is_api(request.url.path):
        return await http_exception_handler(request, exc)
    return _envelope_response(request, exc.status_code, code, exc.headers)


class RequestLogMiddleware:
    """Assign a request id, log one content-free JSON line per request, and turn any
    unhandled exception into the 500 envelope (AD-15).

    A pure ASGI middleware: it owns the scope dict, so after the app returns it can read
    the route the router matched and the code a handler stashed. Exceptions stop here, so
    no traceback carrying input reaches uvicorn's logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.monotonic()
        request_id = uuid.uuid4().hex
        state = scope.setdefault("state", {})
        state[_REQUEST_ID] = request_id
        status = 500
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                status = message["status"]
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:  # noqa: BLE001 -- the envelope replaces the traceback (AD-15)
            state[_ERROR_CODE] = ErrorCode.INTERNAL_ERROR.value
            status = 500
            if not started:
                response: Response = (
                    JSONResponse(
                        error_envelope(ErrorCode.INTERNAL_ERROR, request_id), status_code=500
                    )
                    if _is_api(scope["path"])
                    else PlainTextResponse("Internal Server Error", status_code=500)
                )
                await response(scope, receive, send)
        finally:
            route = scope.get("route")
            line = {
                "requestId": request_id,
                "method": scope["method"],
                "route": getattr(route, "path", None),
                "status": status,
                "code": state.get(_ERROR_CODE),
                "durationMs": round((time.monotonic() - start) * 1000, 1),
            }
            _request_log.info(json.dumps(line))


class _StdoutHandler(logging.StreamHandler):
    """Writes to whatever `sys.stdout` is at emit time, so a swapped stdout is followed."""

    @property  # type: ignore[override]
    def stream(self) -> TextIO:
        return sys.stdout

    @stream.setter
    def stream(self, value: TextIO) -> None:
        pass


def _configure_logging() -> None:
    """One stdout handler on the app logger, emitting messages as-is (NFR-9). Idempotent."""
    logger = logging.getLogger(_APP_LOGGER)
    logger.setLevel(logging.INFO)
    if not any(isinstance(h, _StdoutHandler) for h in logger.handlers):
        handler = _StdoutHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)


def _render_shell(version: str) -> str:
    return (_STATIC / "index.html").read_text(encoding="utf-8").replace("{{VERSION}}", version)


def create_app(settings: Settings) -> FastAPI:
    version = __version__
    shell = _render_shell(version)

    app = FastAPI(
        title="LanguageLab", version=version, docs_url=None, redoc_url=None, openapi_url=None
    )

    app.add_middleware(RequestLogMiddleware)
    app.add_exception_handler(RequestValidationError, _on_validation_error)
    app.add_exception_handler(StarletteHTTPException, _on_http_error)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"version": version}

    app.mount(f"/static/{version}", StaticFiles(directory=str(_STATIC)), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    async def shell_route(path: str) -> HTMLResponse:
        if path == "api" or path == "static" or path.startswith(_RESERVED_PREFIXES):
            raise HTTPException(status_code=404)
        return HTMLResponse(shell, headers={"Cache-Control": "no-cache"})

    return app


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    except ValidationError as exc:
        for line in describe_errors(exc):
            print(line, file=sys.stderr)
        sys.exit(1)
    _configure_logging()
    print(f"LanguageLab running at http://{settings.host}:{settings.port}/", flush=True)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, access_log=False)

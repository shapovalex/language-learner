"""Composition root: the only place routes are wired (AD-13)."""

import getpass
import json
import logging
import sys
import time
import uuid
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from typing import NoReturn, TextIO

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
from language_lab.adapters import tailscale
from language_lab.domain.errors import ErrorCode, error_envelope
from language_lab.settings import (
    NECESSARY_KEYS,
    ConfigError,
    Settings,
    active_config_path,
    create_config,
    describe_errors,
    is_dev_mode,
    is_safe_value,
    load_settings,
    render_config,
)

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


def _normalise_host(value: str) -> str:
    """Lowercase, and drop an explicit `:443` (browsers omit Serve's default HTTPS port)."""
    host = value.strip().lower()
    return host.removesuffix(":443")


def _origin_host(origin: str) -> str | None:
    """`host[:port]` of an Origin, scheme ignored; None when it has no scheme (e.g. `null`)."""
    _, sep, rest = origin.partition("://")
    if not sep or not rest:
        return None
    return rest.split("/", 1)[0]


def allowed_hosts(settings: Settings) -> frozenset[str]:
    """The AD-16 allow-list, from settings alone: loopback on the app's port and the tailnet."""
    hosts = {f"127.0.0.1:{settings.port}", f"localhost:{settings.port}"}
    if settings.public_host:
        hosts.add(settings.public_host)
    return frozenset(_normalise_host(host) for host in hosts)


class AllowListMiddleware:
    """Reject requests whose Host, X-Forwarded-Host or (on non-GET /api) Origin isn't on the
    allow-list (AD-16), with 403 `forbidden_origin`.

    Runs inside `RequestLogMiddleware`, so a rejection gets a request id and one log line.
    No header value is ever echoed into the body or the log.
    """

    def __init__(self, app: ASGIApp, allowed: frozenset[str]) -> None:
        self.app = app
        self.allowed = allowed

    def _is_allowed(self, value: str | None) -> bool:
        return value is not None and _normalise_host(value) in self.allowed

    def _permits(self, scope: Scope) -> bool:
        # Every copy of a repeated header is checked, so a second foreign copy can't slip by
        headers: dict[str, list[str]] = {}
        for name, value in scope["headers"]:
            headers.setdefault(name.decode("latin-1").lower(), []).append(value.decode("latin-1"))
        hosts = headers.get("host", [])
        if not hosts or not all(self._is_allowed(host) for host in hosts):
            return False
        if not all(self._is_allowed(host) for host in headers.get("x-forwarded-host", [])):
            return False
        if scope["method"] != "GET" and _is_api(scope["path"]):
            origins = headers.get("origin", [])
            if not origins or not all(self._is_allowed(_origin_host(o)) for o in origins):
                return False
        return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._permits(scope):
            await self.app(scope, receive, send)
            return
        state = scope.setdefault("state", {})
        state[_ERROR_CODE] = ErrorCode.FORBIDDEN_ORIGIN.value
        response: Response
        if _is_api(scope["path"]):
            request_id = state.get(_REQUEST_ID) or uuid.uuid4().hex
            response = JSONResponse(
                error_envelope(ErrorCode.FORBIDDEN_ORIGIN, request_id), status_code=403
            )
        else:
            response = PlainTextResponse("Forbidden", status_code=403)
        await response(scope, receive, send)


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

    # Last added is outermost: the allow-list runs inside the request log (AD-15, AD-16)
    app.add_middleware(AllowListMiddleware, allowed=allowed_hosts(settings))
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


def with_tailnet_host(settings: Settings, discover: Callable[[], str | None]) -> Settings:
    """`settings` with the tailnet host: LANGUAGE_LAB_PUBLIC_HOST if set, else `discover()`."""
    if settings.public_host:
        return settings
    return settings.model_copy(update={"public_host": discover()})


def _fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(1)


def _ask(
    key: str, secret: bool, read_line: Callable[[str], str], read_secret: Callable[[str], str]
) -> str:
    """One answer for `key`, asked again until it can be written. Never echoes the answer."""
    while True:
        value = (read_secret if secret else read_line)(f"{key} (empty to set later): ")
        if is_safe_value(value):
            return value
        print(
            f"{key}: no whitespace, quotes, backticks, #, $, backslashes, or control or "
            "non-printable characters; try again",
            file=sys.stderr,
        )


def _setup_config(
    path: Path,
    dev: bool,
    read_line: Callable[[str], str],
    read_secret: Callable[[str], str],
    is_tty: Callable[[], bool],
) -> None:
    """Create the missing config at `path` from the packaged template.

    In a terminal, asks for the necessary keys first, then writes the file and returns so
    startup continues. Without one, writes the template and exits 1 naming what to set.
    Raises `ConfigError` if the file cannot be created.
    """
    names = ", ".join(key for key, _ in NECESSARY_KEYS)
    if not is_tty():
        create_config(path, render_config(dev, {}))
        _fail(f"created config at {path}; set {names} in it, then start language-lab again")
    print(f"No config at {path}. Enter {names} to create it.", file=sys.stderr)
    try:
        values = {key: _ask(key, secret, read_line, read_secret) for key, secret in NECESSARY_KEYS}
    except KeyboardInterrupt, EOFError:
        print(file=sys.stderr)  # end the unanswered prompt's line
        _fail(f"setup cancelled; no config written to {path}")
    create_config(path, render_config(dev, values))
    print(f"Created config at {path}.", file=sys.stderr)


def main() -> None:
    try:
        path = active_config_path()
        if not path.exists() and not path.is_symlink():
            _setup_config(path, is_dev_mode(), input, getpass.getpass, sys.stdin.isatty)
        settings = load_settings()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    except ValidationError as exc:
        for line in describe_errors(exc):
            print(line, file=sys.stderr)
        sys.exit(1)
    settings = with_tailnet_host(settings, tailscale.discover_tailnet_host)
    _configure_logging()
    print(f"LanguageLab running at http://{settings.host}:{settings.port}/", flush=True)
    if settings.public_host:
        print(f"On your tailnet: https://{settings.public_host}/", flush=True)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, access_log=False)

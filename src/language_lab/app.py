"""Composition root: the only place routes are wired (AD-13)."""

import getpass
import json
import logging
import sys
import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
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
from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import build_manifest
from language_lab.adapters.anki.migrations import build_migrations
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.adapters.azure import AzureSpeech
from language_lab.adapters.openrouter import OpenRouterLlm
from language_lab.domain.errors import AppError, ErrorCode, error_envelope
from language_lab.features.audio.routes import audio_router
from language_lab.features.audio.service import AudioService
from language_lab.features.captures.routes import captures_router
from language_lab.features.captures.service import CaptureService
from language_lab.features.drafts.routes import drafts_router
from language_lab.features.drafts.service import DraftService
from language_lab.features.items.routes import items_router, media_router
from language_lab.features.items.service import ItemService
from language_lab.features.pronunciation.routes import pronunciation_router
from language_lab.features.pronunciation.service import PronunciationService
from language_lab.features.setup.routes import setup_router
from language_lab.features.setup.service import SetupService
from language_lab.features.sync.scheduler import Clock, SyncScheduler
from language_lab.features.sync.service import SyncService
from language_lab.ports.anki_store import AnkiStore
from language_lab.ports.llm import Llm
from language_lab.ports.speech import Speech
from language_lab.settings import (
    NECESSARY_KEYS,
    ConfigError,
    Settings,
    config_path,
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


def _error_response(scope: Scope, status: int, code: ErrorCode, text: str) -> Response:
    """The envelope on `/api` paths, `text` as plain text elsewhere, for the middlewares."""
    if not _is_api(scope["path"]):
        return PlainTextResponse(text, status_code=status)
    request_id = scope.get("state", {}).get(_REQUEST_ID) or uuid.uuid4().hex
    return JSONResponse(error_envelope(code, request_id), status_code=status)


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


# Domain failures that mean a dependency is down or busy, or that the request's premise is
# stale (a Setup plan Anki no longer has), names nothing (a Capture not in Anki), or is unmet
# (a write while Setup isn't ready, AD-19; a field change whose Sync didn't end OK, AD-17), or
# a body FastAPI can't check itself (a Save's `item` JSON part), or the language model upstream
# failed (502), not a fault in the server
_APP_ERROR_STATUS = {
    ErrorCode.VALIDATION_FAILED: 422,
    ErrorCode.ANKI_UNAVAILABLE: 503,
    ErrorCode.ANKI_BUSY: 503,
    ErrorCode.PLAN_CHANGED: 409,
    ErrorCode.SETUP_REQUIRED: 409,
    ErrorCode.SYNC_REQUIRED: 409,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.LLM_FAILED: 502,
    ErrorCode.TTS_FAILED: 502,
    ErrorCode.ASSESSMENT_FAILED: 503,
    ErrorCode.PAYLOAD_TOO_LARGE: 413,
    ErrorCode.LLM_INVALID_OUTPUT: 502,
}


async def _on_app_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, AppError)
    setattr(request.state, _ERROR_CODE, exc.code.value)
    return _envelope_response(request, _APP_ERROR_STATUS.get(exc.code, 500), exc.code)


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
                response = _error_response(
                    scope, 500, ErrorCode.INTERNAL_ERROR, "Internal Server Error"
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
        scope.setdefault("state", {})[_ERROR_CODE] = ErrorCode.FORBIDDEN_ORIGIN.value
        response = _error_response(scope, 403, ErrorCode.FORBIDDEN_ORIGIN, "Forbidden")
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


def create_app(
    settings: Settings,
    *,
    anki_store: AnkiStore | None = None,
    llm: Llm | None = None,
    clock: Clock | None = None,
    speech: Speech | None = None,
) -> FastAPI:
    """The app. Builds the AnkiConnect adapter from settings unless `anki_store` is given, and
    the OpenRouter adapter unless `llm` is given, and Azure unless `speech` is given.

    `clock` times the Sync schedule (real time unless given). Dev mode never Syncs.
    """
    version = __version__
    shell = _render_shell(version)

    anki_client: AnkiConnectClient | None = None
    if anki_store is None:
        manifest = build_manifest(settings.anki_prefix)
        gate = SetupGate(manifest)  # one gate, shared by the client and the store (AD-19)
        anki_client = AnkiConnectClient(
            settings.anki_connect_url, guard=PrefixGuard(manifest), gate=gate
        )
        anki_store = AnkiConnectStore(
            anki_client,
            AnkiLock(),
            manifest=manifest,
            gate=gate,
            migrations=build_migrations(settings.anki_prefix),
        )

    openrouter: OpenRouterLlm | None = None
    if llm is None:
        openrouter = OpenRouterLlm(
            settings.openrouter_api_key.get_secret_value(), settings.openrouter_models
        )
        llm = openrouter

    azure: AzureSpeech | None = None
    if speech is None:
        azure = AzureSpeech(
            settings.azure_speech_key.get_secret_value(), settings.azure_speech_region
        )
        speech = azure

    # Features take `sync` as the SyncRequester port (Setup and Pronunciation below); none
    # imports it (AD-1, AD-13)
    sync = SyncService(anki_store, enabled=not settings.dev)
    scheduler = SyncScheduler(sync, clock, enabled=not settings.dev)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await scheduler.start()
        setup.start_refresh()  # the SetupState, in the background: never delays startup
        try:
            yield
        finally:
            try:
                await scheduler.stop()
                await setup.aclose()
                await sync.aclose()
            finally:
                try:
                    if anki_client is not None:
                        await anki_client.aclose()
                finally:
                    try:
                        if openrouter is not None:
                            await openrouter.aclose()
                    finally:
                        if azure is not None:
                            await azure.aclose()

    app = FastAPI(
        title="LanguageLab",
        version=version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    # Last added is outermost: the allow-list runs inside the request log (AD-15, AD-16)
    app.add_middleware(AllowListMiddleware, allowed=allowed_hosts(settings))
    app.add_middleware(RequestLogMiddleware)
    app.add_exception_handler(RequestValidationError, _on_validation_error)
    app.add_exception_handler(StarletteHTTPException, _on_http_error)
    app.add_exception_handler(AppError, _on_app_error)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"version": version}

    setup = SetupService(
        anki_store,
        sync=sync,
        prefix=settings.anki_prefix,
        azure_configured=bool(
            settings.azure_speech_key.get_secret_value() and settings.azure_speech_region
        ),
        openrouter_configured=bool(settings.openrouter_api_key.get_secret_value()),
    )
    app.include_router(setup_router(setup))
    app.include_router(captures_router(CaptureService(anki_store)))
    app.include_router(audio_router(AudioService(speech)))
    app.include_router(drafts_router(DraftService(llm)))
    app.include_router(items_router(ItemService(anki_store)))
    app.include_router(media_router(ItemService(anki_store)))
    app.include_router(
        pronunciation_router(PronunciationService(anki_store, sync=sync, speech=speech))
    )

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
        dev = is_dev_mode()
        path = config_path(dev)
        if not path.exists() and not path.is_symlink():
            _setup_config(path, dev, input, getpass.getpass, sys.stdin.isatty)
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

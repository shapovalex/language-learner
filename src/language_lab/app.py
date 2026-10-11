"""Composition root: the only place routes are wired (AD-13)."""

import sys
from importlib.resources import files

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from language_lab import __version__
from language_lab.settings import ConfigError, Settings, describe_errors, load_settings

_STATIC = files("language_lab") / "static"
_RESERVED_PREFIXES = ("api/", "static/")


def _render_shell(version: str) -> str:
    return (_STATIC / "index.html").read_text(encoding="utf-8").replace("{{VERSION}}", version)


def create_app(settings: Settings) -> FastAPI:
    version = __version__
    shell = _render_shell(version)

    app = FastAPI(
        title="LanguageLab", version=version, docs_url=None, redoc_url=None, openapi_url=None
    )

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
    print(f"LanguageLab running at http://{settings.host}:{settings.port}/", flush=True)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)

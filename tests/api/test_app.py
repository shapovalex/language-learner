import os
import re
import socket
import subprocess
import sys
import tomllib
from importlib.resources import files
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from language_lab import __version__
from language_lab import app as app_module
from language_lab.app import create_app
from language_lab.settings import Settings

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


@pytest.fixture(autouse=True)
def _clean_bind_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGUAGE_LAB_HOST", raising=False)
    monkeypatch.delenv("LANGUAGE_LAB_PORT", raising=False)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings()))


def test_version_comes_from_pyproject() -> None:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    assert __version__ == project["version"]


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8787


def test_health_returns_only_version(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"version": __version__}


@pytest.mark.parametrize("path", ["/", "/any/deep/path", "/captures"])
def test_client_paths_return_shell(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"
    assert f'src="/static/{__version__}/main.js"' in response.text
    assert "{{VERSION}}" not in response.text


def test_versioned_asset_served(client: TestClient) -> None:
    response = client.get(f"/static/{__version__}/api.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


@pytest.mark.parametrize("path", ["/api/nope", "/api", "/api/health/extra"])
def test_unknown_api_path_is_json_404(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "<html" not in response.text


@pytest.mark.parametrize(
    "path", [f"/static/{__version__}/missing.js", "/static/0.0.0/api.js", "/static"]
)
def test_missing_static_is_404_not_shell(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert "<html" not in response.text


def test_only_api_js_calls_fetch() -> None:
    static = files("language_lab") / "static"
    offenders = [
        entry.name
        for entry in static.iterdir()
        if entry.name.endswith(".js")
        and entry.name != "api.js"
        and re.search(r"\bfetch\s*\(", entry.read_text(encoding="utf-8"))
    ]
    assert offenders == []
    assert "fetch(" in (static / "api.js").read_text(encoding="utf-8")


def test_main_prints_url_and_binds_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(app_module.uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    app_module.main()
    assert "http://127.0.0.1:8787/" in capsys.readouterr().out
    assert calls == [{"host": "127.0.0.1", "port": 8787}]


def test_port_in_use_exits_non_zero() -> None:
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        result = subprocess.run(
            [sys.executable, "-c", "from language_lab.app import main; main()"],
            env={
                **{k: v for k, v in os.environ.items() if k != "LANGUAGE_LAB_HOST"},
                "LANGUAGE_LAB_PORT": str(port),
            },
            capture_output=True,
            timeout=30,
        )
    assert result.returncode != 0

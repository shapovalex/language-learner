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
from tests.support.app_env import HOME_ENV_RELATIVE, config_values, isolated_environ, write_dotenv
from tests.support.fixtures.settings import ConfigFiles, SettingsFactory

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
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    config_files: ConfigFiles,
) -> None:
    config_files.write_home(config_values(LANGUAGE_LAB_HOST="127.0.0.2", LANGUAGE_LAB_PORT="9123"))
    calls: list[dict] = []
    monkeypatch.setattr(app_module.uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    app_module.main()
    assert "http://127.0.0.2:9123/" in capsys.readouterr().out
    assert calls == [{"host": "127.0.0.2", "port": 9123}]


def test_port_in_use_exits_non_zero(tmp_path: Path) -> None:
    home = tmp_path / "home"
    write_dotenv(home / HOME_ENV_RELATIVE, config_values())
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        result = subprocess.run(
            [sys.executable, "-c", "from language_lab.app import main; main()"],
            env=isolated_environ(home, {"LANGUAGE_LAB_PORT": str(port)}),
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
    assert result.returncode != 0
    assert "LanguageLab running at" in result.stdout  # failed on the busy port, not the config


def test_health_and_shell_expose_no_settings_values(settings_factory: SettingsFactory) -> None:
    """R-06: no configured value reaches /api/health or the shell."""
    values = config_values()
    settings = settings_factory(env=values)
    client = TestClient(create_app(settings))
    sentinels = [
        values[key]
        for key in (
            "LANGUAGE_LAB_PUBLIC_HOST",
            "ANKI_PREFIX",
            "AZURE_SPEECH_KEY",
            "OPENROUTER_API_KEY",
        )
    ]
    assert settings.azure_speech_key.get_secret_value() in sentinels  # the config took effect

    for path in ("/api/health", "/", "/captures"):
        body = client.get(path).text
        assert [value for value in sentinels if value in body] == []

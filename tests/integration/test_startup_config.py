"""Story 1.2: startup aborts on a bad configuration without echoing secrets."""

from pathlib import Path

import pytest

from tests.support.app_env import HOME_ENV_RELATIVE, config_values, isolated_environ, write_dotenv
from tests.support.live_server import bind_free_port
from tests.support.startup import run_language_lab

INVALID_PREFIX = "Language-Lab"  # fails AD-4's ^[A-Za-z][A-Za-z0-9]*$


@pytest.mark.p0
def test_invalid_prefix_aborts_startup_without_echoing_secrets(tmp_path: Path) -> None:
    """AC-3: an invalid ANKI_PREFIX exits non-zero, and no secret reaches the output."""
    home = tmp_path / "home"
    values = config_values(ANKI_PREFIX=INVALID_PREFIX)
    write_dotenv(home / HOME_ENV_RELATIVE, values)
    with bind_free_port() as sock:
        # A free port in the process env, so a server that wrongly starts can't fail on a busy 8787.
        port = str(sock.getsockname()[1])

    result = run_language_lab(env=isolated_environ(home, {"LANGUAGE_LAB_PORT": port}), cwd=tmp_path)

    assert result.returncode not in (None, 0)
    assert values["AZURE_SPEECH_KEY"] not in result.output
    assert values["OPENROUTER_API_KEY"] not in result.output
    assert "ANKI_PREFIX" in result.output
    assert "Traceback" not in result.output


def _free_port() -> str:
    with bind_free_port() as sock:
        return str(sock.getsockname()[1])


@pytest.mark.p0
def test_dev_refusal_aborts_startup_without_echoing_secrets(tmp_path: Path) -> None:
    """AC-6 via main(): the model-level refusal must not print its input dict (R-06)."""
    home = tmp_path / "home"
    values = config_values(ANKI_PREFIX="LanguageLab")
    write_dotenv(tmp_path / ".env", values)
    env = isolated_environ(home, {"LANGUAGE_LAB_DEV": "1", "LANGUAGE_LAB_PORT": _free_port()})

    result = run_language_lab(env=env, cwd=tmp_path)

    assert result.returncode == 1
    assert "ANKI_PREFIX" in result.output
    assert values["AZURE_SPEECH_KEY"] not in result.output
    assert values["OPENROUTER_API_KEY"] not in result.output
    assert "Traceback" not in result.output


@pytest.mark.p1
@pytest.mark.parametrize("dev", [False, True])
def test_missing_config_aborts_startup_naming_the_path(tmp_path: Path, dev: bool) -> None:
    """Decision 2026-10-10: the mode's .env missing is fatal, even if the other one exists."""
    home = tmp_path / "home"
    if dev:
        write_dotenv(home / HOME_ENV_RELATIVE, config_values())
        expected = tmp_path / ".env"
    else:
        write_dotenv(tmp_path / ".env", config_values())
        expected = home / HOME_ENV_RELATIVE
    extra = {"LANGUAGE_LAB_PORT": _free_port(), **({"LANGUAGE_LAB_DEV": "1"} if dev else {})}

    result = run_language_lab(env=isolated_environ(home, extra), cwd=tmp_path)

    assert result.returncode == 1
    assert f"no config at {expected.resolve()}; copy .env.example" in result.output
    assert "Traceback" not in result.output

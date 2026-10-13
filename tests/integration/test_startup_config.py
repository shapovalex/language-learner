"""Story 1.2: startup aborts on a bad configuration without echoing secrets."""

import stat
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


NECESSARY = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "OPENROUTER_API_KEY")


@pytest.mark.p0
@pytest.mark.parametrize("dev", [False, True])
def test_missing_config_without_tty_is_created_and_startup_aborts(
    tmp_path: Path, dev: bool
) -> None:
    """No terminal: the mode's .env is created from the template, and the user told what to set.

    The other mode's file existing changes nothing (decision 2026-10-10), and stays untouched.
    """
    home = tmp_path / "home"
    if dev:
        other = write_dotenv(home / HOME_ENV_RELATIVE, config_values())
        expected = tmp_path / ".env"
    else:
        other = write_dotenv(tmp_path / ".env", config_values())
        expected = home / HOME_ENV_RELATIVE
    other_bytes = other.read_bytes()
    extra = {"LANGUAGE_LAB_PORT": _free_port(), **({"LANGUAGE_LAB_DEV": "1"} if dev else {})}

    result = run_language_lab(env=isolated_environ(home, extra), cwd=tmp_path)

    assert result.returncode == 1
    assert f"created config at {expected.resolve()}" in result.output
    for variable in NECESSARY:
        assert variable in result.output
    assert "Traceback" not in result.output
    assert stat.S_IMODE(expected.stat().st_mode) == 0o600
    prefix = "LanguageLabDev" if dev else "LanguageLab"
    assert f"ANKI_PREFIX={prefix}" in expected.read_text(encoding="utf-8").splitlines()
    assert other.read_bytes() == other_bytes


@pytest.mark.p1
@pytest.mark.parametrize(
    ("content", "valid"), [(b"", True), (f"ANKI_PREFIX={INVALID_PREFIX}\n".encode(), False)]
)
def test_existing_config_is_never_modified(tmp_path: Path, content: bytes, valid: bool) -> None:
    """An existing file, even empty or invalid, is read as is: bytes and mode unchanged."""
    home = tmp_path / "home"
    path = home / HOME_ENV_RELATIVE
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    path.chmod(0o644)

    result = run_language_lab(
        env=isolated_environ(home, {"LANGUAGE_LAB_PORT": _free_port()}), cwd=tmp_path, timeout_s=3
    )

    assert "created config" not in result.output
    assert "Traceback" not in result.output
    if valid:  # read as today: an empty file means defaults, so the server is still up
        assert result.returncode is None, result.output
    else:  # the same validation error as before this feature
        assert result.returncode == 1
        assert "ANKI_PREFIX" in result.output
    assert path.read_bytes() == content
    assert stat.S_IMODE(path.stat().st_mode) == 0o644

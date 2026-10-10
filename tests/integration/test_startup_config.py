"""Story 1.2 (ATDD red phase): startup aborts on a bad configuration without echoing secrets."""

from pathlib import Path

import pytest

from tests.support.app_env import HOME_ENV_RELATIVE, config_values, isolated_environ, write_dotenv
from tests.support.live_server import bind_free_port
from tests.support.startup import run_language_lab

INVALID_PREFIX = "Language-Lab"  # fails AD-4's ^[A-Za-z][A-Za-z0-9]*$


@pytest.mark.skip(reason="ATDD red phase, story 1.2: un-skip with ANKI_PREFIX validation")
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

"""Story 1.8: the wheel the release uploads runs the documented way (AC1, R-04, R-12).

The wheel is built with `uv build`, or given with `--wheel dist/<wheel>` (release.yml smokes
the exact file it attaches). It starts under `uvx --from <wheel> language-lab` with a temp HOME
whose ~/.config/language-lab/.env is its only config. The Mac Mini run stays manual.

The behaviour predates this story (entries 1 and 2). release.yml runs these tests against the
wheel it uploads, before the upload.
"""

import socket
import stat
from pathlib import Path

import httpx
import pytest

from tests.support.app_env import HOME_ENV_RELATIVE, isolated_environ
from tests.support.fixtures.release import ReleaseRun
from tests.support.release import (
    non_loopback_address,
    pyproject_version,
    run_released_until_exit,
    uv_cache_dir,
)

# One xdist worker builds the wheel once, as in a serial run (Makefile passes --dist loadgroup)
pytestmark = pytest.mark.xdist_group("release_wheel")

VERSION = pyproject_version()
DEEP_CLIENT_PATH = "/any/deep/path"
SERVING_ON = "Uvicorn running on http://127.0.0.1:"  # uvicorn's line: the socket it bound


@pytest.mark.p0
def test_built_wheel_serves_its_version_assets_and_shell(released_app: ReleaseRun) -> None:
    """AC-3: the uv-built wheel reports the pyproject version and ships its static assets."""
    base = released_app.app.url

    health = httpx.get(f"{base}/api/health")
    asset = httpx.get(f"{base}/static/{VERSION}/main.js")
    shell = httpx.get(f"{base}{DEEP_CLIENT_PATH}")

    assert health.json() == {"version": VERSION}
    assert asset.status_code == 200
    assert "javascript" in asset.headers["content-type"]
    assert shell.status_code == 200
    assert shell.headers["content-type"].startswith("text/html")
    assert f'src="/static/{VERSION}/main.js"' in shell.text


@pytest.mark.p0
def test_uvx_start_loads_the_home_config(released_app: ReleaseRun) -> None:
    """AC-5: `uvx --from <wheel> language-lab` reads ~/.config/language-lab/.env."""
    output = released_app.app.output
    public_host = released_app.config["LANGUAGE_LAB_PUBLIC_HOST"]

    assert f"LanguageLab running at http://127.0.0.1:{released_app.port}/" in output
    assert f"https://{public_host}/" in output
    assert "Traceback" not in output


@pytest.mark.p0
def test_uvx_start_listens_on_loopback_only(released_app: ReleaseRun) -> None:
    """AC-6: the released app answers on 127.0.0.1 and refuses this machine's LAN address."""
    lan_address = non_loopback_address()
    if lan_address is None:
        pytest.skip("this machine has no non-loopback address to probe")

    with pytest.raises(ConnectionRefusedError):
        socket.create_connection((lan_address, released_app.port), timeout=5).close()
    assert httpx.get(f"{released_app.app.url}/api/health").status_code == 200
    assert f"{SERVING_ON}{released_app.port}" in released_app.app.output


@pytest.mark.p0
def test_uvx_start_on_a_bare_home_creates_the_config(release_wheel: Path, tmp_path: Path) -> None:
    """A fresh machine, no terminal: the wheel writes ~/.config/language-lab/.env from its own
    template, mode 0600, names the three variables to set, and exits 1."""
    home = tmp_path / "home"
    home.mkdir()
    env = isolated_environ(home, {"UV_CACHE_DIR": uv_cache_dir()})

    run = run_released_until_exit(release_wheel, env=env, cwd=tmp_path)

    config = home / HOME_ENV_RELATIVE
    assert run.returncode == 1, run.output
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert "ANKI_PREFIX=LanguageLab" in config.read_text(encoding="utf-8").splitlines()
    assert f"created config at {config}" in run.output
    for variable in ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "OPENROUTER_API_KEY"):
        assert variable in run.output
    assert "Traceback" not in run.output

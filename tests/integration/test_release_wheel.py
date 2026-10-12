"""Story 1.8: the wheel the release uploads runs the documented way (AC1, R-04, R-12).

The wheel is built with `uv build`, or given with `--wheel dist/<wheel>` (release.yml smokes
the exact file it attaches). It starts under `uvx --from <wheel> language-lab` with a temp HOME
whose ~/.config/language-lab/.env is its only config. The Mac Mini run stays manual.

The behaviour predates this story (entries 1 and 2). release.yml runs these tests against the
wheel it uploads, before the upload.
"""

import socket

import httpx
import pytest

from tests.support.fixtures.release import ReleaseRun
from tests.support.release import non_loopback_address, pyproject_version

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

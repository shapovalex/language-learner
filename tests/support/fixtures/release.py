"""`release_wheel`, `released_app`: the wheel the release ships, started the documented way."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.support.app_env import HOME_ENV_RELATIVE, config_values, isolated_environ, write_dotenv
from tests.support.live_server import bind_free_port
from tests.support.release import ReleasedApp, build_wheel, run_released_app, uv_cache_dir


@pytest.fixture(scope="session")
def release_wheel(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """`--wheel PATH` when given (release.yml passes the wheel it uploads), else a fresh build."""
    given = request.config.getoption("--wheel")
    if given is not None:
        return Path(given).resolve()
    return build_wheel(tmp_path_factory.mktemp("dist"))


@dataclass(frozen=True)
class ReleaseRun:
    app: ReleasedApp
    port: int
    config: dict[str, str]  # what ~/.config/language-lab/.env holds


@pytest.fixture(scope="module")
def released_app(
    release_wheel: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[ReleaseRun]:
    """The wheel under `uvx` with a temp HOME whose ~/.config .env is the only config.

    The port and the tailnet host are set in that file and nowhere in the process env, so
    the app serving on that port proves it read the file (AC1, FR-1).
    """
    root = tmp_path_factory.mktemp("release")
    home = root / "home"
    with bind_free_port() as sock:
        port = sock.getsockname()[1]
    config = config_values(LANGUAGE_LAB_PORT=str(port))
    write_dotenv(home / HOME_ENV_RELATIVE, config)
    env = isolated_environ(home, {"UV_CACHE_DIR": uv_cache_dir()})

    with run_released_app(release_wheel, env=env, cwd=root, port=port) as app:
        yield ReleaseRun(app=app, port=port, config=config)

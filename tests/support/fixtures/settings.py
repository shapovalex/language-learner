"""`settings_factory`: builds `Settings` isolated from the developer's environment."""

import os
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from language_lab.settings import Settings

ENV_PREFIX = Settings.model_config["env_prefix"]

type SettingsFactory = Callable[..., Settings]


@pytest.fixture
def settings_factory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SettingsFactory:
    """Return `make(env=None, **overrides) -> Settings`.

    Every `LANGUAGE_LAB_*` variable is cleared, and HOME and the working directory point
    into `tmp_path`, so no real `.env` or `~/.config` leaks in. `env` sets variables the
    way a user would; keyword overrides go straight to `Settings`. monkeypatch undoes
    everything after the test.
    """
    for key in [k for k in os.environ if k.startswith(ENV_PREFIX)]:
        monkeypatch.delenv(key)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    def make(*, env: Mapping[str, str] | None = None, **overrides: object) -> Settings:
        for key, value in (env or {}).items():
            monkeypatch.setenv(key, value)
        return Settings(**overrides)

    return make

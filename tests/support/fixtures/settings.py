"""`settings_factory`, `settings_loader`, `config_files`: Settings isolated from the dev's env."""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from language_lab import settings as settings_module
from language_lab.settings import Settings
from tests.support.app_env import APP_ENV_PREFIXES, HOME_ENV_RELATIVE, write_dotenv

type SettingsFactory = Callable[..., Settings]
type SettingsLoader = Callable[..., Settings]


@dataclass(frozen=True)
class ConfigFiles:
    home: Path  # ~/.config/language-lab/.env under the temp HOME (release mode)
    repo: Path  # ./.env in the temp working directory (dev mode)

    def write_home(self, values: Mapping[str, str]) -> Path:
        return write_dotenv(self.home, values)

    def write_repo(self, values: Mapping[str, str]) -> Path:
        return write_dotenv(self.repo, values)


@pytest.fixture
def settings_factory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SettingsFactory:
    """Return `make(env=None, **overrides) -> Settings`.

    Every app variable (`LANGUAGE_LAB_*`, `ANKI_*`, `AZURE_SPEECH_*`, `OPENROUTER_*`) is
    cleared, and HOME and the working directory point into `tmp_path`, so no real `.env` or
    `~/.config` leaks in. `env` sets variables the way a user would; keyword overrides go
    straight to `Settings`. monkeypatch undoes everything after the test.
    """
    for key in [k for k in os.environ if k.startswith(APP_ENV_PREFIXES)]:
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


@pytest.fixture
def config_files(settings_factory: SettingsFactory, tmp_path: Path) -> ConfigFiles:
    """The two `.env` paths inside the isolated HOME and working directory. Nothing is written."""
    return ConfigFiles(home=tmp_path / "home" / HOME_ENV_RELATIVE, repo=tmp_path / ".env")


@pytest.fixture
def settings_loader(
    settings_factory: SettingsFactory, monkeypatch: pytest.MonkeyPatch
) -> SettingsLoader:
    """Return `load(env=None) -> Settings`: the startup path, `load_settings()`, in isolation."""

    def load(*, env: Mapping[str, str] | None = None) -> Settings:
        for key, value in (env or {}).items():
            monkeypatch.setenv(key, value)
        return settings_module.load_settings()

    return load

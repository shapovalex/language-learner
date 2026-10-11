"""Application configuration (AD-18): the only module that reads the environment or a `.env`."""

import os
from pathlib import Path
from typing import Annotated, Self, TypedDict

from pydantic import (
    Field,
    SecretStr,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ENV_PREFIX = "LANGUAGE_LAB_"
DEV_ENV = f"{ENV_PREFIX}DEV"
HOME_ENV_RELATIVE = Path(".config/language-lab/.env")
RELEASE_PREFIX = "LanguageLab"  # dev mode may never write this Prefix (AD-4, Q5)
PREFIX_PATTERN = r"^[A-Za-z][A-Za-z0-9]*$"


class ConfigError(ValueError):
    """The configuration file the current mode needs does not exist."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file_encoding="utf-8",
        extra="ignore",
        validate_by_name=True,
        validate_by_alias=True,
    )

    host: str = "127.0.0.1"  # loopback by default (R-12)
    port: int = 8787
    public_host: str | None = None
    dev: bool = False

    anki_connect_url: str = Field("http://127.0.0.1:8765", validation_alias="ANKI_CONNECT_URL")
    anki_prefix: str = Field(RELEASE_PREFIX, validation_alias="ANKI_PREFIX", pattern=PREFIX_PATTERN)
    azure_speech_key: SecretStr = Field(SecretStr(""), validation_alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field("", validation_alias="AZURE_SPEECH_REGION")
    openrouter_api_key: SecretStr = Field(SecretStr(""), validation_alias="OPENROUTER_API_KEY")
    openrouter_models: Annotated[list[str], NoDecode] = Field(
        default_factory=list, validation_alias="OPENROUTER_MODELS"
    )

    @field_validator("public_host", mode="before")
    @classmethod
    def _blank_public_host_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("openrouter_models", mode="before")
    @classmethod
    def _split_models(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def _dev_never_uses_release_prefix(self) -> Self:
        if self.dev and self.anki_prefix.casefold() == RELEASE_PREFIX.casefold():
            raise ValueError(
                f"ANKI_PREFIX must not be {RELEASE_PREFIX} (any case) when {DEV_ENV} is on; "
                "use a dev Prefix such as LanguageLabDev"
            )
        return self


class _DevFlag(TypedDict, total=False):
    LANGUAGE_LAB_DEV: bool


def _dev_mode() -> bool:
    """`LANGUAGE_LAB_DEV` from the process env, parsed with the same rules as `Settings.dev`."""
    # Settings matches env keys case-insensitively (later keys win), so match the same way.
    env = {key.lower(): value for key, value in os.environ.items()}
    raw = env.get(DEV_ENV.lower())
    if raw is None:
        return False
    return TypeAdapter(_DevFlag).validate_python({DEV_ENV: raw})[DEV_ENV]


def config_path(dev: bool) -> Path:
    """`./.env` in dev mode, `~/.config/language-lab/.env` otherwise. Resolved at call time."""
    return Path.cwd() / ".env" if dev else Path.home() / HOME_ENV_RELATIVE


def load_settings() -> Settings:
    """Settings from the current mode's `.env`; the process env overrides the file.

    Raises `ConfigError` if that file is missing or unreadable, and `ValidationError` if a
    value is invalid.
    """
    path = config_path(_dev_mode())
    if not path.is_file():
        raise ConfigError(f"no config at {path}; copy .env.example")
    try:
        return Settings(_env_file=path)
    except OSError as exc:
        raise ConfigError(f"cannot read config at {path}: {exc.strerror}") from exc


def _env_key(field_or_alias: str) -> str:
    field = Settings.model_fields.get(field_or_alias)
    if field is None:
        return field_or_alias
    alias = field.validation_alias
    return alias if isinstance(alias, str) else f"{ENV_PREFIX}{field_or_alias}".upper()


def describe_errors(exc: ValidationError) -> list[str]:
    """One `<ENV_KEY>: <message>` line per error. Never includes the input value (R-06)."""
    lines = []
    for error in exc.errors(include_input=False, include_url=False):
        loc = error["loc"]
        msg = error["msg"].removeprefix("Value error, ")
        # A model-level error has no loc; its message names the key itself.
        lines.append(f"{_env_key(str(loc[0]))}: {msg}" if loc else msg)
    return lines

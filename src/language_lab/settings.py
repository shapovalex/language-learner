"""Application configuration (AD-18). Entry 2 adds the `.env` load and remaining keys."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LANGUAGE_LAB_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8787

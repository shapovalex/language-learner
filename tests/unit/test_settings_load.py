"""Story 1.2 (ATDD red phase): configuration from ~/.config/language-lab/.env.

Each test is skipped until `load_settings()` lands. Un-skip one per task, watch it fail,
then make it pass.
"""

from pathlib import Path

import pytest

from tests.support.app_env import config_values, dotenv_keys, settings_env_names
from tests.support.fixtures.settings import ConfigFiles, SettingsLoader

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 1.2: un-skip with load_settings()")

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
RELEASE_PREFIX = "LanguageLab"  # AD-4 / epic note: dev mode may never write this Prefix
DEV_PREFIX = "LanguageLabDev"
DEV_ON = {"LANGUAGE_LAB_DEV": "1"}


@RED_PHASE
@pytest.mark.p0
def test_release_mode_loads_home_config(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-1: release mode loads ~/.config/language-lab/.env with every A2 key."""
    values = config_values()
    config_files.write_home(values)

    settings = settings_loader()

    assert settings.anki_prefix == values["ANKI_PREFIX"]
    assert {
        "host": settings.host,
        "port": settings.port,
        "public_host": settings.public_host,
        "dev": settings.dev,
        "anki_connect_url": settings.anki_connect_url,
        "azure_speech_key": settings.azure_speech_key.get_secret_value(),
        "azure_speech_region": settings.azure_speech_region,
        "openrouter_api_key": settings.openrouter_api_key.get_secret_value(),
    } == {
        "host": values["LANGUAGE_LAB_HOST"],
        "port": int(values["LANGUAGE_LAB_PORT"]),
        "public_host": values["LANGUAGE_LAB_PUBLIC_HOST"],
        "dev": False,
        "anki_connect_url": values["ANKI_CONNECT_URL"],
        "azure_speech_key": values["AZURE_SPEECH_KEY"],
        "azure_speech_region": values["AZURE_SPEECH_REGION"],
        "openrouter_api_key": values["OPENROUTER_API_KEY"],
    }


@RED_PHASE
@pytest.mark.p1
def test_unknown_keys_are_ignored(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-2: unknown keys in the .env, prefixed or not, don't break startup."""
    values = config_values(LANGUAGE_LAB_FUTURE_FLAG="on", SOME_OTHER_TOOL_TOKEN="abc123")
    config_files.write_home(values)

    settings = settings_loader()

    assert settings.anki_prefix == values["ANKI_PREFIX"]
    assert not hasattr(settings, "language_lab_future_flag")
    assert not hasattr(settings, "future_flag")


@RED_PHASE
@pytest.mark.p1
def test_dev_flag_is_exposed(config_files: ConfigFiles, settings_loader: SettingsLoader) -> None:
    """AC-4: LANGUAGE_LAB_DEV=1 shows as `settings.dev`."""
    config_files.write_repo(config_values(ANKI_PREFIX=DEV_PREFIX))

    settings = settings_loader(env=DEV_ON)

    assert settings.dev is True


@RED_PHASE
@pytest.mark.p0
def test_dev_mode_reads_repo_env_instead_of_home(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-5: dev mode reads ./.env, not ~/.config/language-lab/.env."""
    config_files.write_home(config_values())
    config_files.write_repo(config_values(ANKI_PREFIX=DEV_PREFIX))

    settings = settings_loader(env=DEV_ON)

    assert settings.anki_prefix == DEV_PREFIX


@RED_PHASE
@pytest.mark.p0
def test_dev_mode_refuses_release_prefix(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-6: dev mode refuses ANKI_PREFIX=LanguageLab."""
    config_files.write_repo(config_values(ANKI_PREFIX=RELEASE_PREFIX))

    with pytest.raises(ValueError, match=r"(?i)anki_prefix"):
        settings_loader(env=DEV_ON)


@RED_PHASE
@pytest.mark.p1
def test_openrouter_models_parse_in_order(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-7: OPENROUTER_MODELS, comma-separated, parses to a list in the configured order."""
    models = "anthropic/claude-sonnet-4.6, openai/gpt-5.6-luna ,google/gemini-3.5-flash-lite"
    config_files.write_home(config_values(OPENROUTER_MODELS=models))

    settings = settings_loader()

    assert settings.openrouter_models == [
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-5.6-luna",
        "google/gemini-3.5-flash-lite",
    ]


@RED_PHASE
@pytest.mark.p1
def test_env_example_documents_every_settings_field() -> None:
    """AC-8: every Settings field has its key in .env.example."""
    missing = sorted(settings_env_names() - dotenv_keys(ENV_EXAMPLE))

    assert missing == []

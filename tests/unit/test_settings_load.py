"""Story 1.2: configuration from ~/.config/language-lab/.env."""

from pathlib import Path

import pytest

from language_lab.settings import ConfigError
from tests.support.app_env import config_values, dotenv_keys, settings_env_names
from tests.support.fixtures.settings import ConfigFiles, SettingsFactory, SettingsLoader

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
RELEASE_PREFIX = "LanguageLab"  # AD-4 / epic note: dev mode may never write this Prefix
DEV_PREFIX = "LanguageLabDev"
DEV_ON = {"LANGUAGE_LAB_DEV": "1"}


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


@pytest.mark.p1
def test_dev_flag_is_exposed(config_files: ConfigFiles, settings_loader: SettingsLoader) -> None:
    """AC-4: LANGUAGE_LAB_DEV=1 shows as `settings.dev`."""
    config_files.write_repo(config_values(ANKI_PREFIX=DEV_PREFIX))

    settings = settings_loader(env=DEV_ON)

    assert settings.dev is True


@pytest.mark.p0
def test_dev_mode_reads_repo_env_instead_of_home(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-5: dev mode reads ./.env, not ~/.config/language-lab/.env."""
    config_files.write_home(config_values())
    config_files.write_repo(config_values(ANKI_PREFIX=DEV_PREFIX))

    settings = settings_loader(env=DEV_ON)

    assert settings.anki_prefix == DEV_PREFIX


@pytest.mark.p0
def test_dev_mode_refuses_release_prefix(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-6: dev mode refuses ANKI_PREFIX=LanguageLab."""
    config_files.write_repo(config_values(ANKI_PREFIX=RELEASE_PREFIX))

    with pytest.raises(ValueError, match=r"(?i)anki_prefix"):
        settings_loader(env=DEV_ON)


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


@pytest.mark.p1
def test_env_example_documents_every_settings_field() -> None:
    """AC-8: every Settings field has its key in .env.example."""
    missing = sorted(settings_env_names() - dotenv_keys(ENV_EXAMPLE))

    assert missing == []


# Green-phase backlog (ATDD checklist 1-2).


@pytest.mark.p1
@pytest.mark.parametrize("prefix", ["Language-Lab", "1Lab", "Lab::X", "Lang Lab", "", "Labé"])
def test_invalid_prefix_is_rejected(
    config_files: ConfigFiles, settings_loader: SettingsLoader, prefix: str
) -> None:
    """AC-3: ANKI_PREFIX must match ^[A-Za-z][A-Za-z0-9]*$ (AD-4)."""
    config_files.write_home(config_values(ANKI_PREFIX=prefix))

    with pytest.raises(ValueError, match="ANKI_PREFIX"):
        settings_loader()


@pytest.mark.p0
@pytest.mark.parametrize("prefix", ["LanguageLab", "languagelab", "LANGUAGELAB"])
def test_dev_mode_refuses_release_prefix_in_any_case(
    config_files: ConfigFiles, settings_loader: SettingsLoader, prefix: str
) -> None:
    """AC-6 / Q5: the release Prefix is refused in dev mode whatever its letter case."""
    config_files.write_repo(config_values(ANKI_PREFIX=prefix))

    with pytest.raises(ValueError, match="ANKI_PREFIX"):
        settings_loader(env=DEV_ON)


@pytest.mark.p0
def test_dev_mode_accepts_dev_prefix(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-6: LanguageLabDev is a valid dev Prefix."""
    config_files.write_repo(config_values(ANKI_PREFIX=DEV_PREFIX))

    assert settings_loader(env={"LANGUAGE_LAB_DEV": "true"}).anki_prefix == DEV_PREFIX


@pytest.mark.p1
def test_dev_flag_inside_release_file_still_refuses_release_prefix(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """Design note: LANGUAGE_LAB_DEV=1 inside the home file fails safe."""
    config_files.write_home(config_values(ANKI_PREFIX=RELEASE_PREFIX, LANGUAGE_LAB_DEV="1"))

    with pytest.raises(ValueError, match="ANKI_PREFIX"):
        settings_loader()


@pytest.mark.p1
def test_release_prefix_is_accepted_in_release_mode(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    config_files.write_home(config_values(ANKI_PREFIX=RELEASE_PREFIX))

    assert settings_loader().anki_prefix == RELEASE_PREFIX


@pytest.mark.p1
def test_invalid_dev_flag_is_a_validation_error(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    config_files.write_home(config_values())
    config_files.write_repo(config_values(ANKI_PREFIX=DEV_PREFIX))

    with pytest.raises(ValueError, match="LANGUAGE_LAB_DEV"):
        settings_loader(env={"LANGUAGE_LAB_DEV": "maybe"})


@pytest.mark.p1
def test_dev_mode_does_not_load_home_only_keys(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-5: a key set only in the home file is not loaded in dev mode."""
    config_files.write_home(config_values())
    repo_values = config_values(ANKI_PREFIX=DEV_PREFIX)
    del repo_values["AZURE_SPEECH_REGION"]
    config_files.write_repo(repo_values)

    settings = settings_loader(env=DEV_ON)

    assert settings.azure_speech_region == ""


@pytest.mark.p1
def test_release_mode_ignores_cwd_env(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """AC-5: release mode never reads ./.env."""
    home_values = config_values()
    config_files.write_home(home_values)
    config_files.write_repo(config_values(ANKI_PREFIX=DEV_PREFIX))

    assert settings_loader().anki_prefix == home_values["ANKI_PREFIX"]


@pytest.mark.p1
def test_process_env_overrides_file(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    config_files.write_home(config_values())

    assert settings_loader(env={"LANGUAGE_LAB_PORT": "9001"}).port == 9001


@pytest.mark.p2
@pytest.mark.parametrize(
    ("raw", "expected"), [("a, b ,c", ["a", "b", "c"]), ("", []), ("a,,b,", ["a", "b"])]
)
def test_openrouter_models_edge_cases(
    config_files: ConfigFiles, settings_loader: SettingsLoader, raw: str, expected: list[str]
) -> None:
    """AC-7: values are trimmed and blank entries dropped."""
    config_files.write_home(config_values(OPENROUTER_MODELS=raw))

    assert settings_loader().openrouter_models == expected


@pytest.mark.p1
def test_missing_home_file_is_fatal_in_release_mode(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """Decision 2026-10-10: no home .env aborts, even when ./.env exists."""
    config_files.write_repo(config_values())

    with pytest.raises(ConfigError, match=str(config_files.home)):
        settings_loader()


@pytest.mark.p1
def test_missing_repo_file_is_fatal_in_dev_mode(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """Decision 2026-10-10: no ./.env aborts dev mode, even when the home .env exists."""
    config_files.write_home(config_values())

    with pytest.raises(ConfigError, match=str(config_files.repo)):
        settings_loader(env=DEV_ON)


@pytest.mark.p1
def test_settings_without_file_uses_defaults(settings_factory: SettingsFactory) -> None:
    """R-12: Settings built directly still binds loopback:8787."""
    settings = settings_factory()

    assert (settings.host, settings.port, settings.anki_prefix) == (
        "127.0.0.1",
        8787,
        RELEASE_PREFIX,
    )


@pytest.mark.p1
def test_repr_and_str_hide_secrets(
    config_files: ConfigFiles, settings_loader: SettingsLoader
) -> None:
    """R-06: SecretStr keeps both keys out of repr and str."""
    values = config_values()
    config_files.write_home(values)

    settings = settings_loader()

    for text in (repr(settings), str(settings)):
        assert values["AZURE_SPEECH_KEY"] not in text
        assert values["OPENROUTER_API_KEY"] not in text


@pytest.mark.p2
def test_env_example_has_no_stale_keys() -> None:
    """AC-8: every key in .env.example maps to a Settings field."""
    stale = sorted(dotenv_keys(ENV_EXAMPLE) - settings_env_names())

    assert stale == []

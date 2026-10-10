"""The app's configuration as a user writes it: `.env` files, their keys, a clean process env."""

import os
import re
import uuid
from collections.abc import Mapping
from pathlib import Path

from language_lab.settings import Settings

# Every variable family Settings reads (A2). Cleared from the environment so a developer's
# shell never leaks into a test.
APP_ENV_PREFIXES = ("LANGUAGE_LAB_", "ANKI_", "AZURE_SPEECH_", "OPENROUTER_")

# Where release mode looks, relative to HOME (AD-18).
HOME_ENV_RELATIVE = Path(".config/language-lab/.env")

_DOTENV_KEY = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)


def config_values(**overrides: str) -> dict[str, str]:
    """A complete, valid A2 configuration keyed by env name. Prefix and secrets are unique."""
    token = uuid.uuid4().hex
    values = {
        "LANGUAGE_LAB_HOST": "127.0.0.1",
        "LANGUAGE_LAB_PORT": "8787",
        "LANGUAGE_LAB_PUBLIC_HOST": f"mac-mini-{token[:8]}.tail1234.ts.net",
        "ANKI_CONNECT_URL": "http://127.0.0.1:8765",
        "ANKI_PREFIX": f"Lab{token[:12]}",
        "AZURE_SPEECH_KEY": f"azure-{token}",
        "AZURE_SPEECH_REGION": "westeurope",
        "OPENROUTER_API_KEY": f"sk-or-v1-{token}",
        "OPENROUTER_MODELS": "openai/gpt-5.6-luna,google/gemini-3.5-flash-lite",
    }
    return {**values, **overrides}


def write_dotenv(path: Path, values: Mapping[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    return path


def dotenv_keys(path: Path) -> frozenset[str]:
    """Keys a `.env`-style file documents, commented-out ones included. A missing file has none."""
    if not path.is_file():
        return frozenset()
    return frozenset(_DOTENV_KEY.findall(path.read_text(encoding="utf-8")))


def settings_env_names(model: type[Settings] = Settings) -> frozenset[str]:
    """The env variable each Settings field reads: its string alias, else env_prefix + name."""
    prefix = model.model_config.get("env_prefix", "")
    names = set()
    for name, field in model.model_fields.items():
        alias = field.validation_alias or field.alias
        names.add((alias if isinstance(alias, str) else f"{prefix}{name}").upper())
    return frozenset(names)


def isolated_environ(home: Path, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """This process's env without any app variable, with HOME at `home`, for a subprocess."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(APP_ENV_PREFIXES)}
    return {**env, "HOME": str(home), **(extra or {})}

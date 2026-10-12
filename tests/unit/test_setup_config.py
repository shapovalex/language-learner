"""First start without a config: `_setup_config` creates it from the packaged template."""

import builtins
import getpass
import os
import stat
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from language_lab import app as app_module
from language_lab.app import _setup_config
from language_lab.settings import ConfigError, Settings, render_config
from tests.support.app_env import HOME_ENV_RELATIVE
from tests.support.fixtures.settings import SettingsFactory

AZURE_KEY = "azure-0f1e2d3c4b5a"
REGION = "westeurope"
OPENROUTER_KEY = "sk-or-v1-9a8b7c6d5e4f"
VARIABLES = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "OPENROUTER_API_KEY")


class Prompts:
    """Fake `input` and `getpass`: answers in order, recording which reader got each prompt."""

    def __init__(self, answers: Iterable[str | BaseException]) -> None:
        self._answers = iter(answers)
        self.asked: list[tuple[str, str]] = []  # (reader, prompt)

    def _next(self, reader: str, prompt: str) -> str:
        self.asked.append((reader, prompt))
        answer = next(self._answers)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def line(self, prompt: str) -> str:
        return self._next("line", prompt)

    def secret(self, prompt: str) -> str:
        return self._next("secret", prompt)


def _tty(value: bool) -> Callable[[], bool]:
    return lambda: value


def _env_lines(path: Path) -> set[str]:
    return set(path.read_text(encoding="utf-8").splitlines())


@pytest.fixture
def release_path(tmp_path: Path) -> Path:
    return tmp_path / "home" / HOME_ENV_RELATIVE


@pytest.mark.p0
def test_tty_answers_create_the_release_config_and_return(
    release_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts = Prompts([AZURE_KEY, REGION, OPENROUTER_KEY])

    _setup_config(release_path, False, prompts.line, prompts.secret, _tty(True))

    assert stat.S_IMODE(release_path.stat().st_mode) == 0o600
    assert {
        f"AZURE_SPEECH_KEY={AZURE_KEY}",
        f"AZURE_SPEECH_REGION={REGION}",
        f"OPENROUTER_API_KEY={OPENROUTER_KEY}",
        "ANKI_PREFIX=LanguageLab",
    } <= _env_lines(release_path)
    assert [(reader, prompt.split()[0]) for reader, prompt in prompts.asked] == [
        ("secret", "AZURE_SPEECH_KEY"),
        ("line", "AZURE_SPEECH_REGION"),
        ("secret", "OPENROUTER_API_KEY"),
    ]
    out = capsys.readouterr()
    assert str(release_path) in out.err
    for answer in (AZURE_KEY, REGION, OPENROUTER_KEY):
        assert answer not in out.out + out.err


@pytest.mark.p0
def test_tty_in_dev_mode_writes_the_dev_prefix(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    prompts = Prompts([AZURE_KEY, REGION, OPENROUTER_KEY])

    _setup_config(path, True, prompts.line, prompts.secret, _tty(True))

    lines = _env_lines(path)
    assert {"ANKI_PREFIX=LanguageLabDev", f"OPENROUTER_API_KEY={OPENROUTER_KEY}"} <= lines


@pytest.mark.p1
def test_empty_answers_leave_the_keys_empty(release_path: Path) -> None:
    prompts = Prompts(["", "", ""])

    _setup_config(release_path, False, prompts.line, prompts.secret, _tty(True))

    assert release_path.read_text(encoding="utf-8") == render_config(False, {})


@pytest.mark.p0
def test_no_tty_creates_the_template_names_path_and_variables_and_exits_1(
    release_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts = Prompts([])

    with pytest.raises(SystemExit) as exit_info:
        _setup_config(release_path, False, prompts.line, prompts.secret, _tty(False))

    assert exit_info.value.code == 1
    assert prompts.asked == []
    assert release_path.read_text(encoding="utf-8") == render_config(False, {})
    assert stat.S_IMODE(release_path.stat().st_mode) == 0o600
    err = capsys.readouterr().err
    assert str(release_path) in err
    for variable in VARIABLES:
        assert variable in err


@pytest.mark.p0
@pytest.mark.parametrize("interrupt", [KeyboardInterrupt(), EOFError()])
@pytest.mark.parametrize("at", [0, 1, 2])
def test_interrupt_at_any_prompt_writes_nothing_and_exits_1(
    release_path: Path, capsys: pytest.CaptureFixture[str], interrupt: BaseException, at: int
) -> None:
    prompts = Prompts([AZURE_KEY, REGION, OPENROUTER_KEY][:at] + [interrupt])

    with pytest.raises(SystemExit) as exit_info:
        _setup_config(release_path, False, prompts.line, prompts.secret, _tty(True))

    assert exit_info.value.code == 1
    assert not release_path.exists()
    out = capsys.readouterr()
    assert "cancelled" in out.err
    for answer in (AZURE_KEY, REGION):
        assert answer not in out.out + out.err


@pytest.mark.p0
@pytest.mark.parametrize("unsafe", ["a b", "a'b", 'a"b', "a#b", "a\\b", "a\nb", " zq9x"])
def test_unsafe_answer_is_asked_again_without_echoing_it(
    release_path: Path, capsys: pytest.CaptureFixture[str], unsafe: str
) -> None:
    prompts = Prompts([unsafe, AZURE_KEY, REGION, OPENROUTER_KEY])

    _setup_config(release_path, False, prompts.line, prompts.secret, _tty(True))

    assert [prompt.split()[0] for _, prompt in prompts.asked][:2] == ["AZURE_SPEECH_KEY"] * 2
    assert f"AZURE_SPEECH_KEY={AZURE_KEY}" in _env_lines(release_path)
    err = capsys.readouterr().err
    reasons = [line for line in err.splitlines() if line.startswith("AZURE_SPEECH_KEY:")]
    assert len(reasons) == 1
    assert unsafe.strip() not in err


@pytest.mark.p1
def test_file_that_appears_during_the_prompts_is_not_overwritten(release_path: Path) -> None:
    def appear_then_answer(prompt: str) -> str:
        if prompt.startswith("OPENROUTER_API_KEY"):
            release_path.parent.mkdir(parents=True, exist_ok=True)
            release_path.write_text("MINE=1\n", encoding="utf-8")
        return "x"

    with pytest.raises(ConfigError, match=f"cannot create config at {release_path}"):
        _setup_config(release_path, False, appear_then_answer, appear_then_answer, _tty(True))

    assert release_path.read_text(encoding="utf-8") == "MINE=1\n"


@pytest.mark.p1
@pytest.mark.skipif(os.geteuid() == 0, reason="root can write a read-only directory")
def test_unwritable_directory_is_a_config_error(tmp_path: Path) -> None:
    locked = tmp_path / "home"
    locked.mkdir()
    locked.chmod(0o500)
    path = locked / HOME_ENV_RELATIVE
    try:
        with pytest.raises(ConfigError, match=f"cannot create config at {path}"):
            _setup_config(path, False, input, input, _tty(False))
    finally:
        locked.chmod(0o700)


@pytest.mark.p0
def test_main_in_a_terminal_creates_the_config_and_starts_with_the_answers(
    settings_factory: SettingsFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC2: no config + a terminal -> prompts, file created, server started on those values."""
    # settings_factory: app env cleared, HOME=tmp_path/home, cwd=tmp_path, no config anywhere
    prompts = Prompts([AZURE_KEY, REGION, OPENROUTER_KEY])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", prompts.line)
    monkeypatch.setattr(getpass, "getpass", prompts.secret)
    monkeypatch.setattr(app_module.tailscale, "discover_tailnet_host", lambda: None)
    monkeypatch.setattr(app_module, "_configure_logging", lambda: None)
    served: list[Settings] = []
    monkeypatch.setattr(app_module, "create_app", lambda settings: served.append(settings))
    monkeypatch.setattr(app_module.uvicorn, "run", lambda *args, **kwargs: None)

    app_module.main()

    config = tmp_path / "home" / HOME_ENV_RELATIVE
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    (settings,) = served
    assert (
        settings.azure_speech_key.get_secret_value(),
        settings.azure_speech_region,
        settings.openrouter_api_key.get_secret_value(),
        settings.anki_prefix,
    ) == (AZURE_KEY, REGION, OPENROUTER_KEY, "LanguageLab")
    out = capsys.readouterr()
    for answer in (AZURE_KEY, REGION, OPENROUTER_KEY):
        assert answer not in out.out + out.err

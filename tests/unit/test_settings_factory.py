import pytest

from tests.support.fixtures.settings import SettingsFactory


@pytest.fixture
def developer_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """A shell that already exports a bind port before the test starts."""
    monkeypatch.setenv("LANGUAGE_LAB_PORT", "9999")


class TestSettingsFactory:
    def test_ignores_ambient_environment(
        self, developer_shell: None, settings_factory: SettingsFactory
    ) -> None:
        assert settings_factory().port == 8787

    @pytest.mark.parametrize(
        ("env", "expected_host", "expected_port"),
        [
            ({"LANGUAGE_LAB_HOST": "0.0.0.0"}, "0.0.0.0", 8787),
            ({"LANGUAGE_LAB_PORT": "9001"}, "127.0.0.1", 9001),
        ],
    )
    def test_env_reaches_settings(
        self,
        settings_factory: SettingsFactory,
        env: dict[str, str],
        expected_host: str,
        expected_port: int,
    ) -> None:
        settings = settings_factory(env=env)
        assert (settings.host, settings.port) == (expected_host, expected_port)

    def test_keyword_override_beats_env(self, settings_factory: SettingsFactory) -> None:
        settings = settings_factory(env={"LANGUAGE_LAB_PORT": "9001"}, port=9002)
        assert settings.port == 9002

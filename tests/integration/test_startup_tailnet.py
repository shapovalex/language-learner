"""Story 1.4: startup prints the Tailscale URL when the tailnet host is known (FR-1).

`main()` runs in-process with `uvicorn.run` replaced, so nothing binds a port.
"""

from dataclasses import dataclass, field

import pytest

from language_lab import app as app_module
from language_lab.adapters import tailscale
from tests.fakes.discovery import FakeDiscovery
from tests.support.app_env import config_values
from tests.support.fixtures.settings import ConfigFiles
from tests.support.hosts import TAILNET_HOST


@dataclass
class ServeRecorder:
    """Stands in for `uvicorn.run`: records the call and returns at once."""

    calls: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, app: object, **kwargs: object) -> None:
        self.calls.append({"app": app, **kwargs})


@pytest.mark.p2
def test_startup_prints_the_tailscale_url_when_known(
    config_files: ConfigFiles, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-8: with the tailnet host known, startup prints its HTTPS URL."""
    config_files.write_home(config_values(LANGUAGE_LAB_PUBLIC_HOST=TAILNET_HOST))
    serve = ServeRecorder()
    monkeypatch.setattr(app_module.uvicorn, "run", serve)

    app_module.main()

    assert f"https://{TAILNET_HOST}/" in capsys.readouterr().out
    assert len(serve.calls) == 1


@pytest.mark.p1
def test_startup_continues_without_a_tailnet_url_when_discovery_fails(
    config_files: ConfigFiles, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-4: with no setting and no Tailscale, startup still serves and prints no https:// line."""
    config_files.write_home(config_values(LANGUAGE_LAB_PUBLIC_HOST=""))
    discover = FakeDiscovery(None)
    monkeypatch.setattr(tailscale, "discover_tailnet_host", discover)
    serve = ServeRecorder()
    monkeypatch.setattr(app_module.uvicorn, "run", serve)

    app_module.main()

    assert len(serve.calls) == 1
    out = capsys.readouterr().out
    assert "https://" not in out
    assert "http://127.0.0.1:8787/" in out
    assert discover.calls == 1


@pytest.mark.p2
def test_startup_prints_the_discovered_tailscale_url(
    config_files: ConfigFiles, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-8: with no setting, the host Tailscale reports is printed as the HTTPS URL."""
    config_files.write_home(config_values(LANGUAGE_LAB_PUBLIC_HOST=""))
    monkeypatch.setattr(tailscale, "discover_tailnet_host", FakeDiscovery(TAILNET_HOST))
    serve = ServeRecorder()
    monkeypatch.setattr(app_module.uvicorn, "run", serve)

    app_module.main()

    assert f"https://{TAILNET_HOST}/" in capsys.readouterr().out
    assert len(serve.calls) == 1

"""Story 1.4: startup prints the Tailscale URL when the tailnet host is known (FR-1).

`main()` runs in-process with `uvicorn.run` replaced, so nothing binds a port.
Skipped until main() prints the tailnet URL. Un-skip, watch it fail, then implement.
"""

from dataclasses import dataclass, field

import pytest

from language_lab import app as app_module
from tests.support.app_env import config_values
from tests.support.fixtures.settings import ConfigFiles
from tests.support.hosts import TAILNET_HOST

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.4: un-skip when main() prints the Tailscale URL"
)


@dataclass
class ServeRecorder:
    """Stands in for `uvicorn.run`: records the call and returns at once."""

    calls: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, app: object, **kwargs: object) -> None:
        self.calls.append({"app": app, **kwargs})


@RED_PHASE
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

"""Story 1.4: the tailnet host comes from LANGUAGE_LAB_PUBLIC_HOST or `tailscale status --json`.

The runner is injected, so no test runs the real `tailscale` (architecture Testing convention).
"""

import subprocess
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

import pytest

from language_lab import app as app_module
from language_lab.adapters import tailscale
from tests.fakes.discovery import FakeDiscovery
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import (
    DISCOVERY_TIMEOUT_S,
    TAILNET_HOST,
    tailscale_status,
    tailscale_status_text,
)


def completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["tailscale", "status", "--json"], returncode, stdout, "")


@dataclass
class FakeRunner:
    """Stands in for `subprocess.run`: records each call, then returns or raises `outcome`."""

    outcome: subprocess.CompletedProcess[str] | Exception
    calls: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append({"args": list(args), **kwargs})
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.mark.p1
def test_public_host_setting_wins_over_discovery(settings_factory: SettingsFactory) -> None:
    """AC-2: LANGUAGE_LAB_PUBLIC_HOST, when set, is the tailnet host, and discovery isn't run."""
    configured = f"studio-{uuid.uuid4().hex[:8]}.tail1234.ts.net"
    settings = settings_factory(env={"LANGUAGE_LAB_PUBLIC_HOST": configured})
    discover = FakeDiscovery(TAILNET_HOST)

    assert app_module.with_tailnet_host(settings, discover=discover).public_host == configured
    assert discover.calls == 0
    unset = settings.model_copy(update={"public_host": None})
    assert app_module.with_tailnet_host(unset, discover=discover).public_host == TAILNET_HOST


@pytest.mark.p1
def test_discovery_reads_the_tailnet_name_from_tailscale_status() -> None:
    """AC-3: discovery parses the recorded `tailscale status --json` into the tailnet host."""
    run = FakeRunner(completed(tailscale_status_text()))

    assert tailscale.discover_tailnet_host(run=run) == TAILNET_HOST
    assert [call["args"][-2:] for call in run.calls] == [["status", "--json"]]


@pytest.mark.p1
@pytest.mark.parametrize(
    "outcome",
    [
        pytest.param(FileNotFoundError(2, "No such file or directory"), id="binary-missing"),
        pytest.param(PermissionError(13, "Permission denied"), id="not-executable"),
        pytest.param(
            subprocess.TimeoutExpired(["tailscale"], DISCOVERY_TIMEOUT_S), id="daemon-hangs"
        ),
        pytest.param(completed("", returncode=1), id="non-zero-exit"),
        pytest.param(completed("not json"), id="unparseable-output"),
        pytest.param(completed(tailscale_status(BackendState="NeedsLogin")), id="logged-out"),
        pytest.param(completed(tailscale_status(Self={})), id="no-dns-name"),
    ],
)
def test_discovery_failure_yields_no_tailnet_host(
    outcome: subprocess.CompletedProcess[str] | Exception,
) -> None:
    """AC-4: discovery is non-fatal: any failure means no tailnet host, never an exception."""
    run = FakeRunner(outcome)

    assert tailscale.discover_tailnet_host(run=run) is None
    assert [call.get("timeout") for call in run.calls] == [DISCOVERY_TIMEOUT_S]

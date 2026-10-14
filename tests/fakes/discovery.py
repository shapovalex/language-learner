"""Fake tailnet discovery: stands in for `tailscale.discover_tailnet_host` (AD-16)."""

from dataclasses import dataclass


@dataclass
class FakeDiscovery:
    """Counts calls and returns `host`."""

    host: str | None
    calls: int = 0

    def __call__(self) -> str | None:
        self.calls += 1
        return self.host

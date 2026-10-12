"""Tailnet discovery (AD-16): the machine's tailnet name from `tailscale status --json`."""

import json
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

# Where the Mac App Store / standalone Tailscale app keeps its CLI when it isn't on PATH
_MACOS_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
DISCOVERY_TIMEOUT_S = 2.0  # Q2: startup waits at most this long for Tailscale

type Runner = Callable[..., subprocess.CompletedProcess[str]]


def _tailscale_binary() -> str:
    return shutil.which("tailscale") or _MACOS_APP_CLI


def discover_tailnet_host(run: Runner | None = None) -> str | None:
    """The tailnet host (`Self.DNSName` without its trailing dot), or None on any failure.

    Never raises: a missing binary, a hung daemon, a logged-out node or odd output all mean
    "no tailnet host", and startup carries on (AD-16).
    """
    runner: Runner = run if run is not None else subprocess.run
    try:
        result = runner(
            [_tailscale_binary(), "status", "--json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=DISCOVERY_TIMEOUT_S,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if result.returncode != 0:
        return None
    try:
        status: Any = json.loads(result.stdout or "")
    except ValueError:
        return None
    if not isinstance(status, dict) or status.get("BackendState") != "Running":
        return None
    me = status.get("Self")
    name = me.get("DNSName") if isinstance(me, dict) else None
    if not isinstance(name, str):
        return None
    host = name.strip().rstrip(".").lower()
    return host or None

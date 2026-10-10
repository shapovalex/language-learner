"""Start `language-lab` in a subprocess and see whether startup aborts."""

import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Long enough for a failing startup to exit; a server that is still up then has started.
STARTUP_ABORT_TIMEOUT_S = 15.0


@dataclass(frozen=True)
class StartupRun:
    returncode: int | None  # None: still running at the deadline, so it was killed
    output: str  # stdout and stderr together


def run_language_lab(
    *, env: Mapping[str, str], cwd: Path, timeout_s: float = STARTUP_ABORT_TIMEOUT_S
) -> StartupRun:
    """Run the console entry point's `main()` with exactly `env` until it exits or times out."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "from language_lab.app import main; main()"],
        env=dict(env),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        output, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        return StartupRun(returncode=None, output=output)
    return StartupRun(returncode=proc.returncode, output=output)

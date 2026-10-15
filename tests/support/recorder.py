"""The fixture recorder (R-05), run as its console script runs it: Tailscale and AnkiConnect."""

import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

# What the `language-lab-record-fixtures` console script runs
RECORDER_COMMAND = [sys.executable, "-m", "language_lab.tools.record_tailscale_fixtures"]
# The line `serve` prints once its socket is listening
LISTENING_MARKER = "Recorder listening on "
RECORDER_START_TIMEOUT_S = 15.0


@dataclass(frozen=True)
class RecorderRun:
    returncode: int
    stdout: str
    stderr: str


def run_recorder_status(stdin: str) -> RecorderRun:
    """`tailscale status --json | language-lab-record-fixtures status`, with `stdin` piped in."""
    proc = subprocess.run(
        [*RECORDER_COMMAND, "status"],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return RecorderRun(proc.returncode, proc.stdout, proc.stderr)


def run_recorder_anki(url: str) -> RecorderRun:
    """`language-lab-record-fixtures anki --url <url>`: AnkiConnect's version exchange on stdout."""
    proc = subprocess.run(
        [*RECORDER_COMMAND, "anki", "--url", url],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return RecorderRun(proc.returncode, proc.stdout, proc.stderr)


def run_recorder_anki_args(url: str, *args: str) -> RecorderRun:
    """`language-lab-record-fixtures anki --url <url> <args...>`, e.g. `probe --profile P`."""
    proc = subprocess.run(
        [*RECORDER_COMMAND, "anki", "--url", url, *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return RecorderRun(proc.returncode, proc.stdout, proc.stderr)


@dataclass(frozen=True)
class Recorder:
    url: str  # http://127.0.0.1:<port>
    port: int


@contextmanager
def run_recorder(out: Path) -> Iterator[Recorder]:
    """The recorder's `serve` on a free port, writing to `out`, until the block exits."""
    proc = subprocess.Popen(
        [*RECORDER_COMMAND, "serve", "--port", "0", "--out", str(out)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline()
        if LISTENING_MARKER not in line:
            raise RuntimeError(f"recorder did not start: {line}{proc.stdout.read()}")
        url = line.split(LISTENING_MARKER, 1)[1].split()[0].rstrip("/")
        yield Recorder(url=url, port=int(url.rsplit(":", 1)[1]))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

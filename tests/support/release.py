"""The release as CI makes it: the pyproject version, the tag guard, the wheel run through uvx."""

import os
import queue
import socket
import subprocess
import sys
import threading
import time
import tomllib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
# Decided 2026-10-12: release.yml runs this with the pushed tag before building anything.
RELEASE_TAG_SCRIPT = REPO_ROOT / "scripts" / "check_release_tag.py"

# uvx resolves the wheel's dependencies from the warm uv cache; a cold one downloads them.
RELEASE_START_TIMEOUT_S = 60.0
# uvicorn's own line once the socket is listening; printed after main()'s "running at" line.
SERVING_MARKER = "Uvicorn running on"

# TEST-NET-1 (RFC 5737): never routed, so a UDP connect to it only picks the outbound interface.
_UNROUTED_PROBE = ("192.0.2.1", 9)


def pyproject_version() -> str:
    with PYPROJECT.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def next_patch(version: str) -> str:
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


@dataclass(frozen=True)
class TagCheck:
    returncode: int
    output: str  # stdout and stderr together


def run_tag_check(tag: str) -> TagCheck:
    """Run the release guard the way release.yml does: from the repo root, tag as the argument."""
    proc = subprocess.run(
        [sys.executable, str(RELEASE_TAG_SCRIPT), tag],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    return TagCheck(returncode=proc.returncode, output=proc.stdout)


def build_wheel(out_dir: Path) -> Path:
    """`uv build --wheel` of this repo into `out_dir`, as the release job does; the one wheel."""
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir), "--quiet"],
        cwd=REPO_ROOT,
        check=True,
        timeout=120,
    )
    (wheel,) = out_dir.glob("language_lab-*.whl")
    return wheel


def uv_cache_dir() -> str:
    """The developer's (or runner's) uv cache, resolved before HOME is swapped for a temp one."""
    if cache := os.environ.get("UV_CACHE_DIR"):
        return cache
    return subprocess.run(
        ["uv", "cache", "dir"], check=True, capture_output=True, text=True
    ).stdout.strip()


def non_loopback_address() -> str | None:
    """This machine's address on its outbound interface, or None when it has only loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(_UNROUTED_PROBE)
        except OSError:
            return None
        address = sock.getsockname()[0]
    return None if address.startswith("127.") or address == "0.0.0.0" else address


@dataclass
class ReleasedApp:
    url: str
    lines: list[str]  # everything it printed up to now, stdout and stderr together

    @property
    def output(self) -> str:
        return "".join(self.lines)


@contextmanager
def run_released_app(
    wheel: Path, *, env: Mapping[str, str], cwd: Path, port: int
) -> Iterator[ReleasedApp]:
    """`uvx --from <wheel> language-lab`, the documented release command, until the block exits.

    `env` is the whole environment (HOME included). Waits for uvicorn's listening line, so the
    app is serving when the block starts; a startup that exits first raises with its output.
    """
    proc = subprocess.Popen(
        ["uvx", "--python", sys.executable, "--from", str(wheel), "language-lab"],
        env=dict(env),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines: queue.Queue[str | None] = queue.Queue()

    def pump() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()
    app = ReleasedApp(url=f"http://127.0.0.1:{port}", lines=[])
    deadline = time.monotonic() + RELEASE_START_TIMEOUT_S
    try:
        while True:
            try:
                line = lines.get(timeout=max(deadline - time.monotonic(), 0.0))
            except queue.Empty:
                raise RuntimeError(f"released app not serving yet:\n{app.output}") from None
            if line is None:
                raise RuntimeError(f"released app exited during startup:\n{app.output}")
            app.lines.append(line)
            if SERVING_MARKER in line:
                break
        yield app
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

"""Run the real app on a loopback port in a background thread."""

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import uvicorn

from language_lab.app import create_app
from language_lab.settings import Settings
from tests.fakes.anki_store import FakeAnkiStore
from tests.fakes.llm import FakeLlm

STARTUP_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class LiveServer:
    settings: Settings

    @property
    def url(self) -> str:
        return f"http://{self.settings.host}:{self.settings.port}"


def bind_free_port(host: str = "127.0.0.1") -> socket.socket:
    """Bind port 0 and keep the socket, so the port can't be taken before the server uses it."""
    sock = socket.socket()
    sock.bind((host, 0))
    return sock


def closed_port(host: str = "127.0.0.1") -> int:
    """A port nothing listens on, so a connection is refused at once.

    The socket is closed before returning: on macOS a bound but non-listening port drops the
    connection attempt, which then waits out its timeout instead of being refused.
    """
    with bind_free_port(host) as sock:
        return sock.getsockname()[1]


@contextmanager
def run_live_server(settings: Settings, sock: socket.socket) -> Iterator[LiveServer]:
    """Serve `create_app(settings)` on `sock` until the block exits.

    The AnkiStore is the in-memory fake (all checks reachable), and the Llm a `FakeLlm`, so no
    E2E test reaches the developer's real AnkiConnect or OpenRouter. A test that needs another
    state stubs the API in the browser.

    `settings.port` must equal the socket's port: the host allow-list (AD-16) is built
    from settings, so a mismatch rejects every request (R-14).
    """
    if sock.getsockname()[1] != settings.port:
        raise ValueError("settings.port must match the bound socket")
    config = uvicorn.Config(
        create_app(settings, anki_store=FakeAnkiStore(), llm=FakeLlm()),
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError("live server did not start")
        time.sleep(0.01)
    try:
        yield LiveServer(settings)
    finally:
        server.should_exit = True
        thread.join(timeout=STARTUP_TIMEOUT_S)
        sock.close()

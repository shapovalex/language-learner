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


@contextmanager
def run_live_server(settings: Settings, sock: socket.socket) -> Iterator[LiveServer]:
    """Serve `create_app(settings)` on `sock` until the block exits.

    `settings.port` must equal the socket's port: the host allow-list (AD-16) is built
    from settings, so a mismatch rejects every request (R-14).
    """
    if sock.getsockname()[1] != settings.port:
        raise ValueError("settings.port must match the bound socket")
    config = uvicorn.Config(create_app(settings), log_config=None, access_log=False)
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

"""`live_server`: the real app on a free loopback port, shared by the session."""

import socket
from collections.abc import Iterator

import pytest

from language_lab.settings import Settings
from tests.support.live_server import LiveServer, bind_free_port, run_live_server


@pytest.fixture(scope="session")
def live_server_socket() -> socket.socket:
    return bind_free_port()


@pytest.fixture(scope="session")
def live_server_settings(live_server_socket: socket.socket) -> Settings:
    """Settings for the live server. Override this fixture to change what the app runs with."""
    host, port = live_server_socket.getsockname()
    return Settings(host=host, port=port)


@pytest.fixture(scope="session")
def live_server(
    live_server_settings: Settings, live_server_socket: socket.socket
) -> Iterator[LiveServer]:
    with run_live_server(live_server_settings, live_server_socket) as server:
        yield server

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
    # Placeholder keys so Setup's readiness passes; this story makes no Azure or OpenRouter call
    return Settings(
        host=host,
        port=port,
        azure_speech_key="e2e-azure-key",
        azure_speech_region="e2e-region",
        openrouter_api_key="e2e-openrouter-key",
    )


@pytest.fixture(scope="session")
def live_server(
    live_server_settings: Settings, live_server_socket: socket.socket
) -> Iterator[LiveServer]:
    with run_live_server(live_server_settings, live_server_socket) as server:
        yield server

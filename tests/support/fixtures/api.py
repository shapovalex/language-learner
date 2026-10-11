"""`probe_client`: the real app plus the test-only probe routes, crashes returned as 500s."""

import pytest
from fastapi.testclient import TestClient

from language_lab.app import create_app
from tests.support.fixtures.settings import SettingsFactory
from tests.support.probes import add_probe_routes


@pytest.fixture
def probe_client(settings_factory: SettingsFactory) -> TestClient:
    app = add_probe_routes(create_app(settings_factory()))
    return TestClient(app, raise_server_exceptions=False)

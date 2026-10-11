"""Story 1.5: the served shell opts into iPhone safe areas, and its CSS uses them.

Skipped until the Studio base styles land. Un-skip, watch it fail, then implement.
"""

import pytest
from fastapi.testclient import TestClient

from language_lab.app import create_app
from tests.support.fixtures.settings import SettingsFactory
from tests.support.shell import fetch_stylesheets, parse_shell, viewport_directives

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.5: un-skip with the Studio base styles"
)

SHELL_PATH = "/captures"
# Without viewport-fit=cover, iOS Safari letterboxes the page and every env() inset is 0
VIEWPORT_FIT_COVER = "viewport-fit=cover"
SAFE_AREA_SIDES = ("top", "right", "bottom", "left")


@pytest.fixture
def client(settings_factory: SettingsFactory) -> TestClient:
    return TestClient(create_app(settings_factory()))


@RED_PHASE
@pytest.mark.p3
def test_shell_and_styles_respect_safe_areas(client: TestClient) -> None:
    """AC-4: base styles respect safe areas."""
    head = parse_shell(client.get(SHELL_PATH).text)

    assert VIEWPORT_FIT_COVER in viewport_directives(head)
    css = fetch_stylesheets(client, SHELL_PATH, head)
    assert [side for side in SAFE_AREA_SIDES if f"env(safe-area-inset-{side}" not in css] == []

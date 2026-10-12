import httpx
import pytest
from playwright.sync_api import Page, ViewportSize, expect

from language_lab import __version__
from tests.support import viewports
from tests.support.live_server import LiveServer
from tests.support.network import stub_api_error


@pytest.mark.smoke
def test_live_server_answers_on_its_settings_port(live_server: LiveServer) -> None:
    # R-14: the allow-list is built from settings, so the served port must be the configured one
    response = httpx.get(f"{live_server.url}/api/health")
    assert response.status_code == 200
    assert response.url.port == live_server.settings.port


class TestShell:
    @pytest.mark.p1
    @pytest.mark.parametrize("viewport", viewports.ALL.values(), ids=viewports.ALL.keys())
    def test_shows_server_version(self, page: Page, viewport: ViewportSize) -> None:
        page.set_viewport_size(viewport)
        # Network-first: arm the wait before the navigation that triggers the request
        with page.expect_response("**/api/health") as health:
            page.goto("/setup")
        assert health.value.ok
        expect(page.get_by_role("main").get_by_text(f"LanguageLab v{__version__}")).to_be_visible()

    @pytest.mark.p1
    def test_shows_message_when_api_fails(self, page: Page) -> None:
        stub_api_error(page, "/api/health", status=500, code="internal_error")
        page.goto("/setup")
        expect(
            page.get_by_role("main").get_by_text("LanguageLab could not reach the server.")
        ).to_be_visible()

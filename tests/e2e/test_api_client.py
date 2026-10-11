"""Story 1.3: api.js turns the AD-15 envelope into a typed error."""

import pytest
from playwright.sync_api import Page

from language_lab import __version__
from tests.support.network import stub_api_error

API_JS = f"/static/{__version__}/api.js"

# Calls the real api.js in the page and reports what it threw, as plain data
CALL_HEALTH = """async (url) => {
  const api = await import(url);
  try {
    await api.request("/api/health");
    return { isApiError: false };
  } catch (error) {
    return {
      isApiError: typeof api.ApiError === "function" && error instanceof api.ApiError,
      status: error.status,
      code: error.code,
      message: error.message,
      requestId: error.requestId,
    };
  }
}"""


@pytest.mark.p1
def test_request_throws_api_error_parsed_from_envelope(page: Page) -> None:
    """AC-7: api.js parses the envelope into a typed error."""
    envelope = stub_api_error(
        page, "/api/health", status=503, code="anki_unavailable", message="Anki isn't running"
    )
    page.goto("/")

    thrown = page.evaluate(CALL_HEALTH, API_JS)

    assert thrown["isApiError"] is True
    assert {key: thrown.get(key) for key in ("status", "code", "message", "requestId")} == {
        "status": 503,
        "code": envelope["error"]["code"],
        "message": envelope["error"]["message"],
        "requestId": envelope["error"]["requestId"],
    }


@pytest.mark.p1
def test_non_envelope_failure_becomes_internal_error(page: Page) -> None:
    """AC-7: a failure without the envelope (a proxy's HTML 502) is still an ApiError."""
    page.route(
        "**/api/health",
        lambda route: route.fulfill(
            status=502, content_type="text/html", body="<html>Bad Gateway</html>"
        ),
    )
    page.goto("/")

    thrown = page.evaluate(CALL_HEALTH, API_JS)

    assert thrown["isApiError"] is True
    assert (thrown["status"], thrown["code"], thrown["requestId"]) == (502, "internal_error", None)

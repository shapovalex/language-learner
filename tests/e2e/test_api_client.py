"""Story 1.3: api.js turns the AD-15 envelope into a typed error.

Skipped until `ApiError` lands in api.js. Un-skip, watch it fail, then implement.
"""

import pytest
from playwright.sync_api import Page

from language_lab import __version__
from tests.support.network import stub_api_error

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 1.3: un-skip with ApiError in api.js")

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


@RED_PHASE
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

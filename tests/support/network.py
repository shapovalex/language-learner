"""Browser network helpers. Register them before the navigation that triggers the request."""

import json
import uuid

from playwright.sync_api import Page, Request


def stub_api_error(
    page: Page, path: str, *, status: int, code: str, message: str = "Stubbed failure"
) -> None:
    """Answer `path` with an AD-15 error envelope instead of reaching the server."""
    body = {"error": {"code": code, "message": message, "requestId": str(uuid.uuid4())}}
    page.route(
        f"**{path}",
        lambda route: route.fulfill(
            status=status, content_type="application/json", body=json.dumps(body)
        ),
    )


def record_requests(page: Page) -> list[str]:
    """Return a list that fills with every request URL the page makes from now on."""
    urls: list[str] = []

    def on_request(request: Request) -> None:
        urls.append(request.url)

    page.on("request", on_request)
    return urls

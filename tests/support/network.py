"""Browser network helpers. Register them before the navigation that triggers the request."""

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Page, Request, Route


def stub_api_error(
    page: Page, path: str, *, status: int, code: str, message: str = "Stubbed failure"
) -> dict:
    """Answer `path` with an AD-15 error envelope instead of reaching the server.

    Returns the envelope, so a test can compare what the client parsed.
    """
    body = {"error": {"code": code, "message": message, "requestId": str(uuid.uuid4())}}
    page.route(
        f"**{path}",
        lambda route: route.fulfill(
            status=status, content_type="application/json", body=json.dumps(body)
        ),
    )
    return body


def stub_api_json(page: Page, path: str, body: Any, *, status: int = 200) -> None:
    """Answer every request to `path` with `body` as JSON instead of reaching the server."""
    page.route(
        f"**{path}",
        lambda route: route.fulfill(
            status=status, content_type="application/json", body=json.dumps(body)
        ),
    )


class HeldRoute:
    """Holds every request to `path` until the test answers it, so a loading state can be seen.

    Register it before the navigation that triggers the request, like `stub_api_error`.
    """

    def __init__(self, page: Page, path: str, timeout_s: float = 10.0) -> None:
        self._page = page
        self._path = path
        self._timeout_s = timeout_s
        self._routes: list[Route] = []
        page.route(f"**{path}", lambda route: self._routes.append(route))

    def fulfill_json(self, body: Any, *, status: int = 200) -> None:
        """Answer the oldest held request with `body` as JSON."""
        deadline = time.monotonic() + self._timeout_s
        while not self._routes:
            if time.monotonic() > deadline:
                raise TimeoutError(f"no request to {self._path} arrived")
            # A round trip lets Playwright deliver a pending route event; nothing sleeps
            self._page.evaluate("0")
        self._routes.pop(0).fulfill(
            status=status, content_type="application/json", body=json.dumps(body)
        )


@dataclass(frozen=True)
class Resource:
    resource_type: str  # Playwright's: "document", "stylesheet", "font", "fetch", …
    url: str


def record_resources(page: Page) -> list[Resource]:
    """Like `record_requests`, with each request's resource type."""
    resources: list[Resource] = []

    def on_request(request: Request) -> None:
        resources.append(Resource(request.resource_type, request.url))

    page.on("request", on_request)
    return resources


def record_requests(page: Page) -> list[str]:
    """Return a list that fills with every request URL the page makes from now on."""
    urls: list[str] = []

    def on_request(request: Request) -> None:
        urls.append(request.url)

    page.on("request", on_request)
    return urls


def record_json_bodies(page: Page, path: str) -> list[Any]:
    """Return a list that fills with the JSON body of every non-GET request to `path`."""
    bodies: list[Any] = []

    def on_request(request: Request) -> None:
        if request.method != "GET" and request.url.endswith(path):
            bodies.append(request.post_data_json)

    page.on("request", on_request)
    return bodies

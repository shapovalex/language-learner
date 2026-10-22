"""Browser network helpers. Register them before the navigation that triggers the request."""

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Page, Request, Route


def _fulfill_json(page: Page, path: str, body: Any, *, status: int, method: str | None) -> None:
    """Answer requests to `path` with `body` as JSON; with `method`, only that method's, and
    every other request falls back to an earlier handler, or the server.
    """

    def handle(route: Route) -> None:
        if method is not None and route.request.method != method:
            route.fallback()
            return
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

    page.route(f"**{path}", handle)


def stub_api_error(
    page: Page,
    path: str,
    *,
    status: int,
    code: str,
    message: str = "Stubbed failure",
    method: str | None = None,
) -> dict:
    """Answer `path` (only `method`'s requests, when given) with an AD-15 error envelope
    instead of reaching the server.

    Returns the envelope, so a test can compare what the client parsed.
    """
    body = {"error": {"code": code, "message": message, "requestId": str(uuid.uuid4())}}
    _fulfill_json(page, path, body, status=status, method=method)
    return body


def stub_api_json(
    page: Page, path: str, body: Any, *, status: int = 200, method: str | None = None
) -> None:
    """Answer every request to `path` (only `method`'s, when given) with `body` as JSON
    instead of reaching the server.
    """
    _fulfill_json(page, path, body, status=status, method=method)


class HeldRoute:
    """Holds every request to `path` (only `method`'s, when given: the others fall back to an
    earlier handler, or the server) until the test answers it, so a loading state can be seen.

    Register it before the navigation that triggers the request, like `stub_api_error`.
    """

    def __init__(
        self, page: Page, path: str, timeout_s: float = 10.0, *, method: str | None = None
    ) -> None:
        self._page = page
        self._path = path
        self._timeout_s = timeout_s
        self._method = method
        self._routes: list[Route] = []
        page.route(f"**{path}", self._hold)

    def _hold(self, route: Route) -> None:
        if self._method is not None and route.request.method != self._method:
            route.fallback()
            return
        self._routes.append(route)

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

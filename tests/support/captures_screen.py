"""The Captures screen's routes, copy and locators, shared by the Captures E2E tests
(tests/e2e/test_captures_*.py). The copy strings are the ones more than one Captures test
checks; `capture(text, created_at)` is a GET /api/captures entry under a fresh CaptureId.
"""

import uuid

from playwright.sync_api import Locator, Page, Response

CAPTURES_PATH = "/captures"
API = "/api/captures"

COMPOSE_LABEL = "New Capture"
SAVE = "Save Capture"
NO_SELECTION = "Choose a Capture to see it here."
NOT_IN_ANKI = "This Capture isn't in Anki."


def capture(text: str, created_at: str) -> dict[str, str]:
    return {"captureId": str(uuid.uuid4()), "text": text, "createdAt": created_at}


def main(page: Page) -> Locator:
    return page.get_by_role("main")


def compose_box(page: Page) -> Locator:
    return main(page).get_by_role("textbox", name=COMPOSE_LABEL, exact=True)


def captures_list(page: Page) -> Locator:
    return main(page).get_by_role("list", name="Captures", exact=True)


def rows(page: Page) -> Locator:
    return captures_list(page).get_by_role("link")


def detail(page: Page) -> Locator:
    return main(page).get_by_role("article")


def is_save(response: Response) -> bool:
    return response.request.method == "POST" and response.url.endswith(API)


def horizontal_overflow(page: Page) -> float:
    return page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )

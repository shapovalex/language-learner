"""Story 5.1 browser factories and accessible locators; all state is local to one page.

List metadata is deliberately separate from editable ItemContent. The network double records
Save requests and changes its Item snapshot only after a successful explicit Save. It tests
client behavior; adapter identity/history preservation is covered below the browser layer.
"""

import re
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.captures_screen import main
from tests.support.duplicates import on_wire, vocabulary
from tests.support.items_screen import is_item_save, item_api, item_detail_path, item_part
from tests.support.network import stub_api_json

SAVE_CHANGES = "Save changes"
AUDIO_INDICATOR = "Reference audio"


def stored_item(*, has_audio: bool = False, **changes: Any) -> dict[str, Any]:
    return {**on_wire(str(uuid.uuid4()), vocabulary(**changes)), "hasAudio": has_audio}


def detail_wire(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "hasAudio"}


def search_box(page: Page, language: str = "English") -> Locator:
    return main(page).get_by_role("textbox", name=f"Search {language} Items", exact=True)


def item_row(page: Page, target: str) -> Locator:
    return main(page).get_by_role("link").filter(has_text=target)


def edit_field(page: Page, label: str) -> Locator:
    name = re.compile(rf"^{re.escape(label)}(?! in Russian)\b")
    return main(page).get_by_role("textbox", name=name)


def save_changes(page: Page) -> Locator:
    return main(page).get_by_role("button", name=SAVE_CHANGES, exact=True)


def query_of(request: Request) -> str:
    return parse_qs(urlparse(request.url).query).get("q", [""])[0]


def stub_items(page: Page, items: list[dict[str, Any]], *, lang: str = "en") -> None:
    """List requests only; detail and duplicate reads cannot be swallowed by the pattern."""
    pattern = re.compile(rf"/api/items/{lang}(?:\?.*)?$")

    def reply(route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        route.fulfill(json={"items": items})

    page.route(pattern, reply)


def record_saves(page: Page) -> list[Request]:
    requests: list[Request] = []
    page.on("request", lambda request: requests.append(request) if is_item_save(request) else None)
    return requests


class EditableItemApi:
    """Per-test read/Save double. No shared live-server fake or real Anki is changed.

    `save_status=503` leaves `current` alone; changing it to 200 allows a retry. A successful
    write accepts exactly the browser's multipart payload (rather than manufacturing edits).
    """

    def __init__(self, page: Page, row: dict[str, Any], *, lang: str = "en") -> None:
        self.current = detail_wire(row)
        self.original = detail_wire(row)
        self.item_id = row["itemId"]
        self.lang = lang
        self.save_status = 200
        self.saved_payloads: list[dict[str, Any]] = []
        page.route(f"**{item_api(lang, self.item_id)}", self._read)
        page.route(f"**/api/items/{lang}", self._save)

    def _read(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        route.fulfill(json=self.current)

    def _save(self, route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        payload = item_part(route.request)
        self.saved_payloads.append(payload)
        if self.save_status != 200:
            route.fulfill(
                status=self.save_status,
                json={
                    "error": {
                        "code": "anki_unavailable",
                        "message": "Anki isn't reachable.",
                        "requestId": "atdd-edit-save",
                    }
                },
            )
            return
        self.current = {key: value for key, value in payload.items() if key != "audio"}
        route.fulfill(json={"itemId": self.item_id})

    def open(self, page: Page) -> None:
        page.goto(item_detail_path(self.lang, self.item_id))


def stub_item_detail(page: Page, row: dict[str, Any], *, lang: str = "en") -> None:
    stub_api_json(page, item_api(lang, row["itemId"]), detail_wire(row), method="GET")

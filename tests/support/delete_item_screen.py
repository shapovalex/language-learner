"""Story 5.3 delete confirmation locators and a page-local Item API double.

The double observes client behavior only. The adapter tests own actual note/Card/media
deletion. Reads and mutations are scoped to this page, so no live-server state is shared.
"""

import re
from typing import Any

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.captures_screen import main
from tests.support.items_screen import item_api, item_detail_path
from tests.support.maintain_items_screen import detail_wire

DELETE = "Delete"
CONFIRM = "Delete permanently"
CANCEL = "Cancel"
PERMANENT = (
    "This permanently removes the Item and its 4 Cards from Anki, with their review history:"
)
NO_UNDO = "There is no undo."
CARDS = ("Understand", "Produce", "Write", "Pronounce")
NOT_DELETED = "Not deleted — Anki isn't reachable"
NOT_DELETED_BODY = "Make sure Anki Desktop is open on the Mac mini, then try again."


def delete_button(page: Page) -> Locator:
    return main(page).get_by_role("button", name=DELETE, exact=True)


def delete_dialog(page: Page, target: str) -> Locator:
    return page.get_by_role("alertdialog", name=f"Delete “{target}”?", exact=True)


def confirm_button(page: Page, target: str) -> Locator:
    return delete_dialog(page, target).get_by_role("button", name=CONFIRM, exact=True)


def cancel_button(page: Page, target: str) -> Locator:
    return delete_dialog(page, target).get_by_role("button", name=CANCEL, exact=True)


class DeletableItemApi:
    """GET detail/list and DELETE, with controllable failures and observed mutation requests.

    A successful DELETE removes just its row. `delete_status=503` leaves every row intact.
    List reads are counted so the browser must request a refreshed list after deletion.
    """

    def __init__(
        self, page: Page, row: dict[str, Any], other: dict[str, Any], *, lang: str = "en"
    ) -> None:
        self.row = row
        self.other = other
        self.lang = lang
        self.path = item_api(lang, row["itemId"])
        self.rows = [row, other]
        self.delete_status = 204
        self.list_reads = 0
        self.mutations: list[Request] = []
        page.on("request", self._observe)
        page.route(re.compile(rf"/api/items/{lang}(?:\?.*)?$"), self._list)
        page.route(f"**{self.path}", self._detail)

    def _observe(self, request: Request) -> None:
        if request.method in ("DELETE", "POST", "PUT", "PATCH"):
            self.mutations.append(request)

    def _list(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        self.list_reads += 1
        route.fulfill(json={"items": self.rows})

    def _detail(self, route: Route) -> None:
        if route.request.method == "GET":
            route.fulfill(json=detail_wire(self.row))
        elif route.request.method == "DELETE":
            if self.delete_status == 204:
                self.rows = [self.other]
                route.fulfill(status=204, body="")
            else:
                route.fulfill(
                    status=self.delete_status,
                    json={
                        "error": {
                            "code": "anki_unavailable",
                            "message": "Anki isn't reachable.",
                            "requestId": "atdd-item-delete",
                        }
                    },
                )
        else:
            route.fallback()

    def open(self, page: Page) -> None:
        page.goto(item_detail_path(self.lang, self.row["itemId"]))

    @property
    def deletes(self) -> list[Request]:
        return [request for request in self.mutations if request.method == "DELETE"]

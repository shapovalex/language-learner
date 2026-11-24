"""Flagged Items: the Flagged filter on the Items screen and Clear flag on Item detail.

The Items screen's "Flagged" toggle (`aria-pressed`) sends `flagged=true` on the same list read
as the search, so only Items with a card flagged in Anki are listed, combined with the search.
Each flagged row shows a flag marker. The toggle is remembered per Language, so coming back from
an Item detail keeps it. With nothing flagged the screen says "No flagged <Language> Items.".

Item detail shows "Flagged in Anki" with a "Clear flag" button when the read says `flagged`.
Clear flag sends DELETE /api/items/<lang>/<itemId>/flag at once (not through Save); success
hides the notice, a failure keeps it with an inline alert whose Try again clears again.

API responses are per-page doubles; nothing is shared with the live server's fake store.
"""

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support import viewports
from tests.support.captures_screen import main
from tests.support.items_screen import item_api, item_detail_path, items_back_link
from tests.support.maintain_items_screen import (
    FLAG_MARKER,
    detail_wire,
    flagged_filter,
    item_row,
    search_box,
    stored_item,
)

FLAGGED_NOTICE = "Flagged in Anki"
CLEAR_FLAG = "Clear flag"


class FlaggedItemsApi:
    """List, detail and Clear flag double over `rows`: `flagged` holds the flagged ItemIds;
    `fail` answers the next clears 503 `anki_unavailable` and changes nothing. The list filters
    by `q` (a plain substring of the Target) and `flagged=true`.
    """

    def __init__(self, page: Page, rows: list[dict[str, Any]], flagged: set[str]) -> None:
        self.rows = rows
        self.flagged = set(flagged)
        self.fail = False
        self.clears: list[str] = []
        self.list_reads: list[dict[str, list[str]]] = []
        page.route(re.compile(r"/api/items/en(?:\?.*)?$"), self._list)
        for row in rows:
            page.route(f"**{item_api('en', row['itemId'])}", self._read)
            page.route(f"**{item_api('en', row['itemId'])}/flag", self._clear)

    def _list(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        params = parse_qs(urlparse(route.request.url).query)
        self.list_reads.append(params)
        query = params.get("q", [""])[0].strip().lower()
        only = params.get("flagged", ["false"])[0] == "true"
        items = [
            {**row, "flagged": row["itemId"] in self.flagged}
            for row in self.rows
            if query in row["target"].lower() and (not only or row["itemId"] in self.flagged)
        ]
        route.fulfill(json={"items": items})

    def _read(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        item_id = route.request.url.rsplit("/", 1)[-1]
        row = next(r for r in self.rows if r["itemId"] == item_id)
        route.fulfill(
            json={
                **detail_wire(row),
                "audio": None,
                "pronunciationExcluded": False,
                "flagged": item_id in self.flagged,
            }
        )

    def _clear(self, route: Route) -> None:
        if route.request.method != "DELETE":
            route.fallback()
            return
        item_id = route.request.url.rsplit("/", 2)[-2]
        self.clears.append(item_id)
        if self.fail:
            error = {
                "code": "anki_unavailable",
                "message": "Anki isn't reachable.",
                "requestId": "r",
            }
            route.fulfill(status=503, json={"error": error})
            return
        self.flagged.discard(item_id)
        route.fulfill(status=204, body="")


def flag_notice(page: Page):
    return main(page).get_by_role("region", name="Flag", exact=True)


def clear_flag(page: Page):
    return main(page).get_by_role("button", name=CLEAR_FLAG, exact=True)


class TestFlaggedFilter:
    @pytest.mark.p0
    @pytest.mark.parametrize("width", ["phone", "desktop"])
    def test_flagged_lists_only_the_flagged_items_with_a_marker(
        self, page: Page, width: str
    ) -> None:
        page.set_viewport_size(viewports.ALL[width])
        flagged = stored_item(target="jump to conclusions")
        plain = stored_item(target="on the fence")
        api = FlaggedItemsApi(page, [flagged, plain], {flagged["itemId"]})
        page.goto("/en/items")
        expect(item_row(page, plain["target"])).to_be_visible()
        expect(flagged_filter(page)).to_have_attribute("aria-pressed", "false")
        row = item_row(page, flagged["target"])
        expect(row.get_by_role("img", name=FLAG_MARKER, exact=True)).to_be_visible()
        expect(
            item_row(page, plain["target"]).get_by_role("img", name=FLAG_MARKER, exact=True)
        ).to_have_count(0)

        flagged_filter(page).click()

        expect(flagged_filter(page)).to_have_attribute("aria-pressed", "true")
        expect(item_row(page, plain["target"])).to_have_count(0)
        expect(row).to_be_visible()
        expect(row.get_by_role("img", name=FLAG_MARKER, exact=True)).to_be_visible()
        assert api.list_reads[-1].get("flagged") == ["true"]
        assert "flagged" not in api.list_reads[0]

        flagged_filter(page).click()

        expect(flagged_filter(page)).to_have_attribute("aria-pressed", "false")
        expect(item_row(page, plain["target"])).to_be_visible()

    @pytest.mark.p0
    def test_the_filter_combines_with_the_search(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        jump = stored_item(target="jump to conclusions")
        joy = stored_item(target="jump for joy")
        fence = stored_item(target="on the fence")
        api = FlaggedItemsApi(page, [jump, joy, fence], {jump["itemId"], fence["itemId"]})
        page.goto("/en/items")
        expect(item_row(page, joy["target"])).to_be_visible()

        flagged_filter(page).click()
        expect(item_row(page, joy["target"])).to_have_count(0)
        search_box(page).fill("jump")

        expect(item_row(page, fence["target"])).to_have_count(0)
        expect(item_row(page, jump["target"])).to_be_visible()
        expect(item_row(page, joy["target"])).to_have_count(0)
        assert api.list_reads[-1] == {"q": ["jump"], "flagged": ["true"]}

    @pytest.mark.p1
    def test_nothing_flagged_says_so_and_keeps_the_toggle(self, page: Page) -> None:
        page.set_viewport_size(viewports.PHONE)
        plain = stored_item(target="on the fence")
        FlaggedItemsApi(page, [plain], set())
        page.goto("/en/items")
        expect(item_row(page, plain["target"])).to_be_visible()

        flagged_filter(page).click()

        expect(main(page).get_by_text("No flagged English Items.", exact=True)).to_be_visible()
        expect(flagged_filter(page)).to_be_visible()
        expect(search_box(page)).to_be_visible()

    @pytest.mark.p0
    def test_the_filter_survives_a_round_trip_through_item_detail(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        flagged = stored_item(target="jump to conclusions")
        plain = stored_item(target="on the fence")
        api = FlaggedItemsApi(page, [flagged, plain], {flagged["itemId"]})
        page.goto("/en/items")
        flagged_filter(page).click()
        expect(item_row(page, plain["target"])).to_have_count(0)

        item_row(page, flagged["target"]).click()
        expect(flag_notice(page)).to_contain_text(FLAGGED_NOTICE)
        main(page).get_by_role("link", name=items_back_link("English"), exact=True).click()

        expect(flagged_filter(page)).to_have_attribute("aria-pressed", "true")
        expect(item_row(page, flagged["target"])).to_be_visible()
        expect(item_row(page, plain["target"])).to_have_count(0)
        assert api.list_reads[-1].get("flagged") == ["true"]


class TestClearFlag:
    @pytest.mark.p0
    def test_clear_flag_hides_the_notice_and_the_item_leaves_the_flagged_list(
        self, page: Page
    ) -> None:
        page.set_viewport_size(viewports.PHONE)
        flagged = stored_item(target="jump to conclusions")
        other = stored_item(target="on the fence")
        api = FlaggedItemsApi(page, [flagged, other], {flagged["itemId"], other["itemId"]})
        page.goto("/en/items")
        flagged_filter(page).click()
        expect(item_row(page, flagged["target"])).to_be_visible()
        item_row(page, flagged["target"]).click()
        expect(flag_notice(page)).to_contain_text(FLAGGED_NOTICE)

        clear_flag(page).click()

        expect(flag_notice(page)).to_have_count(0)
        assert api.clears == [flagged["itemId"]]
        # Written at once: no unsaved change
        expect(main(page).get_by_text("unsaved change")).to_have_count(0)
        main(page).get_by_role("link", name=items_back_link("English"), exact=True).click()
        expect(item_row(page, other["target"])).to_be_visible()
        expect(item_row(page, flagged["target"])).to_have_count(0)

    @pytest.mark.p1
    def test_an_unflagged_item_shows_no_notice(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        plain = stored_item(target="on the fence")
        FlaggedItemsApi(page, [plain], set())
        page.goto(item_detail_path("en", plain["itemId"]))
        expect(main(page).get_by_role("checkbox", name="Practise pronunciation")).to_be_visible()

        expect(flag_notice(page)).to_have_count(0)
        expect(clear_flag(page)).to_have_count(0)

    @pytest.mark.p0
    def test_a_failed_clear_keeps_the_notice_with_an_alert_and_try_again(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        flagged = stored_item(target="jump to conclusions")
        api = FlaggedItemsApi(page, [flagged], {flagged["itemId"]})
        api.fail = True
        page.goto(item_detail_path("en", flagged["itemId"]))

        clear_flag(page).click()

        alert = flag_notice(page).get_by_role("alert")
        expect(alert).to_contain_text("Flag not cleared")
        expect(alert).to_contain_text("Anki isn't reachable")
        expect(clear_flag(page)).to_be_enabled()
        api.fail = False
        alert.get_by_role("button", name="Try again", exact=True).click()
        expect(flag_notice(page)).to_have_count(0)
        assert api.clears == [flagged["itemId"]] * 2

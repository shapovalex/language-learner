"""Excluding an Item from Pronunciation, on the Pronunciation screen and on Item detail.

On the Pronunciation screen, "Don't practise this card" sends PUT
/api/items/<lang>/<itemId>/pronunciation `{excluded: true}` at once, with no confirmation and no
Attempt needed, then the next Card shows. A failed exclude keeps the Card with an inline alert
whose Try again sends it again.

On Item detail, "Practise pronunciation" is checked unless the read says
`pronunciationExcluded`. A toggle writes at once (not through Save, and no unsaved change); a
failure puts the checkbox back with an inline alert.

API responses are per-page doubles; nothing is shared with the live server's fake store.
"""

import json
from typing import Any

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support import viewports
from tests.support.attempt_screen import assessment, install_microphone
from tests.support.captures_screen import main
from tests.support.items_screen import item_api, item_detail_path
from tests.support.maintain_items_screen import detail_wire, save_changes, stored_item
from tests.support.pronunciation_screen import (
    EXCLUDE_FAILED,
    RATINGS,
    ReviewApi,
    exclude_alert,
    exclude_button,
    queue_chip,
    rating_button,
    review_card,
    target_text,
)

PRACTISE = "Practise pronunciation"


@pytest.fixture(autouse=True)
def attempt_boundary(page: Page) -> None:
    install_microphone(page)
    page.route(
        "**/api/pronunciation/*/attempt",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"assessment": assessment(), "nothingHeard": False}),
        ),
    )


class TestExcludeFromReview:
    @pytest.mark.p0
    @pytest.mark.parametrize("width", ["phone", "tablet"])
    def test_exclude_advances_to_the_next_card_and_it_stays_out_on_reload(
        self, page: Page, width: str
    ) -> None:
        page.set_viewport_size(viewports.ALL[width])
        first = review_card("squirrel", reps=3)
        second = review_card("anemone")
        api = ReviewApi(page, lang="en", due=[first, second])
        page.goto("/en/pronunciation")
        expect(target_text(page, "squirrel")).to_be_visible()
        for name in RATINGS:
            expect(rating_button(page, name)).to_be_disabled()

        # No Attempt is needed, and nothing asks to confirm
        exclude_button(page).click()

        expect(target_text(page, "anemone")).to_be_visible()
        expect(queue_chip(page, 1, 0)).to_be_visible()
        assert api.exclusions == [(first["itemId"], {"excluded": True})]
        assert api.ratings == []
        page.reload()
        expect(target_text(page, "anemone")).to_be_visible()
        expect(target_text(page, "squirrel")).to_have_count(0)

    @pytest.mark.p0
    def test_a_failed_exclude_keeps_the_card_and_try_again_sends_it_again(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        first = review_card("rural")
        second = review_card("anemone")
        api = ReviewApi(page, lang="en", due=[first, second])
        api.exclude_error = True
        page.goto("/en/pronunciation")

        exclude_button(page).click()

        expect(exclude_alert(page)).to_contain_text(EXCLUDE_FAILED)
        expect(target_text(page, "rural")).to_be_visible()
        expect(exclude_button(page)).to_be_enabled()
        api.exclude_error = False
        exclude_alert(page).get_by_role("button", name="Try again", exact=True).click()
        expect(target_text(page, "anemone")).to_be_visible()
        assert api.exclusions == [(first["itemId"], {"excluded": True})] * 2

    @pytest.mark.p1
    def test_excluding_the_last_card_shows_the_empty_state(self, page: Page) -> None:
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="fr", new=[review_card("merci", audio=False)])
        page.goto("/fr/pronunciation")
        expect(target_text(page, "merci")).to_be_visible()

        exclude_button(page).click()

        expect(main(page).get_by_text("Nothing to practice in French")).to_be_visible()
        api.wait_for("end")


class FlagApi:
    """Item detail read and Pronunciation flag double: `excluded` is what Anki holds;
    `fail` answers the next writes 503 `anki_unavailable` and changes nothing.
    """

    def __init__(self, page: Page, row: dict[str, Any], *, excluded: bool) -> None:
        self.row = detail_wire(row)
        self.item_id = row["itemId"]
        self.excluded = excluded
        self.fail = False
        self.writes: list[dict[str, Any]] = []
        page.route(f"**{item_api('en', self.item_id)}", self._read)
        page.route(f"**{item_api('en', self.item_id)}/pronunciation", self._write)

    def _read(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        route.fulfill(json={**self.row, "audio": None, "pronunciationExcluded": self.excluded})

    def _write(self, route: Route) -> None:
        body = route.request.post_data_json
        self.writes.append(body)
        if self.fail:
            error = {
                "code": "anki_unavailable",
                "message": "Anki isn't reachable.",
                "requestId": "r",
            }
            route.fulfill(status=503, json={"error": error})
            return
        self.excluded = body["excluded"]
        route.fulfill(status=204, body="")


def practise(page: Page):
    return main(page).get_by_role("checkbox", name=PRACTISE)


class TestPractiseOnItemDetail:
    @pytest.mark.p0
    def test_the_checkbox_shows_the_flag_toggles_at_once_and_survives_a_reload(
        self, page: Page
    ) -> None:
        page.set_viewport_size(viewports.PHONE)
        row = stored_item()
        api = FlagApi(page, row, excluded=True)
        page.goto(item_detail_path("en", row["itemId"]))

        expect(practise(page)).not_to_be_checked()
        practise(page).check()

        expect(practise(page)).to_be_checked()
        expect(practise(page)).to_be_enabled()
        assert api.writes == [{"excluded": False}]
        # Written at once: no unsaved change, and Save changes is not involved
        expect(main(page).get_by_text("unsaved change")).to_have_count(0)
        page.reload()
        expect(practise(page)).to_be_checked()
        practise(page).uncheck()
        expect(practise(page)).to_be_enabled()
        expect(practise(page)).not_to_be_checked()
        assert api.writes == [{"excluded": False}, {"excluded": True}]
        page.reload()
        expect(practise(page)).not_to_be_checked()

    @pytest.mark.p0
    def test_a_failed_write_puts_the_checkbox_back_with_an_alert(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        row = stored_item()
        api = FlagApi(page, row, excluded=False)
        api.fail = True
        page.goto(item_detail_path("en", row["itemId"]))
        expect(practise(page)).to_be_checked()

        # A click, not uncheck(): the box goes back, which uncheck() would retry
        practise(page).click()

        alert = main(page).get_by_role("alert").filter(has_text="Not changed")
        expect(alert).to_contain_text("Anki isn't reachable")
        expect(practise(page)).to_be_checked()
        expect(save_changes(page)).to_be_visible()
        api.fail = False
        alert.get_by_role("button", name="Try again", exact=True).click()
        expect(practise(page)).not_to_be_checked()
        expect(alert).to_have_count(0)
        assert api.writes == [{"excluded": True}, {"excluded": True}]

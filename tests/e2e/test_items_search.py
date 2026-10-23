"""Story 5.1: the Items list and live search (S-Items; FR-22).

One primary leaf per AC, then secondary cases. UI contracts come from EXPERIENCE.md; list wire
defaults are in the ATDD checklist. Search normalization is asserted at the API level, not
reimplemented here.
"""

import re
from datetime import UTC, datetime, timedelta

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.captures_screen import horizontal_overflow, main
from tests.support.items_screen import item_detail_path
from tests.support.maintain_items_screen import (
    AUDIO_INDICATOR,
    item_row,
    query_of,
    search_box,
    stored_item,
    stub_item_detail,
    stub_items,
)
from tests.support.navigation import path_pattern, screen_heading
from tests.support.network import HeldRoute, stub_api_error


@pytest.mark.p0
def test_item_rows_open_detail_on_phone_and_desktop(page: Page) -> None:
    """[P0] AC-7 whole-row links show meaning, Category and conditional Reference audio."""
    voiced = stored_item(has_audio=True)
    silent = stored_item(target="on the fence", russian="колебаться")
    stub_items(page, [voiced, silent])
    stub_item_detail(page, voiced)

    for viewport in (viewports.PHONE, viewports.DESKTOP):
        page.set_viewport_size(viewport)
        page.goto("/en/items")
        row = item_row(page, voiced["target"])

        expect(row).to_be_visible()

        expect(row).to_contain_text(voiced["russian"])
        expect(row).to_contain_text("Vocabulary")
        expect(row.get_by_role("img", name=AUDIO_INDICATOR, exact=True)).to_be_visible()
        expect(
            item_row(page, silent["target"]).get_by_role("img", name=AUDIO_INDICATOR, exact=True)
        ).to_have_count(0)
        expect(row).to_have_attribute("href", item_detail_path("en", voiced["itemId"]))
        assert horizontal_overflow(page) <= 0
        row.click()
        expect(page).to_have_url(path_pattern(item_detail_path("en", voiced["itemId"])))
        expect(screen_heading(page)).to_have_text(voiced["target"])


@pytest.mark.p1
def test_live_search_debounces_and_ignores_a_late_old_response(page: Page) -> None:
    """[P1] AC-8 only the latest Language-scoped query can replace the result list.

    Virtual time advances timers without sleeping; 1000 ms is an upper debounce budget, not
    a required implementation delay. The older response is deliberately delivered last.
    """
    initial = stored_item(target="initial collection")
    old = stored_item(target="jump to conclusions")
    newest = stored_item(target="jump for joy")
    stub_items(page, [initial])
    older = HeldRoute(page, "/api/items/en?q=ju", method="GET")
    later = HeldRoute(page, "/api/items/en?q=jump", method="GET")
    queries: list[str] = []
    page.on(
        "request",
        lambda request: (
            queries.append(query_of(request))
            if re.search(r"/api/items/en(?:\?|$)", request.url) and request.method == "GET"
            else None
        ),
    )
    now = datetime(2026, 10, 23, tzinfo=UTC)
    page.clock.install(time=now)
    page.clock.pause_at(now + timedelta(seconds=1))
    page.goto("/en/items")
    search_box(page).wait_for()
    queries.clear()

    search_box(page).fill("j")
    search_box(page).fill("ju")

    assert queries == []

    with page.expect_request(lambda request: query_of(request) == "ju"):
        page.clock.run_for(1000)
    search_box(page).fill("jump")
    with page.expect_request(lambda request: query_of(request) == "jump"):
        page.clock.run_for(1000)
    later.fulfill_json({"items": [newest]})
    expect(item_row(page, newest["target"])).to_be_visible()
    older.fulfill_json({"items": [old]})
    page.clock.run_for(1000)
    expect(item_row(page, newest["target"])).to_be_visible()
    expect(item_row(page, old["target"])).to_have_count(0)
    assert queries == ["ju", "jump"]


@pytest.mark.p1
def test_pending_list_shows_loading_then_results(page: Page) -> None:
    """[P1] AC-9 pending Items read shows a loading skeleton, replaced by results."""
    row = stored_item()
    held = HeldRoute(page, "/api/items/en*", method="GET")
    page.goto("/en/items")
    loading = main(page).get_by_role("status").filter(has_text="Loading English Items…")

    expect(loading).to_be_visible()

    held.fulfill_json({"items": [row]})
    expect(item_row(page, row["target"])).to_be_visible()
    expect(loading).to_have_count(0)


@pytest.mark.p1
def test_search_no_matches_is_distinct_from_an_empty_collection(page: Page) -> None:
    """[P1] AC-10 populated-to-no-matches transition retains search; empty hides it."""
    row = stored_item()
    stub_items(page, [row])
    held = HeldRoute(page, "/api/items/en?q=absent", method="GET")
    page.goto("/en/items")
    search_box(page).fill("absent")
    held.fulfill_json({"items": []})

    expect(main(page).get_by_text("No English Items match “absent”.", exact=True)).to_be_visible()

    expect(search_box(page)).to_have_value("absent")
    stub_items(page, [])
    # The parent navigation causes a new mount, so the empty state comes from a new read.
    page.goto("/en/items")
    expect(main(page).get_by_text("No English Items yet", exact=True)).to_be_visible()
    expect(main(page)).to_contain_text("Items are made from Captures.")
    expect(search_box(page)).to_be_hidden()


@pytest.mark.p1
def test_failed_list_retry_replaces_the_error_with_items(page: Page) -> None:
    """[P1] AC-11 Try again re-reads and replaces an inline list error with results."""
    row = stored_item()
    stub_api_error(
        page,
        "/api/items/en*",
        status=503,
        code="anki_unavailable",
        message="Anki isn't reachable.",
        method="GET",
    )
    page.goto("/en/items")
    alert = main(page).get_by_role("alert")
    alert.wait_for()
    stub_items(page, [row])
    alert.get_by_role("button", name="Try again", exact=True).click()

    expect(item_row(page, row["target"])).to_be_visible()

    expect(alert).to_have_count(0)


@pytest.mark.p1
def test_french_items_use_french_labels_and_paths(page: Page) -> None:
    """[P1] AC-7 the French list is named for French and its rows open French Item detail."""
    row = stored_item(target="tirer des conclusions", russian="делать выводы")
    stub_items(page, [row], lang="fr")
    page.goto("/fr/items")

    expect(screen_heading(page)).to_have_text("French Items")
    expect(search_box(page, "French")).to_have_attribute("placeholder", "Search English or Russian")
    expect(item_row(page, row["target"])).to_have_attribute(
        "href", item_detail_path("fr", row["itemId"])
    )
    stub_items(page, [], lang="fr")
    page.goto("/fr/items")
    expect(main(page).get_by_text("No French Items yet", exact=True)).to_be_visible()


@pytest.mark.p1
def test_a_row_opens_from_the_keyboard(page: Page) -> None:
    """[P1] AC-7 a row is a link: focusing it and pressing Enter opens the Item."""
    row = stored_item()
    stub_items(page, [row])
    stub_item_detail(page, row)
    page.goto("/en/items")
    item_row(page, row["target"]).focus()

    page.keyboard.press("Enter")

    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    expect(screen_heading(page)).to_have_text(row["target"])

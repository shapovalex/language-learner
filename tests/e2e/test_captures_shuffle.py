"""Plan shuffle-captures: "Shuffle" in the Captures list header puts the list in a random order in
the browser only (nothing is sent to the server or Anki). The header then reads "Shuffled" on the
phone and "N Captures · shuffled" on desktop, and "Sort newest first" puts the list back in date
order. The order is kept while the screen stays mounted: opening a Capture keeps it.

`Math.random` is pinned to 0 so the shuffle is known: Fisher–Yates over [A, B, C, D] then gives
[B, C, D, A]. The list and detail are stubbed at the network (GET only).
"""

import uuid

import pytest
from playwright.sync_api import Page, Request, expect

from tests.support import viewports
from tests.support.captures_screen import (
    API,
    CAPTURES_PATH,
    SAVE,
    capture,
    compose_box,
    detail,
    is_save,
    main,
    rows,
)
from tests.support.network import stub_api_json

SHUFFLE = "Shuffle"
NEWEST_FIRST = "Newest first"
SHUFFLED = "Shuffled"
SORT_NEWEST = "Sort newest first"

A = capture("I'd rather not jump to conclusions.", "2026-10-23T01:14:00Z")
B = capture("Il fait un temps de chien.", "2026-10-22T12:02:00Z")
C = capture("notwithstanding", "2026-10-21T23:40:00Z")
D = capture("un rendez-vous", "2026-10-05T16:31:00Z")
NEWEST = [A, B, C, D]
SHUFFLED_ORDER = [B, C, D, A]


def texts(captures: list[dict[str, str]]) -> list[str]:
    return [c["text"] for c in captures]


def open_list(page: Page) -> None:
    page.add_init_script("Math.random = () => 0;")
    stub_api_json(page, API, {"captures": NEWEST}, method="GET")
    page.goto(CAPTURES_PATH)
    expect(rows(page)).to_contain_text(texts(NEWEST))


@pytest.mark.p1
def test_shuffle_reorders_the_list_in_the_browser_and_newest_first_restores_it(
    page: Page,
) -> None:
    page.set_viewport_size(viewports.PHONE)
    sent: list[Request] = []
    page.on("request", lambda r: sent.append(r) if "/api/" in r.url else None)
    open_list(page)
    newest_button = main(page).get_by_role("button", name=SORT_NEWEST, exact=True)
    expect(newest_button).to_be_hidden()
    sent.clear()

    main(page).get_by_role("button", name=SHUFFLE, exact=True).click()

    expect(rows(page)).to_contain_text(texts(SHUFFLED_ORDER))
    expect(main(page).get_by_text(SHUFFLED, exact=True)).to_be_visible()
    newest_button.click()
    expect(rows(page)).to_contain_text(texts(NEWEST))
    expect(main(page).get_by_text(NEWEST_FIRST, exact=True)).to_be_visible()
    expect(newest_button).to_be_hidden()
    assert sent == []


@pytest.mark.p1
def test_the_shuffled_order_is_kept_when_a_capture_opens(page: Page) -> None:
    page.set_viewport_size(viewports.DESKTOP)
    stub_api_json(page, f"{API}/{C['captureId']}", C, method="GET")
    open_list(page)

    main(page).get_by_role("button", name=SHUFFLE, exact=True).click()
    rows(page).nth(1).click()

    expect(detail(page)).to_contain_text(C["text"])
    expect(rows(page)).to_contain_text(texts(SHUFFLED_ORDER))
    expect(rows(page).nth(1)).to_have_attribute("aria-current", "page")
    expect(main(page).get_by_text("4 Captures · shuffled", exact=True)).to_be_visible()


@pytest.mark.p1
def test_a_capture_saved_while_shuffled_tops_the_list_and_the_rest_keep_their_order(
    page: Page,
) -> None:
    """X is saved before Shuffle and Y after: Y goes on top, X keeps its shuffled place
    ([X, A, B, C, D] shuffles to [A, B, C, D, X] with `Math.random` at 0).
    """
    page.set_viewport_size(viewports.DESKTOP)
    open_list(page)
    save = main(page).get_by_role("button", name=SAVE, exact=True)
    x, y = f"first {uuid.uuid4()}", f"second {uuid.uuid4()}"
    compose_box(page).fill(x)
    with page.expect_response(is_save):
        save.click()
    expect(rows(page).first).to_contain_text(x)

    main(page).get_by_role("button", name=SHUFFLE, exact=True).click()
    expect(rows(page)).to_contain_text([*texts(NEWEST), x])
    compose_box(page).fill(y)
    with page.expect_response(is_save):
        save.click()

    expect(rows(page)).to_contain_text([y, *texts(NEWEST), x])
    expect(main(page).get_by_text("6 Captures · shuffled", exact=True)).to_be_visible()


@pytest.mark.p1
def test_one_capture_has_no_shuffle(page: Page) -> None:
    page.set_viewport_size(viewports.PHONE)
    stub_api_json(page, API, {"captures": [A]}, method="GET")
    page.goto(CAPTURES_PATH)

    expect(rows(page)).to_have_count(1)
    expect(main(page).get_by_role("button", name=SHUFFLE, exact=True)).to_be_hidden()

"""Story 3.2: the Captures list and Capture detail (S-Captures, S-CapturesDesk, EXPERIENCE.md).

- **Layouts (decided with the user, 2026-10-22).** Below 1024px (phone, iPad portrait) the
  list sits under the compose box with "Newest first", and a Capture opens at
  /captures/<captureId> as its own screen with the "‹ Captures" back link. From 1024px (iPad
  landscape, desktop) list and detail are two panes: the left pane has the compose box,
  "N Captures · newest first" and the list with the open Capture selected
  (`aria-current="page"`); the right pane has the Capture detail, an `<article>`.
- **Rows.** The list is named "Captures", and each whole row is a link with the text and the
  creation time in the browser's time zone, 24-hour: "Today · 21:14", "Yesterday · 19:40",
  "Oct 5 · 12:31", and "Oct 4, 2025 · 22:05" outside the current year (decided with the user,
  2026-10-22). The detail reads "Captured today · 21:14".
- **States.** A skeleton, a status "Loading Captures…", while the list loads; "No Captures
  yet." under the box when there are none; a newly saved Capture at the top. On desktop with no
  Capture open the right pane reads "Choose a Capture to see it here." A CaptureId that isn't
  in Anki shows "This Capture isn't in Anki." with the back link (both decided with the user,
  2026-10-22).

The list and detail are stubbed at the network (GET only) so their contents are fixed: the live
server's fake is shared by the session. A new Capture at the top runs against the live server.
The Make an Item pane is epic-capture-to-item's, and Delete Capture is entry 3's.
"""

import re
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import Locator, Page, Response, expect

from tests.support import viewports
from tests.support.navigation import path_pattern
from tests.support.network import HeldRoute, stub_api_error, stub_api_json

CAPTURES_PATH = "/captures"
API = "/api/captures"
COMPOSE_LABEL = "New Capture"
SAVE = "Save Capture"

NEWEST_FIRST = "Newest first"
LOADING = "Loading Captures…"
EMPTY = "No Captures yet."
NO_SELECTION = "Choose a Capture to see it here."
NOT_IN_ANKI = "This Capture isn't in Anki."
BACK = re.compile(r"^(‹\s*)?Captures$")

TORONTO = "America/Toronto"
NOW = datetime(2026, 10, 22, 21, 30, tzinfo=ZoneInfo(TORONTO))


def capture(text: str, created_at: str) -> dict[str, str]:
    return {"captureId": str(uuid.uuid4()), "text": text, "createdAt": created_at}


# Newest first, as GET /api/captures answers. In Toronto time (UTC-4 in October 2025 and 2026):
# today 21:14 (already the 23rd in UTC), today 08:02, yesterday 19:40, Oct 5, and last year.
TODAY_LATE = capture("I'd rather not jump to conclusions.", "2026-10-23T01:14:00Z")
TODAY_EARLY = capture("Il fait un temps de chien.", "2026-10-22T12:02:00Z")
YESTERDAY = capture("notwithstanding", "2026-10-21T23:40:00Z")
OCT_5 = capture("un rendez-vous", "2026-10-05T16:31:00Z")
LAST_YEAR = capture("to be on the fence", "2025-10-05T02:05:00Z")
THREE = [TODAY_LATE, TODAY_EARLY, YESTERDAY]


def stub_list(page: Page, captures: list[dict[str, str]]) -> None:
    stub_api_json(page, API, {"captures": captures}, method="GET")


def stub_detail(page: Page, body: dict[str, str]) -> None:
    stub_api_json(page, f"{API}/{body['captureId']}", body, method="GET")


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


def back_link(page: Page) -> Locator:
    return main(page).get_by_role("link", name=BACK)


def is_save(response: Response) -> bool:
    return response.request.method == "POST" and response.url.endswith(API)


def bottom_of(locator: Locator) -> float:
    box = locator.bounding_box()
    assert box is not None
    return box["y"] + box["height"]


def top_of(locator: Locator) -> float:
    box = locator.bounding_box()
    assert box is not None
    return box["y"]


@pytest.mark.p0
def test_on_the_phone_the_list_is_under_the_compose_box_newest_first(page: Page) -> None:
    """AC-8: on the phone the list sits under the compose box, headed "Newest first", one row
    per Capture with its text, in the order the API gives (newest first).
    """
    page.set_viewport_size(viewports.PHONE)
    stub_list(page, THREE)
    page.goto(CAPTURES_PATH)

    expect(rows(page)).to_contain_text([c["text"] for c in THREE])

    expect(rows(page)).to_have_count(len(THREE))
    expect(main(page).get_by_text(NEWEST_FIRST, exact=True)).to_be_visible()
    assert top_of(captures_list(page)) >= bottom_of(compose_box(page))


@pytest.mark.p0
def test_on_the_phone_a_capture_opens_as_its_own_screen_with_a_back_link(page: Page) -> None:
    """AC-9: on the phone, opening a row lands on /captures/<captureId>, the Capture detail as
    its own screen (no compose box or list), with "‹ Captures" leading back.
    """
    page.set_viewport_size(viewports.PHONE)
    stub_list(page, THREE)
    stub_detail(page, TODAY_EARLY)
    page.goto(CAPTURES_PATH)

    rows(page).nth(1).click()

    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{TODAY_EARLY['captureId']}"))
    expect(detail(page)).to_contain_text(TODAY_EARLY["text"])
    expect(compose_box(page)).to_be_hidden()
    expect(captures_list(page)).to_be_hidden()
    back_link(page).click()
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(rows(page)).to_have_count(len(THREE))


@pytest.mark.p0
def test_on_desktop_list_and_detail_are_two_panes_with_the_open_capture_selected(
    page: Page,
) -> None:
    """AC-10: on desktop, /captures/<captureId> shows that Capture's detail in the right pane
    while the left pane keeps the compose box, "N Captures · newest first" and the list, with
    that row selected.
    """
    page.set_viewport_size(viewports.DESKTOP)
    stub_list(page, THREE)
    stub_detail(page, TODAY_EARLY)
    page.goto(f"{CAPTURES_PATH}/{TODAY_EARLY['captureId']}")

    expect(rows(page).nth(1)).to_have_attribute("aria-current", "page")

    expect(detail(page)).to_contain_text(TODAY_EARLY["text"])
    expect(main(page).get_by_text("3 Captures · newest first", exact=True)).to_be_visible()
    expect(compose_box(page)).to_be_visible()
    for other in (0, 2):
        expect(rows(page).nth(other)).not_to_have_attribute("aria-current", "page")


@pytest.mark.p0
@pytest.mark.browser_context_args(timezone_id=TORONTO, locale="en-US")
def test_creation_times_read_relative_to_today_in_the_browsers_time_zone(page: Page) -> None:
    """AC-11: each row shows its creation time in the browser's time zone, 24-hour: "Today",
    "Yesterday", the date this year, the date with its year otherwise; the detail reads
    "Captured today · 21:14".
    """
    page.clock.set_fixed_time(NOW)
    page.set_viewport_size(viewports.DESKTOP)
    stub_list(page, [TODAY_LATE, TODAY_EARLY, YESTERDAY, OCT_5, LAST_YEAR])
    stub_detail(page, TODAY_LATE)
    page.goto(f"{CAPTURES_PATH}/{TODAY_LATE['captureId']}")

    expect(rows(page)).to_contain_text(
        [
            "Today · 21:14",
            "Today · 08:02",
            "Yesterday · 19:40",
            "Oct 5 · 12:31",
            "Oct 4, 2025 · 22:05",
        ]
    )

    expect(detail(page)).to_contain_text("Captured today · 21:14")


@pytest.mark.p0
def test_the_list_shows_a_skeleton_while_it_loads(page: Page) -> None:
    """AC-12: while GET /api/captures is pending the list shows a skeleton, a status reading
    "Loading Captures…", and the rows replace it once the list arrives.
    """
    held = HeldRoute(page, API, method="GET")
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    skeleton = main(page).get_by_role("status").filter(has_text=LOADING)

    expect(skeleton).to_be_visible()

    held.fulfill_json({"captures": [TODAY_LATE]})
    expect(skeleton).to_have_count(0)
    expect(rows(page)).to_have_count(1)


@pytest.mark.p0
def test_with_no_captures_the_empty_state_is_under_the_compose_box(page: Page) -> None:
    """AC-13: with no Captures, "No Captures yet." shows under the compose box, with no rows."""
    page.set_viewport_size(viewports.PHONE)
    stub_list(page, [])
    page.goto(CAPTURES_PATH)
    empty = main(page).get_by_text(EMPTY, exact=True)

    expect(empty).to_be_visible()

    assert top_of(empty) >= bottom_of(compose_box(page))
    expect(main(page).get_by_role("list", name="Captures").get_by_role("link")).to_have_count(0)


@pytest.mark.p0
def test_a_newly_saved_capture_tops_the_list(page: Page) -> None:
    """AC-14: after Save Capture succeeds, the new Capture is the list's first row (J1)."""
    text = f"un rendez-vous {uuid.uuid4()}"
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill(text)

    with page.expect_response(is_save):
        main(page).get_by_role("button", name=SAVE, exact=True).click()

    expect(rows(page).first).to_contain_text(text)


@pytest.mark.p0
def test_on_desktop_with_no_capture_open_the_right_pane_shows_a_hint(page: Page) -> None:
    """AC-15: on desktop at /captures, with no Capture open, the right pane reads "Choose a
    Capture to see it here." and no row is selected.
    """
    page.set_viewport_size(viewports.DESKTOP)
    stub_list(page, THREE)
    page.goto(CAPTURES_PATH)

    expect(main(page).get_by_text(NO_SELECTION, exact=True)).to_be_visible()

    expect(rows(page)).to_have_count(len(THREE))
    expect(captures_list(page).locator('[aria-current="page"]')).to_have_count(0)
    expect(detail(page)).to_have_count(0)


@pytest.mark.p0
def test_a_capture_that_isnt_in_anki_shows_a_message_and_the_back_link(page: Page) -> None:
    """AC-16: /captures/<captureId> for a Capture that isn't in Anki (404 `not_found`) reads
    "This Capture isn't in Anki." with the "‹ Captures" back link, and no Capture detail.
    """
    capture_id = str(uuid.uuid4())
    stub_api_error(
        page,
        f"{API}/{capture_id}",
        status=404,
        code="not_found",
        message="Not found.",
        method="GET",
    )
    page.set_viewport_size(viewports.PHONE)
    page.goto(f"{CAPTURES_PATH}/{capture_id}")

    expect(main(page).get_by_text(NOT_IN_ANKI, exact=True)).to_be_visible()

    expect(back_link(page)).to_be_visible()
    expect(detail(page)).to_have_count(0)


# Secondary cases (green phase)

UNSAVED_ALERT = "Discard unsaved changes?"
LONG_TEXT = "notwithstanding" * 30  # one word, far wider than any screen


def unsaved_alert(page: Page) -> Locator:
    return page.get_by_role("alertdialog", name=UNSAVED_ALERT, exact=True)


def horizontal_overflow(page: Page) -> float:
    return page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )


@pytest.mark.p1
def test_on_desktop_typed_compose_text_survives_opening_a_capture(page: Page) -> None:
    """AC-10: on desktop, opening rows with unsaved compose text keeps the text and asks
    nothing: the screen stays mounted.
    """
    page.set_viewport_size(viewports.DESKTOP)
    stub_list(page, THREE)
    stub_detail(page, TODAY_EARLY)
    stub_detail(page, YESTERDAY)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill("half a thought")

    rows(page).nth(1).click()
    expect(detail(page)).to_contain_text(TODAY_EARLY["text"])
    rows(page).nth(2).click()

    expect(detail(page)).to_contain_text(YESTERDAY["text"])
    expect(rows(page).nth(2)).to_have_attribute("aria-current", "page")
    expect(compose_box(page)).to_have_value("half a thought")
    expect(unsaved_alert(page)).to_be_hidden()


@pytest.mark.p1
def test_on_the_phone_unsaved_text_survives_a_capture_and_back(page: Page) -> None:
    """AC-9: on the phone, opening a Capture and coming back with browser back keeps the
    unsaved compose text, with no alert.
    """
    page.set_viewport_size(viewports.PHONE)
    stub_list(page, THREE)
    stub_detail(page, TODAY_LATE)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill("half a thought")

    rows(page).first.click()
    expect(detail(page)).to_contain_text(TODAY_LATE["text"])
    page.go_back()

    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(compose_box(page)).to_have_value("half a thought")
    expect(unsaved_alert(page)).to_be_hidden()


@pytest.mark.p1
def test_ipad_portrait_uses_the_phone_layout(page: Page) -> None:
    """AC-9: at iPad portrait (below 1024px) a Capture is its own screen, with the back link."""
    page.set_viewport_size(viewports.TABLET)
    stub_list(page, THREE)
    stub_detail(page, TODAY_EARLY)
    page.goto(f"{CAPTURES_PATH}/{TODAY_EARLY['captureId']}")

    expect(detail(page)).to_contain_text(TODAY_EARLY["text"])
    expect(back_link(page)).to_be_visible()
    expect(compose_box(page)).to_be_hidden()
    expect(captures_list(page)).to_be_hidden()


@pytest.mark.p1
def test_ipad_landscape_has_two_panes(page: Page) -> None:
    """AC-10: at iPad landscape (1180px wide) list and detail are two panes, no back link."""
    page.set_viewport_size({"width": 1180, "height": 820})
    stub_list(page, [TODAY_EARLY])
    stub_detail(page, TODAY_EARLY)
    page.goto(f"{CAPTURES_PATH}/{TODAY_EARLY['captureId']}")

    expect(detail(page)).to_contain_text(TODAY_EARLY["text"])
    expect(main(page).get_by_text("1 Capture · newest first", exact=True)).to_be_visible()
    expect(compose_box(page)).to_be_visible()
    expect(back_link(page)).to_have_count(0)


@pytest.mark.p1
def test_on_desktop_a_capture_not_in_anki_leaves_the_list_with_nothing_selected(
    page: Page,
) -> None:
    """AC-16: on desktop the list stays, with no row selected."""
    capture_id = str(uuid.uuid4())
    stub_list(page, THREE)
    stub_api_error(
        page,
        f"{API}/{capture_id}",
        status=404,
        code="not_found",
        message="Not found.",
        method="GET",
    )
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(f"{CAPTURES_PATH}/{capture_id}")

    expect(main(page).get_by_text(NOT_IN_ANKI, exact=True)).to_be_visible()
    expect(rows(page)).to_have_count(len(THREE))
    expect(captures_list(page).locator('[aria-current="page"]')).to_have_count(0)


@pytest.mark.p1
def test_a_list_that_fails_to_load_shows_an_alert_and_try_again_reloads(page: Page) -> None:
    """AC-12: a failed GET /api/captures shows an inline alert with the envelope's message and
    Try again, which reloads the list.
    """
    held = HeldRoute(page, API, method="GET")
    page.set_viewport_size(viewports.PHONE)
    page.goto(CAPTURES_PATH)
    held.fulfill_json(
        {
            "error": {
                "code": "anki_unavailable",
                "message": "Anki isn't reachable.",
                "requestId": "r",
            }
        },
        status=503,
    )
    alert = main(page).get_by_role("alert")
    expect(alert).to_contain_text("Anki isn't reachable.")
    page.unroute(f"**{API}")
    stub_list(page, THREE)

    alert.get_by_role("button", name="Try again", exact=True).click()

    expect(rows(page)).to_have_count(len(THREE))
    expect(main(page).get_by_role("alert")).to_have_count(0)


@pytest.mark.p1
def test_on_the_phone_there_is_no_selection_hint(page: Page) -> None:
    """AC-15: below 1024px there is no hint at /captures."""
    page.set_viewport_size(viewports.PHONE)
    stub_list(page, THREE)
    page.goto(CAPTURES_PATH)
    expect(rows(page)).to_have_count(len(THREE))

    expect(main(page).get_by_text(NO_SELECTION, exact=True)).to_be_hidden()


@pytest.mark.p1
@pytest.mark.parametrize("viewport", viewports.ALL.values(), ids=viewports.ALL.keys())
def test_list_and_detail_fit_every_width_with_long_text(page: Page, viewport: Any) -> None:
    """AC-8 / AC-10: list and detail fit phone, tablet and desktop with no horizontal scroll,
    a long unbroken text wrapping.
    """
    long_one = capture(LONG_TEXT, "2026-10-22T12:02:00Z")
    page.set_viewport_size(viewport)
    stub_list(page, [long_one, *THREE])
    stub_detail(page, long_one)
    page.goto(CAPTURES_PATH)
    expect(rows(page)).to_have_count(4)

    list_overflow = horizontal_overflow(page)
    page.goto(f"{CAPTURES_PATH}/{long_one['captureId']}")
    expect(detail(page)).to_contain_text(LONG_TEXT)

    assert max(list_overflow, horizontal_overflow(page)) <= 0


@pytest.mark.p1
@pytest.mark.browser_context_args(timezone_id=TORONTO, locale="en-US")
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (YESTERDAY, "Captured yesterday · 19:40"),
        (OCT_5, "Captured Oct 5 · 12:31"),
        (LAST_YEAR, "Captured Oct 4, 2025 · 22:05"),
    ],
    ids=["yesterday", "this-year", "last-year"],
)
def test_the_detail_reads_its_creation_time_relative_to_today(
    page: Page, body: dict[str, str], expected: str
) -> None:
    """AC-11: the detail reads "Captured yesterday · …", or the date, with its year outside
    the current one, in the browser's time zone.
    """
    page.clock.set_fixed_time(NOW)
    page.set_viewport_size(viewports.DESKTOP)
    stub_list(page, [TODAY_LATE, TODAY_EARLY, YESTERDAY, OCT_5, LAST_YEAR])
    stub_detail(page, body)
    page.goto(f"{CAPTURES_PATH}/{body['captureId']}")

    expect(detail(page)).to_contain_text(expected)


@pytest.mark.p1
def test_on_the_phone_a_newly_saved_capture_tops_the_list(page: Page) -> None:
    """AC-14: at phone width too, a saved Capture is the list's first row."""
    text = f"un rendez-vous {uuid.uuid4()}"
    page.set_viewport_size(viewports.PHONE)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill(text)

    with page.expect_response(is_save):
        main(page).get_by_role("button", name=SAVE, exact=True).click()

    expect(rows(page).first).to_contain_text(text)


@pytest.mark.p1
def test_on_desktop_a_row_click_selects_it_without_a_full_reload(page: Page) -> None:
    """AC-10: clicking a row on desktop selects it and shows its detail, with no page load."""
    page.set_viewport_size(viewports.DESKTOP)
    stub_list(page, THREE)
    stub_detail(page, YESTERDAY)
    page.goto(CAPTURES_PATH)
    expect(rows(page)).to_have_count(len(THREE))
    page.evaluate("window.__noReload = true")

    rows(page).nth(2).click()

    expect(rows(page).nth(2)).to_have_attribute("aria-current", "page")
    expect(detail(page)).to_contain_text(YESTERDAY["text"])
    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{YESTERDAY['captureId']}"))
    assert page.evaluate("window.__noReload === true")

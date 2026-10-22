"""Story 3.1: the Captures screen's compose box (S-Captures, EXPERIENCE.md, AD-8, AD-13).

- **The box.** A text area labelled "New Capture", placeholder "Paste or type a word, phrase
  or sentence", and the Primary "Save Capture". Save is disabled while the text is blank
  (decided with the user, 2026-10-22: blank is empty or whitespace only) and while a Save is in
  flight.
- **CaptureId.** Generated in the browser (UUIDv4) once per composition, kept across retries of
  that composition, and new after a successful Save (AD-8, AD-20).
- **Success.** The box clears (J1). Listing Captures is entry 2's.
- **Unsaved text.** While the box holds unsaved text the screen calls `router.setDirty`, and the
  router's alert reads "This Capture isn't saved." (decided with the user, 2026-10-22). A
  successful Save clears it.
- **Failure.** The text stays, and an inline alert at the box shows the EXPERIENCE.md copy for
  `anki_unavailable` with Try again. Nothing reports the Capture as saved.

Success runs against the live server, whose AnkiStore is the fake. Failure and in-flight states
are stubbed at the network, POST only, so the screen's list (story 3.2) still loads.
"""

import json
import re
from typing import Any

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support import viewports
from tests.support.captures_screen import API, CAPTURES_PATH, SAVE, compose_box, horizontal_overflow
from tests.support.navigation import SETUP, main_nav, path_pattern
from tests.support.network import HeldRoute, record_json_bodies, stub_api_error
from tests.support.unsaved import unsaved_alert

PLACEHOLDER = "Paste or type a word, phrase or sentence"
TEXT = "I'd rather not jump to conclusions."
UUID4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")

UNSAVED_BODY = "This Capture isn't saved."
NOT_SAVED = "Not saved — Anki isn't reachable"
NOT_SAVED_BODY = (
    "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here."
)
UNAVAILABLE_MESSAGE = "Anki isn't reachable. Check that Anki is running."


def open_captures(page: Page) -> None:
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)


def save_button(page: Page) -> Any:
    return page.get_by_role("main").get_by_role("button", name=SAVE, exact=True)


def saved_body(capture_id: str, text: str = TEXT) -> dict[str, str]:
    return {"captureId": capture_id, "text": text, "createdAt": "2026-10-22T21:14:05Z"}


@pytest.mark.p0
def test_save_is_disabled_while_the_compose_box_is_blank(page: Page) -> None:
    """AC-9: the compose box per S-Captures, with Save Capture disabled while it is blank."""
    open_captures(page)

    expect(save_button(page)).to_be_disabled()
    expect(compose_box(page)).to_have_attribute("placeholder", PLACEHOLDER)
    compose_box(page).fill(" \n\t ")
    expect(save_button(page)).to_be_disabled()
    compose_box(page).fill(TEXT)
    expect(save_button(page)).to_be_enabled()


@pytest.mark.p0
def test_save_sends_a_new_uuid4_capture_id_and_clears_the_box(page: Page) -> None:
    """AC-10: Save posts the text with a browser-generated UUIDv4 CaptureId and, once saved,
    clears the compose box.
    """
    bodies = record_json_bodies(page, API)
    open_captures(page)
    compose_box(page).fill(TEXT)

    save_button(page).click()

    expect(compose_box(page)).to_have_value("")
    (body,) = bodies
    assert body["text"] == TEXT
    assert UUID4.fullmatch(body["captureId"])
    expect(save_button(page)).to_be_disabled()


@pytest.mark.p0
def test_a_retry_keeps_the_capture_id_and_the_next_composition_gets_a_new_one(
    page: Page,
) -> None:
    """AC-11: Try again re-sends the composition's CaptureId; after a successful Save the next
    composition gets a new one.
    """
    answers = ["fail"]

    def first_fails(route: Route) -> None:
        if route.request.method == "POST" and answers and answers.pop() == "fail":
            envelope = {"error": {"code": "anki_unavailable", "message": UNAVAILABLE_MESSAGE}}
            route.fulfill(status=503, content_type="application/json", body=json.dumps(envelope))
        else:
            route.continue_()

    page.route(f"**{API}", first_fails)
    bodies = record_json_bodies(page, API)
    open_captures(page)
    compose_box(page).fill(TEXT)
    save_button(page).click()
    with page.expect_response(f"**{API}"):
        page.get_by_role("main").get_by_role("button", name="Try again", exact=True).click()

    assert bodies[1]["captureId"] == bodies[0]["captureId"]
    compose_box(page).fill("un rendez-vous")
    with page.expect_response(f"**{API}"):
        save_button(page).click()
    assert bodies[2]["captureId"] != bodies[0]["captureId"]
    assert UUID4.fullmatch(bodies[2]["captureId"])


@pytest.mark.p0
def test_save_is_disabled_while_a_save_is_in_flight(page: Page) -> None:
    """AC-12: while a Save is in flight, Save Capture is disabled, so it is sent once."""
    held = HeldRoute(page, API, method="POST")
    bodies = record_json_bodies(page, API)
    open_captures(page)
    compose_box(page).fill(TEXT)

    save_button(page).click()

    expect(save_button(page)).to_be_disabled()
    expect(compose_box(page)).to_have_value(TEXT)
    held.fulfill_json(saved_body(bodies[0]["captureId"]), status=201)
    expect(compose_box(page)).to_have_value("")
    assert len(bodies) == 1


@pytest.mark.p0
def test_leaving_with_unsaved_text_raises_the_alert_with_the_capture_copy(page: Page) -> None:
    """AC-13: unsaved text in the compose box makes the screen dirty: leaving raises the
    router's alert with "This Capture isn't saved.", and Keep editing keeps the text.
    """
    open_captures(page)
    compose_box(page).fill(TEXT)

    main_nav(page).get_by_role("link", name=SETUP.area, exact=True).click()

    expect(unsaved_alert(page)).to_contain_text(UNSAVED_BODY)
    unsaved_alert(page).get_by_role("button", name="Keep editing", exact=True).click()
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(compose_box(page)).to_have_value(TEXT)


@pytest.mark.p0
def test_a_successful_save_clears_the_unsaved_state(page: Page) -> None:
    """AC-14: after a successful Save, leaving the screen asks nothing."""
    open_captures(page)
    compose_box(page).fill(TEXT)
    with page.expect_response(f"**{API}"):
        save_button(page).click()
    # The screen clears its unsaved state after it reads the response, not when it arrives
    expect(compose_box(page)).to_have_value("")

    main_nav(page).get_by_role("link", name=SETUP.area, exact=True).click()

    expect(page).to_have_url(path_pattern(SETUP.path))
    expect(unsaved_alert(page)).to_have_count(0)


@pytest.mark.p0
def test_anki_unreachable_keeps_the_text_and_shows_the_error_with_try_again(page: Page) -> None:
    """AC-15: a Save failing with `anki_unavailable` keeps the text and shows the inline alert
    "Not saved — Anki isn't reachable" with its body and Try again; nothing reports it saved.
    """
    stub_api_error(
        page, API, status=503, code="anki_unavailable", message=UNAVAILABLE_MESSAGE, method="POST"
    )
    open_captures(page)
    compose_box(page).fill(TEXT)

    save_button(page).click()

    alert = page.get_by_role("main").get_by_role("alert")
    expect(alert).to_contain_text(NOT_SAVED)
    expect(alert).to_contain_text(NOT_SAVED_BODY)
    expect(alert.get_by_role("button", name="Try again", exact=True)).to_be_visible()
    expect(compose_box(page)).to_have_value(TEXT)
    expect(page.get_by_role("status")).to_have_count(0)


@pytest.mark.p1
@pytest.mark.parametrize("viewport", viewports.ALL.values(), ids=viewports.ALL.keys())
def test_the_compose_box_fits_every_width(page: Page, viewport: Any) -> None:
    """AC-9: on phone, tablet and desktop the compose box fits with no horizontal scroll, and
    its text is at least 16px, so iOS Safari doesn't zoom on focus.
    """
    page.set_viewport_size(viewport)
    page.goto(CAPTURES_PATH)
    expect(compose_box(page)).to_be_visible()

    overflow = horizontal_overflow(page)
    assert overflow <= 0
    font_size = compose_box(page).evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert font_size >= 16
    box = compose_box(page).bounding_box()
    assert box is not None and box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]

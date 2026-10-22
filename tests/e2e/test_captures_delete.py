"""Story 3.3: delete a Capture after confirmation (S-Delete, EXPERIENCE.md, spec Assumptions).

- **The dialog.** Capture detail has "Delete Capture", which opens the confirmation dialog, an
  `alertdialog` built on the router's (so Item delete in epic-maintain-items reuses it). Its
  title is "Delete this Capture?", its body "This removes the Capture from Anki. Items you made
  from it stay.", and its buttons Delete permanently and Cancel. Focus starts on Cancel and
  stays within the dialog; Esc is Cancel; closing returns focus to "Delete Capture".
- **Delete permanently.** While the DELETE is in flight the dialog stays open, with Delete
  permanently disabled and its label kept (decided with the user, 2026-10-22). After the
  delete the user lands on the list without it: on desktop with nothing selected.
- **Failure (decided with the user, 2026-10-22).** The dialog closes, the Capture stays, and
  Capture detail shows an inline alert: for `anki_unavailable` "Not deleted — Anki isn't
  reachable" / "Make sure Anki Desktop is open on the Mac mini, then try again."; for any other
  code "Not deleted" with the envelope's message. There is no Try again: Delete Capture asks
  again.

The list and detail are stubbed at the network (GET only) so their contents are fixed: the live
server's fake is shared by the session. A delete that succeeds runs against the live server,
on a Capture the test saves itself.
"""

import uuid
from typing import Any

import pytest
from playwright.sync_api import Locator, Page, Request, Response, expect

from tests.support import viewports
from tests.support.keys import shift_tab, tab
from tests.support.navigation import path_pattern
from tests.support.network import HeldRoute, stub_api_error, stub_api_json

CAPTURES_PATH = "/captures"
API = "/api/captures"
COMPOSE_LABEL = "New Capture"
SAVE = "Save Capture"
NO_SELECTION = "Choose a Capture to see it here."

DELETE_CAPTURE = "Delete Capture"
DIALOG_TITLE = "Delete this Capture?"
DIALOG_BODY = "This removes the Capture from Anki. Items you made from it stay."
CONFIRM = "Delete permanently"
CANCEL = "Cancel"
NOT_DELETED = "Not deleted — Anki isn't reachable"
NOT_DELETED_BODY = "Make sure Anki Desktop is open on the Mac mini, then try again."


def capture(text: str, created_at: str) -> dict[str, str]:
    return {"captureId": str(uuid.uuid4()), "text": text, "createdAt": created_at}


TARGET = capture("I'd rather not jump to conclusions.", "2026-10-22T21:14:00Z")
OTHER = capture("Il fait un temps de chien.", "2026-10-22T12:02:00Z")


def open_stubbed_capture(page: Page, viewport: dict[str, int]) -> None:
    """/captures/<TARGET> at `viewport`, with the list (TARGET, OTHER) and TARGET's detail
    stubbed (GET only).
    """
    page.set_viewport_size(viewport)
    stub_api_json(page, API, {"captures": [TARGET, OTHER]}, method="GET")
    stub_api_json(page, f"{API}/{TARGET['captureId']}", TARGET, method="GET")
    page.goto(f"{CAPTURES_PATH}/{TARGET['captureId']}")


def main(page: Page) -> Locator:
    return page.get_by_role("main")


def compose_box(page: Page) -> Locator:
    return main(page).get_by_role("textbox", name=COMPOSE_LABEL, exact=True)


def rows(page: Page) -> Locator:
    return main(page).get_by_role("list", name="Captures", exact=True).get_by_role("link")


def detail(page: Page) -> Locator:
    return main(page).get_by_role("article")


def delete_button(page: Page) -> Locator:
    return main(page).get_by_role("button", name=DELETE_CAPTURE, exact=True)


def dialog(page: Page) -> Locator:
    return page.get_by_role("alertdialog", name=DIALOG_TITLE, exact=True)


def confirm_button(page: Page) -> Locator:
    return dialog(page).get_by_role("button", name=CONFIRM, exact=True)


def cancel_button(page: Page) -> Locator:
    return dialog(page).get_by_role("button", name=CANCEL, exact=True)


def record_deletes(page: Page) -> list[str]:
    """Return a list that fills with the URL of every DELETE the page sends from now on."""
    urls: list[str] = []

    def on_request(request: Request) -> None:
        if request.method == "DELETE":
            urls.append(request.url)

    page.on("request", on_request)
    return urls


def is_save(response: Response) -> bool:
    return response.request.method == "POST" and response.url.endswith(API)


def save_and_open(page: Page, text: str) -> None:
    """Save a Capture of `text` from the compose box on the live server, then open its row."""
    compose_box(page).fill(text)
    with page.expect_response(is_save):
        main(page).get_by_role("button", name=SAVE, exact=True).click()
    rows(page).filter(has_text=text).click()
    expect(detail(page)).to_contain_text(text)


@pytest.mark.p0
def test_delete_capture_opens_the_confirmation_dialog(page: Page) -> None:
    """AC-6: "Delete Capture" in Capture detail opens the alert dialog "Delete this Capture?"
    with the body "This removes the Capture from Anki. Items you made from it stay." and the
    buttons Delete permanently and Cancel.
    """
    open_stubbed_capture(page, viewports.DESKTOP)

    delete_button(page).click()

    expect(dialog(page)).to_be_visible()
    expect(dialog(page)).to_have_accessible_description(DIALOG_BODY)
    expect(confirm_button(page)).to_be_visible()
    expect(cancel_button(page)).to_be_visible()


@pytest.mark.p0
def test_cancel_closes_the_dialog_and_keeps_the_capture(page: Page) -> None:
    """AC-7: Cancel closes the dialog with no DELETE sent; the Capture stays open in detail
    and in the list.
    """
    deletes = record_deletes(page)
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).click()

    cancel_button(page).click()

    expect(dialog(page)).to_be_hidden()
    assert deletes == []
    expect(detail(page)).to_contain_text(TARGET["text"])
    expect(rows(page)).to_have_count(2)
    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{TARGET['captureId']}"))


@pytest.mark.p0
def test_on_the_phone_delete_permanently_lands_on_the_list_without_it(page: Page) -> None:
    """AC-8: on the phone, Delete permanently deletes the Capture and lands on /captures, the
    list without it.
    """
    text = f"to be on the fence {uuid.uuid4()}"
    page.set_viewport_size(viewports.PHONE)
    page.goto(CAPTURES_PATH)
    save_and_open(page, text)
    delete_button(page).click()

    confirm_button(page).click()

    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(rows(page).filter(has_text=text)).to_have_count(0)
    expect(dialog(page)).to_be_hidden()
    page.reload()
    expect(compose_box(page)).to_be_visible()
    expect(rows(page).filter(has_text=text)).to_have_count(0)


@pytest.mark.p0
def test_on_desktop_after_delete_nothing_is_selected(page: Page) -> None:
    """AC-9: on desktop, after Delete permanently the right pane reads "Choose a Capture to see
    it here.", no row is selected, and the deleted Capture is gone from the list.
    """
    text = f"notwithstanding {uuid.uuid4()}"
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    save_and_open(page, text)
    delete_button(page).click()

    confirm_button(page).click()

    expect(main(page).get_by_text(NO_SELECTION, exact=True)).to_be_visible()
    expect(rows(page).filter(has_text=text)).to_have_count(0)
    expect(main(page).locator('[aria-current="page"]')).to_have_count(0)
    expect(detail(page)).to_have_count(0)
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))


@pytest.mark.p0
def test_the_dialog_keeps_keyboard_focus_and_esc_cancels(page: Page, browser_name: str) -> None:
    """AC-10: focus starts on Cancel (the safe default) and Tab / Shift+Tab stay within the
    dialog; Esc closes it like Cancel, with no DELETE sent, and focus returns to "Delete
    Capture".
    """
    deletes = record_deletes(page)
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).focus()
    page.keyboard.press("Enter")

    expect(cancel_button(page)).to_be_focused()

    page.keyboard.press(tab(browser_name))
    expect(confirm_button(page)).to_be_focused()
    page.keyboard.press(tab(browser_name))
    expect(cancel_button(page)).to_be_focused()
    page.keyboard.press(shift_tab(browser_name))
    expect(confirm_button(page)).to_be_focused()
    page.keyboard.press("Escape")
    expect(dialog(page)).to_be_hidden()
    expect(delete_button(page)).to_be_focused()
    expect(detail(page)).to_contain_text(TARGET["text"])
    assert deletes == []


@pytest.mark.p0
def test_while_the_delete_is_in_flight_the_dialog_stays_open_and_busy(page: Page) -> None:
    """AC-11: while the DELETE is pending the dialog stays open, with Delete permanently
    disabled and its label kept, so a second press sends nothing.
    """
    held = HeldRoute(page, f"{API}/{TARGET['captureId']}", method="DELETE")
    deletes = record_deletes(page)
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).click()

    confirm_button(page).click()

    expect(confirm_button(page)).to_be_disabled()
    expect(dialog(page)).to_be_visible()
    assert len(deletes) == 1
    error = {"code": "anki_unavailable", "message": "Anki isn't reachable.", "requestId": ""}
    held.fulfill_json({"error": error}, status=503)
    expect(dialog(page)).to_be_hidden()


@pytest.mark.p0
def test_a_failed_delete_keeps_the_capture_and_shows_the_error(page: Page) -> None:
    """AC-12: when the DELETE fails with `anki_unavailable`, the dialog closes, the Capture
    stays (detail, row and URL), and Capture detail shows the inline alert "Not deleted — Anki
    isn't reachable" / "Make sure Anki Desktop is open on the Mac mini, then try again."
    """
    stub_api_error(
        page,
        f"{API}/{TARGET['captureId']}",
        status=503,
        code="anki_unavailable",
        message="Anki isn't reachable.",
        method="DELETE",
    )
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).click()

    confirm_button(page).click()

    alert = main(page).get_by_role("alert").filter(has_text=NOT_DELETED)
    expect(alert).to_be_visible()
    expect(alert).to_contain_text(NOT_DELETED_BODY)
    expect(dialog(page)).to_be_hidden()
    expect(detail(page)).to_contain_text(TARGET["text"])
    expect(rows(page).filter(has_text=TARGET["text"])).to_have_count(1)
    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{TARGET['captureId']}"))


# Secondary cases (green phase)

UNSAVED_ALERT = "Discard unsaved changes?"
NOT_IN_ANKI = "This Capture isn't in Anki."


def unsaved_alert(page: Page) -> Locator:
    return page.get_by_role("alertdialog", name=UNSAVED_ALERT, exact=True)


def horizontal_overflow(page: Page) -> float:
    return page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )


@pytest.mark.p1
def test_cancel_returns_focus_and_the_dialog_opens_again(page: Page) -> None:
    """AC-7: Cancel returns focus to "Delete Capture"; the dialog opens again, and a second
    Cancel also sends nothing.
    """
    deletes = record_deletes(page)
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).click()
    cancel_button(page).click()

    expect(delete_button(page)).to_be_focused()

    delete_button(page).click()
    expect(dialog(page)).to_be_visible()
    cancel_button(page).click()
    expect(dialog(page)).to_be_hidden()
    assert deletes == []


@pytest.mark.p1
def test_compose_text_survives_a_delete_and_focus_lands_on_the_heading(page: Page) -> None:
    """AC-8: unsaved compose text survives the delete with no unsaved alert (same-screen
    navigation), and focus moves to the "Captures" heading, since the button is gone.
    """
    text = f"in the offing {uuid.uuid4()}"
    page.set_viewport_size(viewports.PHONE)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill(text)
    with page.expect_response(is_save):
        main(page).get_by_role("button", name=SAVE, exact=True).click()
    compose_box(page).fill("half typed")
    rows(page).filter(has_text=text).click()
    delete_button(page).click()

    confirm_button(page).click()

    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(unsaved_alert(page)).to_be_hidden()
    expect(compose_box(page)).to_have_value("half typed")
    expect(main(page).get_by_role("heading", name="Captures", exact=True)).to_be_focused()


@pytest.mark.p1
def test_on_desktop_the_header_count_drops_after_a_delete(page: Page) -> None:
    """AC-9: the header count ("N Captures · newest first") drops by one after the delete."""
    text = f"by and large {uuid.uuid4()}"
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    save_and_open(page, text)
    before = rows(page).count()
    delete_button(page).click()

    confirm_button(page).click()

    expect(rows(page)).to_have_count(before - 1)
    left = before - 1
    header = f"{left} {'Capture' if left == 1 else 'Captures'} · newest first"
    expect(main(page).get_by_text(header, exact=True)).to_have_count(1 if left else 0)


@pytest.mark.p1
def test_cancel_is_disabled_while_the_delete_is_in_flight(page: Page) -> None:
    """AC-11: while the DELETE is pending Cancel is disabled too, and Esc doesn't close it."""
    held = HeldRoute(page, f"{API}/{TARGET['captureId']}", method="DELETE")
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).click()
    confirm_button(page).click()

    expect(cancel_button(page)).to_be_disabled()

    expect(confirm_button(page)).to_have_text(CONFIRM)
    page.keyboard.press("Escape")
    expect(dialog(page)).to_be_visible()
    held.fulfill_json(
        {"error": {"code": "anki_busy", "message": "Busy.", "requestId": ""}}, status=503
    )
    expect(dialog(page)).to_be_hidden()


@pytest.mark.p1
def test_a_second_press_while_busy_sends_no_second_delete(page: Page) -> None:
    """AC-11: a second Delete permanently while the DELETE is pending sends nothing more."""
    held = HeldRoute(page, f"{API}/{TARGET['captureId']}", method="DELETE")
    deletes = record_deletes(page)
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).click()
    confirm_button(page).click()
    expect(confirm_button(page)).to_be_disabled()

    confirm_button(page).dispatch_event("click")

    assert len(deletes) == 1
    error = {"code": "anki_unavailable", "message": "Anki isn't reachable.", "requestId": ""}
    held.fulfill_json({"error": error}, status=503)
    expect(dialog(page)).to_be_hidden()
    assert len(deletes) == 1


@pytest.mark.p1
def test_a_browser_back_while_the_delete_is_in_flight_keeps_the_capture_open(
    page: Page,
) -> None:
    """AC-12: a browser back while the DELETE is pending leaves the route as it was, so a
    failure still shows its alert in Capture detail.
    """
    held = HeldRoute(page, f"{API}/{TARGET['captureId']}", method="DELETE")
    page.set_viewport_size(viewports.PHONE)
    stub_api_json(page, API, {"captures": [TARGET, OTHER]}, method="GET")
    stub_api_json(page, f"{API}/{TARGET['captureId']}", TARGET, method="GET")
    page.goto(CAPTURES_PATH)
    rows(page).filter(has_text=TARGET["text"]).click()
    delete_button(page).click()
    confirm_button(page).click()
    expect(confirm_button(page)).to_be_disabled()

    page.evaluate("history.back()")

    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{TARGET['captureId']}"))
    error = {"code": "anki_unavailable", "message": "Anki isn't reachable.", "requestId": ""}
    held.fulfill_json({"error": error}, status=503)
    expect(main(page).get_by_role("alert").filter(has_text=NOT_DELETED)).to_be_visible()
    expect(detail(page)).to_contain_text(TARGET["text"])


@pytest.mark.p1
def test_on_desktop_delete_capture_sits_in_the_card(page: Page) -> None:
    """AC-6: on desktop "Delete Capture" is inside the detail card, beside the text."""
    open_stubbed_capture(page, viewports.DESKTOP)

    expect(detail(page).get_by_role("button", name=DELETE_CAPTURE, exact=True)).to_be_visible()

    expect(delete_button(page)).to_have_count(1)


@pytest.mark.p1
def test_another_failure_shows_not_deleted_with_the_envelope_message(page: Page) -> None:
    """AC-12: a failure other than `anki_unavailable` shows "Not deleted" with the envelope's
    message, and Delete Capture opens the dialog again.
    """
    stub_api_error(
        page,
        f"{API}/{TARGET['captureId']}",
        status=503,
        code="anki_busy",
        message="Anki is busy. Try again in a moment.",
        method="DELETE",
    )
    open_stubbed_capture(page, viewports.DESKTOP)
    delete_button(page).click()

    confirm_button(page).click()

    alert = main(page).get_by_role("alert").filter(has_text="Not deleted")
    expect(alert).to_contain_text("Anki is busy. Try again in a moment.")
    expect(alert).not_to_contain_text(NOT_DELETED)
    expect(delete_button(page)).to_be_focused()
    delete_button(page).click()
    expect(dialog(page)).to_be_visible()


@pytest.mark.p1
def test_a_network_failure_shows_the_server_unreachable_message(page: Page) -> None:
    """AC-12: a DELETE that never reaches the server shows "LanguageLab could not reach the
    server."
    """

    def abort_delete(route: Any) -> None:
        if route.request.method == "DELETE":
            route.abort()
        else:
            route.fallback()

    page.route(f"**{API}/{TARGET['captureId']}", abort_delete)
    open_stubbed_capture(page, viewports.PHONE)
    delete_button(page).click()

    confirm_button(page).click()

    alert = main(page).get_by_role("alert").filter(has_text="Not deleted")
    expect(alert).to_contain_text("LanguageLab could not reach the server.")
    expect(detail(page)).to_contain_text(TARGET["text"])


@pytest.mark.p1
def test_no_delete_capture_on_a_capture_that_isnt_in_anki(page: Page) -> None:
    """AC-6: "This Capture isn't in Anki." has no Delete Capture."""
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

    expect(delete_button(page)).to_have_count(0)


@pytest.mark.p1
def test_a_browser_back_closes_the_dialog_as_cancel(page: Page) -> None:
    """AC-10: a browser back while the dialog is open closes it like Cancel, with no DELETE."""
    deletes = record_deletes(page)
    page.set_viewport_size(viewports.DESKTOP)
    stub_api_json(page, API, {"captures": [TARGET, OTHER]}, method="GET")
    stub_api_json(page, f"{API}/{TARGET['captureId']}", TARGET, method="GET")
    page.goto(CAPTURES_PATH)
    rows(page).filter(has_text=TARGET["text"]).click()
    delete_button(page).click()

    page.go_back()

    expect(dialog(page)).to_be_hidden()
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    assert deletes == []


@pytest.mark.p1
@pytest.mark.parametrize("viewport", viewports.ALL.values(), ids=viewports.ALL.keys())
def test_the_dialog_fits_every_width(page: Page, viewport: Any) -> None:
    """AC-6: the dialog fits phone, tablet and desktop with no horizontal scroll."""
    open_stubbed_capture(page, viewport)
    delete_button(page).click()

    expect(dialog(page)).to_be_visible()

    assert horizontal_overflow(page) <= 0
    box = dialog(page).bounding_box()
    assert box is not None and box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]

"""Capture copy actions and a prefilled Custom value (plan capture-copy-actions).

- **Copy to compose box.** A shown Capture's "Copy to compose box" puts its text into New
  Capture (replacing what was there), goes to /captures and focuses the box; the screen is
  dirty, and Example sentences opens its pane for that text. Nothing is saved.
- **Copy.** "Copy" writes the Capture's text to the clipboard and reads "Copied" for a moment;
  when no way to copy works it reads "Couldn't copy" instead, with no alert.
- **Custom value.** Choosing Custom value while its field is empty fills it with the text Use
  as is takes (the Capture's, or the compose text at /captures/make); an edit survives
  switching back and forth.

The Capture is stubbed at the network (GET only).
"""

import pytest
from playwright.sync_api import Page, ViewportSize, expect

from tests.support import viewports
from tests.support.captures_screen import API, CAPTURES_PATH, capture, compose_box, detail, main
from tests.support.examples_screen import examples_button, examples_pane
from tests.support.items_screen import (
    CUSTOM_VALUE,
    USE_AS_IS,
    choice,
    pane,
    write_it_myself,
)
from tests.support.navigation import path_pattern
from tests.support.network import HeldRoute, stub_api_json
from tests.support.unsaved import LEAVE_PATHS, keep_editing_button, unsaved_alert

TEXT = "jump to conclusions"
CAPTURE = capture(TEXT, "2026-11-15T09:30:00Z")
CAPTURE_ID = CAPTURE["captureId"]

COPY_TO_BOX = "Copy to compose box"
COPY = "Copy"
COPIED = "Copied"
NOT_COPIED = "Couldn't copy"
MAKE_AN_ITEM = "Make an Item"
MAKE_PATH = "/captures/make"

WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}


def open_capture(page: Page, viewport: ViewportSize) -> None:
    page.set_viewport_size(viewport)
    stub_api_json(page, API, {"captures": [CAPTURE]}, method="GET")
    stub_api_json(page, f"{API}/{CAPTURE_ID}", CAPTURE, method="GET")
    page.goto(f"{CAPTURES_PATH}/{CAPTURE_ID}")
    expect(copy_to_box(page)).to_be_visible()


def copy_to_box(page: Page):
    return detail(page).get_by_role("button", name=COPY_TO_BOX, exact=True)


def copy_button(page: Page):
    return detail(page).locator(".capture-copy")


def custom_field(page: Page):
    return pane(page).get_by_role("textbox", name=CUSTOM_VALUE)


@pytest.mark.p0
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_copy_to_compose_box_puts_the_text_in_new_capture(
    page: Page, viewport: ViewportSize
) -> None:
    """COPY_TO_BOX: /captures with the text in the focused box, replacing earlier text; the
    screen is dirty and Example sentences opens for that text, without generating.
    """
    open_capture(page, viewport)
    if viewport == viewports.DESKTOP:
        compose_box(page).fill("something else")

    copy_to_box(page).click()

    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(compose_box(page)).to_have_value(TEXT)
    expect(compose_box(page)).to_be_focused()
    expect(main(page).get_by_role("button", name="Save Capture", exact=True)).to_be_enabled()

    # Dirty: leaving asks first, and Keep editing stays with the text
    leave = "phone-menu-row" if viewport == viewports.PHONE else "desktop-pill"
    LEAVE_PATHS[leave].leave(page)
    expect(unsaved_alert(page)).to_be_visible()
    keep_editing_button(page).click()
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(compose_box(page)).to_have_value(TEXT)

    examples_button(page).click()
    expect(examples_pane(page)).to_be_visible()
    expect(examples_pane(page)).to_contain_text(TEXT)
    expect(examples_pane(page).get_by_role("heading", name="A1")).to_have_count(0)


@pytest.mark.p1
def test_copy_to_compose_box_waits_while_a_save_is_in_flight(page: Page) -> None:
    """COPY_TO_BOX_BUSY: while a Save is in flight the button is disabled, and the box keeps
    the text being saved.
    """
    held = HeldRoute(page, API, method="POST")
    open_capture(page, viewports.DESKTOP)
    compose_box(page).fill("being saved")

    main(page).get_by_role("button", name="Save Capture", exact=True).click()

    expect(copy_to_box(page)).to_be_disabled()
    expect(compose_box(page)).to_have_value("being saved")
    held.fulfill_json(capture("being saved", "2026-11-15T09:31:00Z"), status=201)
    expect(copy_to_box(page)).to_be_enabled()


@pytest.mark.p1
def test_copy_writes_the_text_to_the_clipboard(page: Page, browser_name: str) -> None:
    """CLIPBOARD_OK: the clipboard holds the Capture's text; the label reads "Copied", then
    "Copy" again.
    """
    if browser_name != "chromium":
        pytest.skip("Reading the clipboard needs Chromium's clipboard permissions")
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    open_capture(page, viewports.DESKTOP)

    copy_button(page).click()

    expect(copy_button(page)).to_have_text(COPIED)
    assert page.evaluate("navigator.clipboard.readText()") == TEXT
    expect(copy_button(page)).to_have_text(COPY, timeout=5_000)


@pytest.mark.p1
def test_copy_falls_back_when_the_clipboard_api_refuses(page: Page, browser_name: str) -> None:
    """The async API rejects (as over plain http): the textarea fallback still puts the
    Capture's text on the clipboard, and the label reads "Copied".
    """
    if browser_name != "chromium":
        pytest.skip("Reading the clipboard needs Chromium's clipboard permissions")
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.add_init_script(
        """
        navigator.clipboard.writeText = () => Promise.reject(new Error("denied"));
        """
    )
    open_capture(page, viewports.DESKTOP)

    copy_button(page).click()

    expect(copy_button(page)).to_have_text(COPIED)
    assert page.evaluate("navigator.clipboard.readText()") == TEXT


@pytest.mark.p2
def test_a_failed_copy_says_so_without_an_alert(page: Page) -> None:
    """CLIPBOARD_FAILS: both the async API and execCommand fail; the label reads "Couldn't
    copy", then reverts, and no alert shows.
    """
    page.add_init_script(
        """
        Object.defineProperty(navigator, "clipboard", {
          value: { writeText: () => Promise.reject(new Error("denied")) },
        });
        document.execCommand = () => false;
        """
    )
    open_capture(page, viewports.DESKTOP)

    copy_button(page).click()

    expect(copy_button(page)).to_have_text(NOT_COPIED)
    expect(main(page).get_by_role("alert")).to_have_count(0)
    expect(copy_button(page)).to_have_text(COPY, timeout=5_000)


@pytest.mark.p1
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_custom_value_starts_with_the_capture_text_and_keeps_edits(
    page: Page, viewport: ViewportSize
) -> None:
    """CUSTOM_PREFILL and CUSTOM_KEPT in Capture detail."""
    open_capture(page, viewport)
    choice(page, "English").click()
    choice(page, "Vocabulary").click()

    pane(page).get_by_role("radio", name=CUSTOM_VALUE, exact=True).check()
    expect(custom_field(page)).to_have_value(TEXT)
    expect(write_it_myself(page)).to_be_enabled()

    custom_field(page).fill("jump to a conclusion")
    pane(page).get_by_role("radio", name=USE_AS_IS, exact=True).check()
    pane(page).get_by_role("radio", name=CUSTOM_VALUE, exact=True).check()
    expect(custom_field(page)).to_have_value("jump to a conclusion")


@pytest.mark.p1
def test_custom_value_starts_with_the_compose_text_at_captures_make(page: Page) -> None:
    """CUSTOM_PREFILL at /captures/make: the field holds the compose text."""
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill(f"  {TEXT}  ")
    main(page).locator(".compose-card").get_by_role("button", name=MAKE_AN_ITEM, exact=True).click()
    expect(page).to_have_url(path_pattern(MAKE_PATH))

    pane(page).get_by_role("radio", name=CUSTOM_VALUE, exact=True).check()
    expect(custom_field(page)).to_have_value(TEXT)

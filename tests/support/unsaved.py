"""The router's unsaved-changes guard and flash, driven from the page (AD-13, story 1.7).

The tests reach `setDirty`, `confirmLeave` and `navigate` by importing the real `router.js`
through its versioned URL: the same module instance `main.js` started, so no test-only hook.
"""

from collections.abc import Callable
from dataclasses import dataclass

from playwright.sync_api import Dialog, Locator, Page, ViewportSize, expect

from language_lab import __version__
from tests.support import viewports
from tests.support.navigation import (
    CAPTURES,
    EN_ITEMS,
    SETUP,
    Destination,
    go_by_nav,
    main_nav,
    menu_button,
    menu_sheet,
    screen_heading,
)

ROUTER_JS = f"/static/{__version__}/router.js"

ALERT_TITLE = "Discard unsaved changes?"
TARGET = "jump to conclusions"

# setDirty states. kind "draft" picks the Draft body; any other kind the counted one
DRAFT = {"kind": "draft", "count": 1, "target": TARGET}
EDITS = {"kind": "edits", "count": 2, "target": TARGET}

# The screen the guard is tested on. Reached by nav from Captures, so back has an entry.
DIRTY_SCREEN = EN_ITEMS

BACK_LINK_TEXT = "‹ Captures"
# Idempotent, so a test can take the back link more than once
_INJECT_BACK_LINK = """(text) => {
  if (document.querySelector("main > a.back-link")) return;
  const link = document.createElement("a");
  link.className = "back-link";
  link.href = "/captures";
  link.textContent = text;
  document.querySelector("main").prepend(link);
}"""

_SET_DIRTY = "async ({ url, state }) => (await import(url)).setDirty(state)"
_NAVIGATE = "async ({ url, path, options }) => (await import(url)).navigate(path, options)"
# confirmLeave() waits for an answer, so start it, answer, then read what it resolved to
_START_CONFIRM_LEAVE = (
    "async (url) => { window.__confirmLeave = (await import(url)).confirmLeave(); }"
)
_READ_CONFIRM_LEAVE = "() => window.__confirmLeave"


def set_dirty(page: Page, state: dict | None) -> None:
    page.evaluate(_SET_DIRTY, {"url": ROUTER_JS, "state": state})


def navigate(page: Page, path: str, **options: str) -> None:
    page.evaluate(_NAVIGATE, {"url": ROUTER_JS, "path": path, "options": options})


def start_confirm_leave(page: Page) -> None:
    page.evaluate(_START_CONFIRM_LEAVE, ROUTER_JS)


def confirm_leave_result(page: Page) -> object:
    return page.evaluate(_READ_CONFIRM_LEAVE)


def unsaved_alert(page: Page) -> Locator:
    return page.get_by_role("alertdialog")


def discard_button(page: Page) -> Locator:
    return unsaved_alert(page).get_by_role("button", name="Discard", exact=True)


def keep_editing_button(page: Page) -> Locator:
    return unsaved_alert(page).get_by_role("button", name="Keep editing", exact=True)


def open_dirty_screen(page: Page, viewport: ViewportSize, state: dict | None = EDITS) -> None:
    """Captures, then English Items by nav (a user gesture, and a history entry to go back to),
    then `setDirty(state)` there."""
    page.set_viewport_size(viewport)
    page.goto(CAPTURES.path)
    expect(screen_heading(page)).to_have_text(CAPTURES.heading)
    go_by_nav(page, DIRTY_SCREEN)
    expect(screen_heading(page)).to_have_text(DIRTY_SCREEN.heading)
    set_dirty(page, state)


def reload_collecting_dialogs(page: Page) -> list[str]:
    """Reload the page (`beforeunload` runs), accept any dialog, and return the dialog types seen.

    A reload, not `page.close(run_before_unload=True)`: under WebKit a served page never closes
    that way, prompt or not.
    """
    seen: list[str] = []

    def accept(dialog: Dialog) -> None:
        seen.append(dialog.type)
        dialog.accept()

    page.on("dialog", accept)
    page.reload()
    return seen


# Leave paths (R-03)


def _pill_to_setup(page: Page) -> None:
    main_nav(page).get_by_role("link", name=SETUP.area, exact=True).click()


def _menu_row_to_setup(page: Page) -> None:
    menu_button(page).click()
    menu_sheet(page).get_by_role("link", name=SETUP.area, exact=True).click()


def _back_link(page: Page) -> None:
    page.evaluate(_INJECT_BACK_LINK, BACK_LINK_TEXT)
    page.get_by_role("main").get_by_role("link", name=BACK_LINK_TEXT, exact=True).click()


def _browser_back(page: Page) -> None:
    page.go_back()


@dataclass(frozen=True)
class LeavePath:
    viewport: ViewportSize
    leave: Callable[[Page], None]
    target: Destination  # where the leave goes once discarded


# The ways off the dirty screen a user has at each width (EXPERIENCE "Unsaved changes")
LEAVE_PATHS = {
    "phone-menu-row": LeavePath(viewports.PHONE, _menu_row_to_setup, SETUP),
    "phone-back-link": LeavePath(viewports.PHONE, _back_link, CAPTURES),
    "phone-browser-back": LeavePath(viewports.PHONE, _browser_back, CAPTURES),
    "tablet-pill": LeavePath(viewports.TABLET, _pill_to_setup, SETUP),
    "tablet-back-link": LeavePath(viewports.TABLET, _back_link, CAPTURES),
    "tablet-browser-back": LeavePath(viewports.TABLET, _browser_back, CAPTURES),
    "desktop-pill": LeavePath(viewports.DESKTOP, _pill_to_setup, SETUP),
    "desktop-back-link": LeavePath(viewports.DESKTOP, _back_link, CAPTURES),
    "desktop-browser-back": LeavePath(viewports.DESKTOP, _browser_back, CAPTURES),
}

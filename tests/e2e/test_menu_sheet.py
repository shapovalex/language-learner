"""Story 1.6: the phone Menu bottom sheet (EXPERIENCE "Menu (phone)", a11y floor).

Decided 2026-10-11: the Menu button stays above the scrim and toggles the sheet closed, and the
Tab trap cycles through the sheet's rows only.

Skipped until router.js and the screens land. Un-skip one per task, watch it fail, then implement.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support import keys, viewports
from tests.support.navigation import (
    AREAS,
    CAPTURES,
    FR_ITEMS,
    FR_PRONUNCIATION,
    main_nav,
    menu_button,
    menu_sheet,
    path_pattern,
    screen_heading,
)

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 1.6: un-skip with the Menu sheet")


def tap_scrim(page: Page) -> None:
    """Tap just above the sheet, where only the scrim is (the sheet sits at the bottom)."""
    box = menu_sheet(page).bounding_box()
    assert box is not None, "the Menu sheet is not rendered"
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] - 24)


CLOSE_PATHS = {
    "esc": lambda page: page.keyboard.press("Escape"),
    "scrim": tap_scrim,
    "menu-button": lambda page: menu_button(page).click(),
}


@RED_PHASE
@pytest.mark.p1
def test_phone_menu_sheet_lists_areas_and_navigates(page: Page) -> None:
    """AC-3: on phone a Menu bottom sheet replaces the pills; a row navigates and closes it."""
    page.set_viewport_size(viewports.PHONE)
    page.goto(CAPTURES.path)

    expect(menu_button(page)).to_be_visible()
    expect(main_nav(page)).to_be_hidden()

    menu_button(page).click()
    sheet = menu_sheet(page)
    expect(sheet.get_by_role("link")).to_have_text(list(AREAS))
    expect(sheet.locator("[aria-current='page']")).to_have_text([CAPTURES.area])
    sheet.get_by_role("link", name=FR_ITEMS.area, exact=True).click()
    expect(page).to_have_url(path_pattern(FR_ITEMS.path))
    expect(screen_heading(page)).to_have_text(FR_ITEMS.heading)
    expect(sheet).to_be_hidden()


@RED_PHASE
@pytest.mark.p1
@pytest.mark.parametrize("close", CLOSE_PATHS.values(), ids=CLOSE_PATHS.keys())
def test_menu_sheet_traps_and_returns_focus(page: Page, browser_name: str, close) -> None:
    """AC-10: the Menu sheet takes focus to the current row, traps it, and returns it to Menu."""
    page.set_viewport_size(viewports.PHONE)
    page.goto(FR_PRONUNCIATION.path)
    menu_button(page).click()
    sheet = menu_sheet(page)

    expect(sheet.get_by_role("link", name=FR_PRONUNCIATION.area, exact=True)).to_be_focused()

    # French -> Setup -> wraps to Captures, the first row
    page.keyboard.press(keys.tab(browser_name))
    page.keyboard.press(keys.tab(browser_name))
    expect(sheet.get_by_role("link", name=CAPTURES.area, exact=True)).to_be_focused()
    close(page)
    expect(sheet).to_be_hidden()
    expect(menu_button(page)).to_be_focused()
    expect(menu_button(page)).to_have_attribute("aria-expanded", "false")
    expect(page).to_have_url(path_pattern(FR_PRONUNCIATION.path))

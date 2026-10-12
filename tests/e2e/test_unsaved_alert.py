"""Story 1.7: the router's unsaved-changes alert on every way off a dirty screen (AD-13, R-03).

Decided 2026-10-11: tests inject the back link (no screen has one yet); kind "draft" picks the
Draft body and any other kind the counted one; confirmLeave() resolves true at once when clean,
and Discard clears the dirty state.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.keys import shift_tab, tab
from tests.support.navigation import (
    CAPTURES,
    FR_ITEMS,
    SETUP,
    go_by_nav,
    main_nav,
    menu_button,
    path_pattern,
    screen_heading,
)
from tests.support.unsaved import (
    ALERT_TITLE,
    DIRTY_SCREEN,
    DRAFT,
    EDITS,
    LEAVE_PATHS,
    ROUTER_JS,
    TARGET,
    LeavePath,
    confirm_leave_result,
    discard_button,
    keep_editing_button,
    open_dirty_screen,
    reload_collecting_dialogs,
    set_dirty,
    start_confirm_leave,
    unsaved_alert,
)

leave_paths = pytest.mark.parametrize("path", LEAVE_PATHS.values(), ids=LEAVE_PATHS.keys())

BODY_VARIANTS = {
    "draft": (DRAFT, "This Draft isn't saved."),
    "edits-2": (EDITS, f"2 unsaved changes to “{TARGET}”"),
    "edits-1": ({**EDITS, "count": 1}, f"1 unsaved change to “{TARGET}”"),
    "preview-1": (
        {"kind": "preview", "count": 1, "target": TARGET},
        f"1 unsaved change to “{TARGET}”",
    ),
}


def click_setup_pill(page: Page) -> None:
    main_nav(page).get_by_role("link", name=SETUP.area, exact=True).click()


@pytest.mark.p1
def test_set_dirty_null_lets_leave_without_alert(page: Page) -> None:
    """AC-1: after setDirty(null), leaving the screen asks nothing."""
    open_dirty_screen(page, viewports.DESKTOP)
    set_dirty(page, None)

    click_setup_pill(page)

    expect(page).to_have_url(path_pattern(SETUP.path))
    expect(unsaved_alert(page)).to_have_count(0)
    expect(screen_heading(page)).to_have_text(SETUP.heading)


@pytest.mark.p1
def test_alert_is_one_labelled_alertdialog(page: Page) -> None:
    """AC-2: the unsaved alert is one role=alertdialog with a labelled title and description."""
    open_dirty_screen(page, viewports.DESKTOP)
    click_setup_pill(page)

    expect(page.get_by_role("alertdialog", name=ALERT_TITLE, exact=True)).to_have_count(1)
    alert = unsaved_alert(page)
    expect(alert).to_have_count(1)
    expect(alert).to_have_accessible_description(f"2 unsaved changes to “{TARGET}”")
    expect(alert.get_by_role("button")).to_have_text(["Discard", "Keep editing"])


@pytest.mark.p1
@pytest.mark.parametrize(("state", "body"), BODY_VARIANTS.values(), ids=BODY_VARIANTS.keys())
def test_alert_body_names_what_is_lost(page: Page, state: dict, body: str) -> None:
    """AC-3: the Draft body, or the counted body naming the target."""
    open_dirty_screen(page, viewports.DESKTOP, state)
    click_setup_pill(page)

    expect(unsaved_alert(page)).to_have_accessible_description(body)


@pytest.mark.p1
def test_alert_focuses_keep_editing(page: Page) -> None:
    """AC-4: focus starts on Keep editing, the safe default."""
    open_dirty_screen(page, viewports.DESKTOP)
    click_setup_pill(page)

    expect(keep_editing_button(page)).to_be_focused()


@pytest.mark.p1
@leave_paths
def test_escape_cancels_the_leave(page: Page, path: LeavePath) -> None:
    """AC-5: Esc closes the alert and the dirty screen stays, URL included."""
    open_dirty_screen(page, path.viewport)
    path.leave(page)
    unsaved_alert(page).wait_for()

    page.keyboard.press("Escape")

    expect(unsaved_alert(page)).to_be_hidden()
    expect(page).to_have_url(path_pattern(DIRTY_SCREEN.path))
    expect(screen_heading(page)).to_have_text(DIRTY_SCREEN.heading)


@pytest.mark.p1
@leave_paths
def test_every_leave_path_raises_the_alert(page: Page, path: LeavePath) -> None:
    """AC-6: pill, Menu row, back link and browser back all raise the alert while dirty."""
    open_dirty_screen(page, path.viewport)

    path.leave(page)

    expect(unsaved_alert(page)).to_be_visible()
    expect(page).to_have_url(path_pattern(DIRTY_SCREEN.path))


CONFIRM_LEAVE_CASES = {
    # (state, answer, resolves to, where the Setup pill then leads)
    "clean": (None, lambda page: None, True, SETUP.path),
    "discard": (EDITS, lambda page: discard_button(page).click(), True, SETUP.path),
    "keep-editing": (
        EDITS,
        lambda page: keep_editing_button(page).click(),
        False,
        DIRTY_SCREEN.path,
    ),
}


@pytest.mark.p1
@pytest.mark.parametrize(
    ("state", "answer", "resolved", "pill_leads_to"),
    CONFIRM_LEAVE_CASES.values(),
    ids=CONFIRM_LEAVE_CASES.keys(),
)
def test_confirm_leave_resolves_with_the_answer(
    page: Page, state: dict | None, answer, resolved: bool, pill_leads_to: str
) -> None:
    """AC-7: confirmLeave() is true when clean or on Discard, false on Keep editing."""
    open_dirty_screen(page, viewports.DESKTOP, state)
    start_confirm_leave(page)
    answer(page)

    assert confirm_leave_result(page) is resolved
    expect(unsaved_alert(page)).to_have_count(0)
    expect(page).to_have_url(path_pattern(DIRTY_SCREEN.path))
    # Discard cleared the dirty state; Keep editing kept it, so the pill raises the alert
    click_setup_pill(page)
    expect(page).to_have_url(path_pattern(pill_leads_to))


BEFOREUNLOAD_CASES = {"dirty": (EDITS, ["beforeunload"]), "clean": (None, [])}


@pytest.mark.p1
@pytest.mark.parametrize(
    ("state", "dialogs"), BEFOREUNLOAD_CASES.values(), ids=BEFOREUNLOAD_CASES.keys()
)
def test_beforeunload_only_while_dirty(page: Page, state: dict | None, dialogs: list[str]) -> None:
    """AC-8: unloading the page prompts while dirty, and not once setDirty(null) cleared it."""
    open_dirty_screen(page, viewports.DESKTOP)
    set_dirty(page, state)

    assert reload_collecting_dialogs(page) == dialogs


@pytest.mark.p1
@leave_paths
def test_keep_editing_stays_on_the_screen(page: Page, path: LeavePath) -> None:
    """AC-10: Keep editing returns to the dirty screen unchanged; browser back keeps the URL."""
    open_dirty_screen(page, path.viewport)
    path.leave(page)
    keep_editing_button(page).click()

    expect(unsaved_alert(page)).to_be_hidden()
    expect(page).to_have_url(path_pattern(DIRTY_SCREEN.path))
    expect(screen_heading(page)).to_have_text(DIRTY_SCREEN.heading)
    # Still dirty: the same leave asks again, through the one alert
    path.leave(page)
    expect(unsaved_alert(page)).to_have_count(1)


@pytest.mark.p1
@leave_paths
def test_discard_continues_the_leave(page: Page, path: LeavePath) -> None:
    """AC-11: Discard goes where the leave path was going, and the next leave asks nothing."""
    open_dirty_screen(page, path.viewport)
    path.leave(page)
    discard_button(page).click()

    expect(page).to_have_url(path_pattern(path.target.path))
    expect(unsaved_alert(page)).to_be_hidden()
    expect(screen_heading(page)).to_have_text(path.target.heading)
    go_by_nav(page, FR_ITEMS)
    expect(screen_heading(page)).to_have_text(FR_ITEMS.heading)


# Green-phase additions (plan matrix and acceptance)


@pytest.mark.p1
@pytest.mark.parametrize("viewport", viewports.ALL.values(), ids=viewports.ALL.keys())
def test_tab_stays_within_the_alert(page: Page, browser_name: str, viewport) -> None:
    """AC-2: while the alert is open, Tab and Shift+Tab only reach Discard and Keep editing."""
    open_dirty_screen(page, viewport)
    page.go_back()
    expect(keep_editing_button(page)).to_be_focused()

    for key, focused in [
        (tab(browser_name), discard_button),
        (tab(browser_name), keep_editing_button),
        (shift_tab(browser_name), discard_button),
        (shift_tab(browser_name), keep_editing_button),
    ]:
        page.keyboard.press(key)
        expect(focused(page)).to_be_focused()


FOCUS_RETURN_CASES = {
    "desktop-pill": (
        LEAVE_PATHS["desktop-pill"],
        lambda page: main_nav(page).get_by_role("link", name=SETUP.area, exact=True),
    ),
    "phone-menu-row": (LEAVE_PATHS["phone-menu-row"], menu_button),
    "desktop-back-link": (
        LEAVE_PATHS["desktop-back-link"],
        lambda page: page.locator("main > a.back-link"),
    ),
}


@pytest.mark.p2
@pytest.mark.parametrize(
    ("path", "control"), FOCUS_RETURN_CASES.values(), ids=FOCUS_RETURN_CASES.keys()
)
def test_keep_editing_returns_focus_to_the_leave_control(
    page: Page, path: LeavePath, control
) -> None:
    """AC-10: Keep editing puts focus back on the control that started the leave."""
    open_dirty_screen(page, path.viewport)
    path.leave(page)
    keep_editing_button(page).click()

    expect(control(page)).to_be_focused()


@pytest.mark.p2
def test_back_after_keep_editing_needs_one_press(page: Page) -> None:
    """AC-10: Keep editing on browser back leaves no duplicate entry; the next back and Discard
    land on Captures at once."""
    open_dirty_screen(page, viewports.DESKTOP)
    page.go_back()
    keep_editing_button(page).click()
    expect(page).to_have_url(path_pattern(DIRTY_SCREEN.path))

    page.go_back()
    discard_button(page).click()

    expect(page).to_have_url(path_pattern(CAPTURES.path))
    expect(screen_heading(page)).to_have_text(CAPTURES.heading)
    expect(unsaved_alert(page)).to_be_hidden()


@pytest.mark.p2
def test_second_leave_shares_the_open_alert(page: Page) -> None:
    """AC-7: confirmLeave() while the alert is open gets the same pending answer, one alert."""
    open_dirty_screen(page, viewports.DESKTOP)
    page.evaluate(
        """async (url) => {
          const { confirmLeave } = await import(url);
          window.__first = confirmLeave();
          window.__second = confirmLeave();
          window.__same = window.__first === window.__second;
        }""",
        ROUTER_JS,
    )
    expect(unsaved_alert(page)).to_have_count(1)
    assert page.evaluate("() => window.__same") is True

    keep_editing_button(page).click()

    assert page.evaluate("() => Promise.all([window.__first, window.__second])") == [False, False]


@pytest.mark.p2
def test_flash_on_a_cancelled_navigate_is_dropped(page: Page) -> None:
    """AC-9: a flash handed to navigate() that Keep editing cancels is never shown."""
    flash = "Saved, but this should never show."
    open_dirty_screen(page, viewports.DESKTOP)
    # Not awaited: navigate() waits for the alert's answer
    page.evaluate(
        "async ({ url, flash }) => { (await import(url)).navigate('/setup', { flash }); }",
        {"url": ROUTER_JS, "flash": flash},
    )
    keep_editing_button(page).click()

    expect(page).to_have_url(path_pattern(DIRTY_SCREEN.path))
    set_dirty(page, None)
    click_setup_pill(page)
    expect(screen_heading(page)).to_have_text(SETUP.heading)
    expect(page.get_by_text(flash)).to_have_count(0)

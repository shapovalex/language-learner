"""Story 1.7: the router's unsaved-changes alert on every way off a dirty screen (AD-13, R-03).

Decided 2026-10-11: tests inject the back link (no screen has one yet); kind "draft" picks the
Draft body and any other kind the counted one; confirmLeave() resolves true at once when clean,
and Discard clears the dirty state.

Skipped until router.js has the guard. Un-skip one per task, watch it fail, then implement.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.navigation import (
    FR_ITEMS,
    SETUP,
    go_by_nav,
    main_nav,
    path_pattern,
    screen_heading,
)
from tests.support.unsaved import (
    ALERT_TITLE,
    DIRTY_SCREEN,
    DRAFT,
    EDITS,
    LEAVE_PATHS,
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

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.7: un-skip with the guard in router.js"
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


@RED_PHASE
@pytest.mark.p1
def test_set_dirty_null_lets_leave_without_alert(page: Page) -> None:
    """AC-1: after setDirty(null), leaving the screen asks nothing."""
    open_dirty_screen(page, viewports.DESKTOP)
    set_dirty(page, None)

    click_setup_pill(page)

    expect(page).to_have_url(path_pattern(SETUP.path))
    expect(unsaved_alert(page)).to_have_count(0)
    expect(screen_heading(page)).to_have_text(SETUP.heading)


@RED_PHASE
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


@RED_PHASE
@pytest.mark.p1
@pytest.mark.parametrize(("state", "body"), BODY_VARIANTS.values(), ids=BODY_VARIANTS.keys())
def test_alert_body_names_what_is_lost(page: Page, state: dict, body: str) -> None:
    """AC-3: the Draft body, or the counted body naming the target."""
    open_dirty_screen(page, viewports.DESKTOP, state)
    click_setup_pill(page)

    expect(unsaved_alert(page)).to_have_accessible_description(body)


@RED_PHASE
@pytest.mark.p1
def test_alert_focuses_keep_editing(page: Page) -> None:
    """AC-4: focus starts on Keep editing, the safe default."""
    open_dirty_screen(page, viewports.DESKTOP)
    click_setup_pill(page)

    expect(keep_editing_button(page)).to_be_focused()


@RED_PHASE
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


@RED_PHASE
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


@RED_PHASE
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


@RED_PHASE
@pytest.mark.p1
@pytest.mark.parametrize(
    ("state", "dialogs"), BEFOREUNLOAD_CASES.values(), ids=BEFOREUNLOAD_CASES.keys()
)
def test_beforeunload_only_while_dirty(page: Page, state: dict | None, dialogs: list[str]) -> None:
    """AC-8: unloading the page prompts while dirty, and not once setDirty(null) cleared it."""
    open_dirty_screen(page, viewports.DESKTOP)
    set_dirty(page, state)

    assert reload_collecting_dialogs(page) == dialogs


@RED_PHASE
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


@RED_PHASE
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

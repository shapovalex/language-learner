"""Story 1.7: navigate(path, { flash }) carries a one-shot message to the next screen (AD-13).

Decided 2026-10-11: router.js renders the flash as a role="status" banner in main, after the
next screen mounts, and removes it on the next navigation.

Skipped until router.js has the flash. Un-skip it, watch it fail, then implement.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support.navigation import CAPTURES, SETUP, go_by_nav, screen_heading
from tests.support.unsaved import TARGET, navigate

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.7: un-skip with the flash in router.js"
)

# The post-Save banner text (EXPERIENCE "Saved from a Capture")
FLASH = f"Saved “{TARGET}” to Anki. Make another Item from this Capture, or delete it."


@RED_PHASE
@pytest.mark.p1
def test_flash_shows_once_then_goes(page: Page) -> None:
    """AC-9: the flash shows on the screen navigated to, and is gone after the next navigation."""
    page.goto(CAPTURES.path)
    expect(screen_heading(page)).to_have_text(CAPTURES.heading)

    navigate(page, SETUP.path, flash=FLASH)

    flash = page.get_by_role("main").get_by_role("status").filter(has_text=FLASH)
    expect(flash).to_have_text(FLASH)
    expect(screen_heading(page)).to_have_text(SETUP.heading)
    go_by_nav(page, CAPTURES)
    expect(flash).to_have_count(0)
    go_by_nav(page, SETUP)
    expect(screen_heading(page)).to_have_text(SETUP.heading)
    expect(flash).to_have_count(0)

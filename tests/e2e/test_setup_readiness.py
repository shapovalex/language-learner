"""Story 2.1: the Setup screen's readiness tiles (FR-5; EXPERIENCE.md Setup, J5).

While /api/setup/readiness is pending the screen shows a skeleton. Then it shows one tile per
check, each failing tile followed by its fix hint (`role="alert"`), and a subtitle naming the
Prefix the server reports. The copy is the mockups' (S-Setup, S-SetupStates). The AnkiConnect
and Azure hints follow the OpenRouter one, which is the only hint mocked.

The browser stubs the readiness call, so this checks rendering only; the per-check logic is in
tests/api/test_setup_readiness.py.

Skipped until setup.js renders the tiles. Un-skip it, watch it fail, then implement.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support.network import HeldRoute

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 2.1: un-skip with the readiness tiles")

READINESS = "/api/setup/readiness"
PREFIX = "LanguageLabDev"  # not the default, so a hard-coded "LanguageLab" can't pass

SKELETON_LABEL = "Checking Anki and your keys…"
SUBTITLE = (
    f"Creates or repairs everything LanguageLab manages under the prefix {PREFIX}. "
    "Safe to run again."
)
READINESS_HEADING = "Ready to go?"
OPENROUTER_FIX = (
    "Add your OpenRouter key to the LanguageLab configuration on the Mac mini, "
    "restart LanguageLab, then reload this page."
)


@RED_PHASE
@pytest.mark.p1
def test_setup_shows_a_skeleton_then_one_tile_per_check(page: Page) -> None:
    """AC-6: skeleton, then three tiles, a fix hint for the failing one, and the Prefix."""
    readiness = HeldRoute(page, READINESS)
    page.goto("/setup")
    main = page.get_by_role("main")
    skeleton = main.get_by_role("status").filter(has_text=SKELETON_LABEL)

    expect(skeleton).to_be_visible()

    readiness.fulfill_json(
        {
            "prefix": PREFIX,
            "checks": [
                {"id": "ankiConnect", "ok": True},
                {"id": "azure", "ok": True},
                {"id": "openrouter", "ok": False},
            ],
        }
    )
    tiles = main.get_by_role("list", name=READINESS_HEADING).get_by_role("listitem")
    expect(tiles).to_have_count(3)
    expect(tiles).to_contain_text(
        ["AnkiConnect reachable", "Azure configured", "OpenRouter not configured"]
    )
    expect(main.get_by_role("alert")).to_have_text(OPENROUTER_FIX)
    expect(main.get_by_text(SUBTITLE, exact=True)).to_be_visible()
    expect(skeleton).to_have_count(0)

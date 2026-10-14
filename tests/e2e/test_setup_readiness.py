"""Story 2.1: the Setup screen's readiness tiles (FR-5; EXPERIENCE.md Setup, J5).

While /api/setup/readiness is pending the screen shows a skeleton. Then it shows one tile per
check, each failing tile followed by its fix hint (`role="alert"`), and a subtitle naming the
Prefix the server reports. The copy is the mockups' (S-Setup, S-SetupStates). The AnkiConnect
and Azure hints follow the OpenRouter one, which is the only hint mocked.

The browser stubs the readiness call, so this checks rendering only; the per-check logic is in
tests/api/test_setup_readiness.py.
The live server injects FakeAnkiStore() (tests/support/live_server.py), so the unstubbed test
sees AnkiConnect reachable without a real Anki.
"""

import pytest
from playwright.sync_api import Page, expect

from language_lab import __version__
from tests.support.live_server import LiveServer
from tests.support.network import HeldRoute, stub_api_error

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


@pytest.mark.p1
def test_setup_shows_three_passing_tiles_against_the_live_server(
    page: Page, live_server: LiveServer
) -> None:
    """AC-6: unstubbed, with every check passing, three tiles show and no fix hint does."""
    # The in-process server, not --base-url: the expected Prefix comes from its settings
    page.goto(f"{live_server.url}/setup")
    main = page.get_by_role("main")

    tiles = main.get_by_role("list", name=READINESS_HEADING).get_by_role("listitem")
    expect(tiles).to_have_count(3)
    expect(tiles).to_have_text(
        ["AnkiConnect reachable", "Azure configured", "OpenRouter configured"]
    )
    expect(main.get_by_role("alert")).to_have_count(0)
    prefix = live_server.settings.anki_prefix
    expect(main.get_by_text(f"under the prefix {prefix}.")).to_be_visible()


@pytest.mark.p2
def test_setup_shows_the_error_message_when_readiness_fails(page: Page) -> None:
    """AC-6: a readiness error envelope replaces the tiles with its message; the version stays."""
    envelope = stub_api_error(
        page,
        READINESS,
        status=503,
        code="anki_busy",
        message="Anki is busy. Try again in a moment.",
    )
    page.goto("/setup")
    main = page.get_by_role("main")

    expect(main.get_by_role("alert")).to_have_text(envelope["error"]["message"])
    expect(main.get_by_role("list", name=READINESS_HEADING)).to_have_count(0)
    expect(main.get_by_role("status").filter(has_text=SKELETON_LABEL)).to_have_count(0)
    expect(main.get_by_text(f"LanguageLab v{__version__}")).to_be_visible()

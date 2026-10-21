"""Story 2.8: the `newer_schema` blocking alert on the Setup screen (AD-19).

Decided 2026-10-14 (epic notes): when Anki was set up by a newer LanguageLab, Setup shows a
blocking inline alert, "Anki was set up by a newer LanguageLab. Install the latest release.",
in the failing readiness tile's visual pattern, with Apply hidden. Decided with the user
(2026-10-21): the alert takes the change list's place.

The screen learns the state from GET /api/setup/plan's `"state"`. The browser stubs readiness,
the plan and the apply status, so this checks rendering only. The states are in
tests/integration/test_anki_setup_state.py and the route in tests/api/test_setup_state.py.
"""

from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.support.network import stub_api_json

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.8: un-skip with the newer_schema alert in setup.js"
)

READINESS = "/api/setup/readiness"
PLAN = "/api/setup/plan"
STATUS = "/api/setup/apply/status"
PREFIX = "LanguageLabDev"  # not the default, so a hard-coded "LanguageLab" can't pass

NEWER_SCHEMA = "Anki was set up by a newer LanguageLab. Install the latest release."
APPLY_LABEL = "Apply setup"
CHANGES_HEADING = "What will change in Anki"


def readiness() -> dict[str, Any]:
    return {
        "prefix": PREFIX,
        "checks": [
            {"id": "ankiConnect", "ok": True},
            {"id": "azure", "ok": True},
            {"id": "openrouter", "ok": True},
        ],
    }


# A newer release's fields read as a Migrate row: the plan has items, so Apply would show
ITEMS = [{"action": "migrate", "kind": "noteType", "name": f"{PREFIX} English Vocabulary"}]


@RED_PHASE
@pytest.mark.p0
def test_newer_schema_shows_the_blocking_alert_in_place_of_the_change_list(page: Page) -> None:
    """AC-12: the alert replaces the change list, and Apply setup is hidden."""
    stub_api_json(page, READINESS, readiness())
    stub_api_json(
        page,
        PLAN,
        {
            "prefix": PREFIX,
            "planHash": "0" * 64,
            "state": "newer_schema",
            "items": ITEMS,
            "unmanaged": [],
        },
    )
    stub_api_json(page, STATUS, {"state": "idle", "result": None})
    page.goto("/setup")
    main = page.get_by_role("main")

    expect(main.get_by_role("alert").filter(has_text=NEWER_SCHEMA)).to_be_visible()
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_have_count(0)
    expect(main.get_by_role("list", name=CHANGES_HEADING)).to_have_count(0)

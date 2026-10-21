"""Story 2.8: the `newer_schema` blocking alert on the Setup screen (AD-19).

Decided 2026-10-14 (epic notes): when Anki was set up by a newer LanguageLab, Setup shows a
blocking inline alert, "Anki was set up by a newer LanguageLab. Install the latest release.",
in the failing readiness tile's visual pattern, with Apply hidden. Decided with the user
(2026-10-21): the alert takes the change list's place.

The screen learns the state from GET /api/setup/plan's `"state"`. The browser stubs readiness,
the plan and the apply status, so this checks rendering only. The states are in
tests/integration/test_anki_setup_state.py and the route in tests/api/test_setup_state.py.
"""

import json
from typing import Any

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support.network import stub_api_error, stub_api_json

READINESS = "/api/setup/readiness"
PLAN = "/api/setup/plan"
STATUS = "/api/setup/apply/status"
APPLY = "/api/setup/apply"
PREFIX = "LanguageLabDev"  # not the default, so a hard-coded "LanguageLab" can't pass

NEWER_SCHEMA = "Anki was set up by a newer LanguageLab. Install the latest release."
APPLY_LABEL = "Apply setup"
CHANGES_HEADING = "What will change in Anki"


FIX_REASON = "Fix the failing check to continue."
PLAN_HASH = "0" * 64


def readiness(*, anki_ok: bool = True) -> dict[str, Any]:
    return {
        "prefix": PREFIX,
        "checks": [
            {"id": "ankiConnect", "ok": anki_ok},
            {"id": "azure", "ok": True},
            {"id": "openrouter", "ok": True},
        ],
    }


# A newer release's fields read as a Migrate row: the plan has items, so Apply would show
ITEMS = [{"action": "migrate", "kind": "noteType", "name": f"{PREFIX} English Vocabulary"}]


def newer_schema_plan() -> dict[str, Any]:
    return {
        "prefix": PREFIX,
        "planHash": PLAN_HASH,
        "state": "newer_schema",
        "items": ITEMS,
        "unmanaged": [],
    }


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


@pytest.mark.p1
def test_newer_schema_with_a_failing_check_still_hides_apply_and_its_reason(page: Page) -> None:
    """AC-12: a failing readiness check doesn't bring back Apply or "Fix the failing check"."""
    stub_api_json(page, READINESS, readiness(anki_ok=False))
    stub_api_json(page, PLAN, newer_schema_plan())
    stub_api_json(page, STATUS, {"state": "idle", "result": None})
    page.goto("/setup")
    main = page.get_by_role("main")

    expect(main.get_by_role("alert").filter(has_text=NEWER_SCHEMA)).to_be_visible()
    expect(main.get_by_text("AnkiConnect not reachable")).to_be_visible()
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_have_count(0)
    expect(main.get_by_text(FIX_REASON)).to_have_count(0)


@pytest.mark.p1
def test_newer_schema_shows_the_alert_over_a_finished_apply(page: Page) -> None:
    """AC-12: coming back with a finished apply of the same hash still shows the alert."""
    result = {"verified": False, "planHash": PLAN_HASH, "discrepancies": ITEMS}
    stub_api_json(page, READINESS, readiness())
    stub_api_json(page, PLAN, newer_schema_plan())
    stub_api_json(page, STATUS, {"state": "finished", "result": result})
    page.goto("/setup")
    main = page.get_by_role("main")

    expect(main.get_by_role("alert").filter(has_text=NEWER_SCHEMA)).to_be_visible()
    expect(main.get_by_role("button", name="Run Setup again")).to_have_count(0)
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_have_count(0)


@pytest.mark.p1
def test_apply_refused_as_setup_required_rereads_the_plan_and_shows_the_alert(
    page: Page,
) -> None:
    """AC-12: a stale page whose apply is 409 `setup_required` re-reads the plan, and its
    `newer_schema` state brings up the alert with Apply hidden.
    """
    plans = [{**newer_schema_plan(), "state": "needs_migration"}]

    def answer_plan(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(plans[-1]))

    stub_api_json(page, READINESS, readiness())
    page.route(f"**{PLAN}", answer_plan)
    stub_api_json(page, STATUS, {"state": "idle", "result": None})
    stub_api_error(page, APPLY, status=409, code="setup_required")
    page.goto("/setup")
    main = page.get_by_role("main")
    apply_button = main.get_by_role("button", name=APPLY_LABEL)
    expect(apply_button).to_be_enabled()
    plans.append(newer_schema_plan())  # a newer release set Anki up after the preview

    apply_button.click()

    expect(main.get_by_role("alert").filter(has_text=NEWER_SCHEMA)).to_be_visible()
    expect(apply_button).to_have_count(0)
    expect(main.get_by_role("list", name=CHANGES_HEADING)).to_have_count(0)

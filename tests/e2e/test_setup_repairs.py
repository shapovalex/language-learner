"""Story 2.11: opt-in repair rows on the Setup screen (AD-3, FR-6).

- **The rows.** Below the change list (or the "Nothing to change" callout), an "Optional
  repairs" card lists the plan's `repairs`, one row per resource, each with a checkbox,
  unchecked, and "Nothing here changes unless you check it." (default copy; not in the UX
  docs). Its list is labelled by its heading, as the other Setup cards' lists are. It stays
  apart from the read-only "Not managed by LanguageLab" rows.
- **Checking.** Toggling a box re-reads GET /api/setup/plan with every checked key as a
  `repair` query parameter, and Apply setup posts that plan's `planHash` with the checked keys
  as `repairs` (decided with the user, 2026-10-21). Apply setup shows when the plan has an item
  or a box is checked.

The browser stubs readiness, the plan and the apply status, so this checks rendering and the
requests only. The routes are in tests/api/test_setup_repairs.py.
"""

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support.network import stub_api_json
from tests.support.setup_screen import (
    APPLY,
    APPLY_LABEL,
    IDLE,
    PLAN_HASH,
    PREFIX,
    READINESS,
    STATUS,
    readiness,
)

PLAN = re.compile(r".*/api/setup/plan(\?.*)?$")
VOCABULARY = f"{PREFIX} English Vocabulary"
CAPTURE = f"{PREFIX} Capture"

REPAIRS_HEADING = "Optional repairs"
REPAIRS_HINT = "Nothing here changes unless you check it."
UNMANAGED_HEADING = "Not managed by LanguageLab"

MEDIA = f"{PREFIX}_00000000-0000-4000-8000-000000000001_0123456789ab.mp3"
REPAIRS = [
    {"key": f"orphanMedia:{MEDIA}", "action": "repair", "kind": "orphanMedia", "name": MEDIA},
    {
        "key": "misplacedCard:1792093019101",
        "action": "repair",
        "kind": "misplacedCard",
        "name": "1792093019101",
        "noteType": VOCABULARY,
        "card": "Produce",
        "deck": f"{PREFIX}::Study::English::Vocabulary::Understand",
        "expectedDeck": f"{PREFIX}::Study::English::Vocabulary::Produce",
    },
    {
        "key": "unsuspendedCard:1792093019102",
        "action": "repair",
        "kind": "unsuspendedCard",
        "name": "1792093019102",
        "noteType": CAPTURE,
        "card": "Capture",
        "deck": f"{PREFIX}::Captures",
    },
]


def checked_hash(checked: list[str]) -> str:
    """A stand-in plan hash per selection: the screen must post the one the server answered."""
    return PLAN_HASH if not checked else str(len(checked)) * 64


def plan_for(url: str) -> dict[str, Any]:
    checked = parse_qs(urlparse(url).query).get("repair", [])
    return {
        "prefix": PREFIX,
        "planHash": checked_hash(checked),
        "state": "ready",
        "items": [],
        "repairs": [{**row, "checked": row["key"] in checked} for row in REPAIRS],
        "unmanaged": [{"kind": "deck", "name": f"{PREFIX}::Old"}],
    }


def open_setup(page: Page) -> tuple[Any, list[str]]:
    """Setup with every check passing and a plan of repairs only; returns (main, plan URLs)."""
    plan_urls: list[str] = []

    def answer_plan(route: Route) -> None:
        plan_urls.append(route.request.url)
        route.fulfill(content_type="application/json", body=json.dumps(plan_for(route.request.url)))

    stub_api_json(page, READINESS, readiness(full_sync_ok=True))
    page.route(PLAN, answer_plan)
    stub_api_json(page, STATUS, IDLE)
    page.goto("/setup")
    return page.get_by_role("main"), plan_urls


@pytest.mark.p0
def test_each_opt_in_repair_shows_with_an_unchecked_checkbox(page: Page) -> None:
    """AC-5: the Optional repairs card lists one row per repair, each with an unchecked box,
    apart from the read-only Not managed rows, and no Apply until one is checked.
    """
    main, _ = open_setup(page)
    repairs = main.get_by_role("list", name=REPAIRS_HEADING)

    expect(repairs.get_by_role("checkbox")).to_have_count(len(REPAIRS))
    for box in repairs.get_by_role("checkbox").all():
        expect(box).not_to_be_checked()
    expect(main.get_by_text(REPAIRS_HINT)).to_be_visible()
    expect(repairs.get_by_text(MEDIA, exact=False)).to_be_visible()
    expect(repairs.get_by_text(REPAIRS[1]["expectedDeck"], exact=False)).to_be_visible()
    unmanaged = main.get_by_role("list", name=UNMANAGED_HEADING)
    expect(unmanaged.get_by_role("checkbox")).to_have_count(0)
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_have_count(0)


@pytest.mark.p0
def test_checking_a_repair_replans_and_apply_posts_it_with_the_new_hash(page: Page) -> None:
    """AC-12: checking a box re-reads the plan with `?repair=<key>`, and Apply setup posts
    that plan's hash with the checked key.
    """
    verified = {"verified": True, "planHash": "f" * 64, "discrepancies": []}
    stub_api_json(page, APPLY, {**verified, "fullSyncRequired": False})
    main, plan_urls = open_setup(page)
    media_key = REPAIRS[0]["key"]

    main.get_by_role("list", name=REPAIRS_HEADING).get_by_role("checkbox").first.check()
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith(APPLY)) as posted:
        main.get_by_role("button", name=APPLY_LABEL).click()

    assert posted.value.post_data_json == {
        "planHash": checked_hash([media_key]),
        "repairs": [media_key],
    }
    assert any(parse_qs(urlparse(u).query).get("repair") == [media_key] for u in plan_urls)


@pytest.mark.p1
def test_unchecking_a_repair_replans_without_it_and_hides_apply_again(page: Page) -> None:
    """AC-12: unchecking re-reads the plan without the key, and with no items and nothing
    checked Apply setup is hidden again.
    """
    main, _ = open_setup(page)
    box = main.get_by_role("list", name=REPAIRS_HEADING).get_by_role("checkbox").first
    box.check()
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_be_enabled()

    with page.expect_request(PLAN) as reread:
        box.uncheck()

    assert parse_qs(urlparse(reread.value.url).query).get("repair") is None
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_have_count(0)
    expect(box).not_to_be_checked()


@pytest.mark.p1
def test_run_setup_again_retries_the_checked_repairs_that_failed(page: Page) -> None:
    """AC-10: a run whose checked repair didn't take lists it as a discrepancy, and Run Setup
    again posts the result's hash with that repair's key (not with the required items alone).
    """
    card = REPAIRS[2]
    left_over = "7" * 64
    failed = {"action": "repair", "kind": card["kind"], "name": card["name"]}
    stub_api_json(
        page,
        APPLY,
        {
            "verified": False,
            "planHash": left_over,
            "discrepancies": [{**failed, "requiresFullSync": False}],
            "fullSyncRequired": False,
        },
    )
    main, _ = open_setup(page)
    main.get_by_role("list", name=REPAIRS_HEADING).get_by_role("checkbox").nth(2).check()
    main.get_by_role("button", name=APPLY_LABEL).click()

    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith(APPLY)) as again:
        main.get_by_role("button", name="Run Setup again").click()

    assert again.value.post_data_json == {"planHash": left_over, "repairs": [card["key"]]}

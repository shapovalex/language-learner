"""Story 2.7: Apply setup and its result on the Setup screen (FR-6; EXPERIENCE.md Setup, Buttons,
Progress card, Verification banner, State Patterns, J5; mockups S-SetupStates).

Apply setup is the readiness card's Primary. It shows once readiness and the plan have arrived,
only when the plan has items, and is disabled with "Fix the failing check to continue." while
any readiness check fails. A click POSTs `{"planHash"}` to /api/setup/apply.

While the run is pending, the progress card "Applying setup and verifying… Keep Anki open."
replaces the change list and Apply stays disabled. The verification then shows as one of two
banners:

- verified: "Setup applied and verified" (`role="status"`);
- discrepancies: "Setup applied, but N things don't match" (`role="alert"`), with one row per
  discrepancy, expected vs. found, and Run Setup again, which POSTs the result's `planHash`.

Leaving does not cancel the run. Decided with the user (2026-10-21): coming back, the screen
reads GET /api/setup/apply/status. It shows the progress card while the run is `running`
(polling until it is finished), the result while Anki still matches it, and the current change
list otherwise.

The browser stubs readiness, the plan, the apply and its status, so this checks rendering only.
The apply logic is in tests/integration/test_anki_setup_apply.py and the routes in
tests/api/test_setup_apply.py.
"""

import json
from typing import Any

import pytest
from playwright.sync_api import Locator, Page, Route, expect

from tests.support.navigation import CAPTURES, SETUP, go_by_nav
from tests.support.network import HeldRoute, record_json_bodies, stub_api_error, stub_api_json

READINESS = "/api/setup/readiness"
PLAN = "/api/setup/plan"
APPLY = "/api/setup/apply"
STATUS = "/api/setup/apply/status"
PREFIX = "LanguageLabDev"  # not the default, so a hard-coded "LanguageLab" can't pass
PLAN_HASH = "0" * 64
LEFT_OVER_HASH = "1" * 64
EMPTY_HASH = "2" * 64  # stands in for plan_hash(()): the screen only compares hashes

APPLY_LABEL = "Apply setup"
FIX_REASON = "Fix the failing check to continue."
PROGRESS = "Applying setup and verifying… Keep Anki open."
VERIFIED_TITLE = "Setup applied and verified"
VERIFIED_DETAIL = "Decks, note types, templates and deck options match what LanguageLab expects."
DISCREPANCY_EXPLANATION = "Anki was changed. Review the difference below, then run Setup again."
RUN_AGAIN = "Run Setup again"
CHANGES_HEADING = "What will change in Anki"

PRESET_FOUND = (
    "Expected sibling burying off on every Study and Pronunciation deck; "
    "found it on, or a deck on another preset."
)
DECK_FOUND = "Expected this deck; found none."


def readiness(*, anki_connect: bool = True) -> dict[str, Any]:
    return {
        "prefix": PREFIX,
        "checks": [
            {"id": "ankiConnect", "ok": anki_connect},
            {"id": "azure", "ok": True},
            {"id": "openrouter", "ok": True},
        ],
    }


def item(action: str, kind: str, name: str) -> dict[str, str]:
    return {"action": action, "kind": kind, "name": name}


ITEMS = [
    item("create", "deck", f"{PREFIX}::Study::French"),
    item("repair", "templates", f"{PREFIX} French Sentence"),
    item("repair", "preset", PREFIX),
]
DISCREPANCIES = [
    item("repair", "preset", PREFIX),
    item("create", "deck", f"{PREFIX}::Study::French"),
]


def plan(items: list[dict[str, str]], plan_hash: str = PLAN_HASH) -> dict[str, Any]:
    return {"prefix": PREFIX, "planHash": plan_hash, "items": items, "unmanaged": []}


def result(discrepancies: list[dict[str, str]], plan_hash: str) -> dict[str, Any]:
    return {"verified": not discrepancies, "planHash": plan_hash, "discrepancies": discrepancies}


IDLE = {"state": "idle", "result": None}
RUNNING = {"state": "running", "result": None}


class Stub:
    """Answers every GET to `path` with `body`, which the test may change between requests."""

    def __init__(self, page: Page, path: str, body: Any) -> None:
        self.body = body
        page.route(f"**{path}", self._fulfill)

    def _fulfill(self, route: Route) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(self.body))


def open_setup(
    page: Page, plan_body: dict[str, Any], *, anki_connect: bool = True, status: Any = IDLE
) -> Locator:
    stub_api_json(page, READINESS, readiness(anki_connect=anki_connect))
    stub_api_json(page, PLAN, plan_body)
    stub_api_json(page, STATUS, status)
    page.goto("/setup")
    return page.get_by_role("main")


@pytest.mark.p0
def test_apply_is_disabled_with_a_reason_while_a_readiness_check_fails(page: Page) -> None:
    """AC-10: Apply setup is disabled, with "Fix the failing check to continue." beside it."""
    main = open_setup(page, plan(ITEMS), anki_connect=False)

    expect(main.get_by_role("button", name=APPLY_LABEL)).to_be_disabled()
    expect(main.get_by_text(FIX_REASON, exact=True)).to_be_visible()
    expect(main.get_by_role("list", name=CHANGES_HEADING)).to_be_visible()


@pytest.mark.p0
def test_apply_posts_the_plan_hash_and_shows_the_applying_card(page: Page) -> None:
    """AC-11: while the run is pending, the progress card replaces the list; Apply is disabled."""
    held = HeldRoute(page, APPLY)
    bodies = record_json_bodies(page, APPLY)
    main = open_setup(page, plan(ITEMS))
    apply_button = main.get_by_role("button", name=APPLY_LABEL)

    apply_button.click()

    expect(main.get_by_text(PROGRESS, exact=True)).to_be_visible()
    expect(main.get_by_role("status").filter(has_text=PROGRESS)).to_be_visible()
    assert bodies == [{"planHash": PLAN_HASH, "repairs": []}]
    expect(apply_button).to_be_disabled()
    expect(main.get_by_role("list", name=CHANGES_HEADING)).to_have_count(0)
    held.fulfill_json(result([], EMPTY_HASH))


@pytest.mark.p0
def test_a_verified_run_shows_the_verified_banner(page: Page) -> None:
    """AC-12: "Setup applied and verified" replaces the change list; Apply setup is gone."""
    main = open_setup(page, plan(ITEMS))
    stub_api_json(page, APPLY, result([], EMPTY_HASH))

    main.get_by_role("button", name=APPLY_LABEL).click()

    expect(main.get_by_text(VERIFIED_TITLE, exact=True)).to_be_visible()
    banner = main.get_by_role("status").filter(has_text=VERIFIED_TITLE)
    expect(banner).to_contain_text(VERIFIED_DETAIL)
    expect(main.get_by_role("list", name=CHANGES_HEADING)).to_have_count(0)
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_have_count(0)
    expect(main.get_by_role("alert")).to_have_count(0)


@pytest.mark.p1
@pytest.mark.parametrize(
    ("count", "title"),
    [
        (1, "Setup applied, but 1 thing doesn't match"),
        (2, "Setup applied, but 2 things don't match"),
    ],
    ids=["one", "two"],
)
def test_a_run_with_discrepancies_lists_them_and_offers_run_setup_again(
    page: Page, count: int, title: str
) -> None:
    """AC-13: the discrepancy banner counts and lists what doesn't match, expected vs. found;
    Run Setup again applies the plan verify left.
    """
    main = open_setup(page, plan(ITEMS))
    stub_api_json(page, APPLY, result(DISCREPANCIES[:count], LEFT_OVER_HASH))

    main.get_by_role("button", name=APPLY_LABEL).click()

    expect(main.get_by_text(title, exact=True)).to_be_visible()
    banner = main.get_by_role("alert").filter(has_text=title)
    expect(banner).to_contain_text(DISCREPANCY_EXPLANATION)
    rows = banner.get_by_role("listitem")
    expect(rows).to_have_count(count)
    expect(rows).to_contain_text(
        [f"Deck options · {PREFIX}", f"Deck · {PREFIX}::Study::French"][:count]
    )
    expect(rows).to_contain_text([PRESET_FOUND, DECK_FOUND][:count])
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_have_count(0)
    with page.expect_request(lambda r: r.url.endswith(APPLY) and r.method == "POST") as again:
        banner.get_by_role("button", name=RUN_AGAIN).click()
    assert again.value.post_data_json == {"planHash": LEFT_OVER_HASH, "repairs": []}


@pytest.mark.p1
def test_leaving_does_not_cancel_and_coming_back_shows_the_run(page: Page) -> None:
    """AC-14: back on Setup mid-run, the progress card shows; once the run finishes and Anki
    still matches its result, the verified banner does.
    """
    stub_api_json(page, READINESS, readiness())
    plan_stub = Stub(page, PLAN, plan(ITEMS))
    status = Stub(page, STATUS, IDLE)
    held = HeldRoute(page, APPLY)
    page.goto("/setup")
    main = page.get_by_role("main")
    main.get_by_role("button", name=APPLY_LABEL).click()

    status.body = RUNNING
    go_by_nav(page, CAPTURES)  # leaving while the POST is still pending
    go_by_nav(page, SETUP)

    expect(main.get_by_text(PROGRESS, exact=True)).to_be_visible()
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_be_disabled()
    plan_stub.body = plan([], EMPTY_HASH)
    status.body = {"state": "finished", "result": result([], EMPTY_HASH)}
    expect(main.get_by_text(VERIFIED_TITLE, exact=True)).to_be_visible()
    expect(main.get_by_text(PROGRESS, exact=True)).to_have_count(0)
    held.fulfill_json(result([], EMPTY_HASH))


@pytest.mark.p1
def test_coming_back_after_anki_changed_shows_the_current_change_list(page: Page) -> None:
    """AC-14: a finished result whose hash the fresh plan no longer has is not shown; the current
    change list is, with Apply setup enabled.
    """
    finished = {"state": "finished", "result": result([], EMPTY_HASH)}
    main = open_setup(page, plan(ITEMS), status=finished)

    expect(main.get_by_role("button", name=APPLY_LABEL)).to_be_enabled()
    expect(main.get_by_role("list", name=CHANGES_HEADING)).to_be_visible()
    expect(main.get_by_text(VERIFIED_TITLE, exact=True)).to_have_count(0)
    expect(main.get_by_role("alert")).to_have_count(0)


PLAN_CHANGED_MESSAGE = "Anki changed since the preview. Review the changes and apply again."


@pytest.mark.p1
def test_a_stale_plan_rereads_the_plan_and_shows_why(page: Page) -> None:
    """AC-8: on 409 `plan_changed` the screen re-reads the plan, shows the current change list
    and the message as an inline alert.
    """
    stub_api_json(page, READINESS, readiness())
    plan_stub = Stub(page, PLAN, plan(ITEMS))
    stub_api_json(page, STATUS, IDLE)
    stub_api_error(page, APPLY, status=409, code="plan_changed", message=PLAN_CHANGED_MESSAGE)
    page.goto("/setup")
    main = page.get_by_role("main")
    apply_button = main.get_by_role("button", name=APPLY_LABEL)
    expect(apply_button).to_be_enabled()
    plan_stub.body = plan(ITEMS[:1], LEFT_OVER_HASH)  # Anki changed after the preview

    apply_button.click()

    expect(main.get_by_role("alert").filter(has_text=PLAN_CHANGED_MESSAGE)).to_be_visible()
    rows = main.get_by_role("list", name=CHANGES_HEADING).get_by_role("listitem")
    expect(rows).to_have_count(1)
    expect(rows).to_contain_text([f"Decks · {PREFIX}::Study::French"])
    expect(apply_button).to_be_enabled()
    with page.expect_request(lambda r: r.url.endswith(APPLY) and r.method == "POST") as again:
        apply_button.click()
    assert again.value.post_data_json == {"planHash": LEFT_OVER_HASH, "repairs": []}

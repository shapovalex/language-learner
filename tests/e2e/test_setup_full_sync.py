"""Story 2.9: the Full sync required tile and the Migrate rows on the Setup screen (AD-3,
AD-17, EXPERIENCE.md "Full sync required").

- **The tile.** Readiness's `fullSync` check is shown only while it fails, as a warning tile:
  "Full sync required" / "Open Anki Desktop, sync, and choose Upload to AnkiWeb." It doesn't
  disable Apply. Its "I've uploaded" button POSTs /api/setup/full-sync/uploaded and the tile
  goes (decided with the user, 2026-10-21).
- **The rows.** Migrate rows of kind `notes` go under "Notes", after "Note types", and a row
  with `requiresFullSync` says "Needs a full sync afterwards." (default copy; not in the UX
  docs).

The browser stubs readiness, the plan and the apply status, so this checks rendering only. The
routes are in tests/api/test_setup_migrations.py.
"""

from typing import Any

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support.network import stub_api_json

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.9: un-skip with the Full sync required tile and Notes rows"
)

READINESS = "/api/setup/readiness"
PLAN = "/api/setup/plan"
STATUS = "/api/setup/apply/status"
UPLOADED = "/api/setup/full-sync/uploaded"
PREFIX = "LanguageLabDev"  # not the default, so a hard-coded "LanguageLab" can't pass
VOCABULARY = f"{PREFIX} English Vocabulary"

FULL_SYNC_TITLE = "Full sync required"
FULL_SYNC_FIX = "Open Anki Desktop, sync, and choose Upload to AnkiWeb."
UPLOADED_LABEL = "I've uploaded"
NEEDS_FULL_SYNC = "Needs a full sync afterwards."
APPLY_LABEL = "Apply setup"
CHANGES_HEADING = "What will change in Anki"


def readiness(*, full_sync_ok: bool) -> dict[str, Any]:
    return {
        "prefix": PREFIX,
        "checks": [
            {"id": "ankiConnect", "ok": True},
            {"id": "azure", "ok": True},
            {"id": "openrouter", "ok": True},
            {"id": "fullSync", "ok": full_sync_ok},
        ],
    }


ITEMS = [
    {"action": "migrate", "kind": "noteType", "name": VOCABULARY, "requiresFullSync": True},
    {"action": "migrate", "kind": "notes", "name": VOCABULARY, "requiresFullSync": False},
]


def migration_plan() -> dict[str, Any]:
    return {
        "prefix": PREFIX,
        "planHash": "0" * 64,
        "state": "needs_migration",
        "items": ITEMS,
        "unmanaged": [],
    }


def open_setup(page: Page, *, full_sync_ok: bool) -> Any:
    stub_api_json(page, READINESS, readiness(full_sync_ok=full_sync_ok))
    stub_api_json(page, PLAN, migration_plan())
    stub_api_json(page, STATUS, {"state": "idle", "result": None})
    page.goto("/setup")
    return page.get_by_role("main")


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize("full_sync_ok", [False, True], ids=["required", "not-required"])
def test_the_full_sync_required_tile_shows_only_while_its_check_fails(
    page: Page, full_sync_ok: bool
) -> None:
    """AC-16: the warning tile and its copy while `fullSync` fails, and Apply stays enabled."""
    main = open_setup(page, full_sync_ok=full_sync_ok)

    expect(main.get_by_text(FULL_SYNC_TITLE, exact=True)).to_have_count(0 if full_sync_ok else 1)
    expect(main.get_by_text(FULL_SYNC_FIX)).to_have_count(0 if full_sync_ok else 1)
    expect(main.get_by_role("button", name=APPLY_LABEL)).to_be_enabled()


@RED_PHASE
@pytest.mark.p0
def test_ive_uploaded_clears_the_full_sync_required_tile(page: Page) -> None:
    """AC-17: the button POSTs the clear route, and the re-read readiness drops the tile."""
    readings = [readiness(full_sync_ok=False)]
    posts: list[str] = []

    def answer_readiness(route: Route) -> None:
        route.fulfill(status=200, json=readings[-1])

    def answer_uploaded(route: Route) -> None:
        posts.append(route.request.method)
        readings.append(readiness(full_sync_ok=True))
        route.fulfill(status=204)

    page.route(f"**{READINESS}", answer_readiness)
    page.route(f"**{UPLOADED}", answer_uploaded)
    stub_api_json(page, PLAN, migration_plan())
    stub_api_json(page, STATUS, {"state": "idle", "result": None})
    page.goto("/setup")
    main = page.get_by_role("main")

    main.get_by_role("button", name=UPLOADED_LABEL).click()

    expect(main.get_by_text(FULL_SYNC_TITLE, exact=True)).to_have_count(0)
    assert posts == ["POST"]


@RED_PHASE
@pytest.mark.p1
def test_the_change_list_shows_notes_rows_and_marks_a_full_sync(page: Page) -> None:
    """AC-18: a "Notes" row for the notes to migrate; the field change says it needs a full sync."""
    main = open_setup(page, full_sync_ok=True)
    rows = main.get_by_role("list", name=CHANGES_HEADING).get_by_role("listitem")

    notes_row = rows.filter(has_text="Notes")
    expect(notes_row).to_contain_text(VOCABULARY)
    expect(rows.filter(has_text="Note types")).to_contain_text(NEEDS_FULL_SYNC)
    expect(notes_row).not_to_contain_text(NEEDS_FULL_SYNC)

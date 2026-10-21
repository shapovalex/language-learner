"""Story 2.6: the Setup screen's change list, from GET /api/setup/plan (FR-6; EXPERIENCE.md
Setup, J5; mockups S-Setup).

Below the readiness card the screen shows "What will change in Anki" with "Nothing changes
until you apply." and one change row per resource kind and action, in the mockup's order:
Decks, Note types, Card templates and CSS, Deck options. Each row names the kind, lists its
resources as muted detail and ends in a chip with the action and the count ("Create 28").
Grouped rows were decided with the user on 2026-10-21. Rows are read-only.

An empty plan shows the info callout "Nothing to change. Everything LanguageLab manages is
already set up." instead of the list. Unrecognized decks and note types under the Prefix are
listed, read-only, under "Not managed by LanguageLab". The footer says to study
"<Prefix>::Study", not the root deck. Apply setup is entry 7's, so no button exists yet.

The browser stubs readiness and the plan, so this checks rendering only. The plan logic is in
tests/integration/test_anki_setup_preview.py and the route in tests/api/test_setup_plan.py.

Skipped until the screen renders the plan. Un-skip a test, watch it fail, then implement.
"""

from typing import Any

import pytest
from playwright.sync_api import Locator, Page, expect

from tests.support.network import stub_api_json

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.6: un-skip with the change list in static/screens/setup.js"
)

READINESS = "/api/setup/readiness"
PLAN = "/api/setup/plan"
PREFIX = "LanguageLabDev"  # not the default, so a hard-coded "LanguageLab" can't pass
PLAN_HASH = "0" * 64

CHANGES_HEADING = "What will change in Anki"
CHANGES_NOTE = "Nothing changes until you apply."
NOTHING_TO_CHANGE = "Nothing to change."
NOTHING_TO_CHANGE_DETAIL = "Everything LanguageLab manages is already set up."
NOT_MANAGED_HEADING = "Not managed by LanguageLab"
STUDY_FOOTER = f"In Anki, study “{PREFIX}::Study”, not the root deck"
PRONOUNCE_FOOTER = (
    f"Pronounce Cards live under {PREFIX}::Pronunciation and are reviewed here, in LanguageLab."
)

NOTE_TYPES = [
    f"{PREFIX} Capture",
    f"{PREFIX} English Vocabulary",
    f"{PREFIX} English Sentence",
    f"{PREFIX} French Vocabulary",
    f"{PREFIX} French Sentence",
]


def readiness(ok: bool = True) -> dict[str, Any]:
    return {
        "prefix": PREFIX,
        "checks": [
            {"id": "ankiConnect", "ok": ok},
            {"id": "azure", "ok": True},
            {"id": "openrouter", "ok": True},
        ],
    }


def item(action: str, kind: str, name: str) -> dict[str, str]:
    return {"action": action, "kind": kind, "name": name}


def plan(items: list[dict[str, str]], unmanaged: list[dict[str, str]] | None = None) -> dict:
    return {"prefix": PREFIX, "planHash": PLAN_HASH, "items": items, "unmanaged": unmanaged or []}


def empty_prefix_plan() -> dict:
    """An empty Prefix: 28 decks, 5 note types, their templates and CSS, and the preset.

    Deck names stand in for the manifest's (the screen counts and lists, it doesn't check).
    """
    decks = [item("create", "deck", f"{PREFIX}::Deck {n}") for n in range(28)]
    note_types = [item("create", "noteType", name) for name in NOTE_TYPES]
    templates = [item("create", "templates", name) for name in NOTE_TYPES]
    # Shuffled kinds: the screen orders the rows itself
    return plan([*templates, item("create", "preset", PREFIX), *note_types, *decks])


def open_setup(page: Page, plan_body: dict) -> Locator:
    stub_api_json(page, READINESS, readiness())
    stub_api_json(page, PLAN, plan_body)
    page.goto("/setup")
    return page.get_by_role("main")


@RED_PHASE
@pytest.mark.p0
def test_setup_lists_what_will_change_grouped_by_kind_and_action(page: Page) -> None:
    """AC-10: one read-only change row per kind and action, with its count, under the heading."""
    main = open_setup(page, empty_prefix_plan())

    rows = main.get_by_role("list", name=CHANGES_HEADING).get_by_role("listitem")

    expect(rows).to_have_count(4)
    expect(rows).to_contain_text(["Decks", "Note types", "Card templates and CSS", "Deck options"])
    expect(rows).to_contain_text(["Create 28", "Create 5", "Create 5", "Create 1"])
    expect(main.get_by_role("heading", name=CHANGES_HEADING)).to_be_visible()
    expect(main.get_by_text(CHANGES_NOTE, exact=True)).to_be_visible()
    expect(rows.nth(1)).to_contain_text(f"{PREFIX} English Vocabulary")
    expect(main.get_by_role("list", name=CHANGES_HEADING).get_by_role("checkbox")).to_have_count(0)
    expect(main.get_by_role("list", name=CHANGES_HEADING).get_by_role("button")).to_have_count(0)


@RED_PHASE
@pytest.mark.p1
def test_setup_shows_nothing_to_change_when_the_plan_is_empty(page: Page) -> None:
    """AC-11: an empty plan shows the info callout instead of the change list."""
    main = open_setup(page, plan([]))

    callout = main.get_by_text(NOTHING_TO_CHANGE, exact=True)

    expect(callout).to_be_visible()
    expect(main.get_by_text(NOTHING_TO_CHANGE_DETAIL, exact=True)).to_be_visible()
    expect(main.get_by_role("heading", name=CHANGES_HEADING)).to_have_count(0)
    expect(main.get_by_text(CHANGES_NOTE, exact=True)).to_have_count(0)
    expect(main.get_by_role("alert")).to_have_count(0)
    expect(main.get_by_role("button", name="Apply setup")).to_have_count(0)


@RED_PHASE
@pytest.mark.p1
def test_setup_lists_unrecognized_content_as_not_managed(page: Page) -> None:
    """AC-12: unknown decks and note types under the Prefix are read-only "Not managed" rows."""
    unmanaged = [
        {"kind": "deck", "name": f"{PREFIX}::Old stuff"},
        {"kind": "noteType", "name": f"{PREFIX} Spanish Vocabulary"},
    ]
    repair = [item("repair", "templates", f"{PREFIX} English Vocabulary")]
    main = open_setup(page, plan(repair, unmanaged))

    rows = main.get_by_role("list", name=NOT_MANAGED_HEADING).get_by_role("listitem")

    expect(rows).to_have_count(2)
    expect(rows).to_contain_text([f"{PREFIX}::Old stuff", f"{PREFIX} Spanish Vocabulary"])
    expect(rows.get_by_role("checkbox")).to_have_count(0)
    expect(rows.get_by_role("button")).to_have_count(0)
    changes = main.get_by_role("list", name=CHANGES_HEADING).get_by_role("listitem")
    expect(changes).to_have_count(1)
    expect(changes).to_contain_text(["Card templates and CSS"])
    expect(changes).to_contain_text(["Repair 1"])


@RED_PHASE
@pytest.mark.p2
def test_setup_footer_says_to_study_the_study_deck_not_the_root(page: Page) -> None:
    """AC-13: the footer names "<Prefix>::Study", under the subtitle naming the Prefix."""
    main = open_setup(page, empty_prefix_plan())

    expect(main.get_by_text(STUDY_FOOTER, exact=True)).to_be_visible()
    expect(main.get_by_text(PRONOUNCE_FOOTER, exact=True)).to_be_visible()
    expect(main.get_by_text(f"under the prefix {PREFIX}.")).to_be_visible()

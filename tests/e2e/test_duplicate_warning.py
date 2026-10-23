"""Story 4.3: the duplicate check at Save to Anki and the duplicate sheet (S-Duplicate,
EXPERIENCE.md; FR-19; AD-12, AD-13).

- **When.** Decided 2026-10-22: Save to Anki on a Draft first asks GET
  /api/items/<lang>/duplicates with the Draft's Category, its current Target and its ItemId.
  With no match the Save goes ahead and no sheet is shown. Nothing is read while the user types.
- **The sheet.** A dialog named "You already have an Item with this text", with the overline
  "Possible duplicate · English · Vocabulary", each match's Target and Russian meaning, "Nothing
  has been saved yet. You can still create a second Item." and Open existing, Cancel and Create
  anyway. A bottom sheet on the phone, a centered dialog from tablet width up.
- **The choices.** Create anyway saves the Draft under its ItemId and returns to the Capture
  with the success banner: creation is never blocked. Cancel goes back to the editor with the
  Draft kept, and the next Save to Anki checks again with the Target as it is then. Open
  existing asks about the unsaved Draft (the router's alert), and on Discard opens the match's
  Item detail at /<lang>/items/<itemId>.

The Capture, the generated Draft, the duplicate read and the Item read are stubbed at the
network; Save reaches the live server's fake.
"""

import pytest
from playwright.sync_api import Page, Request, ViewportSize, expect

from tests.support import viewports
from tests.support.captures_screen import API, CAPTURES_PATH, capture, horizontal_overflow
from tests.support.drafts import GENERATED_VOCABULARY, drafted
from tests.support.items_screen import (
    CANCEL,
    CREATE_ANYWAY,
    DUPLICATE_BODY,
    GENERATE_API,
    NOT_SAVED_TITLE,
    OPEN_EXISTING,
    banner,
    choose,
    duplicate_overline,
    duplicate_query,
    duplicate_sheet,
    duplicates_api,
    editor,
    field,
    generate_draft,
    is_duplicate_check,
    is_item_save,
    item_api,
    item_detail_path,
    item_part,
    save_button,
    sheet_button,
    stub_duplicates,
)
from tests.support.navigation import path_pattern, screen_heading
from tests.support.network import stub_api_error, stub_api_json
from tests.support.unsaved import discard_button, unsaved_alert

CAPTURE = capture("I'd rather not jump to conclusions.", "2026-10-22T21:14:00Z")
CAPTURE_ID = CAPTURE["captureId"]
TARGET = "jump to conclusions"
ITEM_ID = "7d1c2a4e-9b3f-4c6d-8e2a-1f0b3c5d7e9a"

# An English Vocabulary Item already in Anki with the same Target, as the duplicate read answers
MATCH_ID = "3f6b9c2d-1a4e-4b7c-9d8e-2c5a7f1b0e3d"
MATCH = {
    "itemId": MATCH_ID,
    **drafted("vocabulary", "Jump to conclusions"),
    "russian": "делать поспешные выводы",
    "mnemonic": "a leap over the facts",
}

WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}


def open_draft(page: Page, viewport: ViewportSize = viewports.DESKTOP) -> None:
    """A generated English Vocabulary Draft of `TARGET` (Custom value) in the Draft editor."""
    page.set_viewport_size(viewport)
    stub_api_json(page, API, {"captures": [CAPTURE]}, method="GET")
    stub_api_json(page, f"{API}/{CAPTURE_ID}", CAPTURE, method="GET")
    reply = {"itemId": ITEM_ID, **drafted("vocabulary", TARGET)}
    stub_api_json(page, GENERATE_API, reply, status=201, method="POST")
    page.goto(f"{CAPTURES_PATH}/{CAPTURE_ID}")
    choose(page, "English", "Vocabulary", custom=TARGET)
    generate_draft(page).click()
    expect(field(page, "Russian meaning")).to_have_value(GENERATED_VOCABULARY["russian"])


def record_saves(page: Page) -> list[Request]:
    """A list that fills with every Save the page sends from now on."""
    saves: list[Request] = []
    page.on("request", lambda request: saves.append(request) if is_item_save(request) else None)
    return saves


def open_sheet(page: Page, viewport: ViewportSize = viewports.DESKTOP) -> None:
    """The Draft, then Save to Anki with `MATCH` answered: the sheet for it opens. Nothing is
    asserted here; each test's own step on the sheet is its first.
    """
    open_draft(page, viewport)
    stub_duplicates(page, [MATCH])
    save_button(page).click()


@pytest.mark.p0
def test_save_checks_the_current_target_first_and_saves_when_nothing_matches(page: Page) -> None:
    """AC-12: Save to Anki first asks the duplicate read with the Draft's Category, its Target
    as edited and its ItemId; with no match the Draft is saved at once and no sheet is shown.
    """
    open_draft(page)
    stub_duplicates(page, [])
    edited = "jump to hasty conclusions"
    field(page, "Target").fill(edited)
    with page.expect_request(is_duplicate_check) as checked:
        with page.expect_request(is_item_save) as saved:
            save_button(page).click()

    assert duplicate_query(checked.value) == {
        "category": "vocabulary",
        "target": edited,
        "itemId": ITEM_ID,
    }

    assert checked.value.url.split("?")[0].endswith(duplicates_api("en"))
    assert item_part(saved.value)["target"] == edited
    expect(banner(page, edited)).to_be_visible()
    expect(duplicate_sheet(page)).to_have_count(0)


@pytest.mark.p0
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_match_opens_the_duplicate_sheet_and_nothing_is_saved(
    page: Page, viewport: ViewportSize
) -> None:
    """AC-13: a match opens the sheet, with its overline, title, the match's Target and Russian
    meaning, the reassurance and the three choices; no Save is sent.
    """
    open_draft(page, viewport)
    saves = record_saves(page)
    stub_duplicates(page, [MATCH])
    save_button(page).click()

    expect(duplicate_sheet(page)).to_be_visible()

    sheet = duplicate_sheet(page)
    expect(sheet).to_contain_text(duplicate_overline("English", "Vocabulary"))
    expect(sheet).to_contain_text(MATCH["target"])
    expect(sheet).to_contain_text(MATCH["russian"])
    expect(sheet).to_contain_text(DUPLICATE_BODY)
    for name in (OPEN_EXISTING, CANCEL, CREATE_ANYWAY):
        expect(sheet_button(page, name)).to_be_visible()
    assert saves == []


@pytest.mark.p0
def test_create_anyway_saves_the_draft_and_returns_to_the_capture(page: Page) -> None:
    """AC-14: Create anyway saves the Draft under its ItemId and returns to the same Capture
    with the success banner (FR-19: never blocked).
    """
    open_sheet(page)
    with page.expect_request(is_item_save) as saved:
        sheet_button(page, CREATE_ANYWAY).click()

    assert item_part(saved.value)["itemId"] == ITEM_ID

    expect(banner(page, TARGET)).to_be_visible()
    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))


@pytest.mark.p0
def test_cancel_keeps_the_draft_and_an_edited_target_is_checked_again(page: Page) -> None:
    """AC-15: Cancel closes the sheet and keeps the Draft in the editor with nothing saved;
    after the Target is edited, Save to Anki checks again with the new Target.
    """
    open_sheet(page)
    saves = record_saves(page)
    sheet_button(page, CANCEL).click()

    expect(duplicate_sheet(page)).to_be_hidden()

    expect(editor(page)).to_be_visible()
    expect(field(page, "Russian meaning")).to_have_value(GENERATED_VOCABULARY["russian"])
    assert saves == []
    stub_duplicates(page, [])
    field(page, "Target").fill("leap to conclusions")
    with page.expect_request(is_duplicate_check) as checked:
        with page.expect_request(is_item_save):
            save_button(page).click()
    assert duplicate_query(checked.value)["target"] == "leap to conclusions"


@pytest.mark.p0
def test_open_existing_asks_about_the_draft_then_opens_the_match(page: Page) -> None:
    """AC-16: Open existing raises the unsaved Draft alert; Discard opens the match's Item
    detail at /en/items/<itemId>.
    """
    open_sheet(page)
    stub_api_json(page, item_api("en", MATCH_ID), MATCH, method="GET")
    sheet_button(page, OPEN_EXISTING).click()

    expect(unsaved_alert(page)).to_be_visible()

    discard_button(page).click()
    expect(page).to_have_url(path_pattern(item_detail_path("en", MATCH_ID)))
    expect(screen_heading(page)).to_have_text(MATCH["target"])


@pytest.mark.p1
def test_a_failed_check_shows_the_save_alert_and_saves_nothing(page: Page) -> None:
    """AC-12: a duplicate read that fails (Anki down) shows the Save's inline alert, and no
    Save is sent.
    """
    open_draft(page)
    saves = record_saves(page)
    stub_api_error(
        page, f"{duplicates_api('en')}?*", status=503, code="anki_unavailable", method="GET"
    )
    save_button(page).click()

    expect(editor(page).get_by_role("alert")).to_contain_text(NOT_SAVED_TITLE)
    assert saves == []


@pytest.mark.p1
def test_a_retried_save_after_create_anyway_asks_no_second_check(page: Page) -> None:
    """AC-14: when the Save after Create anyway fails, Save to Anki again sends the Save with
    no second check while the Target is unchanged.
    """
    open_sheet(page)
    stub_api_error(page, "/api/items/en", status=503, code="anki_unavailable", method="POST")
    with page.expect_request(is_item_save):
        sheet_button(page, CREATE_ANYWAY).click()
    expect(editor(page).get_by_role("alert")).to_contain_text(NOT_SAVED_TITLE)
    checks: list[Request] = []
    page.on("request", lambda r: checks.append(r) if is_duplicate_check(r) else None)

    with page.expect_request(is_item_save) as retried:
        save_button(page).click()

    assert item_part(retried.value)["itemId"] == ITEM_ID
    assert checks == []


@pytest.mark.p1
def test_on_the_phone_the_sheet_sits_at_the_bottom_with_no_horizontal_overflow(page: Page) -> None:
    """AC-13: at phone width the sheet is a bottom sheet: its bottom edge is the viewport's, it
    spans the width, and the page doesn't scroll sideways (EXPERIENCE.md Bottom sheet).
    """
    open_sheet(page, viewports.PHONE)
    expect(duplicate_sheet(page)).to_be_visible()

    box = duplicate_sheet(page).bounding_box()

    assert box is not None
    assert box["y"] + box["height"] == pytest.approx(viewports.PHONE["height"], abs=1)
    assert box["width"] == pytest.approx(viewports.PHONE["width"], abs=1)
    assert horizontal_overflow(page) <= 0


@pytest.mark.p1
def test_focus_starts_on_open_existing_and_stays_on_the_sheet(page: Page) -> None:
    """AC-13: focus starts on Open existing, and Tab and Shift+Tab cycle the sheet's three
    buttons without leaving it (EXPERIENCE.md Bottom sheet).
    """
    open_sheet(page)
    expect(sheet_button(page, OPEN_EXISTING)).to_be_focused()

    for name in (CANCEL, CREATE_ANYWAY, OPEN_EXISTING):
        page.keyboard.press("Tab")
        expect(sheet_button(page, name)).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(sheet_button(page, CREATE_ANYWAY)).to_be_focused()

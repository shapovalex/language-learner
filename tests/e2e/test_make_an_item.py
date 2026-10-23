"""Story 4.1: the Make an Item pane, the blank Draft editor, and Save to Anki (S-NewItem,
S-CapturesDesk, C-Draft, S-DraftPhone, EXPERIENCE.md; FR-11, FR-12, FR-18, FR-20; AD-8, AD-13).

- **Make an Item pane.** In Capture detail (its own screen on the phone, the right pane on
  desktop), a region "Make an Item" with the text choice "Use as is" (chosen) or "Custom value"
  with its field, the Language (English, French) and Category (Vocabulary, Sentence) pickers,
  none chosen at first, and "Write it myself". Like Generate Draft (entry 2) it is disabled with
  a visible reason until a Language and Category are chosen ("Choose a Language and Category.")
  and, for Custom value, its field is filled ("Enter the custom value.").
- **Blank Draft.** "Write it myself" asks POST /api/drafts/blank for the ItemId and opens the
  Draft editor at /captures/<captureId>/new: "From Capture “…”", the chip "Draft — not saved
  yet", and every field of the Category, editable. Decided with the user (2026-10-22): Target is
  prefilled with the chosen text and every other field is empty; the alternatives are a
  textarea, one per line; and /captures/<captureId>/new with no Draft in memory (a reload, a
  direct visit) is replaced by /captures/<captureId>.
- **Unsaved.** The Draft marks the screen dirty (`router.setDirty`, kind `draft`), so leaving
  raises the router alert "This Draft isn't saved."
- **Save to Anki.** POST /api/items/<lang> with the `item` part (the Draft's ItemId, `audio:
  "keep"` and the fields), then back to the same Capture with the success banner "Saved
  “<Target>” to Anki. Make another Item from this Capture, or delete it." (FR-12). A failed
  Save keeps the editor and its edits with the inline alert, and a retry sends the same ItemId
  (AD-20).

The Capture is stubbed at the network (GET only); the blank Draft and Save reach the live
server's fake.
"""

import uuid
from typing import Any

import pytest
from playwright.sync_api import Page, ViewportSize, expect

from tests.support import viewports
from tests.support.captures_screen import API, CAPTURES_PATH, capture, compose_box, main
from tests.support.items_screen import (
    CHOOSE_REASON,
    CUSTOM_REASON,
    CUSTOM_VALUE,
    DRAFT_CHIP,
    DRAFT_LOSS,
    NOT_SAVED_BODY,
    NOT_SAVED_TITLE,
    SENTENCE_FIELDS,
    USE_AS_IS,
    VOCABULARY_FIELDS,
    banner,
    choice,
    choose,
    editor,
    field,
    from_capture,
    is_blank_draft,
    is_item_save,
    item_part,
    new_item_path,
    pane,
    save_button,
    stub_duplicates,
    write_it_myself,
)
from tests.support.navigation import path_pattern
from tests.support.network import stub_api_error, stub_api_json
from tests.support.unsaved import LEAVE_PATHS, discard_button, unsaved_alert

CAPTURE = capture("I'd rather not jump to conclusions.", "2026-10-22T21:14:00Z")
CAPTURE_ID = CAPTURE["captureId"]

VOCABULARY_TARGET = "jump to conclusions"
SENTENCE_TARGET = "Ne tirons pas de conclusions hâtives."

WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}


def open_capture(page: Page, viewport: ViewportSize) -> None:
    """Capture detail for `CAPTURE`, with the list and detail stubbed (GET only), and no
    duplicate for any Save (story 4.3: the live server's fake keeps earlier tests' Items).
    """
    page.set_viewport_size(viewport)
    stub_api_json(page, API, {"captures": [CAPTURE]}, method="GET")
    stub_api_json(page, f"{API}/{CAPTURE_ID}", CAPTURE, method="GET")
    for language in ("en", "fr"):
        stub_duplicates(page, [], language)
    page.goto(f"{CAPTURES_PATH}/{CAPTURE_ID}")


def write_blank_draft(page: Page, language: str, category: str, custom: str | None = None) -> str:
    """Choose, then "Write it myself"; return the ItemId the blank Draft issued."""
    choose(page, language, category, custom)
    with page.expect_response(lambda r: is_blank_draft(r.request)) as issued:
        write_it_myself(page).click()
    return issued.value.json()["itemId"]


@pytest.mark.p0
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_write_it_myself_waits_for_a_language_a_category_and_a_custom_value(
    page: Page, viewport: ViewportSize
) -> None:
    """AC-12: Capture detail has the Make an Item pane with "Use as is" chosen; "Write it
    myself" is disabled with "Choose a Language and Category." until both are picked, and with
    "Enter the custom value." while Custom value is chosen and empty.
    """
    open_capture(page, viewport)

    expect(write_it_myself(page)).to_be_disabled()

    expect(pane(page)).to_contain_text(CHOOSE_REASON)
    expect(pane(page).get_by_role("radio", name=USE_AS_IS, exact=True)).to_be_checked()
    choice(page, "English").click()
    expect(write_it_myself(page)).to_be_disabled()
    choice(page, "Vocabulary").click()
    expect(choice(page, "English")).to_have_attribute("aria-pressed", "true")
    expect(choice(page, "Vocabulary")).to_have_attribute("aria-pressed", "true")
    expect(write_it_myself(page)).to_be_enabled()
    pane(page).get_by_role("radio", name=CUSTOM_VALUE, exact=True).check()
    expect(write_it_myself(page)).to_be_disabled()
    expect(pane(page)).to_contain_text(CUSTOM_REASON)
    pane(page).get_by_role("textbox", name=CUSTOM_VALUE).fill(VOCABULARY_TARGET)
    expect(write_it_myself(page)).to_be_enabled()


OPENED = {
    "vocabulary": ("Vocabulary", VOCABULARY_FIELDS, "Note"),
    "sentence": ("Sentence", SENTENCE_FIELDS, "Mnemonic"),
}


@pytest.mark.p0
@pytest.mark.parametrize(("category", "fields", "absent"), OPENED.values(), ids=OPENED.keys())
def test_write_it_myself_opens_a_blank_draft_with_the_target_prefilled(
    page: Page, category: str, fields: tuple[str, ...], absent: str
) -> None:
    """AC-13: "Write it myself" opens the Draft editor at /captures/<captureId>/new with
    Target prefilled by the chosen text (Use as is here), every other field of the Category
    editable and empty, "From Capture “…”" and the chip "Draft — not saved yet".
    """
    open_capture(page, viewports.DESKTOP)
    choose(page, "English", category)
    write_it_myself(page).click()

    expect(field(page, "Target")).to_have_value(CAPTURE["text"])

    expect(page).to_have_url(path_pattern(new_item_path(CAPTURE_ID)))
    expect(main(page)).to_contain_text(from_capture(CAPTURE["text"]))
    expect(main(page)).to_contain_text(DRAFT_CHIP)
    for label in fields:
        expect(field(page, label)).to_be_editable()
        if label != "Target":
            expect(field(page, label)).to_have_value("")
    expect(field(page, absent)).to_have_count(0)


@pytest.mark.p0
def test_leaving_the_draft_editor_raises_the_unsaved_draft_alert(page: Page) -> None:
    """AC-14: the open Draft marks the screen dirty, so leaving it raises the router's unsaved
    alert with "This Draft isn't saved."
    """
    leave = LEAVE_PATHS["desktop-pill"]
    open_capture(page, leave.viewport)
    write_blank_draft(page, "English", "Vocabulary")
    expect(editor(page)).to_be_visible()

    leave.leave(page)

    expect(unsaved_alert(page)).to_contain_text(DRAFT_LOSS)


def save_draft(page: Page, russian: str, alternatives: str = "") -> dict[str, Any]:
    """Fill the Russian meaning and alternatives, Save to Anki, and return the `item` part sent."""
    field(page, "Russian meaning").fill(russian)
    field(page, "Alternatives").fill(alternatives)
    with page.expect_request(is_item_save) as sent:
        save_button(page).click()
    return item_part(sent.value)


@pytest.mark.p0
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_vocabulary_and_a_sentence_item_are_saved_from_one_capture(
    page: Page, viewport: ViewportSize
) -> None:
    """AC-15: Save to Anki sends the Draft's ItemId with `audio: "keep"` and the fields (the
    alternatives one per line), then returns to the same Capture with the success banner; an
    English Vocabulary and a French Sentence Item are saved from one Capture this way.
    """
    open_capture(page, viewport)
    vocabulary_id = write_blank_draft(page, "English", "Vocabulary", VOCABULARY_TARGET)
    vocabulary = save_draft(page, "делать поспешные выводы", "торопиться с выводами\nспешить")

    expect(banner(page, VOCABULARY_TARGET)).to_be_visible()

    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))
    assert (vocabulary["itemId"], vocabulary["audio"]) == (vocabulary_id, "keep")
    assert vocabulary["category"] == "vocabulary"
    assert vocabulary["target"] == VOCABULARY_TARGET
    assert vocabulary["russianAlternatives"] == ["торопиться с выводами", "спешить"]
    sentence_id = write_blank_draft(page, "French", "Sentence", SENTENCE_TARGET)
    sentence = save_draft(page, "Не будем делать поспешных выводов.")
    expect(banner(page, SENTENCE_TARGET)).to_be_visible()
    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))
    assert (sentence["itemId"], sentence["category"]) == (sentence_id, "sentence")
    assert sentence["russianAlternatives"] == []
    assert sentence_id != vocabulary_id


@pytest.mark.p0
def test_a_failed_save_keeps_the_draft_and_a_retry_sends_the_same_item_id(page: Page) -> None:
    """AC-16: a Save answered `anki_unavailable` keeps the Draft editor and its edits with the
    inline alert "Not saved — Anki isn't reachable"; Save again sends the same ItemId (AD-20)
    and returns to the Capture.
    """
    open_capture(page, viewports.DESKTOP)
    item_id = write_blank_draft(page, "English", "Vocabulary")
    stub_api_error(page, "/api/items/en", status=503, code="anki_unavailable", method="POST")
    first = save_draft(page, "делать поспешные выводы")

    expect(editor(page).get_by_role("alert")).to_contain_text(NOT_SAVED_TITLE)

    expect(editor(page).get_by_role("alert")).to_contain_text(NOT_SAVED_BODY)
    expect(page).to_have_url(path_pattern(new_item_path(CAPTURE_ID)))
    expect(field(page, "Russian meaning")).to_have_value("делать поспешные выводы")
    page.unroute("**/api/items/en")
    with page.expect_request(is_item_save) as retried:
        save_button(page).click()
    expect(banner(page, CAPTURE["text"])).to_be_visible()
    assert first["itemId"] == item_id
    assert item_part(retried.value)["itemId"] == item_id


@pytest.mark.p0
def test_the_draft_route_with_no_draft_in_memory_shows_the_capture(page: Page) -> None:
    """AC-17: /captures/<captureId>/new with no Draft in memory (a reload, a direct visit) is
    replaced by /captures/<captureId>, the Capture detail with the Make an Item pane.
    """
    page.set_viewport_size(viewports.DESKTOP)
    stub_api_json(page, API, {"captures": [CAPTURE]}, method="GET")
    stub_api_json(page, f"{API}/{CAPTURE_ID}", CAPTURE, method="GET")

    page.goto(new_item_path(CAPTURE_ID))

    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))
    expect(pane(page)).to_be_visible()
    expect(editor(page)).to_have_count(0)


@pytest.mark.p1
def test_the_blank_draft_is_not_written_to_anki_before_save(page: Page) -> None:
    """AC-15: opening and editing a blank Draft sends no Save; only Save to Anki does (FR-18)."""
    saves: list[str] = []
    page.on("request", lambda r: saves.append(r.url) if is_item_save(r) else None)
    open_capture(page, viewports.DESKTOP)
    write_blank_draft(page, "English", "Vocabulary")

    field(page, "Russian meaning").fill("делать поспешные выводы")

    expect(field(page, "Russian meaning")).to_have_value("делать поспешные выводы")
    assert saves == []


@pytest.mark.p1
def test_each_write_it_myself_issues_a_new_item_id(page: Page) -> None:
    """AC-13: a second blank Draft from the same Capture carries a new ItemId (AD-8)."""
    open_capture(page, viewports.DESKTOP)
    first = write_blank_draft(page, "English", "Vocabulary")
    save_draft(page, "делать поспешные выводы")
    expect(banner(page, CAPTURE["text"])).to_be_visible()

    second = write_blank_draft(page, "English", "Vocabulary")

    assert second != first
    assert uuid.UUID(second).version == 4


@pytest.mark.p1
def test_discarding_a_draft_keeps_the_unsaved_compose_text(page: Page) -> None:
    """AC-14: Discard in the Draft editor asks first, and on Discard returns to the Capture with
    the compose text still there and still unsaved: leaving the screen asks again, about it.
    """
    open_capture(page, viewports.DESKTOP)
    compose_box(page).fill("une idée à noter")
    write_blank_draft(page, "English", "Vocabulary")
    editor(page).get_by_role("button", name="Discard", exact=True).click()
    expect(unsaved_alert(page)).to_contain_text(DRAFT_LOSS)
    discard_button(page).click()

    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))

    expect(compose_box(page)).to_have_value("une idée à noter")
    LEAVE_PATHS["desktop-pill"].leave(page)
    expect(unsaved_alert(page)).to_contain_text("This Capture isn't saved.")

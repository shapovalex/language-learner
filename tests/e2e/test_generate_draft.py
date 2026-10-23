"""Story 4.2: Generate Draft in the Make an Item pane, and the generated Draft in the Draft
editor (S-NewItem, C-Draft, S-DraftPhone, EXPERIENCE.md; FR-11, FR-14 to FR-18; AD-11, AD-13).

- **Make an Item pane.** Under the pickers, the field "Generation context · optional · used
  once, never saved", then the Primary "Generate Draft" with "Write it myself" kept beside it.
  Generate Draft is disabled for the same reasons ("Choose a Language and Category." / "Enter
  the custom value.").
- **Generating.** Generate Draft POSTs /api/drafts/generate with the chosen text, Language,
  Category and Generation context, opens /captures/<captureId>/new at once with the skeleton
  and "Writing your Draft…", then fills the Draft editor from the reply: Target as chosen
  (decided 2026-10-22: the model can't change it), Mnemonic empty and editable (FR-18).
- **Example.** A Vocabulary Draft's Example has "Clear", which empties Example and Example in
  Russian; Save then sends both empty (FR-14).
- **Errors.** A failed generation shows the EXPERIENCE.md inline alert for its code, no Draft,
  and "Try again", which sends the same request again.
- **Context.** The Generation context lives only in the screen's memory (AD-13): never in the
  URL, `history.state`, storage, or the Save.

The Capture and the generated Draft are stubbed at the network; Save reaches the live server's
fake.
"""

import pytest
from playwright.sync_api import Page, ViewportSize, expect

from tests.support import viewports
from tests.support.captures_screen import API, CAPTURES_PATH, capture, main
from tests.support.drafts import CONTEXT, GENERATED_SENTENCE, GENERATED_VOCABULARY, drafted
from tests.support.items_screen import (
    CHOOSE_REASON,
    CLEAR,
    CUSTOM_REASON,
    CUSTOM_VALUE,
    GENERATE_API,
    GENERATION_FAILED,
    TRY_AGAIN,
    WRITING,
    banner,
    choose,
    editor,
    field,
    generate_draft,
    generation_context,
    is_generate,
    is_item_save,
    item_part,
    new_item_path,
    pane,
    save_button,
    write_it_myself,
)
from tests.support.navigation import path_pattern
from tests.support.network import HeldRoute, record_requests, stub_api_error, stub_api_json
from tests.support.unsaved import unsaved_alert

CAPTURE = capture("I'd rather not jump to conclusions.", "2026-10-22T21:14:00Z")
CAPTURE_ID = CAPTURE["captureId"]
TARGET = CAPTURE["text"]  # Use as is
ITEM_ID = "7d1c2a4e-9b3f-4c6d-8e2a-1f0b3c5d7e9a"

WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}


def open_capture(page: Page, viewport: ViewportSize = viewports.DESKTOP) -> None:
    """Capture detail for `CAPTURE`, with the list and detail stubbed (GET only)."""
    page.set_viewport_size(viewport)
    stub_api_json(page, API, {"captures": [CAPTURE]}, method="GET")
    stub_api_json(page, f"{API}/{CAPTURE_ID}", CAPTURE, method="GET")
    page.goto(f"{CAPTURES_PATH}/{CAPTURE_ID}")


def draft_reply(category: str = "vocabulary") -> dict:
    """The 201 body of a generated Draft of `TARGET`."""
    return {"itemId": ITEM_ID, **drafted(category, TARGET)}


def stub_generated(page: Page, category: str = "vocabulary") -> None:
    stub_api_json(page, GENERATE_API, draft_reply(category), status=201, method="POST")


@pytest.mark.p0
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_generate_draft_waits_for_a_language_a_category_and_a_custom_value(
    page: Page, viewport: ViewportSize
) -> None:
    """AC-14: the pane has the Generation context field and Generate Draft beside "Write it
    myself"; Generate Draft is disabled with "Choose a Language and Category." until both are
    picked, and with "Enter the custom value." while Custom value is chosen and empty.
    """
    open_capture(page, viewport)

    expect(generate_draft(page)).to_be_disabled()

    expect(pane(page)).to_contain_text(CHOOSE_REASON)
    expect(generation_context(page)).to_be_editable()
    expect(write_it_myself(page)).to_be_visible()
    choose(page, "English", "Vocabulary")
    expect(generate_draft(page)).to_be_enabled()
    pane(page).get_by_role("radio", name=CUSTOM_VALUE, exact=True).check()
    expect(generate_draft(page)).to_be_disabled()
    expect(pane(page)).to_contain_text(CUSTOM_REASON)
    pane(page).get_by_role("textbox", name=CUSTOM_VALUE).fill("jump to conclusions")
    expect(generate_draft(page)).to_be_enabled()


@pytest.mark.p0
def test_generate_draft_shows_the_loading_state_then_fills_the_draft_editor(page: Page) -> None:
    """AC-15: Generate Draft sends the chosen text, Language, Category and Generation context,
    shows "Writing your Draft…" at /captures/<captureId>/new, then fills the Draft editor with
    the generated fields, Target as chosen and Mnemonic empty and editable.
    """
    open_capture(page)
    held = HeldRoute(page, GENERATE_API, method="POST")
    choose(page, "English", "Vocabulary")
    generation_context(page).fill(CONTEXT)
    with page.expect_request(is_generate) as sent:
        generate_draft(page).click()

    expect(main(page).get_by_role("status").filter(has_text=WRITING)).to_be_visible()

    expect(page).to_have_url(path_pattern(new_item_path(CAPTURE_ID)))
    held.fulfill_json(draft_reply(), status=201)
    expect(field(page, "Russian meaning")).to_have_value(GENERATED_VOCABULARY["russian"])
    expect(field(page, "Target")).to_have_value(TARGET)
    expect(field(page, "Alternatives")).to_have_value(
        GENERATED_VOCABULARY["russianAlternatives"][0]
    )
    expect(field(page, "Example")).to_have_value(GENERATED_VOCABULARY["example"])
    expect(field(page, "Example in Russian")).to_have_value(GENERATED_VOCABULARY["exampleRussian"])
    expect(field(page, "Hint")).to_have_value("")
    expect(field(page, "Mnemonic")).to_have_value("")
    expect(field(page, "Mnemonic")).to_be_editable()
    assert sent.value.post_data_json == {
        "language": "en",
        "category": "vocabulary",
        "target": TARGET,
        "generationContext": CONTEXT,
    }


@pytest.mark.p0
def test_clear_removes_the_example_before_save(page: Page) -> None:
    """AC-16: Clear empties Example and Example in Russian; Save then sends both empty under
    the generated ItemId, and returns to the Capture with the success banner.
    """
    open_capture(page)
    stub_generated(page)
    choose(page, "English", "Vocabulary")
    generate_draft(page).click()
    editor(page).get_by_role("button", name=CLEAR, exact=True).click()

    expect(field(page, "Example")).to_have_value("")

    expect(field(page, "Example in Russian")).to_have_value("")
    with page.expect_request(is_item_save) as sent:
        save_button(page).click()
    expect(banner(page, TARGET)).to_be_visible()
    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))
    saved = item_part(sent.value)
    assert (saved["example"], saved["exampleRussian"]) == ("", "")
    assert (saved["itemId"], saved["audio"]) == (ITEM_ID, "keep")
    assert saved["russian"] == GENERATED_VOCABULARY["russian"]


@pytest.mark.p0
@pytest.mark.parametrize("code", GENERATION_FAILED)
def test_a_failed_generation_shows_its_alert_and_try_again_asks_again(
    page: Page, code: str
) -> None:
    """AC-17: a generation answered with `code` shows the EXPERIENCE.md inline alert for it
    and no Draft; Try again sends the same request again and fills the editor.
    """
    title, body = GENERATION_FAILED[code]
    open_capture(page)
    stub_api_error(page, GENERATE_API, status=502, code=code, method="POST")
    choose(page, "English", "Vocabulary")
    generation_context(page).fill(CONTEXT)
    with page.expect_request(is_generate) as first:
        generate_draft(page).click()

    expect(main(page).get_by_role("alert")).to_contain_text(title)

    expect(main(page).get_by_role("alert")).to_contain_text(body)
    expect(editor(page)).to_have_count(0)
    page.unroute(f"**{GENERATE_API}")
    stub_generated(page)
    with page.expect_request(is_generate) as retried:
        main(page).get_by_role("button", name=TRY_AGAIN, exact=True).click()
    expect(field(page, "Russian meaning")).to_have_value(GENERATED_VOCABULARY["russian"])
    assert retried.value.post_data_json == first.value.post_data_json


@pytest.mark.p1
def test_a_sentence_draft_has_no_example_and_its_note_is_empty(page: Page) -> None:
    """AC-15: a generated Sentence Draft fills its own fields, with no Example and no Clear,
    and its null Note empty.
    """
    open_capture(page)
    stub_generated(page, "sentence")
    choose(page, "French", "Sentence")
    generate_draft(page).click()

    expect(field(page, "Russian meaning")).to_have_value(GENERATED_SENTENCE["russian"])
    expect(field(page, "Hint")).to_have_value(GENERATED_SENTENCE["hint"])
    expect(field(page, "Note")).to_have_value("")
    expect(field(page, "Example")).to_have_count(0)
    expect(editor(page).get_by_role("button", name=CLEAR, exact=True)).to_have_count(0)


@pytest.mark.p1
def test_a_generated_draft_is_not_written_to_anki_before_save(page: Page) -> None:
    """AC-15: generating and editing a Draft sends no Save; only Save to Anki does (FR-18)."""
    requests = record_requests(page)
    open_capture(page)
    stub_generated(page)
    choose(page, "English", "Vocabulary")
    generate_draft(page).click()

    field(page, "Mnemonic").fill("a leap over the facts")

    expect(field(page, "Mnemonic")).to_have_value("a leap over the facts")
    assert not [url for url in requests if "/api/items/" in url]


@pytest.mark.p1
def test_the_generation_context_stays_in_the_screens_memory(page: Page) -> None:
    """AC-13: the Generation context is never in the URL, `history.state`, local or session
    storage, or the Save's `item` part (AD-13).
    """
    open_capture(page)
    stub_generated(page)
    choose(page, "English", "Vocabulary")
    generation_context(page).fill(CONTEXT)
    generate_draft(page).click()
    expect(field(page, "Russian meaning")).to_have_value(GENERATED_VOCABULARY["russian"])

    kept = page.evaluate(
        "() => JSON.stringify("
        "[location.href, history.state, {...localStorage}, {...sessionStorage}])"
    )
    with page.expect_request(is_item_save) as sent:
        save_button(page).click()

    assert CONTEXT not in kept
    saved = item_part(sent.value)
    assert "generationContext" not in saved
    assert CONTEXT not in str(saved)


@pytest.mark.p1
def test_leaving_while_the_model_writes_asks_nothing_and_a_late_reply_opens_nothing(
    page: Page,
) -> None:
    """AC-15: no Draft exists until the reply, so going back to the Capture while "Writing your
    Draft…" shows raises no unsaved alert, and the reply that arrives after opens no editor.
    """
    open_capture(page)
    held = HeldRoute(page, GENERATE_API, method="POST")
    choose(page, "English", "Vocabulary")
    generate_draft(page).click()
    expect(main(page).get_by_role("status").filter(has_text=WRITING)).to_be_visible()

    main(page).get_by_role("link", name="‹ Capture", exact=True).click()

    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))
    expect(unsaved_alert(page)).to_have_count(0)
    held.fulfill_json(draft_reply(), status=201)
    expect(pane(page)).to_be_visible()
    expect(editor(page)).to_have_count(0)
    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))


@pytest.mark.p1
def test_leaving_a_failed_generation_asks_nothing(page: Page) -> None:
    """AC-17: a failed generation leaves no Draft, so going back to the Capture raises no
    unsaved alert.
    """
    open_capture(page)
    stub_api_error(page, GENERATE_API, status=502, code="llm_failed", method="POST")
    choose(page, "English", "Vocabulary")
    generate_draft(page).click()
    expect(main(page).get_by_role("alert")).to_contain_text(GENERATION_FAILED["llm_failed"][0])

    main(page).get_by_role("link", name="‹ Capture", exact=True).click()

    expect(page).to_have_url(path_pattern(f"{CAPTURES_PATH}/{CAPTURE_ID}"))
    expect(unsaved_alert(page)).to_have_count(0)
    expect(pane(page)).to_be_visible()


@pytest.mark.p1
def test_the_generation_context_is_used_once(page: Page) -> None:
    """AC-13: after the generated Draft is saved, the pane on the same Capture has an empty
    Generation context, so the next Draft doesn't send it again.
    """
    open_capture(page)
    stub_generated(page)
    choose(page, "English", "Vocabulary")
    generation_context(page).fill(CONTEXT)
    generate_draft(page).click()
    save_button(page).click()
    expect(banner(page, TARGET)).to_be_visible()

    expect(generation_context(page)).to_have_value("")

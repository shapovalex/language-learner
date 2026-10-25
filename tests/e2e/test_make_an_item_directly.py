"""Make an Item without a Capture (decided with the user 2026-10-25).

- **Start.** "Make an Item" beside Save Capture in the compose card opens the Make an Item pane
  at /captures/make for the typed compose text, with no Capture saved. Like Save Capture it is
  disabled while the compose box is blank. The pane's text is "Use as is" (the compose text) or
  a Custom value; its actions wait for a Language and a Category with the existing reason.
- **Draft.** "Write it myself" and "Generate Draft" open the same Draft flow as from a Capture,
  at /captures/make/draft: the editor, the automatic Reference audio, the duplicate check and
  Save to Anki. The Draft names no Capture, and its back link returns to the pane.
- **Save.** Back at /captures with "Saved “<Target>” to Anki." (no Capture sentence), the
  compose box cleared. Leaving the pane or the Draft keeps the compose text.
- **Captures untouched.** No Capture is made, read or deleted: the Captures list is the same
  before and after, also after a reload.

UI only, on the live server (FakeAnkiStore, FakeLlm, FakeSpeech): the tests act through roles
and labels and observe the page. The generation's hold and its one failure are page routes
that fall back to the live server.
"""

import re
import uuid

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support import viewports
from tests.support.audio_screen import audio_card, rendered_audio_bytes
from tests.support.captures_screen import (
    CAPTURES_PATH,
    SAVE,
    captures_list,
    compose_box,
    main,
    rows,
)
from tests.support.delete_item_screen import (
    CARDS,
    PERMANENT,
    cancel_button,
    delete_button,
    delete_dialog,
)
from tests.support.item_audio_screen import item_audio_card, item_voice, player_bytes
from tests.support.items_screen import (
    CANCEL,
    CHOOSE_REASON,
    CREATE_ANYWAY,
    CUSTOM_REASON,
    CUSTOM_VALUE,
    DRAFT_CHIP,
    DRAFT_LOSS,
    GENERATE_API,
    NOT_SAVED_TITLE,
    OPEN_EXISTING,
    TRY_AGAIN,
    USE_AS_IS,
    WRITING,
    choose,
    duplicate_sheet,
    editor,
    field,
    generate_draft,
    generation_context,
    is_generate,
    items_back_link,
    pane,
    save_button,
    sheet_button,
    write_it_myself,
)
from tests.support.maintain_items_screen import item_row, search_box
from tests.support.navigation import EN_ITEMS, FR_ITEMS, go_by_nav, path_pattern
from tests.support.unsaved import discard_button, keep_editing_button, unsaved_alert

MAKE_AN_ITEM = "Make an Item"
MAKE_PATH = "/captures/make"
MAKE_DRAFT_PATH = "/captures/make/draft"
BACK_TO_PANE = "‹ Make an Item"
BACK_TO_CAPTURES = "‹ Captures"
TEXT_REASON = "Type the text in New Capture."
NO_CAPTURES = "No Captures yet."
MODEL_UNREACHABLE = "Couldn't reach the model"
NOTHING_SAVED = "Nothing has been saved yet."
ANKI_DOWN = '{"error": {"code": "anki_unavailable", "message": "x", "requestId": "r"}}'

# Language → (its name, a Category, its Items destination, a Russian meaning)
LANGUAGES = {
    "en": ("English", "Vocabulary", EN_ITEMS, "делать поспешные выводы"),
    "fr": ("French", "Sentence", FR_ITEMS, "Не будем делать поспешных выводов."),
}
WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}

each_language = pytest.mark.parametrize("language", LANGUAGES)
each_width = pytest.mark.parametrize("width", WIDTHS)


def make_button(page: Page):
    return main(page).get_by_role("button", name=MAKE_AN_ITEM, exact=True)


def saved_flash(page: Page, target: str):
    return page.get_by_role("status").filter(has_text=f"Saved “{target}” to Anki.")


def unique(text: str) -> str:
    return f"{text} {uuid.uuid4().hex[:10]}"


def open_captures(page: Page, width: str) -> None:
    page.set_viewport_size(WIDTHS[width])
    page.goto(CAPTURES_PATH)


def capture_texts(page: Page) -> list[str]:
    """The Captures list's rows once it has loaded (none when it's empty)."""
    expect(captures_list(page).or_(main(page).get_by_text(NO_CAPTURES, exact=True))).to_be_visible()
    return rows(page).all_inner_texts()


def open_pane(page: Page, text: str) -> None:
    """Type `text` in New Capture, then "Make an Item"."""
    compose_box(page).fill(text)
    make_button(page).click()
    expect(page).to_have_url(path_pattern(MAKE_PATH))
    expect(pane(page)).to_be_visible()


def write_draft(page: Page, language: str, target: str) -> None:
    """The pane for `target` → Write it myself → the Russian meaning filled in."""
    name, category, _, russian = LANGUAGES[language]
    open_pane(page, target)
    choose(page, name, category)
    write_it_myself(page).click()
    expect(page).to_have_url(path_pattern(MAKE_DRAFT_PATH))
    expect(field(page, "Target")).to_have_value(target)
    field(page, "Russian meaning").fill(russian)


def save_draft(page: Page, target: str) -> None:
    save_button(page).click()
    expect(saved_flash(page, target)).to_have_text(f"Saved “{target}” to Anki.")
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(compose_box(page)).to_have_value("")


def expect_no_capture_copy(page: Page, width: str, *, generating: bool) -> None:
    """The Draft names no Capture: no "From Capture", and no back link to a Capture. Its back
    link returns to the pane, shown on the phone, and at every width while generating."""
    expect(page.get_by_text("From Capture")).to_have_count(0)
    expect(main(page).get_by_role("link", name="‹ Capture", exact=True)).to_have_count(0)
    back = main(page).get_by_role("link", name=BACK_TO_PANE, exact=True)
    if width == "phone" or generating:
        expect(back).to_be_visible()
        expect(back).to_have_attribute("href", MAKE_PATH)
    else:
        expect(back).to_have_count(0)


def open_item(page: Page, language: str, target: str) -> None:
    """Items → search the Target → open its row, as a learner would."""
    name, _, items, _ = LANGUAGES[language]
    go_by_nav(page, items)
    search_box(page, name).fill(target)
    item_row(page, target).click()
    expect(item_voice(page)).to_be_enabled()


def leave_to_captures(page: Page, width: str) -> None:
    """Discard the Draft (answering the alert), then, on the phone, the pane's back link."""
    editor(page).get_by_role("button", name="Discard", exact=True).click()
    discard_button(page).click()
    expect(page).to_have_url(path_pattern(MAKE_PATH))
    if width == "phone":
        main(page).get_by_role("link", name=BACK_TO_CAPTURES, exact=True).click()
    expect(page).to_have_url(re.compile(r"/captures(/make)?$"))


def expect_no_item(page: Page, language: str, target: str) -> None:
    """The Language's Items list has no Item with `target` (or no Items at all)."""
    name, _, items, _ = LANGUAGES[language]
    go_by_nav(page, items)
    nothing_yet = main(page).get_by_text(f"No {name} Items yet", exact=True)
    expect(search_box(page, name).or_(nothing_yet)).to_be_visible()
    if search_box(page, name).is_visible():
        search_box(page, name).fill(target)
        no_match = f"No {name} Items match “{target}”."
        expect(main(page).get_by_text(no_match, exact=True)).to_be_visible()
    expect(item_row(page, target)).to_have_count(0)


def expect_captures_unchanged(page: Page, before: list[str]) -> None:
    """The list as it was, also as the server answers it after a reload."""
    assert capture_texts(page) == before
    page.reload()
    assert capture_texts(page) == before


@pytest.mark.p0
@each_width
def test_make_an_item_is_disabled_while_the_compose_box_is_blank(page: Page, width: str) -> None:
    """Blank compose: "Make an Item" follows Save Capture's enabled rule, and /captures/make
    with no compose text (a reload, a direct visit) shows Captures."""
    open_captures(page, width)
    save = main(page).get_by_role("button", name=SAVE, exact=True)

    expect(make_button(page)).to_be_disabled()
    expect(save).to_be_disabled()
    compose_box(page).fill("   ")
    expect(make_button(page)).to_be_disabled()
    compose_box(page).fill("jump to conclusions")
    expect(make_button(page)).to_be_enabled()
    expect(save).to_be_enabled()

    page.goto(MAKE_PATH)
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(pane(page)).to_have_count(0)
    page.goto(MAKE_DRAFT_PATH)
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(editor(page)).to_have_count(0)


@pytest.mark.p0
@each_width
@each_language
def test_the_pane_waits_for_the_text_a_language_and_a_category(
    page: Page, language: str, width: str
) -> None:
    """Missing input: both actions are disabled with the reason until the text, Language and
    Category are set."""
    name, category, _, _ = LANGUAGES[language]
    open_captures(page, width)
    open_pane(page, unique("missing input"))

    expect(pane(page).get_by_role("radio", name=USE_AS_IS, exact=True)).to_be_checked()
    for action in (write_it_myself(page), generate_draft(page)):
        expect(action).to_be_disabled()
    expect(pane(page)).to_contain_text(CHOOSE_REASON)
    pane(page).get_by_role("button", name=name, exact=True).click()
    expect(write_it_myself(page)).to_be_disabled()
    pane(page).get_by_role("button", name=category, exact=True).click()
    expect(write_it_myself(page)).to_be_enabled()
    expect(generate_draft(page)).to_be_enabled()

    pane(page).get_by_role("radio", name=CUSTOM_VALUE, exact=True).check()
    expect(pane(page)).to_contain_text(CUSTOM_REASON)
    for action in (write_it_myself(page), generate_draft(page)):
        expect(action).to_be_disabled()
    pane(page).get_by_role("radio", name=USE_AS_IS, exact=True).check()
    expect(write_it_myself(page)).to_be_enabled()

    if width == "desktop":
        # The compose box stays beside the pane: a blank Target blocks Use as is
        compose_box(page).fill("")
        expect(pane(page)).to_contain_text(TEXT_REASON)
        for action in (write_it_myself(page), generate_draft(page)):
            expect(action).to_be_disabled()


@pytest.mark.p0
@each_width
@each_language
def test_write_it_myself_saves_an_item_with_its_automatic_audio_and_no_capture(
    page: Page, language: str, width: str
) -> None:
    """Write: type text → Make an Item → Write it myself → Save to Anki → the Item opened from
    search plays the automatic clip, and the Captures list is unchanged."""
    target = unique("make it directly")
    open_captures(page, width)
    before = capture_texts(page)

    write_draft(page, language, target)
    expect(main(page)).to_contain_text(DRAFT_CHIP)
    expect_no_capture_copy(page, width, generating=False)
    expect(audio_card(page).locator("audio")).to_have_count(1)
    [drafted] = rendered_audio_bytes(page)

    # A failed Save keeps the Draft and its text; Save again stores it
    failures = [1]

    def fail_once(route: Route) -> None:
        if route.request.method == "POST" and failures:
            failures.pop()
            route.fulfill(status=503, content_type="application/json", body=ANKI_DOWN)
            return
        route.fallback()

    page.route(f"**/api/items/{language}", fail_once)
    save_button(page).click()
    expect(main(page).get_by_role("alert").filter(has_text=NOT_SAVED_TITLE)).to_be_visible()
    expect(page).to_have_url(path_pattern(MAKE_DRAFT_PATH))
    expect(field(page, "Target")).to_have_value(target)
    expect(field(page, "Russian meaning")).to_have_value(LANGUAGES[language][3])
    save_draft(page, target)

    expect_captures_unchanged(page, before)
    open_item(page, language, target)
    expect(item_audio_card(page).locator("audio")).to_have_count(1)
    assert player_bytes(page) == [drafted]

    # Four Cards: the Item's Delete confirmation names them; Cancel keeps the Item
    delete_button(page).click()
    expect(delete_dialog(page, target)).to_contain_text(PERMANENT)
    expect(delete_dialog(page, target).get_by_role("listitem")).to_have_text(list(CARDS))
    cancel_button(page, target).click()
    expect(delete_dialog(page, target)).to_be_hidden()


@pytest.mark.p0
@each_width
@each_language
def test_generate_draft_saves_an_item_with_its_automatic_audio_and_no_capture(
    page: Page, language: str, width: str
) -> None:
    """Generate: the generating screen, then the Draft from the model with its automatic audio;
    Save as for Write."""
    name, category, _, _ = LANGUAGES[language]
    target = unique("generate it directly")
    context = "Heard in a meeting, said about a hasty post-mortem."
    held: list[Route] = []
    page.route(f"**{GENERATE_API}", lambda route: held.append(route))
    open_captures(page, width)
    before = capture_texts(page)

    open_pane(page, target)
    choose(page, name, category)
    generation_context(page).fill(context)
    with page.expect_request(is_generate) as asked:
        generate_draft(page).click()
    expect(page).to_have_url(path_pattern(MAKE_DRAFT_PATH))
    expect(main(page).get_by_text(WRITING)).to_be_visible()
    expect_no_capture_copy(page, width, generating=True)
    assert asked.value.post_data_json["generationContext"] == context
    held.pop().fallback()

    expect(field(page, "Target")).to_have_value(target)
    expect(field(page, "Russian meaning")).not_to_have_value("")
    expect(audio_card(page).locator("audio")).to_have_count(1)
    [drafted] = rendered_audio_bytes(page)
    save_draft(page, target)

    expect_captures_unchanged(page, before)
    open_item(page, language, target)
    assert player_bytes(page) == [drafted]


@pytest.mark.p1
@each_width
@each_language
def test_a_failed_generation_offers_try_again_with_no_capture_copy(
    page: Page, language: str, width: str
) -> None:
    """Generate failure: the existing alert, saying nothing was saved instead of naming a
    Capture; Try again then opens the Draft."""
    name, category, _, _ = LANGUAGES[language]
    target = unique("generate again")
    failures = [1]

    def fail_once(route: Route) -> None:
        if failures:
            failures.pop()
            route.fulfill(
                status=502,
                content_type="application/json",
                body='{"error": {"code": "llm_failed", "message": "x", "requestId": "r"}}',
            )
            return
        route.fallback()

    page.route(f"**{GENERATE_API}", fail_once)
    open_captures(page, width)
    before = capture_texts(page)
    open_pane(page, target)
    choose(page, name, category)
    generate_draft(page).click()

    alert = main(page).get_by_role("alert").filter(has_text=MODEL_UNREACHABLE)
    expect(alert).to_contain_text(NOTHING_SAVED)
    expect(alert).not_to_contain_text("Capture")
    alert.get_by_role("button", name=TRY_AGAIN, exact=True).click()
    expect(field(page, "Target")).to_have_value(target)

    # Back to Captures, the Draft discarded and the compose text cleared: the list as it was
    leave_to_captures(page, width)
    compose_box(page).fill("")
    expect_captures_unchanged(page, before)


@pytest.mark.p0
@each_width
@each_language
def test_a_duplicate_opens_the_existing_sheet(page: Page, language: str, width: str) -> None:
    """Duplicate: a Target already saved opens the sheet; Cancel returns to the Draft, Create
    anyway saves, and Open existing asks about the Draft, then opens the match."""
    target = unique("duplicate directly")
    open_captures(page, width)
    before = capture_texts(page)
    write_draft(page, language, target)
    save_draft(page, target)

    write_draft(page, language, target)
    save_button(page).click()
    expect(duplicate_sheet(page)).to_be_visible()
    sheet_button(page, CANCEL).click()
    expect(duplicate_sheet(page)).to_have_count(0)
    expect(field(page, "Target")).to_have_value(target)
    save_button(page).click()
    sheet_button(page, CREATE_ANYWAY).click()
    expect(saved_flash(page, target)).to_be_visible()
    expect(compose_box(page)).to_have_value("")

    write_draft(page, language, target)
    save_button(page).click()
    sheet_button(page, OPEN_EXISTING).click()
    expect(unsaved_alert(page)).to_contain_text(DRAFT_LOSS)
    discard_button(page).click()
    expect(page).to_have_url(re.compile(rf"/{language}/items/[^/]+$"))
    name, _, items, _ = LANGUAGES[language]
    main(page).get_by_role("link", name=items_back_link(name), exact=True).click()
    expect(page).to_have_url(path_pattern(items.path))
    search_box(page, name).fill(target)
    expect(item_row(page, target)).to_have_count(2)

    page.goto(CAPTURES_PATH)
    expect_captures_unchanged(page, before)


@pytest.mark.p0
@each_width
@each_language
def test_leaving_the_draft_asks_and_keeps_the_compose_text(
    page: Page, language: str, width: str
) -> None:
    """Leave: back from the Draft asks "This Draft isn't saved."; Keep editing keeps it, and
    Discard returns to the pane with the compose text kept and nothing saved."""
    target = unique("leave directly")
    open_captures(page, width)
    before = capture_texts(page)
    write_draft(page, language, target)

    page.go_back()
    expect(unsaved_alert(page)).to_contain_text(DRAFT_LOSS)
    keep_editing_button(page).click()
    expect(page).to_have_url(path_pattern(MAKE_DRAFT_PATH))
    expect(field(page, "Russian meaning")).not_to_have_value("")

    editor(page).get_by_role("button", name="Discard", exact=True).click()
    expect(unsaved_alert(page)).to_contain_text(DRAFT_LOSS)
    discard_button(page).click()
    expect(page).to_have_url(path_pattern(MAKE_PATH))
    expect(pane(page)).to_be_visible()
    expect(editor(page)).to_have_count(0)

    if width == "phone":
        main(page).get_by_role("link", name=BACK_TO_CAPTURES, exact=True).click()
        expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    expect(compose_box(page)).to_have_value(target)
    assert capture_texts(page) == before

    # Leave discarded it: no Item was stored
    compose_box(page).fill("")
    expect_no_item(page, language, target)


@pytest.mark.p1
def test_save_capture_beside_the_make_pane_shows_the_saved_capture(page: Page) -> None:
    """Desktop: Save Capture while the make pane is open leaves no dead pane: the saved
    Capture opens in its place."""
    text = unique("saved beside the pane")
    open_captures(page, "desktop")
    open_pane(page, text)
    main(page).get_by_role("button", name=SAVE, exact=True).click()

    expect(page).to_have_url(re.compile(r"/captures/(?!make$)[^/]+$"))
    expect(compose_box(page)).to_have_value("")
    expect(main(page).get_by_role("article")).to_contain_text(text)
    expect(rows(page).filter(has_text=text)).to_have_count(1)
    expect(pane(page).get_by_role("radio", name=USE_AS_IS, exact=True)).to_be_checked()

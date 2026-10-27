"""Target helpers red phase: Check grammar under the Draft editor's Target (plan
target-grammar-check-and-cefr-examples, AC-1 and AC-2).

- **Check grammar.** Under Target, "Check grammar" asks POST /api/helpers/grammar with the
  Draft's Language, Category and Target, then shows the verdict there. A wrong Target also
  shows the corrected text and a Russian explanation; "Use correction" replaces the Target
  input and the Draft's title. Nothing changes until the user presses it.
- **Disabled while blank.** Check grammar is disabled while Target is blank, and the compose
  card's "Example sentences" while the compose box is blank, like Make an Item.

The Draft is reached as a learner would (compose → Make an Item → Write it myself) on the live
server; the grammar route is the per-test `GrammarApi` double. Secondary branches kept for the
green phase: the same check in Item edit (the shared editor), and a correct verdict.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.captures_screen import CAPTURES_PATH, compose_box, main
from tests.support.examples_screen import examples_button
from tests.support.grammar_screen import (
    CHECK_GRAMMAR,
    CORRECTED_TARGET,
    EXPLANATION,
    USE_CORRECTION,
    WRONG_TARGET,
    GrammarApi,
    check_grammar,
    draft_title,
    is_grammar_check,
    item_editor,
    use_correction,
)
from tests.support.items_screen import TRY_AGAIN, choose, editor, field, pane, write_it_myself
from tests.support.maintain_items_screen import EditableItemApi, edit_field, stored_item, stub_items
from tests.support.navigation import path_pattern
from tests.support.unsaved import discard_button

MAKE_PATH = "/captures/make"
MAKE_DRAFT_PATH = "/captures/make/draft"


def write_draft(page: Page, target: str) -> None:
    """Desktop Captures → type `target` → Make an Item → English, Sentence → Write it myself."""
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill(target)
    main(page).get_by_role("button", name="Make an Item", exact=True).click()
    choose(page, "English", "Sentence")
    write_it_myself(page).click()
    expect(page).to_have_url(path_pattern(MAKE_DRAFT_PATH))
    expect(field(page, "Target")).to_have_value(target)


@pytest.mark.p0
def test_check_grammar_shows_the_correction_and_use_correction_replaces_the_target(
    page: Page,
) -> None:
    """[P0] AC-1 a wrong Target: Check grammar shows "He goes to school." and the Russian
    explanation under Target, changing nothing; Use correction replaces the Target input and
    the Draft's title.
    """
    grammar = GrammarApi(page)
    write_draft(page, WRONG_TARGET)
    with page.expect_request(is_grammar_check):
        check_grammar(page).click()

    expect(editor(page).get_by_text(CORRECTED_TARGET, exact=True)).to_be_visible()

    expect(editor(page)).to_contain_text(EXPLANATION)
    expect(field(page, "Target")).to_have_value(WRONG_TARGET)
    expect(draft_title(page, WRONG_TARGET)).to_be_visible()
    assert grammar.requests == [{"language": "en", "category": "sentence", "target": WRONG_TARGET}]
    use_correction(page).click()
    expect(field(page, "Target")).to_have_value(CORRECTED_TARGET)
    expect(draft_title(page, CORRECTED_TARGET)).to_be_visible()
    assert len(grammar.requests) == 1


@pytest.mark.p1
def test_check_grammar_and_example_sentences_are_disabled_while_blank(page: Page) -> None:
    """[P1] AC-2 a blank Target disables Check grammar; a blank compose box disables Example
    sentences. Typing text enables each.
    """
    grammar = GrammarApi(page)
    write_draft(page, WRONG_TARGET)
    field(page, "Target").fill("   ")

    expect(check_grammar(page)).to_be_disabled()

    field(page, "Target").fill(WRONG_TARGET)
    expect(check_grammar(page)).to_be_enabled()
    assert grammar.requests == []

    # Back to the pane, the compose box beside it on desktop
    editor(page).get_by_role("button", name="Discard", exact=True).click()
    discard_button(page).click()
    expect(page).to_have_url(path_pattern(MAKE_PATH))
    expect(pane(page)).to_be_visible()
    expect(examples_button(page)).to_be_enabled()
    compose_box(page).fill("")
    expect(examples_button(page)).to_be_disabled()
    compose_box(page).fill("   ")
    expect(examples_button(page)).to_be_disabled()
    compose_box(page).fill("jump to conclusions")
    expect(examples_button(page)).to_be_enabled()


def open_item_edit(page: Page) -> dict:
    """Desktop Item detail of a stored English Item whose Target is `WRONG_TARGET`."""
    page.set_viewport_size(viewports.DESKTOP)
    row = stored_item(target=WRONG_TARGET)
    api = EditableItemApi(page, row)
    stub_items(page, [row])
    api.open(page)
    expect(edit_field(page, "Target")).to_have_value(WRONG_TARGET)
    return row


@pytest.mark.p1
def test_check_grammar_in_item_edit_and_use_correction_replaces_the_target(page: Page) -> None:
    """[P1] AC-1 Item edit shares the editor: Check grammar shows the correction under Target;
    Use correction replaces the Target input and the Item's title.
    """
    grammar = GrammarApi(page)
    open_item_edit(page)
    form = item_editor(page)
    with page.expect_request(is_grammar_check):
        form.get_by_role("button", name=CHECK_GRAMMAR, exact=True).click()

    expect(form.get_by_text(CORRECTED_TARGET, exact=True)).to_be_visible()

    expect(form).to_contain_text(EXPLANATION)
    expect(edit_field(page, "Target")).to_have_value(WRONG_TARGET)
    assert grammar.requests == [
        {"language": "en", "category": "vocabulary", "target": WRONG_TARGET}
    ]
    form.get_by_role("button", name=USE_CORRECTION, exact=True).click()
    expect(edit_field(page, "Target")).to_have_value(CORRECTED_TARGET)
    expect(draft_title(page, CORRECTED_TARGET)).to_be_visible()


@pytest.mark.p1
def test_a_failed_grammar_check_shows_try_again_and_keeps_the_target(page: Page) -> None:
    """[P1] AC-5 the grammar helper answers 502 llm_failed: an alert with Try again under
    Target, the Target unchanged.
    """
    grammar = GrammarApi(page, error="llm_failed")
    open_item_edit(page)
    form = item_editor(page)
    with page.expect_request(is_grammar_check):
        form.get_by_role("button", name=CHECK_GRAMMAR, exact=True).click()

    alert = form.get_by_role("alert").filter(has_text="Couldn't reach the model")
    expect(alert.get_by_role("button", name=TRY_AGAIN, exact=True)).to_be_visible()

    expect(edit_field(page, "Target")).to_have_value(WRONG_TARGET)
    expect(draft_title(page, WRONG_TARGET)).to_be_visible()
    expect(form.get_by_role("button", name=USE_CORRECTION, exact=True)).to_have_count(0)
    assert len(grammar.requests) == 1

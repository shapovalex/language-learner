"""Target helpers red phase: CEFR Example sentences on the Captures screen (plan
target-grammar-check-and-cefr-examples, AC-3 to AC-5).

- **Generate.** "Example sentences" in the compose card opens a pane at /captures/examples for
  the compose text. Choose a Language, optionally add context, press Generate: six groups A1 to
  C2, each with 5 sentences and their Russian.
- **Make an Item.** A sentence's "Make an Item" puts it into the compose box and opens a
  Sentence Draft at /captures/make/draft in the examples Language, with the sentence as Target
  and its shown Russian as Russian meaning; the model isn't asked again and no Capture is
  created. Discarding the Draft leads to the Make an Item pane with the Language chosen.
- **Failure.** A failed generation shows an alert with "Try again"; the compose text is
  unchanged, and Try again asks the same again.

Desktop Captures on the live server; the examples route is the per-test `ExamplesApi` double.
Secondary branches kept for the green phase: a fresh mount at /captures/examples redirects to
/captures, and the context is never kept (AD-13).
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.captures_screen import API, CAPTURES_PATH, compose_box, main
from tests.support.examples_screen import (
    CONTEXT,
    EXAMPLES_PATH,
    EXAMPLES_REPLY,
    LEVELS,
    MAKE_AN_ITEM,
    PHRASE,
    SENTENCES_PER_LEVEL,
    ExamplesApi,
    example,
    examples_button,
    examples_context,
    examples_language,
    examples_pane,
    generate_button,
    is_examples,
    level_group,
    level_groups,
    sentence_item,
    sentence_items,
)
from tests.support.items_screen import (
    TRY_AGAIN,
    USE_AS_IS,
    choice,
    field,
    pane,
)
from tests.support.navigation import path_pattern
from tests.support.network import record_json_bodies, stub_api_error
from tests.support.unsaved import discard_button

MAKE_PATH = "/captures/make"
MAKE_DRAFT_PATH = "/captures/make/draft"
MODEL_UNREACHABLE = "Couldn't reach the model"
GENERATE_API = "/api/drafts/generate"
BLANK_DRAFT_API = "/api/drafts/blank"
BLANK_FAILURE = "No ItemId today"


def open_examples(page: Page, text: str = PHRASE) -> None:
    """Desktop Captures → type `text` → Example sentences."""
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill(text)
    examples_button(page).click()
    expect(page).to_have_url(path_pattern(EXAMPLES_PATH))
    expect(examples_pane(page)).to_be_visible()


def generate(page: Page, language: str = "English", context: str | None = None) -> None:
    examples_language(page, language).click()
    if context is not None:
        examples_context(page).fill(context)
    generate_button(page).click()


@pytest.mark.p0
def test_generate_shows_six_cefr_groups_of_five_sentences_with_russian(page: Page) -> None:
    """[P0] AC-3 compose "jump to conclusions" → Example sentences → English, context →
    Generate: groups A1, A2, B1, B2, C1, C2, each with its 5 sentences and their Russian.
    """
    examples = ExamplesApi(page)
    open_examples(page)
    with page.expect_request(is_examples):
        generate(page, context=CONTEXT)

    expect(level_groups(page)).to_have_count(len(LEVELS))

    for level in LEVELS:
        items = sentence_items(page, level)
        expect(items).to_have_count(SENTENCES_PER_LEVEL)
        for n in range(1, SENTENCES_PER_LEVEL + 1):
            expected = example(level, n)
            item = items.nth(n - 1)
            expect(item).to_contain_text(expected["sentence"])
            expect(item).to_contain_text(expected["russian"])
    assert examples.requests == [{"language": "en", "target": PHRASE, "context": CONTEXT}]
    expect(compose_box(page)).to_have_value(PHRASE)


@pytest.mark.p0
def test_a_sentences_make_an_item_opens_its_sentence_draft_with_its_russian(page: Page) -> None:
    """[P0] AC-4 a B1 sentence's Make an Item: the Draft editor at /captures/make/draft as an
    English Sentence, Target the sentence and Russian meaning its Russian; no Draft generation
    and no POST /api/captures are sent. Discard returns to the pane with the sentence and English.
    """
    capture_saves = record_json_bodies(page, API)
    generations: list[str] = []
    page.on(
        "request",
        lambda request: (
            generations.append(request.url) if request.url.endswith(GENERATE_API) else None
        ),
    )
    ExamplesApi(page)
    open_examples(page)
    generate(page)
    picked = EXAMPLES_REPLY["levels"][2]["sentences"][0]
    sentence, russian = picked["sentence"], picked["russian"]
    expect(level_group(page, "B1")).to_contain_text(sentence)
    sentence_item(page, sentence).get_by_role("button", name=MAKE_AN_ITEM, exact=True).click()

    expect(page).to_have_url(path_pattern(MAKE_DRAFT_PATH))
    expect(field(page, "Target")).to_have_value(sentence)
    expect(field(page, "Russian meaning")).to_have_value(russian)
    expect(main(page)).to_contain_text("English Sentence")
    assert generations == []
    assert capture_saves == []

    main(page).get_by_role("button", name="Discard", exact=True).click()
    discard_button(page).click()
    expect(page).to_have_url(path_pattern(MAKE_PATH))
    expect(compose_box(page)).to_have_value(sentence)
    expect(pane(page).get_by_role("radio", name=USE_AS_IS, exact=True)).to_be_checked()
    expect(choice(page, "English")).to_have_attribute("aria-pressed", "true")


@pytest.mark.p1
def test_a_failed_draft_request_opens_the_pane_with_its_language_and_the_error(
    page: Page,
) -> None:
    """[P1] the Draft's ItemId request fails: the Make an Item pane opens for the sentence with
    the Language the sentences were written in (not the picker's later choice) and the failure.
    """
    stub_api_error(page, BLANK_DRAFT_API, status=500, code="internal", message=BLANK_FAILURE)
    ExamplesApi(page)
    open_examples(page)
    generate(page)
    examples_language(page, "French").click()
    sentence = EXAMPLES_REPLY["levels"][0]["sentences"][0]["sentence"]
    sentence_item(page, sentence).get_by_role("button", name=MAKE_AN_ITEM, exact=True).click()

    expect(page).to_have_url(path_pattern(MAKE_PATH))
    expect(pane(page)).to_contain_text(BLANK_FAILURE)
    expect(choice(page, "English")).to_have_attribute("aria-pressed", "true")
    expect(compose_box(page)).to_have_value(sentence)


@pytest.mark.p1
def test_a_failed_generation_shows_try_again_and_keeps_the_compose_text(page: Page) -> None:
    """[P1] AC-5 the examples helper answers 502 llm_failed: an alert with Try again, the
    compose text unchanged; Try again sends the same request and shows the groups.
    """
    examples = ExamplesApi(page, error="llm_failed")
    open_examples(page)
    generate(page, context=CONTEXT)

    alert = main(page).get_by_role("alert").filter(has_text=MODEL_UNREACHABLE)
    expect(alert.get_by_role("button", name=TRY_AGAIN, exact=True)).to_be_visible()

    expect(compose_box(page)).to_have_value(PHRASE)
    expect(level_groups(page)).to_have_count(0)
    examples.error = None
    with page.expect_request(is_examples):
        alert.get_by_role("button", name=TRY_AGAIN, exact=True).click()
    expect(level_groups(page)).to_have_count(len(LEVELS))
    assert len(examples.requests) == 2
    assert examples.requests[1] == examples.requests[0]
    expect(compose_box(page)).to_have_value(PHRASE)

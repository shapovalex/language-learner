"""Regenerate example in the Vocabulary Draft editor (plan item-example-and-capture-improvements,
item 1).

The Draft editor has the same choices panel as Item detail: "Regenerate example" after the
Example in Russian opens "Example · choose" with an optional context and Generate, which asks
POST /api/helpers/example-choices with the Draft's Language, Target, the context and its Russian
meaning. "Use this example" fills Example and Example in Russian and closes the panel; nothing
reaches Anki before Save to Anki, which then carries the pair. A Sentence Draft has no
Regenerate example.

Desktop Captures on the live server; the example-choices route is the per-test
`ExampleChoicesApi` double, and the Save a page route that records the `item` part.
"""

import uuid
from typing import Any

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support import viewports
from tests.support.captures_screen import CAPTURES_PATH, compose_box, main
from tests.support.items_screen import (
    TRY_AGAIN,
    choose,
    field,
    item_part,
    pane,
    save_button,
    stub_duplicates,
    write_it_myself,
)
from tests.support.navigation import path_pattern
from tests.support.regenerate_screen import (
    CHOICES,
    CHOICES_CONTEXT,
    GENERATE,
    KEEP_CURRENT,
    USE_THIS_EXAMPLE,
    ExampleChoicesApi,
    choice_rows,
    choices_context,
    choices_panel,
    pair_button,
)

MAKE_PATH = "/captures/make"
MAKE_DRAFT_PATH = "/captures/make/draft"
REGENERATE_EXAMPLE = "Regenerate example"
RUSSIAN = "делать поспешные выводы"


def regenerate_button(page: Page):
    return main(page).get_by_role("button", name=REGENERATE_EXAMPLE, exact=True)


def record_saves(page: Page) -> list[dict[str, Any]]:
    """Answer every Save of an English Item with its ItemId, recording its `item` part."""
    saves: list[dict[str, Any]] = []

    def handle(route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        part = item_part(route.request)
        saves.append(part)
        route.fulfill(json={"itemId": part["itemId"]})

    page.route("**/api/items/en", handle)
    return saves


def open_draft(page: Page, category: str = "Vocabulary") -> str:
    """Desktop Captures → compose text → Make an Item → English → Write it myself."""
    target = f"jump to conclusions {uuid.uuid4().hex[:8]}"
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)
    compose_box(page).fill(target)
    main(page).get_by_role("button", name="Make an Item", exact=True).click()
    expect(page).to_have_url(path_pattern(MAKE_PATH))
    expect(pane(page)).to_be_visible()
    choose(page, "English", category)
    write_it_myself(page).click()
    expect(page).to_have_url(path_pattern(MAKE_DRAFT_PATH))
    field(page, "Russian meaning").fill(RUSSIAN)
    return target


@pytest.mark.p0
def test_the_third_choice_fills_the_draft_and_save_carries_it(page: Page) -> None:
    """Matrix "Draft regenerate": 10 pairs listed; Use this example fills Example and Example in
    Russian and closes the panel; Save to Anki sends that pair with the Draft's Voice.
    """
    stub_duplicates(page, [])
    saves = record_saves(page)
    choices = ExampleChoicesApi(page)
    target = open_draft(page)

    regenerate_button(page).click()
    expect(choices_panel(page)).to_be_visible()
    expect(choices_context(page)).to_be_focused()
    choices_context(page).fill(CHOICES_CONTEXT)
    pair_button(choices_panel(page), GENERATE).click()

    expect(choice_rows(page)).to_have_count(10)
    assert choices.requests == [
        {"language": "en", "target": target, "context": CHOICES_CONTEXT, "meaning": RUSSIAN}
    ]
    third = CHOICES["sentences"][2]
    choice_rows(page).nth(2).get_by_role("button", name=USE_THIS_EXAMPLE).click()

    expect(choices_panel(page)).to_have_count(0)
    expect(field(page, "Example")).to_have_value(third["sentence"])
    expect(field(page, "Example in Russian")).to_have_value(third["russian"])
    expect(regenerate_button(page)).to_be_focused()
    assert saves == []

    save_button(page).click()
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))
    [saved] = saves
    assert saved["example"] == third["sentence"]
    assert saved["exampleRussian"] == third["russian"]
    assert saved.get("exampleVoice")


@pytest.mark.p1
def test_keep_current_closes_the_panel_and_leaves_the_fields(page: Page) -> None:
    ExampleChoicesApi(page)
    open_draft(page)

    regenerate_button(page).click()
    pair_button(choices_panel(page), GENERATE).click()
    expect(choice_rows(page)).to_have_count(10)
    pair_button(choices_panel(page), KEEP_CURRENT).click()

    expect(choices_panel(page)).to_have_count(0)
    expect(field(page, "Example")).to_have_value("")
    expect(regenerate_button(page)).to_be_focused()


@pytest.mark.p1
def test_a_model_failure_shows_try_again_and_keeps_the_fields(page: Page) -> None:
    choices = ExampleChoicesApi(page, error="llm_failed")
    open_draft(page)
    field(page, "Example").fill("My own example.")

    regenerate_button(page).click()
    pair_button(choices_panel(page), GENERATE).click()
    alert = choices_panel(page).get_by_role("alert")
    expect(alert).to_contain_text("Couldn't reach the model")
    expect(alert).to_contain_text("Your Draft is unchanged.")
    expect(field(page, "Example")).to_have_value("My own example.")

    choices.error = None
    alert.get_by_role("button", name=TRY_AGAIN).click()
    expect(choice_rows(page)).to_have_count(10)
    assert len(choices.requests) == 2


@pytest.mark.p1
def test_a_sentence_draft_has_no_regenerate_example(page: Page) -> None:
    open_draft(page, "Sentence")
    expect(field(page, "Note")).to_be_visible()
    expect(regenerate_button(page)).to_have_count(0)

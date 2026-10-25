"""Story 6.4: one Item's Reference audio through its whole life in the running app.

Unlike the 6.1 and 6.2 journeys, nothing here is a page-local API double: the app runs on the
live server (FakeAnkiStore, FakeSpeech). The journey acts only through roles and labels and
observes only the page: alerts, chips, list rows and the audio card's native players, whose
sources the in-page probes read because that is what the learner hears. The one route answers
the regeneration's Preview with SECOND_MP3, so the regenerated clip differs from the first.
The manual acceptance on the released wheel is
_bmad-output/test-artifacts/acceptance/reference-audio-acceptance-6-4.md.
"""

import re
import uuid

import pytest
from playwright.sync_api import Page, Route, ViewportSize, expect

from tests.support import viewports
from tests.support.audio import EN_VOICE, FR_VOICE, MP3, PREVIEW_API, SECOND_MP3
from tests.support.audio_screen import (
    STALE_AUDIO,
    audio_button,
    preview_button,
    rendered_audio_bytes,
    voice,
)
from tests.support.captures_screen import SAVE, compose_box, main, rows
from tests.support.delete_item_screen import confirm_button, delete_button
from tests.support.item_audio_screen import (
    REGENERATE_AUDIO,
    REMOVE_AUDIO,
    card_button,
    item_audio_card,
    item_voice,
    player_bytes,
)
from tests.support.items_screen import (
    banner,
    choose,
    field,
    items_back_link,
    save_button,
    write_it_myself,
)
from tests.support.maintain_items_screen import edit_field, item_row, save_changes, search_box
from tests.support.navigation import EN_ITEMS, FR_ITEMS, go_by_nav, path_pattern
from tests.support.regenerate_screen import USE_PREVIEW

LANGUAGES = {"en": ("English", EN_ITEMS), "fr": ("French", FR_ITEMS)}
VOICES = {"en": EN_VOICE, "fr": FR_VOICE}
WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}
ANY_UNSAVED = re.compile(r"^\d+ unsaved changes?$")


def unsaved(page: Page):
    return main(page).get_by_text(ANY_UNSAVED)


def make_item_with_audio(page: Page, language: str, target: str) -> bytes:
    """Capture → Draft → Preview → Use preview → Save; return the clip the Draft played."""
    name, _ = LANGUAGES[language]
    page.goto("/captures")
    compose_box(page).fill(target)
    main(page).get_by_role("button", name=SAVE, exact=True).click()
    rows(page).filter(has_text=target).click()
    choose(page, name, "Vocabulary")
    write_it_myself(page).click()
    field(page, "Russian meaning").fill("проверка аудио")
    voice(page).select_option(VOICES[language])
    expect(voice(page)).to_have_value(VOICES[language])
    preview_button(page).click()
    audio_button(page, USE_PREVIEW).click()
    expect(audio_button(page, USE_PREVIEW)).to_have_count(0)
    [previewed] = rendered_audio_bytes(page)
    save_button(page).click()
    expect(banner(page, target)).to_be_visible()
    return previewed


def open_item(page: Page, language: str, target: str) -> None:
    """Items → search the Target → open its row, as a learner would."""
    name, items = LANGUAGES[language]
    if "/items/" in page.url:  # Item detail has no Language nav, only its back link
        main(page).get_by_role("link", name=items_back_link(name), exact=True).click()
        page.wait_for_url(path_pattern(items.path))
    else:
        go_by_nav(page, items)
    search_box(page, name).fill(target)
    item_row(page, target).click()
    expect(item_voice(page)).to_be_enabled()


def save_item(page: Page) -> None:
    save_changes(page).click()
    expect(unsaved(page)).to_have_count(0)


@pytest.mark.p0
@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_one_items_reference_audio_from_preview_to_deletion(
    page: Page, language: str, width: str
) -> None:
    """[P0] Create, stale, regenerate, remove and delete one Item's audio, UI only."""
    viewport: ViewportSize = WIDTHS[width]
    page.set_viewport_size(viewport)
    target = f"reference audio journey {uuid.uuid4().hex[:12]}"

    # Create: the opened Item plays exactly the clip the Draft previewed.
    previewed = make_item_with_audio(page, language, target)
    assert previewed == MP3
    open_item(page, language, target)
    expect(item_audio_card(page).locator("audio")).to_have_count(1)
    assert player_bytes(page) == [previewed]

    # Stale: a Target edit warns and offers Regenerate audio; Save still works.
    edited = f"{target} edited"
    edit_field(page, "Target").fill(edited)
    expect(item_audio_card(page).get_by_text(STALE_AUDIO)).to_be_visible()
    expect(card_button(page, REGENERATE_AUDIO)).to_be_enabled()
    save_item(page)
    expect(main(page).get_by_role("alert")).to_have_count(0)

    # Regenerate: the accepted second clip is the Item's after Save and a reopen.
    def second_clip(route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        route.fulfill(status=200, content_type="audio/mpeg", body=SECOND_MP3)

    page.route(f"**{PREVIEW_API}", second_clip)
    card_button(page, REGENERATE_AUDIO).click()
    card_button(page, USE_PREVIEW).click()
    expect(card_button(page, USE_PREVIEW)).to_have_count(0)
    save_item(page)
    open_item(page, language, edited)
    expect(item_audio_card(page).locator("audio")).to_have_count(1)
    assert player_bytes(page) == [SECOND_MP3]
    expect(item_audio_card(page).get_by_text(STALE_AUDIO)).to_be_hidden()

    # Remove: after Save and a reopen the card has no player.
    card_button(page, REMOVE_AUDIO).click()
    save_item(page)
    open_item(page, language, edited)
    expect(item_audio_card(page)).to_be_visible()
    expect(item_audio_card(page).locator("audio")).to_have_count(0)
    expect(card_button(page, REMOVE_AUDIO)).to_have_count(0)

    # Delete: back on the Items list, without that Item.
    _, items = LANGUAGES[language]
    delete_button(page).click()
    confirm_button(page, edited).click()
    expect(page).to_have_url(path_pattern(items.path))
    name, _ = LANGUAGES[language]
    nothing_yet = main(page).get_by_text(f"No {name} Items yet", exact=True)
    expect(search_box(page, name).or_(nothing_yet)).to_be_visible()
    if search_box(page, name).is_visible():  # other Items remain: search for the deleted one
        search_box(page, name).fill(edited)
        no_match = f"No {name} Items match “{edited}”."
        expect(main(page).get_by_text(no_match, exact=True)).to_be_visible()
    expect(item_row(page, edited)).to_have_count(0)

"""Example audio on Vocabulary Item detail (plan item-example-and-capture-improvements, item 2).

The "Example audio" card plays the Item's saved example clip (the read's `exampleAudio`) and
"Regenerate example audio" previews the buffer's Example in the Reference audio card's Voice.
Keep current drops the clip; Use new keeps it in memory as one unsaved change, and Save changes
uploads it as `exampleAudioFile`. API responses are per-page doubles
(tests/support/item_audio_screen.py): the stored example clip is SECOND_MP3 under its own name,
and every Preview answers MP3.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.audio import MP3, SECOND_MP3
from tests.support.audio_screen import TTS_ERROR, is_preview
from tests.support.captures_screen import main
from tests.support.item_audio_screen import (
    EXAMPLE_MEDIA_FAILED,
    NO_EXAMPLE,
    REGENERATE_EXAMPLE_AUDIO,
    USE_NEW,
    ItemAudioApi,
    example_audio_card,
    example_card_button,
    example_player_sources,
    item_voice,
)
from tests.support.items_screen import is_item_save
from tests.support.maintain_items_screen import edit_field, save_changes, stored_item
from tests.support.regenerate_screen import KEEP_CURRENT, unsaved_chip


def open_item(page: Page, api: ItemAudioApi) -> None:
    page.set_viewport_size(viewports.DESKTOP)
    api.open()
    # The example card speaks in the Reference audio card's Voice: wait for the Voices
    expect(item_voice(page).locator("option").first).to_be_attached()
    expect(example_card_button(page, REGENERATE_EXAMPLE_AUDIO)).to_be_enabled()


def regenerate_example(page: Page) -> None:
    with page.expect_response(lambda response: is_preview(response.request)):
        example_card_button(page, REGENERATE_EXAMPLE_AUDIO).click()


def save_and_wait(page: Page) -> None:
    with page.expect_response(lambda response: is_item_save(response.request)):
        save_changes(page).click()


@pytest.mark.p0
def test_an_item_with_example_audio_plays_its_saved_clip(page: Page) -> None:
    """Matrix "Example audio play": a player for /api/media/<exampleAudio>."""
    api = ItemAudioApi(page, stored_item(has_audio=True), example_audio=SECOND_MP3)
    open_item(page, api)

    expect(example_audio_card(page).locator("audio")).to_have_count(1)
    assert example_player_sources(page) == [f"/api/media/{api.example_name}"]


@pytest.mark.p0
def test_use_new_counts_as_unsaved_and_save_uploads_the_clip(page: Page) -> None:
    """Matrix "Example audio regenerate": the buffer's Example in the Voice, Use new, then Save
    uploads it as `exampleAudioFile`; the card then holds it as the current clip.
    """
    row = stored_item(has_audio=True)
    api = ItemAudioApi(page, row, example_audio=SECOND_MP3)
    open_item(page, api)
    voice = item_voice(page).input_value()

    regenerate_example(page)
    expect(example_card_button(page, USE_NEW)).to_be_visible()
    [sent] = api.preview_requests
    assert sent["target"] == row["example"]
    assert sent["voice"] == voice
    expect(unsaved_chip(page, 1)).to_be_visible()

    example_card_button(page, USE_NEW).click()
    expect(example_card_button(page, USE_NEW)).to_have_count(0)
    expect(unsaved_chip(page, 1)).to_be_visible()
    assert api.example_files == []

    save_and_wait(page)
    [uploaded] = api.example_files
    assert uploaded == MP3
    [saved] = api.saves
    assert saved.item["example"] == row["example"]
    expect(main(page).locator(".item-detail-unsaved")).to_be_hidden()
    expect(example_audio_card(page).locator("audio")).to_have_count(1)
    expect(example_card_button(page, REGENERATE_EXAMPLE_AUDIO)).to_be_visible()


@pytest.mark.p1
def test_keep_current_drops_the_clip_and_save_uploads_nothing(page: Page) -> None:
    api = ItemAudioApi(page, stored_item(has_audio=True), example_audio=SECOND_MP3)
    open_item(page, api)

    regenerate_example(page)
    example_card_button(page, KEEP_CURRENT).click()
    expect(example_card_button(page, USE_NEW)).to_have_count(0)
    assert example_player_sources(page) == [f"/api/media/{api.example_name}"]

    edit_field(page, "Mnemonic").fill("a change so Save sends something")
    save_and_wait(page)
    assert api.example_files == [None]


@pytest.mark.p1
def test_a_clip_for_an_edited_example_is_not_uploaded(page: Page) -> None:
    """The accepted clip goes only while it speaks the Example being saved."""
    api = ItemAudioApi(page, stored_item(has_audio=True), example_audio=SECOND_MP3)
    open_item(page, api)

    regenerate_example(page)
    example_card_button(page, USE_NEW).click()
    edit_field(page, "Example").fill("A different example sentence.")
    save_and_wait(page)

    assert api.example_files == [None]
    [saved] = api.saves
    assert saved.item.get("exampleVoice")
    # The withheld clip is dropped: the Item is clean again
    expect(main(page).locator(".item-detail-unsaved")).to_be_hidden()
    expect(example_card_button(page, USE_NEW)).to_have_count(0)


@pytest.mark.p1
def test_a_failed_preview_shows_try_again_and_keeps_the_current_clip(page: Page) -> None:
    api = ItemAudioApi(page, stored_item(has_audio=True), example_audio=SECOND_MP3)
    api.preview_error = True
    open_item(page, api)

    regenerate_example(page)
    alert = example_audio_card(page).get_by_role("alert").filter(has_text=TTS_ERROR)
    expect(alert).to_be_visible()
    assert example_player_sources(page) == [f"/api/media/{api.example_name}"]

    api.preview_error = False
    with page.expect_response(lambda response: is_preview(response.request)):
        alert.get_by_role("button", name="Try again").click()
    expect(example_card_button(page, USE_NEW)).to_be_visible()


@pytest.mark.p1
def test_a_blank_example_disables_the_card(page: Page) -> None:
    """Matrix "No example": the hint shows and the button is disabled."""
    api = ItemAudioApi(page, stored_item(has_audio=True, example="", exampleRussian=""))
    page.set_viewport_size(viewports.DESKTOP)
    api.open()
    expect(item_voice(page).locator("option").first).to_be_attached()

    card = example_audio_card(page)
    expect(card.get_by_text(NO_EXAMPLE, exact=True)).to_be_visible()
    button = card.get_by_role("button", name="Preview example audio", exact=True)
    expect(button).to_be_disabled()

    edit_field(page, "Example").fill("Now there is an example.")
    expect(card.get_by_text(NO_EXAMPLE, exact=True)).to_be_hidden()
    expect(button).to_be_enabled()


@pytest.mark.p1
def test_a_saved_example_clip_that_fails_to_load_says_so_and_edits_still_save(
    page: Page,
) -> None:
    """Matrix "Example audio play" error: the media read fails, the card says so without a
    player, and the editor still saves.
    """
    api = ItemAudioApi(page, stored_item(has_audio=True), example_audio=SECOND_MP3)
    del api.media[api.example_name]  # the media read answers 404
    open_item(page, api)

    card = example_audio_card(page)
    expect(card.get_by_text(EXAMPLE_MEDIA_FAILED, exact=True)).to_be_visible()
    expect(card.locator("audio")).to_have_count(0)
    expect(example_card_button(page, REGENERATE_EXAMPLE_AUDIO)).to_be_enabled()

    edit_field(page, "Mnemonic").fill("still editable")
    save_and_wait(page)
    [saved] = api.saves
    assert saved.item["mnemonic"] == "still editable"
    assert api.example_files == [None]

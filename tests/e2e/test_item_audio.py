"""Story 6.2 existing-Item Reference audio journeys at phone, tablet and desktop widths.

API responses are per-page doubles (tests/support/item_audio_screen.py). Every assertion
observes the real Item detail client: its native players' bytes or its outgoing multipart Save,
not only the configured double.
"""

import re
import uuid
from collections.abc import Callable

import pytest
from playwright.sync_api import BrowserContext, Page, Route, expect

from tests.support import viewports
from tests.support.audio import MP3, SECOND_MP3
from tests.support.audio_screen import (
    EN_SECOND,
    KEEP_CURRENT,
    PREVIEW_API,
    STALE_AUDIO,
    TTS_ERROR,
    USE_PREVIEW,
    is_preview,
)
from tests.support.captures_screen import main
from tests.support.duplicates import on_wire, sentence
from tests.support.item_audio_screen import (
    CURRENT_LABEL,
    PREVIEW_LABEL,
    REGENERATE_AUDIO,
    REMOVE_AUDIO,
    ItemAudioApi,
    card_alert,
    card_button,
    item_audio_card,
    item_voice,
    object_urls,
    player_bytes,
    record_object_urls,
    unsaved_chip,
)
from tests.support.items_screen import is_item_save
from tests.support.maintain_items_screen import edit_field, save_changes, stored_item

UNRELATED_EDIT = "a personal mnemonic kept through audio changes"
REMOVAL_NOTE = "Audio will be removed when you save."
KEEP_AUDIO = "Keep audio"
MEDIA_FAILED = "Couldn't load the saved audio."


def french_item() -> dict:
    return {**on_wire(str(uuid.uuid4()), sentence()), "hasAudio": True}


def regenerate(page: Page, api: ItemAudioApi) -> None:
    """Explicitly synthesize a Preview and wait for the compare pair to offer it."""
    with page.expect_response(lambda response: is_preview(response.request)):
        card_button(page, REGENERATE_AUDIO).click()
    expect(card_button(page, USE_PREVIEW)).to_be_visible()


def save_and_wait(page: Page) -> None:
    """Click Save changes and wait for its response, so the double has recorded the upload."""
    with page.expect_response(lambda response: is_item_save(response.request)):
        save_changes(page).click()


def open_item(page: Page, api: ItemAudioApi, viewport) -> None:
    page.set_viewport_size(viewport)
    api.open()
    expect(item_voice(page)).to_be_enabled()


class TestExistingItemAudio:
    @pytest.mark.p1
    def test_opening_an_item_plays_its_current_saved_clip(
        self, page: Page, new_context: Callable[..., BrowserContext]
    ) -> None:
        """[P1] AC-1 Item detail reads the Item and plays its saved clip from /api/media."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        page.set_viewport_size(viewports.PHONE)
        api.open()
        expect(item_audio_card(page).locator("audio")).to_have_count(1)

        assert player_bytes(page) == [SECOND_MP3]

        assert api.media_requests[0] == api.audio_name
        expect(card_button(page, REGENERATE_AUDIO)).to_be_visible()
        # A separate page: an Item without audio has the card but no play control.
        other = new_context().new_page()
        silent = ItemAudioApi(other, stored_item(has_audio=False), has_audio=False)
        silent.open()
        expect(item_audio_card(other)).to_be_visible()
        expect(item_audio_card(other).locator("audio")).to_have_count(0)
        assert silent.media_requests == []

    @pytest.mark.p1
    def test_keep_current_discards_the_preview_and_save_keeps_the_audio(self, page: Page) -> None:
        """[P1] AC-2 Regenerate shows Current vs Preview; Keep current leaves audio unchanged."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.DESKTOP)
        regenerate(page, api)
        expect(item_audio_card(page).get_by_text(CURRENT_LABEL, exact=True)).to_be_visible()
        expect(item_audio_card(page).get_by_text(PREVIEW_LABEL, exact=True)).to_be_visible()
        card_button(page, KEEP_CURRENT).click()

        expect(card_button(page, USE_PREVIEW)).to_have_count(0)

        assert player_bytes(page) == [SECOND_MP3]
        edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
        save_and_wait(page)
        (saved,) = api.saves
        assert saved.item["audio"] == "keep"
        assert saved.audio_file is None
        assert saved.item["mnemonic"] == UNRELATED_EDIT

    @pytest.mark.p0
    def test_use_preview_uploads_the_exact_clip_only_when_saved(self, page: Page) -> None:
        """[P0] AC-3 Use preview then Save changes uploads the previewed MP3 as audio=replace."""
        row = french_item()
        api = ItemAudioApi(page, row, lang="fr")
        open_item(page, api, viewports.PHONE)
        regenerate(page, api)
        card_button(page, USE_PREVIEW).click()
        writes_before_save = len(api.saves)
        save_and_wait(page)

        assert [save.audio_file for save in api.saves] == [MP3]

        assert writes_before_save == 0
        (saved,) = api.saves
        assert saved.item["audio"] == "replace"
        assert saved.item["itemId"] == row["itemId"]
        assert saved.content_type.startswith("multipart/form-data")
        assert api.preview_requests[0]["language"] == "fr"

    @pytest.mark.p0
    def test_remove_audio_is_local_until_save_sends_the_remove_intent(self, page: Page) -> None:
        """[P0] AC-4 Remove audio is an unsaved change; Save changes sends audio=remove."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.DESKTOP)
        card_button(page, REMOVE_AUDIO).click()
        expect(unsaved_chip(page, 1)).to_be_visible()
        writes_before_save = len(api.saves)
        save_and_wait(page)

        assert [save.item.get("audio") for save in api.saves] == ["remove"]

        assert writes_before_save == 0
        assert api.saves[0].audio_file is None
        assert api.saves[0].item["itemId"] == api.item_id

    @pytest.mark.p1
    def test_target_edit_warns_of_stale_audio_and_still_saves_with_keep(self, page: Page) -> None:
        """[P1] AC-5 a Target edit warns the audio is stale yet Save changes keeps it."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.PHONE)
        edit_field(page, "Target").fill("jump to a conclusion")

        expect(item_audio_card(page).get_by_text(STALE_AUDIO)).to_be_visible()

        expect(card_button(page, REGENERATE_AUDIO)).to_be_enabled()
        with page.expect_response(
            lambda response: (
                response.request.method == "POST" and response.url.endswith("/api/items/en")
            )
        ) as saved:
            save_changes(page).click()
        assert saved.value.status == 200
        (upload,) = api.saves
        assert upload.item["audio"] == "keep"
        assert upload.item["target"] == "jump to a conclusion"
        assert upload.audio_file is None
        assert api.preview_requests == []

    @pytest.mark.p0
    def test_changing_voice_never_synthesizes_or_writes(self, page: Page) -> None:
        """[P0] AC-9 a Voice change neither synthesizes nor writes; only Regenerate previews."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.DESKTOP)
        item_voice(page).select_option(EN_SECOND)
        expect(item_voice(page)).to_have_value(EN_SECOND)

        assert (len(api.preview_requests), len(api.saves)) == (0, 0)

        assert player_bytes(page) == [SECOND_MP3]
        regenerate(page, api)
        assert len(api.preview_requests) == 1
        assert api.preview_requests[0]["voice"] == EN_SECOND
        assert api.saves == []

    @pytest.mark.p0
    def test_failed_save_retains_the_pending_audio_and_retry_resends_it(self, page: Page) -> None:
        """[P0] AC-10 a failed Save keeps edits and the accepted clip; retry resends them."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.PHONE)
        edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
        regenerate(page, api)
        card_button(page, USE_PREVIEW).click()
        api.save_error = True
        save_and_wait(page)
        expect(main(page).get_by_role("alert").first).to_be_visible()
        expect(edit_field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        api.save_error = False
        save_and_wait(page)
        failed, retried = api.saves

        assert (retried.item["audio"], retried.audio_file) == (
            failed.item["audio"],
            failed.audio_file,
        )

        assert failed.item["audio"] == "replace"
        assert failed.audio_file == MP3
        assert retried.item["mnemonic"] == UNRELATED_EDIT
        assert retried.item["itemId"] == failed.item["itemId"]
        assert len(api.preview_requests) == 1

    @pytest.mark.p1
    def test_failed_preview_reports_and_keeps_the_current_clip(self, page: Page) -> None:
        """[P1] AC-11 a failed Preview shows the TTS alert and the current clip still plays."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.DESKTOP)
        api.preview_error = True
        card_button(page, REGENERATE_AUDIO).click()

        expect(card_alert(page, TTS_ERROR)).to_be_visible()

        assert player_bytes(page) == [SECOND_MP3]
        expect(card_button(page, USE_PREVIEW)).to_have_count(0)
        assert api.saves == []


class TestExistingItemAudioMatrix:
    @pytest.mark.p1
    def test_pending_removal_can_be_undone_at_tablet_width(self, page: Page) -> None:
        """[P1] AC-4 Keep audio undoes a pending removal: clean again, Save keeps the clip."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.TABLET)
        card_button(page, REMOVE_AUDIO).click()
        expect(card_button(page, KEEP_AUDIO)).to_be_focused()
        expect(item_audio_card(page).get_by_text(REMOVAL_NOTE)).to_be_visible()
        expect(item_audio_card(page).locator("audio")).to_have_count(0)
        expect(unsaved_chip(page, 1)).to_be_visible()

        card_button(page, KEEP_AUDIO).click()

        expect(card_button(page, REMOVE_AUDIO)).to_be_focused()
        expect(unsaved_chip(page, 1)).to_have_count(0)
        assert player_bytes(page) == [SECOND_MP3]
        edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
        save_and_wait(page)
        (saved,) = api.saves
        assert (saved.item["audio"], saved.audio_file) == ("keep", None)

    @pytest.mark.p1
    def test_voice_list_failure_offers_try_again(self, page: Page) -> None:
        """[P1] AC-9 a failed Voice list shows its alert; Try again loads the Voices."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        api.voices_error = True
        page.set_viewport_size(viewports.PHONE)
        api.open()
        expect(card_alert(page, "Couldn't load voices")).to_be_visible()
        expect(card_button(page, REGENERATE_AUDIO)).to_be_disabled()
        assert player_bytes(page) == [SECOND_MP3]

        api.voices_error = False
        item_audio_card(page).get_by_role("button", name="Try again").click()

        expect(card_button(page, REGENERATE_AUDIO)).to_be_enabled()
        assert api.preview_requests == []

    @pytest.mark.p1
    def test_item_without_audio_previews_and_discarding_leaves_nothing_pending(
        self, page: Page
    ) -> None:
        """[P1] AC-1 no audio: Preview instead of Regenerate, no Remove; discarding is clean."""
        api = ItemAudioApi(page, stored_item(has_audio=False), has_audio=False)
        open_item(page, api, viewports.DESKTOP)
        expect(card_button(page, REMOVE_AUDIO)).to_have_count(0)
        with page.expect_response(lambda response: is_preview(response.request)):
            card_button(page, "Preview").click()
        card_button(page, USE_PREVIEW).click()
        expect(unsaved_chip(page, 1)).to_be_visible()

        card_button(page, REMOVE_AUDIO).click()

        expect(unsaved_chip(page, 1)).to_have_count(0)
        expect(item_audio_card(page).locator("audio")).to_have_count(0)
        edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
        save_and_wait(page)
        (saved,) = api.saves
        assert (saved.item["audio"], saved.audio_file) == ("keep", None)

    @pytest.mark.p0
    def test_saved_replace_becomes_current_then_saved_remove_drops_the_player(
        self, page: Page
    ) -> None:
        """[P0] AC-3/AC-4 after Save the accepted clip is Current; a saved removal clears it."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.PHONE)
        regenerate(page, api)
        card_button(page, USE_PREVIEW).click()
        save_and_wait(page)
        expect(unsaved_chip(page, 1)).to_have_count(0)
        assert player_bytes(page) == [MP3]
        expect(item_audio_card(page).get_by_text(STALE_AUDIO)).to_be_hidden()

        card_button(page, REMOVE_AUDIO).click()
        save_and_wait(page)

        expect(unsaved_chip(page, 1)).to_have_count(0)
        expect(item_audio_card(page).locator("audio")).to_have_count(0)
        expect(card_button(page, "Preview")).to_be_visible()
        assert [save.item["audio"] for save in api.saves] == ["replace", "remove"]
        assert api.saves[1].audio_file is None
        assert api.audio_name is None

    @pytest.mark.p1
    def test_blob_urls_are_revoked_on_discard_and_on_leaving(self, page: Page) -> None:
        """[P1] Blob URLs go when a Preview is discarded and when the screen is left."""
        record_object_urls(page)
        api = ItemAudioApi(page, stored_item(has_audio=True))
        open_item(page, api, viewports.DESKTOP)
        regenerate(page, api)
        card_button(page, KEEP_CURRENT).click()
        expect(card_button(page, USE_PREVIEW)).to_have_count(0)
        first = object_urls(page)
        assert first["created"] and first["created"][0] in first["revoked"]

        regenerate(page, api)
        card_button(page, USE_PREVIEW).click()
        save_and_wait(page)
        expect(unsaved_chip(page, 1)).to_have_count(0)
        accepted = object_urls(page)["created"][-1]
        assert accepted not in object_urls(page)["revoked"]
        main(page).get_by_role("link", name=re.compile("Items$")).click()
        expect(page).to_have_url(re.compile(r"/en/items$"))

        assert accepted in object_urls(page)["revoked"]

    @pytest.mark.p1
    def test_a_preview_reply_after_leaving_opens_nothing(self, page: Page) -> None:
        """[P1] a Preview answering after the screen is left creates no clip and no card."""
        record_object_urls(page)
        api = ItemAudioApi(page, stored_item(has_audio=True))
        held: list[Route] = []
        # Registered last, so it answers first: the Preview stays pending until released
        page.route(f"**{PREVIEW_API}", lambda route: held.append(route))
        open_item(page, api, viewports.DESKTOP)
        with page.expect_request(is_preview):
            card_button(page, REGENERATE_AUDIO).click()
        main(page).get_by_role("link", name=re.compile("Items$")).click()
        expect(page).to_have_url(re.compile(r"/en/items$"))
        for _ in range(200):  # the route handler runs on a later dispatch; at most ~2 s
            if held:
                break
            page.wait_for_timeout(10)
        assert held, "the Preview request never reached its held route"
        (pending,) = held
        with page.expect_response(lambda response: is_preview(response.request)):
            pending.fulfill(status=200, content_type="audio/mpeg", body=MP3)

        assert object_urls(page)["created"] == []

        expect(item_audio_card(page)).to_have_count(0)
        assert api.saves == []

    @pytest.mark.p1
    def test_media_failure_leaves_the_card_without_a_clip_and_edits_save(self, page: Page) -> None:
        """[P1] AC-1 a clip that fails to load leaves no player; edits still save with keep."""
        api = ItemAudioApi(page, stored_item(has_audio=True))
        api.media = {}
        open_item(page, api, viewports.PHONE)

        expect(item_audio_card(page).get_by_text(MEDIA_FAILED)).to_be_visible()

        expect(item_audio_card(page).locator("audio")).to_have_count(0)
        edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
        save_and_wait(page)
        (saved,) = api.saves
        assert (saved.item["audio"], saved.audio_file) == ("keep", None)

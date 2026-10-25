"""Story 6.1 red-phase Draft Reference audio journeys at phone and desktop widths.

API responses are provider doubles. Every assertion observes the real client or its outgoing
multipart body, not only the configured double. Python Playwright has no outer promise matcher:
missing Voice/Preview controls currently stop the journey before its outcome assertion. That
red-phase limitation is recorded for task activation; later transitions need re-observation.
"""

import json
from collections.abc import Callable

import pytest
from playwright.sync_api import BrowserContext, Page, expect

from tests.support import viewports
from tests.support.audio import MP3, SECOND_MP3
from tests.support.audio_screen import (
    EN_FIRST,
    EN_SECOND,
    FR_FIRST,
    FR_SECOND,
    LOCALE_KEYS,
    STALE_AUDIO,
    DraftAudioApi,
    audio_button,
    audio_card,
    is_preview,
    is_voice_list,
    rendered_audio_bytes,
    storage_values,
    tts_alert,
    voice,
    voice_alert,
)
from tests.support.items_screen import (
    NOT_SAVED_TITLE,
    banner,
    editor,
    field,
    is_item_save,
    save_button,
)
from tests.support.regenerate_screen import KEEP_CURRENT, USE_PREVIEW
from tests.support.unsaved import discard_button

UNRELATED_EDIT = "a personal mnemonic kept through audio retries"


def discard_draft(page: Page) -> None:
    editor(page).get_by_role("button", name="Discard", exact=True).click()
    discard_button(page).click()


class TestDraftReferenceAudio:
    @pytest.mark.p1
    def test_locale_voice_preferences_survive_new_drafts_and_are_browser_local(
        self, page: Page, new_context: Callable[..., BrowserContext]
    ) -> None:
        """[P1] AC-3 each locale keeps its own selected Voice in this browser only."""
        # Given one browser chooses a different Voice in each locale.
        api = DraftAudioApi(page)
        api.open("en", viewports.DESKTOP)
        voice(page).select_option(EN_SECOND)
        discard_draft(page)
        api.open("fr", viewports.DESKTOP)
        voice(page).select_option(FR_SECOND)
        discard_draft(page)

        # When English is opened again, its preference survives the French selection.
        api.open("en", viewports.DESKTOP)

        # Then the independent English selection is restored, with no persisted Draft/Blob.
        expect(voice(page)).to_have_value(EN_SECOND)
        assert storage_values(page) == {
            LOCALE_KEYS["en-US"]: EN_SECOND,
            LOCALE_KEYS["fr-CA"]: FR_SECOND,
        }
        assert page.evaluate("() => sessionStorage.length") == 0
        assert page.evaluate("() => history.state") is None
        stored = json.dumps(page.context.storage_state())
        assert api.capture["text"] not in stored
        assert "blob:" not in stored

        # A second browser starts without either preference and cannot overwrite the first.
        other_page = new_context().new_page()
        other_page.goto("/captures")
        assert storage_values(other_page) == {}
        other = DraftAudioApi(other_page)
        other.open("fr", viewports.DESKTOP)
        voice(other_page).select_option(FR_FIRST)
        assert storage_values(page)[LOCALE_KEYS["en-US"]] == EN_SECOND
        assert storage_values(page)[LOCALE_KEYS["fr-CA"]] == FR_SECOND
        assert api.preview_requests == other.preview_requests == []
        assert api.saves == other.saves == []

    @pytest.mark.p1
    def test_keep_current_discards_the_preview_and_save_uses_the_keep_intent(
        self, page: Page
    ) -> None:
        """[P1] AC-5 Preview stays local; Keep current discards it and permits ordinary Save."""
        # Given a phone Draft with an explicit Preview and an unrelated local edit.
        api = DraftAudioApi(page)
        item_id = api.open("en", viewports.PHONE)
        field(page, "Mnemonic").fill(UNRELATED_EDIT)
        voice(page).select_option(EN_FIRST)
        api.synthesize()

        # When the user rejects the candidate, the compare controls disappear.
        audio_button(page, KEEP_CURRENT).click()

        # Then no candidate remains; Save retains its ordinary keep contract.
        expect(audio_button(page, USE_PREVIEW)).to_have_count(0)
        assert rendered_audio_bytes(page) == []
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        assert api.saves == []
        with page.expect_response(lambda response: is_item_save(response.request)):
            save_button(page).click()
        expect(banner(page, api.capture["text"])).to_be_visible()
        [saved] = api.saves
        assert saved.item["audio"] == "keep"
        assert saved.item["itemId"] == item_id
        assert saved.audio_file is None
        assert len(api.preview_requests) == 1

    @pytest.mark.p0
    def test_failed_binary_save_retains_the_candidate_and_retry_sends_the_same_bytes(
        self, page: Page
    ) -> None:
        """[P0] AC-11 a failed multipart Save retains edits and the exact accepted MP3 for retry."""
        # Given a phone Draft whose accepted Preview is held only in memory.
        api = DraftAudioApi(page)
        item_id = api.open("en", viewports.PHONE)
        field(page, "Mnemonic").fill(UNRELATED_EDIT)
        voice(page).select_option(EN_FIRST)
        api.preview_and_accept()
        api.save_error = True

        # When the binary multipart Save fails, the actual api.js envelope is displayed.
        with page.expect_response(lambda response: is_item_save(response.request)):
            save_button(page).click()

        # Then the failure keeps both the edit buffer and accepted playable candidate.
        expect(editor(page).get_by_role("alert").filter(has_text=NOT_SAVED_TITLE)).to_be_visible()
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        assert rendered_audio_bytes(page) == [MP3]
        api.save_error = False
        with page.expect_response(lambda response: is_item_save(response.request)):
            save_button(page).click()
        expect(banner(page, api.capture["text"])).to_be_visible()
        assert len(api.saves) == 2
        assert [upload.audio_file for upload in api.saves] == [MP3, MP3]
        assert [upload.item["audio"] for upload in api.saves] == ["replace", "replace"]
        assert [upload.item["itemId"] for upload in api.saves] == [item_id, item_id]
        assert all(upload.item["mnemonic"] == UNRELATED_EDIT for upload in api.saves)
        assert all(upload.content_type.startswith("multipart/form-data;") for upload in api.saves)
        assert len(api.preview_requests) == 1

    @pytest.mark.p1
    def test_changing_voice_keeps_the_candidate_until_an_explicit_new_preview(
        self, page: Page
    ) -> None:
        """[P1] AC-12 Voice selection alone never synthesizes or saves audio."""
        # Given a desktop Draft with a successfully accepted clip.
        api = DraftAudioApi(page)
        api.open("en", viewports.DESKTOP)
        voice(page).select_option(EN_FIRST)
        api.preview_and_accept()
        api.mp3 = SECOND_MP3

        # When Voice changes, the accepted clip stays attached; only Preview makes a new call.
        voice(page).select_option(EN_SECOND)
        retained = rendered_audio_bytes(page)
        requests_before_explicit_preview = len(api.preview_requests)
        with page.expect_response(lambda response: is_preview(response.request)):
            audio_button(page, "Preview").click()
        audio_button(page, USE_PREVIEW).click()

        # Then exactly two calls exist, each caused by an explicit Preview action.
        assert len(api.preview_requests) == 2
        assert requests_before_explicit_preview == 1
        assert retained == [MP3]
        assert [call["voice"] for call in api.preview_requests] == [EN_FIRST, EN_SECOND]
        assert rendered_audio_bytes(page) == [SECOND_MP3]
        assert api.saves == []

    @pytest.mark.p1
    def test_voice_catalog_failure_can_retry_without_losing_draft_edits(self, page: Page) -> None:
        """[P1] AC-13 a failed locale catalog has a visible inline error and a working retry."""
        # Given the French Voice catalog is unavailable when the Draft opens.
        api = DraftAudioApi(page)
        api.voices_error = True
        api.open("fr", viewports.PHONE)
        field(page, "Mnemonic").fill(UNRELATED_EDIT)

        # Then the error belongs to the audio card and preserves the editable Draft.
        expect(voice_alert(page)).to_be_visible()
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)

        # When the user explicitly retries, the locale options recover without a new Draft.
        api.voices_error = False
        with page.expect_response(lambda response: is_voice_list(response.request)):
            voice_alert(page).get_by_role("button", name="Try again", exact=True).click()
        voice(page).select_option(FR_SECOND)
        expect(voice_alert(page)).to_have_count(0)
        expect(voice(page)).to_have_value(FR_SECOND)
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        assert api.voice_requests == ["fr-CA", "fr-CA"]
        assert api.preview_requests == []
        assert api.saves == []

    @pytest.mark.p1
    def test_failed_preview_retains_the_prior_clip_and_explicit_retry_can_replace_it(
        self, page: Page
    ) -> None:
        """[P1] AC-14 failed synthesis preserves edits and the clip until retry succeeds."""
        # Given the user accepted an MP3 and then selected another Voice.
        api = DraftAudioApi(page)
        api.open("en", viewports.DESKTOP)
        field(page, "Mnemonic").fill(UNRELATED_EDIT)
        voice(page).select_option(EN_FIRST)
        api.preview_and_accept()
        voice(page).select_option(EN_SECOND)
        api.preview_error = True

        # When an explicit second Preview fails, the old candidate remains local and usable.
        api.synthesize()

        # Then the TTS-specific inline error preserves the buffer and prior audio.
        expect(tts_alert(page)).to_be_visible()
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        assert rendered_audio_bytes(page) == [MP3]
        api.preview_error = False
        api.mp3 = SECOND_MP3
        with page.expect_response(lambda response: is_preview(response.request)):
            tts_alert(page).get_by_role("button", name="Try again", exact=True).click()
        audio_button(page, USE_PREVIEW).click()
        expect(tts_alert(page)).to_have_count(0)
        assert rendered_audio_bytes(page) == [SECOND_MP3]
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        assert len(api.preview_requests) == 3
        assert api.saves == []

    @pytest.mark.p1
    def test_target_edit_warns_that_the_accepted_candidate_no_longer_matches(
        self, page: Page
    ) -> None:
        """[P1] AC-17 an accepted Preview cannot silently pass as audio for an edited Target."""
        # Given a phone Draft with a selected and accepted Reference clip.
        api = DraftAudioApi(page)
        api.open("en", viewports.PHONE)
        voice(page).select_option(EN_FIRST)
        api.preview_and_accept()

        # When Target changes, the accepted audio is visibly marked stale.
        field(page, "Target").fill("jump the gun")

        # Then the mismatch is visible without automatic synthesis or Anki writes.
        expect(audio_card(page).get_by_text(STALE_AUDIO, exact=True)).to_be_visible()
        expect(field(page, "Target")).to_have_value("jump the gun")
        expect(save_button(page)).to_be_enabled()
        assert len(api.preview_requests) == 1
        assert api.preview_requests[0]["target"] == api.capture["text"]
        assert api.saves == []


@pytest.mark.p1
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("category", ["Vocabulary", "Sentence"])
@pytest.mark.parametrize("viewport", viewports.ALL.values(), ids=viewports.ALL.keys())
def test_audio_can_be_played_and_saved_for_each_draft_at_all_widths(
    page, language, category, viewport
):
    """Both locales and Categories expose usable audio controls without overflow or autoplay."""
    api = DraftAudioApi(page)
    api.open(language, viewport, category)
    api.preview_and_accept()
    player = audio_card(page).locator("audio")
    assert player.evaluate("audio => audio.paused && !audio.autoplay")
    audio_button(page, "Play audio preview").click()
    expect(player).to_have_js_property("paused", False)
    player.evaluate("audio => audio.pause()")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    save_button(page).click()
    expect(editor(page)).to_have_count(0)
    assert api.saves[0].audio_file == MP3
    assert api.saves[0].item["category"] == category.lower()
    assert api.preview_requests[0]["language"] == language


@pytest.mark.p1
@pytest.mark.parametrize("stored", [None, "en-US-RetiredNeural", FR_FIRST])
def test_missing_unavailable_or_other_locale_preference_falls_back_without_synthesis(page, stored):
    if stored:
        page.add_init_script(
            f"localStorage.setItem('languagelab.voice.en-US', {json.dumps(stored)})"
        )
    api = DraftAudioApi(page)
    api.open("en", viewports.TABLET)
    expect(voice(page)).to_have_value(EN_FIRST)
    assert api.preview_requests == []
    assert storage_values(page) == ({LOCALE_KEYS["en-US"]: stored} if stored else {})


@pytest.mark.p1
def test_storage_denial_does_not_break_draft_or_explicit_preview(page):
    page.add_init_script("""Object.defineProperty(window, 'localStorage', {get() {
      throw new DOMException('denied', 'SecurityError');
    }});""")
    api = DraftAudioApi(page)
    api.open("en", viewports.TABLET)
    voice(page).select_option(EN_SECOND)
    api.preview_and_accept()
    assert rendered_audio_bytes(page) == [MP3]
    assert len(api.preview_requests) == 1


def install_url_probe(page):
    page.add_init_script("""window.audioUrls = {created: [], revoked: []};
      const create = URL.createObjectURL.bind(URL);
      const revoke = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = blob => {
        const url = create(blob); audioUrls.created.push(url); return url;
      };
      URL.revokeObjectURL = url => { audioUrls.revoked.push(url); revoke(url); };
    """)


@pytest.mark.p1
def test_rejected_replaced_and_departed_clips_release_all_blob_urls(page):
    install_url_probe(page)
    api = DraftAudioApi(page)
    api.open("en", viewports.DESKTOP)
    api.synthesize()
    audio_button(page, KEEP_CURRENT).click()
    assert page.evaluate("audioUrls.revoked.length") == 1
    api.preview_and_accept()
    api.mp3 = SECOND_MP3
    api.preview_and_accept()
    assert page.evaluate("audioUrls.revoked.length") == 2
    assert rendered_audio_bytes(page) == [SECOND_MP3]
    discard_draft(page)
    assert page.evaluate("audioUrls.created.slice().sort()") == page.evaluate(
        "audioUrls.revoked.slice().sort()"
    )


@pytest.mark.p1
def test_late_preview_after_discard_does_not_create_a_blob_or_reopen_the_draft(page):
    from tests.support.audio_screen import preview_button

    install_url_probe(page)
    api = DraftAudioApi(page)
    api.open("en", viewports.DESKTOP)
    expect(voice(page)).to_have_value(EN_FIRST)
    pending = []
    page.route("**/api/audio/preview", lambda route: pending.append(route))
    preview_button(page).click()
    expect(audio_card(page).get_by_role("button", name="Making audio…")).to_be_visible()
    assert len(pending) == 1
    discard_draft(page)
    with page.expect_response(lambda response: is_preview(response.request)):
        pending[0].fulfill(content_type="audio/mpeg", body=MP3)
    expect(editor(page)).to_have_count(0)
    assert page.evaluate("audioUrls.created") == []


@pytest.mark.p1
def test_empty_current_catalog_disables_preview_but_keeps_ordinary_save(page):
    from tests.support.audio_screen import preview_button

    api = DraftAudioApi(page)
    page.route("**/api/audio/voices?*", lambda route: route.fulfill(json={"voices": []}))
    api.open("fr", viewports.PHONE)
    expect(audio_card(page).get_by_text("No voices available for this language.")).to_be_visible()
    expect(preview_button(page)).to_be_disabled()
    expect(save_button(page)).to_be_enabled()
    save_button(page).click()
    expect(editor(page)).to_have_count(0)
    assert api.saves[0].item["audio"] == "keep"
    assert api.saves[0].audio_file is None


@pytest.mark.p1
def test_network_failure_preserves_both_accepted_and_offered_clips(page):
    api = DraftAudioApi(page)
    api.open("en", viewports.DESKTOP)
    api.preview_and_accept()
    api.mp3 = SECOND_MP3
    api.synthesize()
    assert rendered_audio_bytes(page) == [MP3, SECOND_MP3]
    page.route("**/api/audio/preview", lambda route: route.abort())
    audio_button(page, "Preview").click()
    expect(tts_alert(page)).to_be_visible()
    assert rendered_audio_bytes(page) == [MP3, SECOND_MP3]
    expect(audio_button(page, USE_PREVIEW)).to_be_enabled()


@pytest.mark.p0
@pytest.mark.parametrize("language,name", [("en", "English"), ("fr", "French")])
def test_unintercepted_app_save_and_playback_preserve_preview_bytes(page, language, name):
    """Real browser multipart reaches app persistence; HTTP playback returns the same MP3."""
    import uuid

    from tests.support.audio_screen import preview_button
    from tests.support.captures_screen import compose_box, is_save, rows
    from tests.support.items_screen import choose, write_it_myself

    target = f"audio transport {uuid.uuid4()}"
    page.goto("/captures")
    compose_box(page).fill(target)
    with page.expect_response(is_save):
        page.get_by_role("button", name="Save Capture", exact=True).click()
    rows(page).filter(has_text=target).click()
    choose(page, name, "Vocabulary")
    write_it_myself(page).click()
    field(page, "Russian meaning").fill("проверка аудио")
    with page.expect_response(lambda response: is_preview(response.request)) as previewed:
        preview_button(page).click()
    audio_button(page, USE_PREVIEW).click()
    assert previewed.value.status == 200
    [preview_bytes] = rendered_audio_bytes(page)
    assert preview_bytes == MP3
    with page.expect_response(lambda response: is_item_save(response.request)) as saved:
        save_button(page).click()
    assert saved.value.status == 200
    item_id = saved.value.json()["itemId"]
    detail = page.request.get(f"/api/items/{language}/{item_id}")
    assert detail.status == 200
    filename = detail.json()["audio"]
    assert filename
    played = page.request.get(f"/api/media/{filename}")
    assert played.status == 200
    assert played.body() == preview_bytes

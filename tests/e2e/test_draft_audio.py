"""Story 6.1 Draft Reference audio journeys at phone and desktop widths, and the automatic
Draft audio (decided 2026-10-25, AD-14): a new Draft, generated or written by hand, makes one
Preview once its Voice list loads and holds it as the accepted audio, so Save stores it.

API responses are provider doubles. Every assertion observes the real client or its outgoing
multipart body, not only the configured double. `DraftAudioApi.open` waits for the automatic
clip, so the explicit Previews below never race it.
"""

import json
import re
import time
import uuid
from collections.abc import Callable

import pytest
from playwright.sync_api import BrowserContext, Page, Route, ViewportSize, expect

from tests.support import viewports
from tests.support.audio import MP3, SECOND_MP3
from tests.support.audio_screen import (
    CATALOG,
    EN_FIRST,
    EN_SECOND,
    FR_FIRST,
    FR_GROUPS,
    FR_SECOND,
    FRANCE_FIRST,
    FRANCE_SECOND,
    LEGACY_FR_KEY,
    MAKING_AUDIO,
    STALE_AUDIO,
    VOICE_KEYS,
    DraftAudioApi,
    audio_button,
    audio_card,
    auto_alert,
    is_preview,
    is_voice_list,
    preview_button,
    rendered_audio_bytes,
    storage_values,
    tts_alert,
    voice,
    voice_alert,
    voice_groups,
    waiting_save,
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
WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}
FIRST_VOICE = {"en": EN_FIRST, "fr": FR_FIRST}
SECOND_VOICE = {"en": EN_SECOND, "fr": FR_SECOND}


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
            VOICE_KEYS["en"]: EN_SECOND,
            VOICE_KEYS["fr"]: FR_SECOND,
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
        assert storage_values(page)[VOICE_KEYS["en"]] == EN_SECOND
        assert storage_values(page)[VOICE_KEYS["fr"]] == FR_SECOND
        # Each new Draft made its automatic Preview with the Voice shown when it opened.
        assert [call["voice"] for call in api.preview_requests] == [EN_FIRST, FR_FIRST, EN_SECOND]
        assert [call["voice"] for call in other.preview_requests] == [FR_FIRST]
        assert api.saves == other.saves == []

    @pytest.mark.p1
    def test_keep_current_discards_the_preview_and_save_keeps_the_automatic_audio(
        self, page: Page
    ) -> None:
        """[P1] AC-5 Preview stays local; Keep current discards it and keeps the automatic clip."""
        # Given a phone Draft with its automatic clip, an explicit Preview and a local edit.
        api = DraftAudioApi(page)
        item_id = api.open("en", viewports.PHONE)
        field(page, "Mnemonic").fill(UNRELATED_EDIT)
        api.mp3 = SECOND_MP3
        api.synthesize()
        assert rendered_audio_bytes(page) == [MP3, SECOND_MP3]

        # When the user rejects the candidate, the compare controls disappear.
        audio_button(page, KEEP_CURRENT).click()

        # Then only the automatic clip remains, and Save stores exactly it.
        expect(audio_button(page, USE_PREVIEW)).to_have_count(0)
        assert rendered_audio_bytes(page) == [MP3]
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        assert api.saves == []
        with page.expect_response(lambda response: is_item_save(response.request)):
            save_button(page).click()
        expect(banner(page, api.capture["text"])).to_be_visible()
        [saved] = api.saves
        assert saved.item["audio"] == "replace"
        assert saved.item["itemId"] == item_id
        assert saved.audio_file == MP3
        assert len(api.preview_requests) == 2

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
        assert len(api.preview_requests) == 2  # the automatic one, then the explicit one

    @pytest.mark.p1
    def test_changing_voice_keeps_the_candidate_until_an_explicit_new_preview(
        self, page: Page
    ) -> None:
        """[P1] AC-12 Voice selection alone never synthesizes or saves audio."""
        # Given a desktop Draft with its automatic clip accepted.
        api = DraftAudioApi(page)
        api.open("en", viewports.DESKTOP)
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
        api.open("fr", viewports.PHONE, auto=False)
        field(page, "Mnemonic").fill(UNRELATED_EDIT)

        # Then the error belongs to the audio card and preserves the editable Draft.
        expect(voice_alert(page)).to_be_visible()
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)

        assert api.preview_requests == []

        # When the user explicitly retries, the locale options recover without a new Draft,
        # and the automatic audio follows the successful retry.
        api.voices_error = False
        with page.expect_response(lambda response: is_preview(response.request)):
            with page.expect_response(lambda response: is_voice_list(response.request)):
                voice_alert(page).get_by_role("button", name="Try again", exact=True).click()
        expect(preview_button(page)).to_be_visible()
        voice(page).select_option(FR_SECOND)
        expect(voice_alert(page)).to_have_count(0)
        expect(voice(page)).to_have_value(FR_SECOND)
        expect(field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
        assert api.voice_requests == ["fr", "fr"]
        assert [call["voice"] for call in api.preview_requests] == [FR_FIRST]
        assert rendered_audio_bytes(page) == [MP3]
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
        assert len(api.preview_requests) == 4  # automatic, accepted, failed, retried
        assert api.saves == []

    @pytest.mark.p1
    def test_target_edit_warns_that_the_accepted_candidate_no_longer_matches(
        self, page: Page
    ) -> None:
        """[P1] AC-17 an accepted Preview cannot silently pass as audio for an edited Target."""
        # Given a phone Draft with its automatic Reference clip.
        api = DraftAudioApi(page)
        api.open("en", viewports.PHONE)

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
def test_missing_unavailable_or_other_locale_preference_falls_back_to_the_first_voice(page, stored):
    if stored:
        page.add_init_script(
            f"localStorage.setItem('languagelab.voice.en-US', {json.dumps(stored)})"
        )
    api = DraftAudioApi(page)
    api.open("en", viewports.TABLET)
    expect(voice(page)).to_have_value(EN_FIRST)
    # The automatic Preview uses the fallback Voice and stores no preference of its own
    assert [call["voice"] for call in api.preview_requests] == [EN_FIRST]
    assert storage_values(page) == ({VOICE_KEYS["en"]: stored} if stored else {})


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
    assert [call["voice"] for call in api.preview_requests] == [EN_FIRST, EN_SECOND]


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
    assert page.evaluate("audioUrls.created.length") == 1  # the automatic clip
    api.synthesize()
    audio_button(page, KEEP_CURRENT).click()
    assert page.evaluate("audioUrls.revoked.length") == 1
    api.preview_and_accept()
    api.mp3 = SECOND_MP3
    api.preview_and_accept()
    assert page.evaluate("audioUrls.revoked.length") == 3
    assert rendered_audio_bytes(page) == [SECOND_MP3]
    discard_draft(page)
    assert page.evaluate("audioUrls.created.slice().sort()") == page.evaluate(
        "audioUrls.revoked.slice().sort()"
    )


@pytest.mark.p1
def test_late_preview_after_discard_does_not_create_a_blob_or_reopen_the_draft(page):
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
    # Only the automatic clip was ever created, and the Discard revoked it
    assert page.evaluate("audioUrls.created.length") == 1
    assert page.evaluate("audioUrls.created") == page.evaluate("audioUrls.revoked")


@pytest.mark.p1
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_empty_current_catalog_disables_preview_but_keeps_ordinary_save(page, language, viewport):
    """Matrix "no Voices": no automatic request; the Draft saves without audio."""
    api = DraftAudioApi(page)
    page.route("**/api/audio/voices?*", lambda route: route.fulfill(json={"voices": []}))
    api.open(language, viewport, auto=False)
    expect(audio_card(page).get_by_text("No voices available for this language.")).to_be_visible()
    expect(preview_button(page)).to_be_disabled()
    expect(save_button(page)).to_be_enabled()
    save_button(page).click()
    expect(editor(page)).to_have_count(0)
    assert api.saves[0].item["audio"] == "keep"
    assert api.saves[0].audio_file is None
    assert api.preview_requests == []


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

    from tests.support.captures_screen import compose_box, is_save, rows
    from tests.support.items_screen import choose, write_it_myself

    target = f"audio transport {uuid.uuid4()}"
    page.goto("/captures")
    compose_box(page).fill(target)
    with page.expect_response(is_save):
        page.get_by_role("button", name="Save Capture", exact=True).click()
    rows(page).filter(has_text=target).click()
    choose(page, name, "Vocabulary")
    with page.expect_response(lambda response: is_preview(response.request)):
        write_it_myself(page).click()  # the automatic Preview
    expect(preview_button(page)).to_be_visible()
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


# The automatic Draft audio (decided 2026-10-25): one test per I/O Matrix row of
# plan-auto-draft-reference-audio.md, at phone and desktop widths, in English and French.

PATHS = ["generate", "write"]


def remember(page: Page, language: str, name: str) -> None:
    key = VOICE_KEYS[language]
    page.add_init_script(f"localStorage.setItem({json.dumps(key)}, {json.dumps(name)})")


def hold_previews(page: Page) -> list[Route]:
    """Hold every Preview until the test answers it (registered after DraftAudioApi's route,
    so it wins)."""
    held: list[Route] = []
    page.route("**/api/audio/preview", lambda route: held.append(route))
    return held


def first_held(page: Page, held: list[Route], timeout_s: float = 10.0) -> Route:
    deadline = time.monotonic() + timeout_s
    while not held and time.monotonic() < deadline:
        page.evaluate("0")  # a round trip lets Playwright deliver the route event
    assert held, "the request was never held"
    return held[0]


def held_preview(page: Page, held: list[Route]) -> Route:
    expect(audio_card(page).get_by_role("button", name=MAKING_AUDIO, exact=True)).to_be_visible()
    return first_held(page, held)


def open_draft(
    api: DraftAudioApi, path: str, language: str, viewport: ViewportSize, *, auto: bool = True
) -> str:
    if path == "generate":
        return api.generate(language, viewport, auto=auto)
    return api.open(language, viewport, auto=auto)


def fail(route: Route) -> None:
    route.fulfill(
        status=502,
        json={"error": {"code": "tts_failed", "message": "x", "requestId": str(uuid.uuid4())}},
    )


def save_and_wait(page: Page, api: DraftAudioApi) -> None:
    with page.expect_response(lambda response: is_item_save(response.request)):
        save_button(page).click()
    expect(banner(page, api.capture["text"])).to_be_visible()


@pytest.mark.p0
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_new_draft_saves_its_automatic_audio_with_no_audio_clicks(
    page: Page, path: str, language: str, viewport: ViewportSize
) -> None:
    """Matrix "Generated Draft" / "Written Draft": one Preview with the remembered Voice, a
    paused player with the clip, nothing saved before Save, and Save stores exactly that clip.
    """
    remember(page, language, SECOND_VOICE[language])
    api = DraftAudioApi(page)

    item_id = open_draft(api, path, language, viewport)

    expect(voice(page)).to_have_value(SECOND_VOICE[language])
    assert api.preview_requests == [
        {"language": language, "voice": SECOND_VOICE[language], "target": api.capture["text"]}
    ]
    assert rendered_audio_bytes(page) == [MP3]
    assert audio_card(page).locator("audio").evaluate("audio => audio.paused && !audio.autoplay")
    expect(audio_button(page, USE_PREVIEW)).to_have_count(0)
    assert api.saves == []
    save_and_wait(page, api)
    [saved] = api.saves
    assert (saved.item["itemId"], saved.item["audio"]) == (item_id, "replace")
    assert saved.audio_file == MP3
    assert len(api.preview_requests) == 1


@pytest.mark.p1
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_blank_target_makes_no_audio_even_once_it_is_typed(
    page: Page, language: str, viewport: ViewportSize
) -> None:
    """Matrix "Blank Target": no request when the Draft opens, none on the Target edit, and the
    Draft saves without audio."""
    api = DraftAudioApi(page, text="   ")
    api.open(language, viewport, auto=False)
    expect(voice(page)).to_have_value(FIRST_VOICE[language])
    expect(preview_button(page)).to_be_disabled()
    field(page, "Target").fill("jump to conclusions")
    expect(preview_button(page)).to_be_enabled()
    page.evaluate("0")
    assert api.preview_requests == []
    assert rendered_audio_bytes(page) == []
    with page.expect_response(lambda response: is_item_save(response.request)):
        save_button(page).click()
    expect(editor(page)).to_have_count(0)
    [saved] = api.saves
    assert (saved.item["audio"], saved.audio_file) == ("keep", None)
    assert api.preview_requests == []


@pytest.mark.p1
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_failed_automatic_preview_shows_its_notice_and_the_draft_saves_without_audio(
    page: Page, path: str, language: str, viewport: ViewportSize
) -> None:
    """Matrix "Failure": the notice with Try again; Save still works, without audio."""
    api = DraftAudioApi(page)
    api.preview_error = True
    open_draft(api, path, language, viewport)
    expect(auto_alert(page)).to_be_visible()
    expect(auto_alert(page).get_by_role("button", name="Try again", exact=True)).to_be_enabled()
    expect(tts_alert(page)).to_have_count(0)
    assert rendered_audio_bytes(page) == []
    expect(save_button(page)).to_be_enabled()
    save_and_wait(page, api)
    [saved] = api.saves
    assert (saved.item["audio"], saved.audio_file) == ("keep", None)
    assert len(api.preview_requests) == 1


@pytest.mark.p1
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_try_again_after_a_failed_automatic_preview_makes_the_accepted_audio(
    page: Page, path: str, language: str, viewport: ViewportSize
) -> None:
    """Matrix "Failure": a successful Try again becomes the accepted audio, saved with Save."""
    api = DraftAudioApi(page)
    api.preview_error = True
    open_draft(api, path, language, viewport)
    api.preview_error = False
    with page.expect_response(lambda response: is_preview(response.request)):
        auto_alert(page).get_by_role("button", name="Try again", exact=True).click()
    expect(auto_alert(page)).to_have_count(0)
    expect(audio_button(page, USE_PREVIEW)).to_have_count(0)
    assert rendered_audio_bytes(page) == [MP3]
    save_and_wait(page, api)
    [saved] = api.saves
    assert (saved.item["audio"], saved.audio_file) == ("replace", MP3)
    assert len(api.preview_requests) == 2


@pytest.mark.p0
@pytest.mark.parametrize("outcome", ["made", "failed"])
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_save_pressed_while_the_audio_is_made_waits_for_it(
    page: Page, outcome: str, path: str, language: str, viewport: ViewportSize
) -> None:
    """Matrix "In flight": Save shows "Making audio…" and stays busy, then saves with the clip,
    or without audio if it failed."""
    api = DraftAudioApi(page)
    held = hold_previews(page)
    open_draft(api, path, language, viewport, auto=False)
    pending = held_preview(page, held)

    save_button(page).click()

    expect(waiting_save(page)).to_be_visible()
    expect(waiting_save(page)).to_be_disabled()
    page.evaluate("0")
    assert api.saves == []
    with page.expect_response(lambda response: is_item_save(response.request)):
        if outcome == "made":
            pending.fulfill(status=200, content_type="audio/mpeg", body=MP3)
        else:
            fail(pending)
    expect(banner(page, api.capture["text"])).to_be_visible()
    [saved] = api.saves
    if outcome == "made":
        assert (saved.item["audio"], saved.audio_file) == ("replace", MP3)
    else:
        assert (saved.item["audio"], saved.audio_file) == ("keep", None)
    assert len(held) == 1


@pytest.mark.p1
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_voice_and_target_edits_after_the_automatic_clip_make_no_new_audio(
    page: Page, language: str, viewport: ViewportSize
) -> None:
    """Matrix "Edits": a Voice change only stores the preference; a Target change shows the
    stale warning; neither makes a request."""
    api = DraftAudioApi(page)
    api.open(language, viewport)
    voice(page).select_option(SECOND_VOICE[language])
    expect(audio_card(page).get_by_text(STALE_AUDIO, exact=True)).to_have_count(0)
    field(page, "Target").fill("jump the gun")
    expect(audio_card(page).get_by_text(STALE_AUDIO, exact=True)).to_be_visible()
    expect(preview_button(page)).to_be_enabled()
    page.evaluate("0")
    assert len(api.preview_requests) == 1
    assert storage_values(page)[VOICE_KEYS[language]] == SECOND_VOICE[language]
    assert rendered_audio_bytes(page) == [MP3]
    assert api.saves == []


@pytest.mark.p1
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_an_explicit_preview_after_the_automatic_clip_is_compared_before_use(
    page: Page, language: str, viewport: ViewportSize
) -> None:
    """Matrix "Explicit Preview": the existing compare; Use preview replaces the automatic clip."""
    api = DraftAudioApi(page)
    api.open(language, viewport)
    api.mp3 = SECOND_MP3
    api.synthesize()
    expect(audio_button(page, KEEP_CURRENT)).to_be_visible()
    assert rendered_audio_bytes(page) == [MP3, SECOND_MP3]
    audio_button(page, USE_PREVIEW).click()
    expect(audio_button(page, USE_PREVIEW)).to_have_count(0)
    assert rendered_audio_bytes(page) == [SECOND_MP3]
    save_and_wait(page, api)
    [saved] = api.saves
    assert (saved.item["audio"], saved.audio_file) == ("replace", SECOND_MP3)


@pytest.mark.p1
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_draft_discarded_while_its_audio_is_made_ignores_the_late_reply(
    page: Page, language: str, viewport: ViewportSize
) -> None:
    """Matrix "Leave": the late automatic reply creates no Blob URL and reopens nothing."""
    install_url_probe(page)
    api = DraftAudioApi(page)
    held = hold_previews(page)
    api.open(language, viewport, auto=False)
    pending = held_preview(page, held)
    discard_draft(page)
    expect(editor(page)).to_have_count(0)
    with page.expect_response(lambda response: is_preview(response.request)):
        pending.fulfill(status=200, content_type="audio/mpeg", body=MP3)
    page.evaluate("0")
    expect(editor(page)).to_have_count(0)
    assert page.evaluate("audioUrls.created") == []
    assert api.saves == []


@pytest.mark.p0
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_save_pressed_while_the_voices_load_waits_for_the_automatic_audio(
    page: Page, path: str, language: str, viewport: ViewportSize
) -> None:
    """Matrix "In flight": a Save pressed during "Loading voices…" also waits, then saves with
    the automatic clip."""
    api = DraftAudioApi(page)
    held: list[Route] = []
    page.route(re.compile(r"/api/audio/voices(?:\?.*)?$"), lambda route: held.append(route))
    open_draft(api, path, language, viewport, auto=False)
    expect(audio_card(page).get_by_text("Loading voices…", exact=True)).to_be_visible()
    voices = first_held(page, held)

    save_button(page).click()

    expect(waiting_save(page)).to_be_disabled()
    page.evaluate("0")
    assert api.saves == []
    assert api.preview_requests == []
    with page.expect_response(lambda response: is_item_save(response.request)):
        voices.fulfill(json={"voices": CATALOG[language]})
    expect(banner(page, api.capture["text"])).to_be_visible()
    [saved] = api.saves
    assert (saved.item["audio"], saved.audio_file) == ("replace", MP3)
    assert [call["voice"] for call in api.preview_requests] == [FIRST_VOICE[language]]


# French Voices from fr-CA and fr-FR (plan-french-voices-fr-ca-and-fr-fr.md): one test per I/O
# Matrix row, at phone and desktop widths.


@pytest.mark.p1
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_french_draft_lists_canada_then_france_voices_in_two_groups(
    page: Page, viewport: ViewportSize
) -> None:
    """Matrix "French list": one picker, the "Canada" group then the "France" group."""
    api = DraftAudioApi(page)
    api.open("fr", viewport)
    assert voice_groups(voice(page)) == FR_GROUPS
    expect(voice(page)).to_have_value(FR_FIRST)
    assert api.voice_requests == ["fr"]
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


@pytest.mark.p1
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_an_english_draft_lists_only_us_voices_without_groups(
    page: Page, viewport: ViewportSize
) -> None:
    """Matrix "English": en-US only, no groups."""
    api = DraftAudioApi(page)
    api.open("en", viewport)
    assert voice_groups(voice(page)) == {}
    options = voice(page).locator("option")
    expect(options).to_have_count(2)
    assert options.evaluate_all("options => options.map(o => o.value)") == [EN_FIRST, EN_SECOND]
    assert api.voice_requests == ["en"]


@pytest.mark.p0
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_france_voice_previews_and_saves_like_any_other(
    page: Page, viewport: ViewportSize
) -> None:
    """Matrix "fr-FR Voice": the explicit Preview names the France Voice; Save stores its clip.
    The API tests show the backend synthesizes it in fr-FR."""
    api = DraftAudioApi(page)
    api.open("fr", viewport)
    voice(page).select_option(FRANCE_SECOND)
    api.mp3 = SECOND_MP3
    api.preview_and_accept()
    assert api.preview_requests[-1] == {
        "language": "fr",
        "voice": FRANCE_SECOND,
        "target": api.capture["text"],
    }
    save_and_wait(page, api)
    [saved] = api.saves
    assert (saved.item["audio"], saved.audio_file) == ("replace", SECOND_MP3)


@pytest.mark.p0
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_a_remembered_france_voice_makes_the_automatic_audio_of_a_new_draft(
    page: Page, viewport: ViewportSize
) -> None:
    """Matrix "fr-FR Voice" / "Preference": a France choice is the next French Draft's Voice,
    used by its automatic Preview; English keeps its own preference."""
    api = DraftAudioApi(page)
    api.open("en", viewport)
    voice(page).select_option(EN_SECOND)
    discard_draft(page)
    api.open("fr", viewport)
    voice(page).select_option(FRANCE_FIRST)
    discard_draft(page)

    api.open("fr", viewport)

    expect(voice(page)).to_have_value(FRANCE_FIRST)
    assert api.preview_requests[-1]["voice"] == FRANCE_FIRST
    assert storage_values(page) == {VOICE_KEYS["en"]: EN_SECOND, VOICE_KEYS["fr"]: FRANCE_FIRST}
    discard_draft(page)
    api.open("en", viewport)
    expect(voice(page)).to_have_value(EN_SECOND)


@pytest.mark.p1
@pytest.mark.parametrize(
    "stored,shown",
    [(FR_SECOND, FR_SECOND), ("fr-CA-RetiredNeural", FR_FIRST)],
    ids=["listed", "unavailable"],
)
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_an_old_canada_preference_still_chooses_the_french_voice(page, stored, shown, viewport):
    """Matrix "Old preference": only languagelab.voice.fr-CA is stored; a listed Voice is
    preselected, an unavailable one falls back to the first listed. Nothing is migrated."""
    page.add_init_script(f"localStorage.setItem({json.dumps(LEGACY_FR_KEY)}, {json.dumps(stored)})")
    api = DraftAudioApi(page)
    api.open("fr", viewport)
    expect(voice(page)).to_have_value(shown)
    assert [call["voice"] for call in api.preview_requests] == [shown]
    assert storage_values(page) == {LEGACY_FR_KEY: stored}


@pytest.mark.p1
def test_the_french_preference_wins_over_an_old_canada_one(page):
    """Matrix "Old preference": once the French key is set, the fr-CA key is ignored."""
    page.add_init_script(
        f"localStorage.setItem({json.dumps(LEGACY_FR_KEY)}, {json.dumps(FR_SECOND)});"
        f"localStorage.setItem({json.dumps(VOICE_KEYS['fr'])}, {json.dumps(FRANCE_SECOND)})"
    )
    api = DraftAudioApi(page)
    api.open("fr", viewports.DESKTOP)
    expect(voice(page)).to_have_value(FRANCE_SECOND)


@pytest.mark.p1
@pytest.mark.parametrize("viewport", WIDTHS.values(), ids=WIDTHS.keys())
def test_storage_denial_does_not_break_the_french_picker(page, viewport):
    """Matrix "Preference": denied storage is tolerated; the first listed Voice is shown."""
    page.add_init_script("""Object.defineProperty(window, 'localStorage', {get() {
      throw new DOMException('denied', 'SecurityError');
    }});""")
    api = DraftAudioApi(page)
    api.open("fr", viewport)
    expect(voice(page)).to_have_value(FR_FIRST)
    voice(page).select_option(FRANCE_FIRST)
    api.preview_and_accept()
    assert [call["voice"] for call in api.preview_requests] == [FR_FIRST, FRANCE_FIRST]

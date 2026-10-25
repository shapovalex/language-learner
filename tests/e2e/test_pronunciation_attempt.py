"""Story 7.2 red-phase recording and feedback journeys.

The screen uses getUserMedia/MediaRecorder against a deterministic browser boundary double;
HTTP doubles control Assessment outcomes only. Each test observes its complete browser
journey in one outer assertion, including missing controls and failed navigation. Re-observe
later transitions when activating: a missing initial control still prevents reaching later
feedback or cleanup checks. Real iOS capture, codecs and HTTPS permission belong to 7.4.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.attempt_screen import (
    CHECKING,
    FAILED_BODY,
    FAILED_TITLE,
    LISTENING,
    MIC_BODY,
    MIC_TITLE,
    NOTHING_BODY,
    NOTHING_TITLE,
    AttemptApi,
    finish_attempt,
    install_microphone,
    is_attempt,
    level_meter,
    mic_state,
    observe_journey,
    record_button,
    score_ring,
    word_feedback,
)
from tests.support.captures_screen import main
from tests.support.navigation import language_nav
from tests.support.pronunciation_screen import (
    RATINGS,
    rating_button,
    reference_button,
    review_card,
    target_text,
)

pytestmark = pytest.mark.skip(
    reason="ATDD 7.2 RED: activate when implementing recording, locale feedback and Attempt gating."
)


class TestRecording:
    @pytest.mark.p1
    def test_recording_shows_listening_and_a_live_level_meter(self, page: Page) -> None:
        """[P1] AC-1 user-started MediaRecorder capture shows Listening and live input level."""

        def journey() -> None:
            page.set_viewport_size(viewports.PHONE)
            install_microphone(page, mp4=True)
            api = AttemptApi(page)
            page.goto("/en/pronunciation")

            record_button(page).click()

            expect(record_button(page, LISTENING)).to_be_visible()
            meter = level_meter(page)
            expect(meter).to_be_visible()
            before = meter.get_attribute("value")
            page.evaluate("window.__attemptMic.level = 0.85")
            expect(meter).not_to_have_attribute("value", before)
            state = mic_state(page)
            assert state["gets"] == 1
            assert state["starts"] == 1
            assert state["meterReads"] > 0
            assert api.attempts == []
            with page.expect_response(lambda response: is_attempt(response.request)):
                record_button(page, LISTENING).click()
            expect(level_meter(page)).to_have_count(0)

        assert observe_journey(journey) is None

    @pytest.mark.p0
    def test_denied_microphone_warns_without_answering_and_reference_still_plays(
        self, page: Page
    ) -> None:
        """[P0] AC-2 denied microphone access keeps the Card, with recovery copy and Reference."""

        def journey() -> None:
            page.set_viewport_size(viewports.PHONE)
            install_microphone(page, denied=True)
            api = AttemptApi(page)
            page.goto("/en/pronunciation")

            record_button(page).click()

            alert = main(page).get_by_role("alert")
            expect(alert).to_contain_text(MIC_TITLE)
            expect(alert).to_contain_text(MIC_BODY)
            expect(target_text(page, "thought again")).to_be_visible()
            for name in RATINGS:
                expect(rating_button(page, name)).to_be_disabled()
            with page.expect_request(lambda request: "/api/media/" in request.url):
                reference_button(page).click()
            assert api.review.ratings == []
            assert api.attempts == []
            assert mic_state(page)["starts"] == 0

        assert observe_journey(journey) is None

    @pytest.mark.p0
    def test_recording_autostops_at_thirty_seconds_and_uploads_the_native_blob(
        self, page: Page
    ) -> None:
        """[P0] AC-3 the 30-second timer stops the recorder and sends one Attempt."""

        def journey() -> None:
            page.set_viewport_size(viewports.PHONE)
            native = install_microphone(page)
            api = AttemptApi(page)
            page.clock.install()
            page.goto("/en/pronunciation")
            record_button(page).click()
            page.clock.run_for(29_999)
            before = len(api.attempts)

            with page.expect_response(lambda response: is_attempt(response.request)):
                page.clock.run_for(1)

            assert len(api.attempts) == 1
            assert before == 0
            assert mic_state(page)["stops"] == 1
            assert api.attempts[0]["recording"]["data"] == native
            assert api.attempts[0]["recording"]["content_type"] == "audio/webm"
            assert api.attempts[0]["itemId"]["data"].decode() == api.cards[0]["itemId"]
            assert set(api.attempts[0]) == {"itemId", "recording"}
            expect(record_button(page, LISTENING)).to_have_count(0)

        assert observe_journey(journey) is None


class TestAssessmentFeedback:
    @pytest.mark.p0
    def test_nothing_heard_warns_and_does_not_unlock_rating(self, page: Page) -> None:
        """[P0] AC-10 an all-Omission result asks to record closer and never enables Rating."""

        def journey() -> None:
            page.set_viewport_size(viewports.PHONE)
            install_microphone(page)
            api = AttemptApi(page)
            api.result = {"assessment": None, "nothingHeard": True}
            page.goto("/en/pronunciation")

            finish_attempt(page)

            alert = main(page).get_by_role("alert")
            expect(alert).to_contain_text(NOTHING_TITLE)
            expect(alert).to_contain_text(NOTHING_BODY)
            expect(alert.get_by_role("button", name="Record again", exact=True)).to_be_enabled()
            expect(target_text(page, "thought again")).to_be_visible()
            expect(score_ring(page)).to_have_count(0)
            for name in RATINGS:
                expect(rating_button(page, name)).to_be_disabled()
            assert api.review.ratings == []

        assert observe_journey(journey) is None

    @pytest.mark.p1
    def test_english_feedback_shows_latest_score_and_selectable_word_detail(
        self, page: Page
    ) -> None:
        """[P1] AC-11 latest English scores, IPA, weak-word selection and non-color cues show."""

        def journey() -> None:
            page.set_viewport_size(viewports.PHONE)
            install_microphone(page)
            api = AttemptApi(page)
            page.goto("/en/pronunciation")
            finish_attempt(page)
            api.result["assessment"]["overall"] = 88

            finish_attempt(page, retry=True)

            expect(score_ring(page)).to_have_text("88")
            expect(main(page).get_by_label("Accuracy", exact=True)).to_have_text("81")
            expect(main(page).get_by_label("Fluency", exact=True)).to_have_text("86")
            expect(main(page).get_by_label("Completeness", exact=True)).to_have_text("100")
            expect(main(page).get_by_label("Prosody", exact=True)).to_have_text("72")
            expect(word_feedback(page)).to_contain_text("thought")
            expect(word_feedback(page)).to_contain_text("54")
            expect(word_feedback(page)).to_contain_text("mispronounced")
            expect(word_feedback(page).get_by_text("θ", exact=True)).to_be_visible()
            poor = main(page).get_by_role("button", name="thought", exact=True)
            fair = main(page).get_by_role("button", name="again", exact=True)
            assert poor.evaluate("e => parseFloat(getComputedStyle(e).borderTopWidth)") > 0
            assert fair.evaluate("e => getComputedStyle(e).textDecorationStyle") == "dotted"
            fair.click()
            expect(word_feedback(page)).to_contain_text("again")
            expect(word_feedback(page).get_by_text("ə", exact=True)).to_be_visible()
            expect(word_feedback(page).get_by_text("θ", exact=True)).to_have_count(0)
            assert api.review.ratings == []

        assert observe_journey(journey) is None

    @pytest.mark.p0
    def test_french_feedback_shows_positions_without_naming_a_sound(self, page: Page) -> None:
        """[P0] AC-12 French uses word positions and no IPA or prosody score."""

        def journey() -> None:
            page.set_viewport_size(viewports.TABLET)
            install_microphone(page, mp4=True)
            AttemptApi(page, lang="fr")
            page.goto("/fr/pronunciation")

            finish_attempt(page)

            expect(word_feedback(page).get_by_text("end", exact=True)).to_be_visible()
            expect(score_ring(page)).to_have_text("79")
            expect(word_feedback(page)).to_contain_text("bonjour")
            expect(word_feedback(page).get_by_text("start", exact=True)).to_be_visible()
            expect(word_feedback(page).get_by_text("middle", exact=True)).to_be_visible()
            expect(main(page).get_by_text("Prosody isn't available.", exact=False)).to_be_visible()
            expect(main(page).get_by_label("Prosody", exact=True)).to_have_count(0)
            text = word_feedback(page).inner_text()
            assert all(symbol not in text for symbol in ("ʒ", "ɔ̃", "ʁ", "θ"))
            assert "phoneme" not in text.lower()
            assert "sound /" not in text.lower()

        assert observe_journey(journey) is None

    @pytest.mark.p1
    def test_try_again_records_immediately_and_reference_is_disabled_until_assessing(
        self, page: Page
    ) -> None:
        """[P1] AC-13 repeated retries record at once, then show Checking without auto-Reference."""

        def journey() -> None:
            page.set_viewport_size(viewports.DESKTOP)
            install_microphone(page)
            api = AttemptApi(page)
            page.goto("/en/pronunciation")
            finish_attempt(page)

            record_button(page, "Try again").click()

            expect(record_button(page, LISTENING)).to_be_visible()
            for count in (2, 3, 4):
                expect(reference_button(page)).to_be_disabled()
                api.hold = True
                record_button(page, LISTENING).click()
                api.wait_for_attempts(count)
                expect(record_button(page, CHECKING)).to_be_visible()
                expect(reference_button(page)).to_be_enabled()
                api.release()
                expect(record_button(page, "Try again")).to_be_enabled()
                if count < 4:
                    record_button(page, "Try again").click()
            assert mic_state(page)["starts"] == 4
            assert api.review.media_requests == []
            assert api.review.ratings == []

        assert observe_journey(journey) is None


class TestRatingGateAndDisposal:
    @pytest.mark.p0
    def test_rating_unlocks_after_assessment_and_stays_enabled_during_the_next(
        self, page: Page
    ) -> None:
        """[P0] AC-14 one usable Assessment unlocks every Rating without choosing one."""

        def journey() -> None:
            page.set_viewport_size(viewports.DESKTOP)
            install_microphone(page)
            api = AttemptApi(page)
            page.goto("/en/pronunciation")

            initially_disabled = {name: rating_button(page, name).is_disabled() for name in RATINGS}
            finish_attempt(page)

            expect(rating_button(page, "Good")).to_be_enabled()
            assert initially_disabled == dict.fromkeys(RATINGS, True)
            for name in RATINGS:
                expect(rating_button(page, name)).to_be_enabled()
            api.hold = True
            record_button(page, "Try again").click()
            record_button(page, LISTENING).click()
            api.wait_for_attempts(2)
            expect(record_button(page, CHECKING)).to_be_visible()
            for name in RATINGS:
                button = rating_button(page, name)
                expect(button).to_be_enabled()
                assert button.get_attribute("aria-pressed") in (None, "false")
                assert button.get_attribute("aria-selected") in (None, "false")
            styles = [
                rating_button(page, name).evaluate(
                    "e => {const s=getComputedStyle(e); "
                    "return [s.backgroundColor,s.borderColor,s.fontWeight]}"
                )
                for name in RATINGS
            ]
            assert all(style == styles[0] for style in styles)
            expect(
                main(page).get_by_text("How did that feel? You decide.", exact=True)
            ).to_be_visible()
            assert api.review.ratings == []
            api.release()

        assert observe_journey(journey) is None

    @pytest.mark.p0
    def test_assessment_failure_offers_record_again_or_exit_without_answering(
        self, page: Page
    ) -> None:
        """[P0] AC-15 failed Assessment preserves the unanswered Card and offers recovery."""

        def journey() -> None:
            page.set_viewport_size(viewports.DESKTOP)
            install_microphone(page)
            api = AttemptApi(page)
            api.failed = True
            page.goto("/en/pronunciation")

            finish_attempt(page)

            alert = main(page).get_by_role("alert")
            expect(alert).to_contain_text(FAILED_TITLE)
            expect(alert).to_contain_text(FAILED_BODY)
            expect(alert.get_by_role("button", name="Record again", exact=True)).to_be_enabled()
            expect(alert.get_by_role("button", name="Exit", exact=True)).to_be_enabled()
            expect(target_text(page, "thought again")).to_be_visible()
            for name in RATINGS:
                button = rating_button(page, name)
                expect(button).to_be_disabled()
                assert button.get_attribute("aria-pressed") in (None, "false")
            assert api.review.ratings == []
            alert.get_by_role("button", name="Exit", exact=True).click()
            expect(page).to_have_url(re.compile(r"/en/items$"))

        assert observe_journey(journey) is None

    @pytest.mark.p0
    @pytest.mark.parametrize("leave", ["rating", "navigation"])
    def test_rating_or_leaving_releases_recording_and_clears_assessment(
        self, page: Page, leave: str
    ) -> None:
        """[P0] AC-16 Card transitions clear feedback, stop tracks and release object URLs."""

        def journey() -> None:
            page.set_viewport_size(viewports.DESKTOP)
            install_microphone(page)
            first = review_card("thought again", category="sentence")
            second = review_card("another card", audio=False)
            api = AttemptApi(page, cards=[first, second])
            page.goto("/en/pronunciation")
            finish_attempt(page)
            completed_score = score_ring(page).inner_text()
            record_button(page, "Try again").click()
            recording = mic_state(page)

            if leave == "rating":
                # First Assessment permits a Rating while a later Attempt is being assessed.
                api.hold = True
                record_button(page, LISTENING).click()
                api.wait_for_attempts(2)
                rating_button(page, "Good").click()
                expect(target_text(page, "another card")).to_be_visible()
                api.release()  # late feedback for the previous Card must be ignored
            else:
                language_nav(page, "English").get_by_role("link", name="Items", exact=True).click()
                language_nav(page, "English").get_by_role(
                    "link", name="Pronunciation", exact=True
                ).click()
                expect(target_text(page, "thought again")).to_be_visible()

            expect(score_ring(page)).to_have_count(0)
            assert recording["tracks"] > recording["trackStops"]
            expect(word_feedback(page)).to_have_count(0)
            expect(main(page).get_by_text(completed_score, exact=True)).to_have_count(0)
            for name in RATINGS:
                expect(rating_button(page, name)).to_be_disabled()
            released = mic_state(page)
            assert released["trackStops"] == released["tracks"]
            assert set(released["createdUrls"]) == set(released["revokedUrls"])
            assert (
                page.evaluate(
                    "[...document.querySelectorAll('audio')].some(a => a.src.startsWith('blob:'))"
                )
                is False
            )

        assert observe_journey(journey) is None

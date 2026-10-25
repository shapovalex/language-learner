"""Story 7.1 red-phase Pronunciation review journeys at phone, iPad and desktop widths.

API responses are per-page doubles (tests/support/pronunciation_screen.py). Every assertion
observes the real Pronunciation screen: what it renders, the requests it sends and their order.
Python Playwright has no outer promise matcher: the missing review UI stops most journeys at
their first locator, before later transitions run. That red-phase limitation is recorded for
task activation; later transitions need re-observation once the screen exists.
"""

import json
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.attempt_screen import (
    assessment,
    finish_attempt,
    install_microphone,
    record_button,
)
from tests.support.captures_screen import main
from tests.support.navigation import language_nav, screen_heading
from tests.support.pronunciation_screen import (
    EMPTY_BODY,
    EMPTY_TITLE,
    LANGUAGES,
    QUEUE_FAILED,
    RATING_FAILED,
    RATINGS,
    ReviewApi,
    is_media,
    is_session,
    queue_chip,
    rating_alert,
    rating_button,
    reference_button,
    review_card,
    target_text,
)


@pytest.fixture(autouse=True)
def attempt_boundary(page: Page) -> None:
    """Ratings still exercise the real UI gate, with native microphone/API boundaries."""
    install_microphone(page)
    page.route(
        "**/api/pronunciation/*/attempt",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"assessment": assessment(), "nothingHeard": False}),
        ),
    )


class TestReviewLoop:
    @pytest.mark.p1
    @pytest.mark.parametrize(
        ("width", "lang"), [("phone", "en"), ("tablet", "fr")], ids=["iphone-en", "ipad-fr"]
    )
    def test_the_screen_shows_the_queue_chip_and_the_current_target(
        self, page: Page, width: str, lang: str
    ) -> None:
        """[P1] AC-4 "N due · M new" chip and the first Card's Target on phone and iPad."""
        page.set_viewport_size(viewports.ALL[width])
        due = [review_card(f"due {i}") for i in range(3)]
        new = [review_card(f"new {i}", category="sentence") for i in range(2)]
        ReviewApi(page, lang=lang, due=due, new=new)

        page.goto(f"/{lang}/pronunciation")

        expect(queue_chip(page, 3, 2)).to_have_text("3 due · 2 new")
        expect(target_text(page, "due 0")).to_be_visible()
        expect(screen_heading(page)).to_have_text(f"{LANGUAGES[lang]} Pronunciation")

    @pytest.mark.p1
    def test_an_empty_queue_shows_the_empty_state(self, page: Page) -> None:
        """[P1] AC-5 the empty state copy, and no Rating buttons."""
        page.set_viewport_size(viewports.PHONE)
        ReviewApi(page, lang="fr")

        page.goto("/fr/pronunciation")

        expect(main(page).get_by_text(EMPTY_TITLE.format(language="French"))).to_be_visible()
        expect(main(page).get_by_text(EMPTY_BODY)).to_be_visible()
        for name in RATINGS:
            expect(rating_button(page, name)).to_have_count(0)

    @pytest.mark.p0
    def test_the_first_card_shows_before_and_without_waiting_for_the_presession_sync(
        self, page: Page
    ) -> None:
        """[P0] AC-6 the queue is read first; a held session start never delays the Card."""
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="en", due=[review_card("thoroughly")], hold_start=True)

        page.goto("/en/pronunciation")

        expect(target_text(page, "thoroughly")).to_be_visible()
        api.wait_for("start")  # sent, and still unanswered
        assert api.events.index("queue") < api.events.index("start")
        assert api.sessions == ["start"]
        expect(main(page).get_by_text("Sync")).to_have_count(0)

    @pytest.mark.p1
    def test_reference_plays_from_media_and_is_absent_without_audio(self, page: Page) -> None:
        """[P1] AC-7 Reference fetches the Card's clip; a Card without audio has no control."""
        page.set_viewport_size(viewports.DESKTOP)
        with_audio = review_card("water", reps=2)
        without_audio = review_card("butter", audio=False)
        api = ReviewApi(page, lang="en", due=[with_audio, without_audio])
        page.goto("/en/pronunciation")

        with page.expect_request(is_media) as played:
            reference_button(page).click()

        assert urlparse(played.value.url).path == f"/api/media/{with_audio['audio']}"
        finish_attempt(page)

        rating_button(page, "Good").click()
        expect(target_text(page, "butter")).to_be_visible()
        expect(reference_button(page)).to_have_count(0)
        assert api.media_requests == [f"/api/media/{with_audio['audio']}"]

    @pytest.mark.p0
    def test_a_rating_submits_that_card_and_loads_the_next(self, page: Page) -> None:
        """[P0] AC-9 Good posts cardId, reps and rating, then the next Card and chip show."""
        page.set_viewport_size(viewports.PHONE)
        first = review_card("squirrel", reps=4)
        second = review_card("Je voudrais un café.", category="sentence", audio=False)
        api = ReviewApi(page, lang="en", due=[first], new=[second])
        page.goto("/en/pronunciation")

        finish_attempt(page)

        rating_button(page, "Good").click()

        expect(target_text(page, "Je voudrais un café.")).to_be_visible()
        assert api.ratings == [{"cardId": first["cardId"], "reps": 4, "rating": "good"}]
        expect(target_text(page, "squirrel")).to_have_count(0)
        expect(queue_chip(page, 0, 1)).to_have_text("0 due · 1 new")
        for name in RATINGS:
            expect(rating_button(page, name)).to_be_disabled()

    @pytest.mark.p0
    def test_a_failed_rating_keeps_the_card_current_and_try_again_resends_it(
        self, page: Page
    ) -> None:
        """[P0] AC-11 the Rating alert shows, the Card stays, and Try again resends it."""
        page.set_viewport_size(viewports.DESKTOP)
        first = review_card("rural", reps=1)
        second = review_card("anemone")
        api = ReviewApi(page, lang="en", due=[first, second])
        api.rating_error = True
        page.goto("/en/pronunciation")

        finish_attempt(page)

        rating_button(page, "Hard").click()

        expect(rating_alert(page)).to_contain_text(RATING_FAILED)
        expect(target_text(page, "rural")).to_be_visible()
        expect(queue_chip(page, 2, 0)).to_be_visible()
        api.rating_error = False
        rating_alert(page).get_by_role("button", name="Try again", exact=True).click()
        expect(target_text(page, "anemone")).to_be_visible()
        assert api.ratings == [{"cardId": first["cardId"], "reps": 1, "rating": "hard"}] * 2

    @pytest.mark.p0
    def test_leaving_the_review_sends_the_session_end_signal(self, page: Page) -> None:
        """[P0] AC-13 unmounting the screen (navigating to Items) sends session end."""
        page.set_viewport_size(viewports.DESKTOP)
        api = ReviewApi(page, lang="en", due=[review_card("weather")])
        page.goto("/en/pronunciation")
        expect(target_text(page, "weather")).to_be_visible()

        with page.expect_request(is_session("en", "end")) as ended:
            language_nav(page, "English").get_by_role("link", name="Items", exact=True).click()

        assert urlparse(ended.value.url).path == "/api/pronunciation/en/session/end"
        assert api.sessions[:1] == ["start"]
        expect(screen_heading(page)).to_have_text("English Items")


def _hide_page(page: Page) -> None:
    """The page goes to the background, as a phone's app switch leaves it."""
    page.evaluate(
        """() => {
          Object.defineProperty(document, "visibilityState", {
            value: "hidden", configurable: true,
          });
          document.dispatchEvent(new Event("visibilitychange"));
        }"""
    )


class TestReviewLoopGreenPhase:
    @pytest.mark.p1
    def test_reference_never_autoplays_and_fetches_nothing_before_a_tap(self, page: Page) -> None:
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="en", due=[review_card("water")])
        page.goto("/en/pronunciation")

        expect(target_text(page, "water")).to_be_visible()
        expect(reference_button(page)).to_be_visible()
        api.wait_for("start")

        assert api.media_requests == []
        assert page.evaluate("document.querySelectorAll('audio').length") == 0

    @pytest.mark.p1
    def test_a_skeleton_shows_while_the_first_card_is_read(self, page: Page) -> None:
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="fr", due=[review_card("bonjour")])
        api.hold_queue = True
        page.goto("/fr/pronunciation")

        api.wait_for("queue")
        expect(main(page).get_by_role("status")).to_contain_text("Loading French Pronunciation")
        for name in RATINGS:
            expect(rating_button(page, name)).to_have_count(0)
        assert api.sessions == []
        api.release_queue()
        expect(target_text(page, "bonjour")).to_be_visible()

    @pytest.mark.p1
    def test_a_failed_queue_read_shows_an_alert_and_try_again_reads_it(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        api = ReviewApi(page, lang="en", due=[review_card("weather")])
        api.queue_error = True
        page.goto("/en/pronunciation")

        alert = main(page).get_by_role("alert")
        expect(alert).to_contain_text(QUEUE_FAILED)
        assert api.sessions == []
        api.queue_error = False
        alert.get_by_role("button", name="Try again", exact=True).click()

        expect(target_text(page, "weather")).to_be_visible()
        api.wait_for("start")

    @pytest.mark.p0
    def test_an_empty_queue_sends_the_session_end(self, page: Page) -> None:
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="en")
        page.goto("/en/pronunciation")

        expect(main(page).get_by_text(EMPTY_TITLE.format(language="English"))).to_be_visible()
        api.wait_for("end")
        assert api.sessions == ["end"]

    @pytest.mark.p0
    def test_rating_the_last_card_shows_the_empty_state_and_ends_the_session(
        self, page: Page
    ) -> None:
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="fr", new=[review_card("merci", audio=False)])
        page.goto("/fr/pronunciation")
        expect(target_text(page, "merci")).to_be_visible()

        finish_attempt(page)

        rating_button(page, "Easy").click()

        expect(main(page).get_by_text(EMPTY_BODY)).to_be_visible()
        api.wait_for("end")
        assert api.sessions == ["start", "end"]

    @pytest.mark.p0
    def test_a_hidden_page_ends_the_session_and_showing_it_again_starts_one(
        self, page: Page
    ) -> None:
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="en", due=[review_card("weather")])
        page.goto("/en/pronunciation")
        expect(target_text(page, "weather")).to_be_visible()
        api.wait_for("start")

        with page.expect_request(is_session("en", "end")):
            _hide_page(page)

        page.evaluate(
            """() => {
              Object.defineProperty(document, "visibilityState", {
                value: "visible", configurable: true,
              });
              document.dispatchEvent(new Event("visibilitychange"));
            }"""
        )
        with page.expect_request(is_session("en", "end")):
            language_nav(page, "English").get_by_role("link", name="Items", exact=True).click()
        assert api.sessions[:3] == ["start", "end", "start"]

    @pytest.mark.p0
    def test_pagehide_sends_the_session_end_as_a_beacon(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        ReviewApi(page, lang="en", due=[review_card("weather")])
        page.goto("/en/pronunciation")
        expect(target_text(page, "weather")).to_be_visible()

        with page.expect_request(is_session("en", "end")) as ended:
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide'))")

        assert ended.value.method == "POST"
        # sendBeacon: Chromium reports it as "ping", WebKit as "beacon"
        assert ended.value.resource_type in ("ping", "beacon")

    @pytest.mark.p2
    @pytest.mark.parametrize(("width", "rows"), [("phone", 2), ("tablet", 1)])
    def test_rating_is_two_by_two_on_phone_and_four_across_on_tablet(
        self, page: Page, width: str, rows: int
    ) -> None:
        page.set_viewport_size(viewports.ALL[width])
        ReviewApi(page, lang="en", due=[review_card("weather")])
        page.goto("/en/pronunciation")
        expect(rating_button(page, "Easy")).to_be_visible()

        tops = {round(rating_button(page, name).bounding_box()["y"]) for name in RATINGS}

        assert len(tops) == rows

    @pytest.mark.p1
    def test_the_live_server_accepts_the_session_signals_and_the_beacon(self, page: Page) -> None:
        """AD-16: a same-origin signal, the beacon included, passes the Origin allow-list."""
        page.set_viewport_size(viewports.DESKTOP)
        card = json.dumps({"due": 1, "new": 0, "cards": [review_card("weather")]})
        page.route(
            "**/api/pronunciation/en/queue",
            lambda route: route.fulfill(status=200, content_type="application/json", body=card),
        )

        with page.expect_response(lambda r: is_session("en", "start")(r.request)) as started:
            page.goto("/en/pronunciation")
        with page.expect_response(lambda r: is_session("en", "end")(r.request)) as ended:
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide'))")

        assert started.value.status == 204
        assert ended.value.status == 204

    @pytest.mark.p0
    def test_a_rating_of_a_card_gone_from_anki_reads_the_queue_again(self, page: Page) -> None:
        """404: the Card left the queue since the read; the next one shows, with no alert."""
        page.set_viewport_size(viewports.PHONE)
        gone = review_card("rural", reps=1)
        api = ReviewApi(page, lang="en", due=[gone, review_card("anemone")])
        api.gone.add(gone["cardId"])
        page.goto("/en/pronunciation")

        finish_attempt(page)

        rating_button(page, "Good").click()

        expect(target_text(page, "anemone")).to_be_visible()
        expect(main(page).get_by_role("alert")).to_have_count(0)
        assert api.ratings == [{"cardId": gone["cardId"], "reps": 1, "rating": "good"}]

    @pytest.mark.p1
    def test_keyboard_focus_moves_to_record_for_the_next_card(self, page: Page) -> None:
        page.set_viewport_size(viewports.DESKTOP)
        ReviewApi(page, lang="en", due=[review_card("water"), review_card("butter")])
        page.goto("/en/pronunciation")

        finish_attempt(page)
        rating_button(page, "Good").focus()
        page.keyboard.press("Enter")

        expect(target_text(page, "butter")).to_be_visible()
        expect(record_button(page)).to_be_focused()

    @pytest.mark.p1
    def test_a_page_hidden_before_the_first_card_starts_its_session_when_shown(
        self, page: Page
    ) -> None:
        page.set_viewport_size(viewports.PHONE)
        api = ReviewApi(page, lang="en", due=[review_card("weather")])
        api.hold_queue = True
        page.goto("/en/pronunciation")
        api.wait_for("queue")
        _hide_page(page)

        api.release_queue()
        expect(target_text(page, "weather")).to_be_attached()
        assert api.sessions == []

        with page.expect_request(is_session("en", "start")):
            page.evaluate(
                """() => {
                  Object.defineProperty(document, "visibilityState", {
                    value: "visible", configurable: true,
                  });
                  document.dispatchEvent(new Event("visibilitychange"));
                }"""
            )

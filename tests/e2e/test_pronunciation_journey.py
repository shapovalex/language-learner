"""Story 7.4: one Pronunciation review session through the running app, end to end.

Unlike the 7.1 and 7.2 screen tests, nothing here is a page-local API double: each case runs
the real app on its own live server, with a FakeAnkiStore seeded per Language (one due
Pronounce Card with Reference audio, one new one) and a FakeSpeech whose Assessment is the real
Azure reply fixture parsed by the real Azure adapter. The only browser double is the fake
microphone. The journey acts only through roles and labels and observes only the page: the
chip, the Target, the score ring, Word feedback, the Rating buttons and the empty state. An
in-page probe records which source the Reference player was asked to play, because that is what
the learner hears. The manual acceptance on the released wheel is
_bmad-output/test-artifacts/acceptance/pronunciation-review-acceptance-7-4.md.
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import pytest
from playwright.sync_api import Page, expect

from language_lab.domain.catalog import Category, Language
from language_lab.domain.pronunciation import Assessment, PronounceCard
from language_lab.settings import Settings
from tests.fakes.anki_store import FakeAnkiStore
from tests.fakes.speech import FakeSpeech
from tests.support import viewports
from tests.support.aio import run
from tests.support.assessment import EN_REPLY, FR_REPLY, assess_wire, response_fixture
from tests.support.attempt_screen import (
    LISTENING,
    finish_attempt,
    install_microphone,
    record_button,
    score_ring,
    word_feedback,
)
from tests.support.audio import MP3, managed_name
from tests.support.azure import AzureReplay
from tests.support.captures_screen import main
from tests.support.duplicates import vocabulary
from tests.support.items import content
from tests.support.live_server import LiveServer, bind_free_port, run_live_server
from tests.support.pronunciation_screen import (
    EMPTY_TITLE,
    LANGUAGES,
    RATINGS,
    queue_chip,
    rating_button,
    reference_button,
    target_text,
)


@dataclass(frozen=True)
class Seed:
    locale: str
    reply: str
    due: str  # the due Card's Target; distinct from the reply's word, so no text collides
    new: str


SEEDS = {
    "en": Seed("en-US", EN_REPLY, due="I thought so", new="taught"),
    "fr": Seed("fr-CA", FR_REPLY, due="Bonjour, Marie", new="bonsoir"),
}
WIDTHS = {"phone": viewports.PHONE, "desktop": viewports.DESKTOP}

# Records each source a media element is asked to play, before the browser may refuse it.
PLAYED_PROBE = """(() => {
  window.__played = [];
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function (...args) {
    window.__played.push(this.currentSrc || this.src);
    return play.apply(this, args);
  };
})();"""


def real_assessment(seed: Seed) -> Assessment:
    """The real Azure reply fixture, parsed by the real adapter over the offline replay."""
    replay = AzureReplay([httpx.Response(200, json=response_fixture(seed.reply))])
    wire = run(assess_wire(replay, locale=seed.locale, target=seed.due))
    return Assessment.model_validate(wire)


def seeded_store(language: Language, seed: Seed) -> FakeAnkiStore:
    """One due Card (with its Reference clip in media) and one new Card, in `language`."""
    store = FakeAnkiStore()
    due_id, new_id = str(uuid.uuid4()), str(uuid.uuid4())
    clip = managed_name(due_id)
    store.items[due_id] = (language, content(vocabulary(seed.due)))
    store.items[new_id] = (language, content(vocabulary(seed.new)))
    store.audio[due_id] = clip
    store.media[clip] = MP3
    store.pronounce = [
        (language, True, PronounceCard(1001, due_id, 3, Category.VOCABULARY, seed.due, clip)),
        (language, False, PronounceCard(1002, new_id, 0, Category.VOCABULARY, seed.new, None)),
    ]
    return store


@pytest.fixture
def seeded_server(request: pytest.FixtureRequest) -> Iterator[LiveServer]:
    """A fresh seeded app per case, on its own socket, so no case sees another's Ratings."""
    lang = request.node.callspec.params["language"]
    seed = SEEDS[lang]
    speech = FakeSpeech()
    speech.assessment = real_assessment(seed)
    sock = bind_free_port()
    host, port = sock.getsockname()
    settings = Settings(
        host=host,
        port=port,
        azure_speech_key="e2e-azure-key",
        azure_speech_region="e2e-region",
        openrouter_api_key="e2e-openrouter-key",
    )
    store = seeded_store(Language(lang), seed)
    with run_live_server(settings, sock, anki_store=store, speech=speech) as server:
        yield server


def played_bytes(page: Page) -> list[bytes]:
    """The clips the page asked a player to play, fetched from their sources, in order."""
    arrays = page.evaluate(
        """async () => Promise.all(window.__played.map(async source => {
          const response = await fetch(source);
          if (!response.ok) return [];
          return Array.from(new Uint8Array(await response.arrayBuffer()));
        }))"""
    )
    return [bytes(value) for value in arrays]


def expect_feedback(page: Page, lang: str) -> None:
    """The real fixture's feedback, as the learner sees it for this Language."""
    feedback = word_feedback(page)
    if lang == "en":
        expect(score_ring(page)).to_have_text("79.2")
        expect(main(page).get_by_label("Prosody", exact=True)).to_have_text("53.4")
        expect(feedback).to_contain_text("thought")
        for symbol in ("θ", "ɔ", "t"):
            expect(feedback.get_by_text(symbol, exact=True)).to_be_visible()
        return
    expect(score_ring(page)).to_have_text("10.6")
    expect(feedback).to_contain_text("bonjour")
    for position in ("start", "middle", "end"):
        expect(feedback.get_by_text(position, exact=True)).to_be_visible()
    expect(main(page).get_by_label("Prosody", exact=True)).to_have_count(0)
    text = feedback.inner_text()
    assert all(symbol not in text for symbol in ("ʒ", "ɔ̃", "ʁ", "θ"))
    assert "phoneme" not in text.lower()
    assert "sound /" not in text.lower()


@pytest.mark.p0
@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_one_review_session_from_queue_to_empty_state(
    page: Page, seeded_server: LiveServer, language: str, width: str
) -> None:
    """[P0] Queue → Reference → Attempt → retry → Rating → next Card → empty state, UI only."""
    page.set_viewport_size(WIDTHS[width])
    seed = SEEDS[language]
    install_microphone(page)
    page.add_init_script(script=PLAYED_PROBE)

    # Open: the chip counts the seeded queue; the due Card is first; Ratings wait for an Attempt.
    page.goto(f"{seeded_server.url}/{language}/pronunciation")
    expect(queue_chip(page, 1, 1)).to_have_text("1 due · 1 new")
    expect(target_text(page, seed.due)).to_be_visible()
    for name in RATINGS:
        expect(rating_button(page, name)).to_be_disabled()

    # Reference: the player is given the seeded clip.
    reference_button(page).click()
    page.wait_for_function("window.__played.length > 0")
    assert played_bytes(page) == [MP3]

    # Attempt: the real fixture's feedback in this Language's form.
    finish_attempt(page)
    expect_feedback(page, language)
    for name in RATINGS:
        expect(rating_button(page, name)).to_be_enabled()

    # Retry: the old feedback goes while listening, new feedback comes; same Card, still ratable.
    record_button(page, "Try again").click()
    expect(record_button(page, LISTENING)).to_be_visible()
    expect(score_ring(page)).to_have_count(0)
    record_button(page, LISTENING).click()
    expect_feedback(page, language)
    expect(target_text(page, seed.due)).to_be_visible()
    expect(queue_chip(page, 1, 1)).to_be_visible()
    for name in RATINGS:
        expect(rating_button(page, name)).to_be_enabled()

    # Rate: Good moves to the new Card, with no feedback and Ratings waiting again.
    rating_button(page, "Good").click()
    expect(target_text(page, seed.new)).to_be_visible()
    expect(queue_chip(page, 0, 1)).to_have_text("0 due · 1 new")
    expect(score_ring(page)).to_have_count(0)
    expect(word_feedback(page)).to_have_count(0)
    expect(target_text(page, seed.due)).to_have_count(0)
    for name in RATINGS:
        expect(rating_button(page, name)).to_be_disabled()

    # Finish: one Attempt and Easy empty the queue.
    finish_attempt(page)
    expect(score_ring(page)).to_be_visible()
    rating_button(page, "Easy").click()
    title = EMPTY_TITLE.format(language=LANGUAGES[language])
    expect(main(page).get_by_text(title, exact=True)).to_be_visible()
    for name in RATINGS:
        expect(rating_button(page, name)).to_have_count(0)

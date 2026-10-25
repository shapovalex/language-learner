"""Story 7.1 Pronunciation review over HTTP: the queue read, Ratings, and session Sync.

Proposed contracts (the builder may rename them and update these tests):

- `GET /api/pronunciation/<lang>/queue` → `{"due", "new", "cards": [{"cardId", "itemId",
  "reps", "category", "target", "audio"}]}` in FR-30 order; `audio` is the managed name or null.
- `POST /api/pronunciation/<lang>/rating` with `{"cardId", "reps", "rating"}` →
  `{"alreadyAnswered": bool}` (AD-20).
- `POST /api/pronunciation/<lang>/session/start` and `.../end` → 204, idempotent, each only
  requesting a Sync through the SyncRequester (AD-17), never waiting for it.

The queue and Rating tests run the real guarded adapter over hand-built AnkiConnect exchanges
(tests/support/pronunciation.py). The session tests run the app's own SyncService over the fake
store in the test's loop, without the lifespan, so only the session's Syncs are counted.
"""

import pytest

from language_lab.app import create_app
from language_lab.domain.catalog import Category, Language
from language_lab.settings import DEV_PREFIX
from tests.fakes.anki_store import FakeAnkiStore
from tests.fakes.llm import FakeLlm
from tests.fakes.speech import FakeSpeech
from tests.support.aio import run
from tests.support.anki_state import managed_collection, sent_writes
from tests.support.audio import audio_client
from tests.support.captures import MANIFEST
from tests.support.clock import drain
from tests.support.fixtures.settings import SettingsFactory
from tests.support.pronunciation import (
    QUEUE,
    RATING,
    SESSION,
    ReviewRig,
    asgi_client,
    due,
    new,
    queue_of,
)


def _client(settings_factory: SettingsFactory, rig: ReviewRig):
    settings = settings_factory(anki_prefix=MANIFEST.prefix)
    return audio_client(settings, rig.store, FakeSpeech())


class TestQueueRead:
    @pytest.mark.p0
    def test_the_queue_read_carries_counts_and_each_cards_identity_reps_and_audio(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-3 counts plus cardId, itemId, reps, Category, Target and audio per Card."""
        # Given a due English word with Reference audio and a new English sentence without.
        rig = ReviewRig(managed_collection(MANIFEST))
        word = rig.pronounce(
            Language.EN, Category.VOCABULARY, due(4, reps=6), target="through", audio=True
        )
        sentence = rig.pronounce(
            Language.EN, Category.SENTENCE, new(1), target="I'd rather not jump."
        )

        # When the English queue is read.
        response = _client(settings_factory, rig).get(QUEUE.format(lang="en"))

        # Then the first Card carries what the review screen and the Rating need.
        body = response.json()
        first = (body.get("cards") or [None])[0]
        assert first == {
            "cardId": word.card_id,
            "itemId": word.item_id,
            "reps": 6,
            "category": "vocabulary",
            "target": "through",
            "audio": word.audio,
        }
        assert response.status_code == 200
        assert (body["due"], body["new"]) == (1, 1)
        assert body["cards"][1] == {
            "cardId": sentence.card_id,
            "itemId": sentence.item_id,
            "reps": 0,
            "category": "sentence",
            "target": "I'd rather not jump.",
            "audio": None,
        }
        assert sent_writes(rig.replay.sent) == []


class TestRatingRetry:
    @pytest.mark.p0
    def test_a_retried_rating_with_stale_reps_is_already_answered_without_a_second_answer(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-10 the retry returns alreadyAnswered and Anki is answered once."""
        # Given a due French card at reps 4, rated Good once (the reply was lost).
        rig = ReviewRig(managed_collection(MANIFEST))
        card = rig.pronounce(Language.FR, Category.VOCABULARY, due(2, reps=4))
        client = _client(settings_factory, rig)
        rating = {"cardId": card.card_id, "reps": 4, "rating": "good"}
        client.post(RATING.format(lang="fr"), json=rating)

        # When the client retries the same Rating.
        retry = client.post(RATING.format(lang="fr"), json=rating)

        # Then it succeeds as already answered, and Anki saw a single answer.
        assert retry.json().get("alreadyAnswered") is True
        assert retry.status_code == 200
        assert rig.answers == [{"cardId": card.card_id, "ease": 3}]
        assert sent_writes(rig.replay.sent) == ["answerCards"]
        assert card.card_id not in [c.card_id for c in run(queue_of(rig.store, Language.FR)).cards]


class TestSessionSync:
    @pytest.mark.p0
    def test_session_start_and_end_each_request_a_sync_coalesced_and_never_awaited(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-12 start requests one Sync at once; repeats while it runs coalesce."""
        # Given the app over a store whose Syncs stay in flight until finished.
        settings = settings_factory()
        store = FakeAnkiStore(gated=True)
        app = create_app(settings, anki_store=store, llm=FakeLlm(), speech=FakeSpeech())

        async def scenario() -> dict[str, object]:
            async with asgi_client(app, settings) as client:
                start = await client.post(SESSION.format(lang="en", signal="start"))
                await drain()
                after_start = store.sync_calls
                repeated = await client.post(SESSION.format(lang="en", signal="start"))
                end = await client.post(SESSION.format(lang="en", signal="end"))
                await drain()
                while_running = store.sync_calls
                if store.in_flight:
                    store.finish()  # the running Sync ends; the one pending Sync starts
                await drain()
                after_first = store.sync_calls
                while store.in_flight:
                    store.finish()
                    await drain()
            return {
                "after_start": after_start,
                "statuses": [start.status_code, repeated.status_code, end.status_code],
                "while_running": while_running,
                "after_first": after_first,
                "max_in_flight": store.max_in_flight,
            }

        observed = run(scenario())

        # Then start answered before its Sync ended, and the duplicates became one pending Sync.
        assert observed["after_start"] == 1
        assert observed["statuses"] == [204, 204, 204]
        assert observed["while_running"] == 1
        assert observed["after_first"] == 2
        assert observed["max_in_flight"] == 1

    @pytest.mark.p1
    def test_dev_mode_session_signals_succeed_and_request_no_sync(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P1] AC-14 with LANGUAGE_LAB_DEV=1 start and end answer 204 and Sync nothing."""
        settings = settings_factory(dev=True, anki_prefix=DEV_PREFIX)
        store = FakeAnkiStore()
        app = create_app(settings, anki_store=store, llm=FakeLlm(), speech=FakeSpeech())

        async def scenario() -> list[int]:
            async with asgi_client(app, settings) as client:
                statuses = [
                    (await client.post(SESSION.format(lang=lang, signal=signal))).status_code
                    for lang in ("en", "fr")
                    for signal in ("start", "end")
                ]
                await drain()
            return statuses

        statuses = run(scenario())

        assert statuses == [204, 204, 204, 204]
        assert store.sync_calls == 0


def _code(response) -> str | None:
    return (response.json().get("error") or {}).get("code")


class TestRatingGreenPhase:
    @pytest.mark.p1
    @pytest.mark.parametrize(
        "body",
        [
            {"cardId": "1", "reps": 0, "rating": "good"},
            {"cardId": 1, "reps": -1, "rating": "good"},
            {"cardId": 1, "reps": 0, "rating": "perfect"},
            {"cardId": True, "reps": 0, "rating": "good"},
            {"cardId": 1, "reps": 0},
            {"cardId": 1, "reps": 0, "rating": "good", "extra": 1},
        ],
    )
    def test_a_malformed_rating_is_validation_failed_and_reaches_no_anki(
        self, settings_factory: SettingsFactory, body: dict[str, object]
    ) -> None:
        rig = ReviewRig(managed_collection(MANIFEST))

        response = _client(settings_factory, rig).post(RATING.format(lang="en"), json=body)

        assert response.status_code == 422
        assert _code(response) == "validation_failed"
        assert rig.replay.sent == []

    @pytest.mark.p0
    def test_a_rating_while_setup_is_not_ready_is_409_setup_required(
        self, settings_factory: SettingsFactory
    ) -> None:
        rig = ReviewRig(managed_collection(MANIFEST), state="needs_setup")
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1, reps=2))
        rating = {"cardId": card.card_id, "reps": 2, "rating": "good"}

        response = _client(settings_factory, rig).post(RATING.format(lang="en"), json=rating)

        assert response.status_code == 409
        assert _code(response) == "setup_required"
        assert rig.answers == []

    @pytest.mark.p0
    def test_a_rating_for_another_languages_card_is_404(
        self, settings_factory: SettingsFactory
    ) -> None:
        rig = ReviewRig(managed_collection(MANIFEST))
        card = rig.pronounce(Language.FR, Category.VOCABULARY, due(1, reps=2))
        rating = {"cardId": card.card_id, "reps": 2, "rating": "good"}

        response = _client(settings_factory, rig).post(RATING.format(lang="en"), json=rating)

        assert response.status_code == 404
        assert _code(response) == "not_found"
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    def test_an_unconfirmed_answer_is_503_anki_unavailable(
        self, settings_factory: SettingsFactory
    ) -> None:
        rig = ReviewRig(
            managed_collection(MANIFEST),
            replies={"answerCards": {"result": [False], "error": None}},
        )
        card = rig.pronounce(Language.EN, Category.SENTENCE, new(1))
        rating = {"cardId": card.card_id, "reps": 0, "rating": "again"}

        response = _client(settings_factory, rig).post(RATING.format(lang="en"), json=rating)

        assert response.status_code == 503
        assert _code(response) == "anki_unavailable"

    @pytest.mark.p1
    def test_a_fresh_rating_is_answered_now(self, settings_factory: SettingsFactory) -> None:
        rig = ReviewRig(managed_collection(MANIFEST))
        card = rig.pronounce(Language.EN, Category.SENTENCE, new(1))
        rating = {"cardId": card.card_id, "reps": 0, "rating": "easy"}

        response = _client(settings_factory, rig).post(RATING.format(lang="en"), json=rating)

        assert response.status_code == 200
        assert response.json() == {"alreadyAnswered": False}
        assert rig.answers == [{"cardId": card.card_id, "ease": 4}]


class TestQueueGreenPhase:
    @pytest.mark.p1
    @pytest.mark.parametrize(
        ("store", "code"),
        [
            (FakeAnkiStore(available=False), "anki_unavailable"),
            (FakeAnkiStore(busy=True), "anki_busy"),
        ],
        ids=["unavailable", "busy"],
    )
    def test_a_queue_read_anki_cannot_answer_is_503(
        self, settings_factory: SettingsFactory, store: FakeAnkiStore, code: str
    ) -> None:
        response = audio_client(settings_factory(), store).get(QUEUE.format(lang="fr"))

        assert response.status_code == 503
        assert _code(response) == code

    @pytest.mark.p1
    def test_an_unknown_language_is_422(self, settings_factory: SettingsFactory) -> None:
        store = FakeAnkiStore()
        client = audio_client(settings_factory(), store)

        assert client.get(QUEUE.format(lang="de")).status_code == 422
        assert client.post(SESSION.format(lang="de", signal="start")).status_code == 422
        assert store.sync_calls == 0

    @pytest.mark.p1
    def test_the_queue_route_logs_no_target_text(
        self, settings_factory: SettingsFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        """NFR-7: the request log line carries the route, never the Card's Target."""
        rig = ReviewRig(managed_collection(MANIFEST))
        rig.pronounce(Language.EN, Category.VOCABULARY, due(1), target="secretword")

        with caplog.at_level("INFO", logger="language_lab"):
            response = _client(settings_factory, rig).get(QUEUE.format(lang="en"))

        assert response.status_code == 200
        assert "secretword" not in caplog.text
        assert "/api/pronunciation/{lang}/queue" in caplog.text


class TestSessionGreenPhase:
    @pytest.mark.p1
    def test_a_failing_sync_never_fails_a_session_signal(
        self, settings_factory: SettingsFactory
    ) -> None:
        settings = settings_factory()
        store = FakeAnkiStore(available=False)
        app = create_app(settings, anki_store=store, llm=FakeLlm(), speech=FakeSpeech())

        async def scenario() -> list[int]:
            async with asgi_client(app, settings) as client:
                statuses = [
                    (await client.post(SESSION.format(lang="en", signal=s))).status_code
                    for s in ("start", "end")
                ]
                await drain()
            return statuses

        assert run(scenario()) == [204, 204]
        assert store.sync_calls >= 1

"""Story 7.1 Pronunciation queue and Rating through the real guarded Anki adapter.

FR-30 and AD-6: the queue is the Language's ord-3 cards in its Pronunciation decks, `is:due` or
`is:new` and not suspended, due first (oldest due first), then new in creation order. FR-34 and
AD-20: a Rating answers that card only, through Anki's scheduler, with again/hard/good/easy
mapped to ease 1-4 in the adapter, under one lock hold. The AnkiConnect exchanges are hand-built
(tests/support/pronunciation.py) until story 7.4 records them.
"""

import pytest

from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from tests.support.aio import settle
from tests.support.anki_state import (
    apply_manifest,
    capture_note,
    managed_collection,
    sent_writes,
)
from tests.support.captures import DEV_MANIFEST, MANIFEST
from tests.support.pronunciation import (
    ReviewRig,
    buried,
    card_id_set,
    card_ids,
    counts,
    day_learning,
    due,
    learning,
    new,
    not_due,
    queue_of,
    rate,
)

CAPTURE_ID = "c7a1e2b4-0000-4000-8000-000000000001"
CREATED_AT = "2026-10-25T09:00:00Z"


class TestPronunciationQueue:
    @pytest.mark.p0
    def test_queue_holds_only_the_languages_new_and_due_unsuspended_pronounce_cards(
        self,
    ) -> None:
        """[P0] AC-1 only new or due, unsuspended ord-3 cards in the Pronunciation decks."""
        # Given English Pronounce cards in and out of scope, and lookalikes elsewhere.
        collection = managed_collection(MANIFEST)
        apply_manifest(collection, DEV_MANIFEST)
        rig = ReviewRig(collection)
        due_word = rig.pronounce(Language.EN, Category.VOCABULARY, due(2))
        new_sentence = rig.pronounce(Language.EN, Category.SENTENCE, new(1))
        rig.pronounce(Language.EN, Category.VOCABULARY, not_due())
        rig.pronounce(Language.EN, Category.VOCABULARY, new(2), suspended=True)
        rig.pronounce(Language.EN, Category.SENTENCE, due(3), suspended=True)
        rig.pronounce(Language.FR, Category.VOCABULARY, due(5))
        rig.pronounce(Language.EN, Category.VOCABULARY, due(6), manifest=DEV_MANIFEST)
        capture_note(collection, MANIFEST, CAPTURE_ID, "x", CREATED_AT)
        # An Item whose Understand card a failed move left in the Pronunciation deck (AD-6)
        left_behind = rig.pronounce(Language.EN, Category.VOCABULARY, not_due())
        understand = rig.card_ids_of(left_behind.note_id)[0]
        collection.cards[understand].deck = MANIFEST.card_deck(
            MANIFEST.item_note_type(Language.EN, Category.VOCABULARY), 3
        )

        # When the English queue is read.
        outcome = settle(queue_of(rig.store, Language.EN))

        # Then exactly the due and the new in-scope Pronounce cards are queued.
        assert card_id_set(outcome) == {due_word.card_id, new_sentence.card_id}
        assert counts(outcome) == (1, 1)
        assert rig.answers == []
        assert rig.lock.holds == 1
        assert rig.lock.depth == 0
        assert set(rig.lock.request_depths) == {1}

    @pytest.mark.p0
    def test_queue_is_due_first_oldest_due_first_then_new_in_creation_order(self) -> None:
        """[P0] AC-2 due before new, oldest due first, new in creation order."""
        # Given due and new cards whose creation order differs from their due order, mixed
        # across both Categories.
        rig = ReviewRig(managed_collection(MANIFEST))
        recently_due = rig.pronounce(Language.FR, Category.VOCABULARY, due(1))
        long_due = rig.pronounce(Language.FR, Category.SENTENCE, due(9))
        first_new = rig.pronounce(Language.FR, Category.SENTENCE, new(10))
        due_today = rig.pronounce(Language.FR, Category.VOCABULARY, due(0))
        second_new = rig.pronounce(Language.FR, Category.VOCABULARY, new(11))
        third_new = rig.pronounce(Language.FR, Category.SENTENCE, new(12))

        # When the French queue is read.
        outcome = settle(queue_of(rig.store, Language.FR))

        # Then it is in FR-30 order.
        assert card_ids(outcome) == [
            long_due.card_id,
            recently_due.card_id,
            due_today.card_id,
            first_new.card_id,
            second_new.card_id,
            third_new.card_id,
        ]
        assert counts(outcome) == (3, 3)
        cards = outcome.cards
        assert cards[0].item_id == long_due.item_id
        assert cards[0].category is Category.SENTENCE
        assert cards[0].target == long_due.target


class TestRating:
    @pytest.mark.p0
    def test_a_rating_answers_only_that_card_through_the_scheduler(self) -> None:
        """[P0] AC-8 one answerCards for that card, Hard mapped to ease 2, under one lock."""
        # Given two due English Pronounce cards.
        rig = ReviewRig(managed_collection(MANIFEST))
        rated = rig.pronounce(Language.EN, Category.VOCABULARY, due(3, reps=4))
        other = rig.pronounce(Language.EN, Category.SENTENCE, due(2, reps=7))

        # When the first is rated Hard at the reps shown.
        outcome = settle(rate(rig.store, Language.EN, rated.card_id, 4, "hard"))

        # Then Anki answered that card only, with ease 2.
        assert rig.answers == [{"cardId": rated.card_id, "ease": 2}]
        assert outcome is False  # answered now, not alreadyAnswered
        assert rig.schedules[rated.card_id].reps == 5
        assert rig.schedules[other.card_id].reps == 7
        assert rig.lock.holds == 1
        assert rig.lock.depth == 0
        assert set(rig.lock.request_depths) == {1}


class TestQueueGreenPhase:
    @pytest.mark.p1
    def test_learning_cards_are_due_and_buried_cards_are_dropped(self) -> None:
        """Day-based due cards (review and day learning) by day, intraday learning after them;
        a buried card, new or due, never queues."""
        rig = ReviewRig(managed_collection(MANIFEST))
        intraday = rig.pronounce(Language.EN, Category.VOCABULARY, learning(600))
        review = rig.pronounce(Language.EN, Category.SENTENCE, due(1))
        day_learn = rig.pronounce(Language.EN, Category.VOCABULARY, day_learning(4))
        later = rig.pronounce(Language.EN, Category.SENTENCE, learning(5))
        rig.pronounce(Language.EN, Category.VOCABULARY, buried(new(1)))
        rig.pronounce(Language.EN, Category.SENTENCE, buried(due(7)))
        fresh = rig.pronounce(Language.EN, Category.SENTENCE, new(2))

        outcome = settle(queue_of(rig.store, Language.EN))

        assert card_ids(outcome) == [
            day_learn.card_id,
            review.card_id,
            intraday.card_id,
            later.card_id,
            fresh.card_id,
        ]
        assert counts(outcome) == (4, 1)

    @pytest.mark.p1
    def test_the_target_is_decoded_through_the_codec_and_audio_is_the_managed_name(self) -> None:
        """AD-9: the stored field's HTML escapes come back as the plain Target."""
        rig = ReviewRig(managed_collection(MANIFEST))
        card = rig.pronounce(
            Language.FR, Category.SENTENCE, due(1), target="Tom &amp; Jerry &lt;3", audio=True
        )

        outcome = settle(queue_of(rig.store, Language.FR))

        [queued] = outcome.cards
        assert queued.target == "Tom & Jerry <3"
        assert queued.audio == card.audio
        assert queued.item_id == card.item_id

    @pytest.mark.p1
    def test_an_empty_queue_reads_no_cards_and_writes_nothing(self) -> None:
        rig = ReviewRig(managed_collection(MANIFEST))
        rig.pronounce(Language.EN, Category.VOCABULARY, not_due())

        outcome = settle(queue_of(rig.store, Language.EN))

        assert card_ids(outcome) == []
        assert counts(outcome) == (0, 0)
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p1
    def test_a_malformed_find_reply_is_anki_unavailable(self) -> None:
        rig = ReviewRig(
            managed_collection(MANIFEST), replies={"findCards": {"result": "x", "error": None}}
        )

        outcome = settle(queue_of(rig.store, Language.EN))

        assert isinstance(outcome, AppError)
        assert outcome.code is ErrorCode.ANKI_UNAVAILABLE

    @pytest.mark.p1
    def test_the_queue_is_read_ungated(self) -> None:
        """AD-19: reads stay open while Setup isn't ready."""
        rig = ReviewRig(managed_collection(MANIFEST), state="needs_setup")
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))

        assert card_ids(settle(queue_of(rig.store, Language.EN))) == [card.card_id]


class TestRatingGreenPhase:
    @pytest.mark.p0
    @pytest.mark.parametrize(
        ("rating", "ease"), [("again", 1), ("hard", 2), ("good", 3), ("easy", 4)]
    )
    def test_each_rating_maps_to_its_ease(self, rating: str, ease: int) -> None:
        rig = ReviewRig(managed_collection(MANIFEST))
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1, reps=2))

        outcome = settle(rate(rig.store, Language.EN, card.card_id, 2, rating))

        assert outcome is False
        assert rig.answers == [{"cardId": card.card_id, "ease": ease}]

    @pytest.mark.p0
    def test_stale_reps_send_no_answer(self) -> None:
        """AD-20: the reps moved on, so the Rating already landed."""
        rig = ReviewRig(managed_collection(MANIFEST))
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1, reps=5))

        outcome = settle(rate(rig.store, Language.EN, card.card_id, 4, "good"))

        assert outcome is True
        assert rig.answers == []
        assert sent_writes(rig.replay.sent) == []
        assert rig.lock.holds == 1

    @pytest.mark.p0
    def test_a_rating_while_setup_is_not_ready_is_refused_before_any_answer(self) -> None:
        """AD-19: the answer is a gated write."""
        rig = ReviewRig(managed_collection(MANIFEST), state="needs_setup")
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1, reps=2))

        outcome = settle(rate(rig.store, Language.EN, card.card_id, 2, "good"))

        assert isinstance(outcome, AppError)
        assert outcome.code is ErrorCode.SETUP_REQUIRED
        assert rig.answers == []
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    def test_a_card_outside_the_languages_pronounce_scope_is_not_found(self) -> None:
        """Another Language's card, a Study card, another Prefix's card or an unknown id."""
        collection = managed_collection(MANIFEST)
        apply_manifest(collection, DEV_MANIFEST)
        rig = ReviewRig(collection)
        french = rig.pronounce(Language.FR, Category.VOCABULARY, due(1, reps=0))
        english = rig.pronounce(Language.EN, Category.VOCABULARY, due(1, reps=0))
        understand = rig.card_ids_of(english.note_id)[0]
        dev = rig.pronounce(Language.EN, Category.VOCABULARY, due(1, reps=0), manifest=DEV_MANIFEST)
        foreign = [french.card_id, understand, dev.card_id, 9_999_999_999]

        outcomes = [settle(rate(rig.store, Language.EN, cid, 0, "good")) for cid in foreign]

        assert [getattr(o, "code", o) for o in outcomes] == [ErrorCode.NOT_FOUND] * 4
        assert rig.answers == []
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    @pytest.mark.parametrize("change", ["suspended", "buried", "moved"])
    def test_a_card_suspended_buried_or_moved_since_the_read_is_not_found(
        self, change: str
    ) -> None:
        """A card that left the queue after it was read is never answered."""
        rig = ReviewRig(managed_collection(MANIFEST))
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1, reps=2))
        if change == "suspended":
            rig.collection.cards[card.card_id].suspended = True
        elif change == "buried":
            rig.schedules[card.card_id] = buried(due(1, reps=2))
        else:
            model = MANIFEST.item_note_type(Language.EN, Category.VOCABULARY)
            rig.collection.cards[card.card_id].deck = MANIFEST.card_deck(model, 0)

        outcome = settle(rate(rig.store, Language.EN, card.card_id, 2, "good"))

        assert getattr(outcome, "code", outcome) is ErrorCode.NOT_FOUND
        assert rig.answers == []
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p1
    @pytest.mark.parametrize("reply", [[False], [], None, [True, True]])
    def test_an_unconfirmed_answer_is_anki_unavailable(self, reply: object) -> None:
        rig = ReviewRig(
            managed_collection(MANIFEST),
            replies={"answerCards": {"result": reply, "error": None}},
        )
        card = rig.pronounce(Language.EN, Category.SENTENCE, due(1, reps=1))

        outcome = settle(rate(rig.store, Language.EN, card.card_id, 1, "easy"))

        assert isinstance(outcome, AppError)
        assert outcome.code is ErrorCode.ANKI_UNAVAILABLE

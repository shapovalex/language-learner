"""Story 7.1 Pronunciation queue and Rating through the real guarded Anki adapter.

FR-30 and AD-6: the queue is the Language's ord-3 cards in its Pronunciation decks, `is:due` or
`is:new` and not suspended, due first (oldest due first), then new in creation order. FR-34 and
AD-20: a Rating answers that card only, through Anki's scheduler, with again/hard/good/easy
mapped to ease 1-4 in the adapter, under one lock hold. The AnkiConnect exchanges are hand-built
(tests/support/pronunciation.py) until story 7.4 records them.
"""

import pytest

from language_lab.domain.catalog import Category, Language
from tests.support.aio import settle
from tests.support.anki_state import apply_manifest, capture_note, managed_collection
from tests.support.captures import DEV_MANIFEST, MANIFEST
from tests.support.pronunciation import (
    ReviewRig,
    card_id_set,
    card_ids,
    counts,
    due,
    new,
    not_due,
    queue_of,
    rate,
)

pytestmark = pytest.mark.skip(
    reason="ATDD red phase until story 7.1 adds the AnkiStore queue and answer methods"
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

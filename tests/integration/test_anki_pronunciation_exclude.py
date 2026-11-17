"""Excluding an Item from Pronunciation, through the real guarded and gated Anki adapter.

The flag lives in Anki only (AD-13): an Item is excluded when its Pronounce Card (ord 3) is
suspended. `set_pronunciation_excluded(language, item_id, excluded)` finds the Item in the exact
scopes of both Categories, its ItemId matched in Python (AD-4), and sends `suspend` or
`unsuspend` for that one card only when its state differs, under one lock hold. The Study cards
(ords 0-2) are never written. `get_item` reports the flag as `pronunciation_excluded`.
"""

import uuid
from typing import Any

import pytest

from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from tests.support.aio import settle
from tests.support.anki_state import managed_collection, sent_writes
from tests.support.captures import MANIFEST
from tests.support.item_delete import action_bodies
from tests.support.pronunciation import ReviewRig, card_ids, due, new, queue_of


def exclude(rig: ReviewRig, language: Language, item_id: str, excluded: bool = True) -> Any:
    return settle(rig.store.set_pronunciation_excluded(language, item_id, excluded))


def writes(rig: ReviewRig) -> list[dict[str, Any]]:
    """The write bodies the adapter sent: every action that isn't a read."""
    names = set(sent_writes(rig.replay.sent))
    return [body for body in action_bodies(rig.replay) if body.get("action") in names]


def suspended(rig: ReviewRig, note_id: int) -> dict[int, bool]:
    """`{ord: suspended}` of one note's cards."""
    return {
        card.ord: card.suspended for card in rig.collection.cards.values() if card.note == note_id
    }


class TestExclude:
    @pytest.mark.p0
    @pytest.mark.parametrize("category", list(Category))
    def test_exclude_suspends_only_the_pronounce_card_and_it_leaves_the_queue(
        self, category: Category
    ) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        card = rig.pronounce(Language.EN, category, due(1))
        other = rig.pronounce(Language.EN, Category.VOCABULARY, due(2))

        outcome = exclude(rig, Language.EN, card.item_id)

        assert outcome is None
        assert writes(rig) == [
            {"action": "suspend", "version": 6, "params": {"cards": [card.card_id]}}
        ]
        assert suspended(rig, card.note_id) == {0: False, 1: False, 2: False, 3: True}
        assert card_ids(settle(queue_of(rig.store, Language.EN))) == [other.card_id]
        assert rig.lock.holds == 2  # the exclude, then the queue read
        assert set(rig.lock.request_depths) == {1}

    @pytest.mark.p0
    def test_include_unsuspends_only_the_pronounce_card_and_it_is_queued_again(self) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        card = rig.pronounce(Language.FR, Category.SENTENCE, new(1), suspended=True)

        outcome = exclude(rig, Language.FR, card.item_id, excluded=False)

        assert outcome is None
        assert writes(rig) == [
            {"action": "unsuspend", "version": 6, "params": {"cards": [card.card_id]}}
        ]
        assert suspended(rig, card.note_id) == {0: False, 1: False, 2: False, 3: False}
        assert card_ids(settle(queue_of(rig.store, Language.FR))) == [card.card_id]

    @pytest.mark.p0
    @pytest.mark.parametrize("excluded", [True, False])
    def test_a_flag_that_already_matches_writes_nothing(self, excluded: bool) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1), suspended=excluded)

        outcome = exclude(rig, Language.EN, card.item_id, excluded)

        assert outcome is None
        assert sent_writes(rig.replay.sent) == []
        assert rig.lock.holds == 1

    @pytest.mark.p0
    def test_the_item_id_is_matched_in_python_and_never_sent(self) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        card = rig.pronounce(Language.EN, Category.SENTENCE, due(1))

        exclude(rig, Language.EN, card.item_id)

        assert card.item_id not in repr([r.body for r in rig.replay.sent])

    @pytest.mark.p0
    @pytest.mark.parametrize("where", ["absent", "other-language"])
    def test_an_item_the_language_doesnt_hold_is_not_found_and_writes_nothing(
        self, where: str
    ) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        french = rig.pronounce(Language.FR, Category.VOCABULARY, due(1))
        item_id = french.item_id if where == "other-language" else str(uuid.uuid4())

        outcome = exclude(rig, Language.EN, item_id)

        assert getattr(outcome, "code", outcome) is ErrorCode.NOT_FOUND
        assert sent_writes(rig.replay.sent) == []
        assert rig.collection.cards[french.card_id].suspended is False

    @pytest.mark.p0
    def test_the_write_is_gated_while_setup_is_not_ready(self) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False), state="needs_setup")
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))

        outcome = exclude(rig, Language.EN, card.item_id)

        assert getattr(outcome, "code", outcome) is ErrorCode.SETUP_REQUIRED
        assert sent_writes(rig.replay.sent) == []
        assert rig.collection.cards[card.card_id].suspended is False

    @pytest.mark.p1
    @pytest.mark.parametrize(
        "reply",
        [
            {"result": None, "error": None},
            {"result": [{"cardId": "x", "ord": 3, "queue": 0}] * 4, "error": None},
            {"result": [{"cardId": 1, "ord": 0, "queue": 0}] * 4, "error": None},
            {"result": [], "error": None},
        ],
        ids=["not-a-list", "malformed-card", "no-pronounce-card", "wrong-length"],
    )
    def test_a_malformed_cards_info_is_anki_unavailable(self, reply: dict[str, Any]) -> None:
        rig = ReviewRig(
            managed_collection(MANIFEST, reading_rules=False), replies={"cardsInfo": reply}
        )
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))

        outcome = exclude(rig, Language.EN, card.item_id)
        read = settle(rig.store.get_item(Language.EN, card.item_id))

        assert getattr(outcome, "code", outcome) is ErrorCode.ANKI_UNAVAILABLE
        assert getattr(read, "code", read) is ErrorCode.ANKI_UNAVAILABLE
        assert sent_writes(rig.replay.sent) == []


class TestReadFlag:
    @pytest.mark.p0
    @pytest.mark.parametrize("excluded", [True, False])
    def test_get_item_reports_whether_the_pronounce_card_is_suspended(self, excluded: bool) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        card = rig.pronounce(Language.EN, Category.SENTENCE, due(1), suspended=excluded)

        item = settle(rig.store.get_item(Language.EN, card.item_id))

        assert not isinstance(item, AppError)
        assert item.pronunciation_excluded is excluded
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p1
    def test_a_suspended_study_card_is_not_an_exclusion(self) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))
        understand = rig.card_ids_of(card.note_id)[0]
        rig.collection.cards[understand].suspended = True

        item = settle(rig.store.get_item(Language.EN, card.item_id))

        assert item.pronunciation_excluded is False

    @pytest.mark.p1
    def test_the_read_follows_the_write(self) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        card = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))

        exclude(rig, Language.EN, card.item_id)
        excluded = settle(rig.store.get_item(Language.EN, card.item_id))
        exclude(rig, Language.EN, card.item_id, excluded=False)
        included = settle(rig.store.get_item(Language.EN, card.item_id))

        assert (excluded.pronunciation_excluded, included.pronunciation_excluded) == (True, False)

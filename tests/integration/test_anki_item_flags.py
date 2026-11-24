"""Flagged Items, through the real guarded and gated Anki adapter.

The flag lives in Anki only (AD-13): an Item is flagged when any of its cards (any ord) carries
any flag colour (1-7). Asked `with_flags=True` (the Items list only), `item_candidates` sends
one more `findNotes` in the same lock hold, the exact note type scope with the fixed `-flag:0`
literal, and marks the notes it returns; without it the reads are unchanged.
`get_item` reads `flags` from the `cardsInfo` it already sends (missing reads as 0).
`clear_flag` sends one `setSpecificValueOfCard` (`flags` to the integer 0) per flagged card
only, guarded and gated, under one lock hold; an Item with no flagged card writes nothing.
"""

import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.query import flagged_notes_query
from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from tests.support.aio import settle
from tests.support.anki_state import (
    collection_replies,
    flag_card,
    managed_collection,
    sent_queries,
    sent_writes,
)
from tests.support.captures import MANIFEST
from tests.support.item_delete import action_bodies
from tests.support.pronunciation import Pronounce, ReviewRig, due

VOCABULARY = MANIFEST.item_note_type(Language.EN, Category.VOCABULARY)


def rig_with(*categories: Category, **kwargs: Any) -> tuple[ReviewRig, list[Pronounce]]:
    rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False), **kwargs)
    items = [rig.pronounce(Language.EN, c, due(i + 1)) for i, c in enumerate(categories)]
    return rig, items


def writes(rig: ReviewRig) -> list[dict[str, Any]]:
    names = set(sent_writes(rig.replay.sent))
    return [body for body in action_bodies(rig.replay) if body.get("action") in names]


def flags(rig: ReviewRig, note_id: int) -> dict[int, int]:
    """`{ord: flags}` of one note's cards."""
    return {c.ord: c.flags for c in rig.collection.cards.values() if c.note == note_id}


def clear_write(card_id: int) -> dict[str, Any]:
    return {
        "action": "setSpecificValueOfCard",
        "version": 6,
        "params": {"card": card_id, "keys": ["flags"], "newValues": [0]},
    }


class TestCandidates:
    @pytest.mark.p0
    @pytest.mark.parametrize("ord", [0, 3], ids=["study-card", "pronounce-card"])
    def test_an_item_with_any_flagged_card_is_flagged(self, ord: int) -> None:
        rig, (flagged, plain) = rig_with(Category.VOCABULARY, Category.VOCABULARY)
        flag_card(rig.collection, flagged.note_id, ord, flags=4)

        items = settle(rig.store.item_candidates(Language.EN, Category.VOCABULARY, with_flags=True))

        assert {i.item_id: i.flagged for i in items} == {
            flagged.item_id: True,
            plain.item_id: False,
        }
        assert rig.lock.holds == 1
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    def test_the_flag_read_is_the_exact_scope_with_the_fixed_literal(self) -> None:
        rig, (item,) = rig_with(Category.VOCABULARY)

        settle(rig.store.item_candidates(Language.EN, Category.VOCABULARY, with_flags=True))

        assert flagged_notes_query(MANIFEST, VOCABULARY) == f'note:"{VOCABULARY}" -flag:0'
        assert sent_queries(rig.replay.sent).count(flagged_notes_query(MANIFEST, VOCABULARY)) == 1
        assert item.item_id not in repr([r.body for r in rig.replay.sent])

    @pytest.mark.p0
    def test_without_with_flags_no_flag_read_is_sent_and_nothing_is_flagged(self) -> None:
        rig, (item,) = rig_with(Category.VOCABULARY)
        flag_card(rig.collection, item.note_id, 0)

        items = settle(rig.store.item_candidates(Language.EN, Category.VOCABULARY))

        assert [i.flagged for i in items] == [False]
        assert sent_queries(rig.replay.sent) == [f'note:"{VOCABULARY}"']

    @pytest.mark.p1
    @pytest.mark.parametrize(
        "reply",
        [{"result": None, "error": None}, {"result": ["1"], "error": None}],
        ids=["not-a-list", "not-ids"],
    )
    def test_a_malformed_flag_read_is_anki_unavailable(self, reply: dict[str, Any]) -> None:
        collection = managed_collection(MANIFEST, reading_rules=False)
        base = collection_replies(collection)["findNotes"]

        def find_notes(body: Any) -> Any:
            return reply if body["params"]["query"].endswith(" -flag:0") else base(body)

        rig = ReviewRig(collection, replies={"findNotes": find_notes})
        rig.pronounce(Language.EN, Category.VOCABULARY, due(1))

        outcome = settle(
            rig.store.item_candidates(Language.EN, Category.VOCABULARY, with_flags=True)
        )

        assert getattr(outcome, "code", outcome) is ErrorCode.ANKI_UNAVAILABLE


class TestDetail:
    @pytest.mark.p0
    @pytest.mark.parametrize("flag", [0, 1, 7])
    def test_get_item_reports_any_flagged_card(self, flag: int) -> None:
        rig, (item,) = rig_with(Category.SENTENCE)
        flag_card(rig.collection, item.note_id, 3, flags=flag)

        got = settle(rig.store.get_item(Language.EN, item.item_id))

        assert not isinstance(got, AppError)
        assert got.flagged is (flag != 0)
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p1
    def test_a_missing_flags_key_reads_as_unflagged(self) -> None:
        collection = managed_collection(MANIFEST, reading_rules=False)
        base = collection_replies(collection)["cardsInfo"]

        def without_flags(body: Any) -> Any:
            reply = base(body)
            for info in reply["result"]:
                info.pop("flags", None)
            return reply

        rig = ReviewRig(collection, replies={"cardsInfo": without_flags})
        item = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))
        flag_card(rig.collection, item.note_id, 0)

        got = settle(rig.store.get_item(Language.EN, item.item_id))

        assert got.flagged is False


class TestClear:
    @pytest.mark.p0
    def test_clear_writes_flag_zero_to_each_flagged_card_only(self) -> None:
        rig, (item, other) = rig_with(Category.VOCABULARY, Category.VOCABULARY)
        first = flag_card(rig.collection, item.note_id, 0, flags=1)
        pronounce = flag_card(rig.collection, item.note_id, 3, flags=6)
        flag_card(rig.collection, other.note_id, 0, flags=2)

        outcome = settle(rig.store.clear_flag(Language.EN, item.item_id))

        assert outcome is None
        assert writes(rig) == [clear_write(first), clear_write(pronounce)]
        assert set(flags(rig, item.note_id).values()) == {0}
        assert flags(rig, other.note_id)[0] == 2
        assert rig.lock.holds == 1
        assert item.item_id not in repr([r.body for r in rig.replay.sent])
        listed = settle(
            rig.store.item_candidates(Language.EN, Category.VOCABULARY, with_flags=True)
        )
        assert {i.item_id: i.flagged for i in listed} == {item.item_id: False, other.item_id: True}

    @pytest.mark.p0
    def test_an_item_with_no_flagged_card_writes_nothing(self) -> None:
        rig, (item,) = rig_with(Category.SENTENCE)

        outcome = settle(rig.store.clear_flag(Language.EN, item.item_id))

        assert outcome is None
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    @pytest.mark.parametrize("where", ["absent", "other-language"])
    def test_an_item_the_language_doesnt_hold_is_not_found(self, where: str) -> None:
        rig = ReviewRig(managed_collection(MANIFEST, reading_rules=False))
        french = rig.pronounce(Language.FR, Category.VOCABULARY, due(1))
        flag_card(rig.collection, french.note_id, 0)
        item_id = french.item_id if where == "other-language" else str(uuid.uuid4())

        outcome = settle(rig.store.clear_flag(Language.EN, item_id))

        assert getattr(outcome, "code", outcome) is ErrorCode.NOT_FOUND
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    def test_the_write_is_gated_while_setup_is_not_ready(self) -> None:
        rig, (item,) = rig_with(Category.VOCABULARY, state="needs_setup")
        flag_card(rig.collection, item.note_id, 0)

        outcome = settle(rig.store.clear_flag(Language.EN, item.item_id))

        assert getattr(outcome, "code", outcome) is ErrorCode.SETUP_REQUIRED
        assert sent_writes(rig.replay.sent) == []
        assert flags(rig, item.note_id)[0] == 1

    @pytest.mark.p1
    @pytest.mark.parametrize(
        "reply",
        [
            {"result": [False], "error": None},
            {"result": [[False, "'0' is not of type 'integer'"]], "error": None},
            {"result": None, "error": None},
            {"result": None, "error": "Card was not found"},
        ],
        ids=["false", "schema-refusal", "null", "error"],
    )
    def test_a_reply_other_than_true_is_anki_unavailable(self, reply: dict[str, Any]) -> None:
        rig = ReviewRig(
            managed_collection(MANIFEST, reading_rules=False),
            replies={"setSpecificValueOfCard": reply},
        )
        item = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))
        flag_card(rig.collection, item.note_id, 0)

        outcome = settle(rig.store.clear_flag(Language.EN, item.item_id))

        assert getattr(outcome, "code", outcome) is ErrorCode.ANKI_UNAVAILABLE


class TestSimulator:
    """The simulated add-on answers a flag write as the installed one does."""

    @pytest.mark.p1
    @pytest.mark.parametrize("value", ["0", False, 0.0, 8, -1])
    def test_a_non_integer_or_out_of_range_flag_is_refused_and_sets_nothing(
        self, value: Any
    ) -> None:
        collection = managed_collection(MANIFEST, reading_rules=False)
        rig = ReviewRig(collection)
        item = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))
        card = flag_card(collection, item.note_id, 0, flags=3)
        answer = collection_replies(collection, writes=True)["setSpecificValueOfCard"]

        reply = answer({"params": {"card": card, "keys": ["flags"], "newValues": [value]}})

        assert reply["result"][0][0] is False
        assert flags(rig, item.note_id)[0] == 3

    @pytest.mark.p1
    def test_find_cards_with_the_flag_literal_answers_only_flagged_cards(self) -> None:
        collection = managed_collection(MANIFEST, reading_rules=False)
        rig = ReviewRig(collection)
        item = rig.pronounce(Language.EN, Category.VOCABULARY, due(1))
        card = flag_card(collection, item.note_id, 3)
        find_cards = collection_replies(collection)["findCards"]

        reply = find_cards({"params": {"query": flagged_notes_query(MANIFEST, VOCABULARY)}})

        assert reply["result"] == [card]

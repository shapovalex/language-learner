"""Story 7.1 Pronunciation review: hand-built AnkiConnect exchanges for the queue and Ratings.

Epic 7 decided (2026-10-25) that 7.1's queue and answer exchanges are hand-built from
AnkiConnect's documented `findCards`, `cardsInfo` and `answerCards`, and that story 7.4 replaces
them with recordings from `language-lab-record-fixtures anki`.

`ReviewRig(collection)` is the real guarded and gated adapter (`wired_delete`) over an in-memory
collection (tests/support/anki_state.py) whose cards also carry a `Schedule`. It answers:

- `findCards` as Anki's search does, at token level (no boolean parsing): every `deck:"X"` term
  matches X and its children (several are OR'd), `note:"T"` and `card:N` / `card:Name` filter,
  `is:due` is a review or day-learning card (queue 2 or 3) due on or before `TODAY` or an
  intraday learning card (queue 1) due on or before `NOW` (epoch seconds), and `is:new` is card
  type 0 **whether suspended or buried or not** (Anki's `is:new` is type-based, so only
  `-is:suspended` drops a suspended new card, and nothing in the query drops a buried one). With
  both `is:due` and `is:new` the result is their union.
- `cardsInfo` in AnkiConnect's documented shape plus `type`, `queue`, `due`, `reps`, `interval`.
- `answerCards` (`{"answers": [{"cardId", "ease"}]}` → one bool each): records the answer in
  `.answers`, bumps `reps` and makes the card a review card due later, so it leaves the queue.

Proposed contracts (scaffold choices; the builder may rename and update these helpers):

- `AnkiStore.pronunciation_queue(language) -> PronunciationQueue` with `.due`, `.new` and
  `.cards`, each a `PronounceCard(card_id, item_id, reps, category, target, audio)`.
- `AnkiStore.answer_card(language, card_id, reps, rating) -> bool`: True when Anki's `reps` had
  moved on, so nothing was answered (AD-20 `alreadyAnswered`).
- `domain.pronunciation.Rating` (`again`/`hard`/`good`/`easy`), mapped to ease 1-4 only in the
  Anki adapter.

New modules are imported inside the coroutines, so a missing one fails inside `settle` and the
test's own assertion reports it.
"""

import re
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI

from language_lab.adapters.anki.manifest import Manifest
from language_lab.domain.catalog import Category, Language
from language_lab.settings import Settings
from tests.support.anki_state import Collection, collection_replies, item_note
from tests.support.audio import managed_name
from tests.support.captures import MANIFEST
from tests.support.hosts import local_url
from tests.support.item_delete import ObservedLock, wired_delete

TODAY = 200  # the collection's day number: a review card with due <= TODAY is due
NOW = 1_792_000_000  # the collection's clock, in epoch seconds: an intraday learning card's due

QUEUE = "/api/pronunciation/{lang}/queue"
RATING = "/api/pronunciation/{lang}/rating"
SESSION = "/api/pronunciation/{lang}/session/{signal}"

_PRONOUNCE_ORD = 3
_TEMPLATE_ORDS = {"understand": 0, "produce": 1, "write": 2, "pronounce": 3}


@dataclass
class Schedule:
    """A card's scheduling state as `cardsInfo` reports it."""

    type: int  # 0 new, 1 learning, 2 review, 3 relearning
    queue: int  # 0 new, 1 intraday learning, 2 review, 3 day learning; -1 suspended (set from
    # the card), -2/-3 buried
    due: int  # a new card's position, a review card's day number, or epoch seconds (queue 1)
    reps: int
    interval: int = 0


def due(days_overdue: int, reps: int = 3) -> Schedule:
    """A review card that has been due for `days_overdue` days (0: due today)."""
    return Schedule(type=2, queue=2, due=TODAY - days_overdue, reps=reps, interval=5)


def not_due(reps: int = 3) -> Schedule:
    return Schedule(type=2, queue=2, due=TODAY + 4, reps=reps, interval=9)


def new(position: int) -> Schedule:
    """A new card at `position` in Anki's new queue (creation order)."""
    return Schedule(type=0, queue=0, due=position, reps=0)


def learning(seconds_ago: int, reps: int = 1) -> Schedule:
    """An intraday learning card (queue 1), due `seconds_ago` seconds before `NOW`."""
    return Schedule(type=1, queue=1, due=NOW - seconds_ago, reps=reps)


def day_learning(days_overdue: int, reps: int = 2) -> Schedule:
    """A day-learning card (queue 3), due `days_overdue` days before `TODAY`."""
    return Schedule(type=1, queue=3, due=TODAY - days_overdue, reps=reps)


def buried(schedule: Schedule) -> Schedule:
    """`schedule` buried by the user (queue -3)."""
    return Schedule(schedule.type, -3, schedule.due, schedule.reps, schedule.interval)


@dataclass(frozen=True)
class Pronounce:
    """An Item note put in the collection, and its Pronounce (ord 3) card."""

    item_id: str
    card_id: int
    note_id: int
    target: str
    audio: str | None


_DECK = re.compile(r'(?<!-)deck:"([^"]*)"')
_NOTE = re.compile(r'(?<!-)note:"([^"]*)"')
_CARD = re.compile(r'(?<!-)card:"?([A-Za-z0-9]+)"?')
_IS_DUE = re.compile(r"(?<![-\w])is:due\b")
_IS_NEW = re.compile(r"(?<![-\w])is:new\b")


class ReviewRig:
    """The real adapter over `collection`, with scheduled cards and an observed lock."""

    def __init__(
        self,
        collection: Collection,
        *,
        state: str = "ready",
        replies: dict[str, Any] | None = None,
        manifest: Manifest = MANIFEST,
    ) -> None:
        self.collection = collection
        self.schedules: dict[int, Schedule] = {}
        self.answers: list[dict[str, int]] = []
        self.lock = ObservedLock()
        self._base = collection_replies(collection, writes=True)
        answers = {
            "findCards": self._find_cards,
            "cardsInfo": self._cards_info,
            "answerCards": self._answer_cards,
        } | (replies or {})
        self.store, self.replay = wired_delete(
            collection, lock=self.lock, replies=answers, state=state, manifest=manifest
        )

    def pronounce(
        self,
        language: Language,
        category: Category,
        schedule: Schedule,
        *,
        target: str | None = None,
        audio: bool = False,
        suspended: bool = False,
        manifest: Manifest = MANIFEST,
        study: Schedule | None = None,
    ) -> Pronounce:
        """Put an Item of `language` and `category` in the collection as Save leaves it, its
        Pronounce card scheduled by `schedule` (and suspended when asked). Its Study cards are
        due (`study`, by default), so only the deck and ord scope keep them out of the queue.
        """
        item_id = str(uuid.uuid4())
        target = target or f"target {item_id[:8]}"
        name = managed_name(item_id, prefix=manifest.prefix) if audio else None
        note_type = manifest.item_note_type(language, category)
        fields = {"Target": target, "Audio": f"[sound:{name}]" if name else ""}
        note_id = item_note(self.collection, manifest, note_type, item_id, fields)
        card_id = 0
        for cid, card in self.collection.cards.items():
            if card.note != note_id:
                continue
            if card.ord == _PRONOUNCE_ORD:
                card_id = cid
                card.suspended = suspended
                self.schedules[cid] = schedule
            else:
                self.schedules[cid] = study or due(1)
        return Pronounce(item_id, card_id, note_id, target, name)

    def card_ids_of(self, note_id: int) -> dict[int, int]:
        """`{ord: card id}` of one note's cards."""
        return {c.ord: cid for cid, c in self.collection.cards.items() if c.note == note_id}

    def _schedule(self, card_id: int) -> Schedule:
        return self.schedules.get(card_id) or new(card_id)

    def _is_suspended(self, card_id: int) -> bool:
        return self.collection.cards[card_id].suspended

    def _matches(self, card_id: int, query: str) -> bool:
        card = self.collection.cards[card_id]
        decks = _DECK.findall(query)
        if decks and not any(card.deck == d or card.deck.startswith(f"{d}::") for d in decks):
            return False
        note_types = _NOTE.findall(query)
        if note_types and self.collection.notes[card.note].model not in note_types:
            return False
        for term in _CARD.findall(query):
            ord = int(term) - 1 if term.isdigit() else _TEMPLATE_ORDS.get(term.lower(), -1)
            if card.ord != ord:
                return False
        if "-is:suspended" in query and self._is_suspended(card_id):
            return False
        schedule = self._schedule(card_id)
        is_due = not self._is_suspended(card_id) and (
            (schedule.queue in (2, 3) and schedule.due <= TODAY)
            or (schedule.queue == 1 and schedule.due <= NOW)
        )
        is_new = schedule.type == 0  # suspended or not, as Anki's is:new
        wants_due, wants_new = bool(_IS_DUE.search(query)), bool(_IS_NEW.search(query))
        if wants_due and wants_new:
            return is_due or is_new
        if wants_due:
            return is_due
        if wants_new:
            return is_new
        return True

    def _find_cards(self, body: dict[str, Any]) -> dict[str, Any]:
        query = body["params"].get("query", "")
        found = sorted(cid for cid in self.collection.cards if self._matches(cid, query))
        return {"result": found, "error": None}

    def _cards_info(self, body: dict[str, Any]) -> dict[str, Any]:
        reply = self._base["cardsInfo"]
        infos = (reply(body) if callable(reply) else reply)["result"]
        for info in infos:
            card_id = info.get("cardId")
            if card_id is None:
                continue
            schedule = self._schedule(card_id)
            info.update(
                type=schedule.type,
                queue=-1 if self._is_suspended(card_id) else schedule.queue,
                due=schedule.due,
                reps=schedule.reps,
                interval=schedule.interval,
            )
        return {"result": infos, "error": None}

    def _answer_cards(self, body: dict[str, Any]) -> dict[str, Any]:
        results: list[bool] = []
        for answer in body["params"].get("answers", []):
            card_id, ease = answer.get("cardId"), answer.get("ease")
            if card_id not in self.collection.cards:
                results.append(False)
                continue
            self.answers.append({"cardId": card_id, "ease": ease})
            schedule = self._schedule(card_id)
            self.schedules[card_id] = Schedule(
                type=2, queue=2, due=TODAY + ease, reps=schedule.reps + 1, interval=ease
            )
            results.append(True)
        return {"result": results, "error": None}


async def queue_of(store: Any, language: Language) -> Any:
    return await store.pronunciation_queue(language)


async def rate(store: Any, language: Language, card_id: int, reps: int, rating: str) -> Any:
    from language_lab.domain.pronunciation import Rating  # story 7.1 adds it

    return await store.answer_card(language, card_id, reps, Rating(rating))


def card_ids(outcome: Any) -> list[int] | Any:
    """The queue's card ids in order, or the outcome itself when it isn't a queue."""
    cards = getattr(outcome, "cards", None)
    return outcome if cards is None else [card.card_id for card in cards]


def card_id_set(outcome: Any) -> set[int] | Any:
    """The queue's card ids as a set, or the outcome itself when it isn't a queue."""
    ids = card_ids(outcome)
    return set(ids) if isinstance(ids, list) else ids


def counts(outcome: Any) -> tuple[int, int] | Any:
    """The queue's (due, new) counts, or the outcome itself when it isn't a queue."""
    if not hasattr(outcome, "due"):
        return outcome
    return outcome.due, outcome.new


def asgi_client(app: FastAPI, settings: Settings) -> httpx.AsyncClient:
    """An async client in the test's own loop, so a Sync the request starts can be drained.

    Sends an allowed Host and the same-origin Origin (AD-16). The app's lifespan is not run, so
    no startup Sync is counted.
    """
    url = local_url(settings)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=url, headers={"origin": url}
    )

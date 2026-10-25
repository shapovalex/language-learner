"""Story 7.1 Pronunciation screen: a per-page review API double and review locators.

Only API boundaries are stubbed: the real screen reads the queue, plays Reference audio from
/api/media, posts Ratings and sends the session signals. `ReviewApi` answers the proposed
contracts of tests/api/test_pronunciation.py from its own `due` and `new` lists; a successful
Rating removes that Card, so a re-read returns the rest. Armed before navigation; nothing is
shared with the live server's fake store.

Copy comes from EXPERIENCE.md (Queue header, Review states). Selector choices the builder may
change with these helpers: the Reference control is a button named "Play reference audio" or
"Reference"; the chip is any element labelled "N due, M new".
"""

import json
import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.audio import MP3, managed_name
from tests.support.captures_screen import main

RATINGS = ("Again", "Hard", "Good", "Easy")
RATING_FAILED = "Rating not saved — Anki isn't reachable."
EMPTY_TITLE = "Nothing to practice in {language}"
EMPTY_BODY = "No new or due Pronounce Cards right now."
REFERENCE = re.compile(r"^(Play reference audio|Reference)$")
LANGUAGES = {"en": "English", "fr": "French"}


def review_card(
    target: str, *, category: str = "vocabulary", audio: bool = True, reps: int = 0
) -> dict[str, Any]:
    """One queued Card on the wire, with a fresh cardId and ItemId."""
    item_id = str(uuid.uuid4())
    return {
        "cardId": uuid.uuid4().int % 10**13,
        "itemId": item_id,
        "reps": reps,
        "category": category,
        "target": target,
        "audio": managed_name(item_id) if audio else None,
    }


def queue_chip(page: Page, due: int, new: int) -> Locator:
    return page.get_by_label(f"{due} due, {new} new", exact=True)


def target_text(page: Page, text: str) -> Locator:
    return main(page).get_by_text(text, exact=True)


def rating_button(page: Page, name: str) -> Locator:
    return main(page).get_by_role("button", name=name, exact=True)


def reference_button(page: Page) -> Locator:
    return main(page).get_by_role("button", name=REFERENCE)


def rating_alert(page: Page) -> Locator:
    return main(page).get_by_role("alert").filter(has_text=RATING_FAILED)


def is_media(request: Request) -> bool:
    return request.method == "GET" and urlparse(request.url).path.startswith("/api/media/")


def is_session(lang: str, signal: str):
    path = f"/api/pronunciation/{lang}/session/{signal}"
    return lambda request: request.method == "POST" and urlparse(request.url).path == path


QUEUE_FAILED = "Anki isn't reachable. Check that Anki is running."


def _unavailable(route: Route) -> None:
    """503 `anki_unavailable`, as the server's envelope (AD-15)."""
    error = {
        "error": {
            "code": "anki_unavailable",
            "message": QUEUE_FAILED,
            "requestId": str(uuid.uuid4()),
        }
    }
    route.fulfill(status=503, content_type="application/json", body=json.dumps(error))


class ReviewApi:
    """Per-page queue, Rating, session and media double for one Language.

    `rating_error` answers every Rating 503 `anki_unavailable` and changes nothing;
    `queue_error` does the same for queue reads. A Rating of a cardId in `gone` answers 404
    `not_found` and drops that Card, as one suspended or moved in Anki since the read. With
    `hold_queue` a queue read is recorded and left unanswered until `release_queue()`. With
    `hold_start` a session start is recorded and never answered, as a slow pre-session Sync
    would leave it if the endpoint waited. `events` lists what arrived, in order: "queue",
    "rating", "start" or "end". `ratings` holds each Rating's JSON body.
    """

    def __init__(
        self,
        page: Page,
        *,
        lang: str = "en",
        due: list[dict[str, Any]] | None = None,
        new: list[dict[str, Any]] | None = None,
        hold_start: bool = False,
    ) -> None:
        self.page = page
        self.lang = lang
        self.due = list(due or [])
        self.new = list(new or [])
        self.rating_error = False
        self.queue_error = False
        self.gone: set[int] = set()
        self.hold_start = hold_start
        self.hold_queue = False
        self._held: list[Route] = []
        self._held_queue: list[Route] = []
        self.events: list[str] = []
        self.ratings: list[dict[str, Any]] = []
        self.media_requests: list[str] = []
        base = f"**/api/pronunciation/{lang}"
        page.route(f"{base}/queue*", self._queue)
        page.route(f"{base}/rating", self._rating)
        page.route(f"{base}/session/*", self._session)
        page.route("**/api/media/*", self._media)

    @property
    def sessions(self) -> list[str]:
        return [event for event in self.events if event in ("start", "end")]

    def wait_for(self, event: str, timeout_s: float = 10.0) -> None:
        """Return once `event` has arrived; raise `TimeoutError` after `timeout_s`."""
        deadline = time.monotonic() + timeout_s
        while event not in self.events:
            if time.monotonic() > deadline:
                raise TimeoutError(f"no {event} request arrived")
            # A round trip lets Playwright deliver a pending route event; nothing sleeps
            self.page.evaluate("0")

    def release_queue(self) -> None:
        """Answer the held queue reads."""
        self.hold_queue = False
        held, self._held_queue = self._held_queue, []
        for route in held:
            self._answer_queue(route)

    def _queue(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        self.events.append("queue")
        if self.hold_queue:
            self._held_queue.append(route)
            return
        self._answer_queue(route)

    def _answer_queue(self, route: Route) -> None:
        if self.queue_error:
            _unavailable(route)
            return
        body = {"due": len(self.due), "new": len(self.new), "cards": self.due + self.new}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    def _rating(self, route: Route) -> None:
        self.events.append("rating")
        body = route.request.post_data_json
        self.ratings.append(body)
        if self.rating_error:
            _unavailable(route)
            return
        if body.get("cardId") in self.gone:
            for cards in (self.due, self.new):
                cards[:] = [card for card in cards if card["cardId"] != body.get("cardId")]
            error = {"error": {"code": "not_found", "message": "Not found.", "requestId": "r"}}
            route.fulfill(status=404, content_type="application/json", body=json.dumps(error))
            return
        for cards in (self.due, self.new):
            cards[:] = [card for card in cards if card["cardId"] != body.get("cardId")]
        answer = {"alreadyAnswered": False}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(answer))

    def _session(self, route: Route) -> None:
        signal = urlparse(route.request.url).path.rsplit("/", 1)[-1]
        self.events.append(signal)
        if signal == "start" and self.hold_start:
            self._held.append(route)
            return
        route.fulfill(status=204, body="")

    def _media(self, route: Route) -> None:
        self.media_requests.append(urlparse(route.request.url).path)
        route.fulfill(status=200, content_type="audio/mpeg", body=MP3)

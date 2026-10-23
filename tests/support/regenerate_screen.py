"""Story 5.2 regeneration: the proposed wire contract, Preview replies and accessible locators.

`POST /api/drafts/regenerate` takes `{language, category, target}` and answers 200 with the
Category's full generated model as flat ItemContent, without an ItemId (AD-11). The Preview
replies differ from tests/support/items.py's stored values in every field, including the ones
the client must not take (hint, grammar, part of speech), so a test can see which group moved.
"""

import uuid
from typing import Any

from playwright.sync_api import Locator, Page, Route

from tests.support.captures_screen import main
from tests.support.duplicates import on_wire, sentence

REGENERATE_API = "/api/drafts/regenerate"

KEEP_CURRENT = "Keep current"
USE_PREVIEW = "Use preview"
CURRENT = "Current"
PREVIEW_NOT_SAVED = "Preview · not saved"

PREVIEW_VOCABULARY: dict[str, Any] = {
    "category": "vocabulary",
    "target": "jump to conclusions",
    "russian": "делать скоропалительные выводы",
    "russianAlternatives": ["судить сгоряча"],
    "hint": "regenerated hint the client must not take",
    "partOfSpeech": "idiom",
    "grammar": "regenerated grammar the client must not take",
    "example": "She tends to jump to conclusions about people she's just met.",
    "exampleRussian": "Она склонна делать поспешные выводы о людях, с которыми только что "
    "познакомилась.",
    "mnemonic": "",
}

PREVIEW_SENTENCE: dict[str, Any] = {
    "category": "sentence",
    "target": "Ne tirons pas de conclusions hâtives.",
    "russian": "Не будем торопиться с выводами.",
    "russianAlternatives": [],
    "hint": "regenerated hint the client must not take",
    "note": "« hâtives » s'accorde avec « conclusions ».",
}


def stored_sentence(**changes: Any) -> dict[str, Any]:
    """A stored Sentence row, shaped like `maintain_items_screen.stored_item`."""
    return {**on_wire(str(uuid.uuid4()), sentence(**changes)), "hasAudio": False}


def regenerate_button(page: Page, name: str) -> Locator:
    """A Regenerate button: "Regenerate Russian meaning", "Regenerate example" or "... Note"."""
    return main(page).get_by_role("button", name=name, exact=True)


def compare_pair(page: Page, group: str) -> Locator:
    """The compare pair of `group` ("Russian meaning", "Example", "Note"): "<group> · compare"."""
    return main(page).get_by_role("group", name=f"{group} · compare", exact=True)


def pair_button(pair: Locator, name: str) -> Locator:
    return pair.get_by_role("button", name=name, exact=True)


def unsaved_chip(page: Page, count: int) -> Locator:
    return main(page).get_by_text(f"{count} unsaved {'change' if count == 1 else 'changes'}")


class RegenerateApi:
    """Per-test double of the regeneration route: records each JSON body, then answers `reply`
    or, while `error` is set, a 502 AD-15 envelope with that code. It never touches Items.
    """

    def __init__(self, page: Page, reply: dict[str, Any], *, error: str | None = None) -> None:
        self.reply = reply
        self.error = error
        self.requests: list[dict[str, Any]] = []
        page.route(f"**{REGENERATE_API}", self._handle)

    def _handle(self, route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        self.requests.append(route.request.post_data_json)
        if self.error is not None:
            route.fulfill(
                status=502,
                json={
                    "error": {
                        "code": self.error,
                        "message": "The model is unavailable.",
                        "requestId": "atdd-regenerate",
                    }
                },
            )
            return
        route.fulfill(json=self.reply)

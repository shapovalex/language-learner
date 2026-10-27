"""The Example sentences tool on the Captures screen: the proposed wire contract, a reply and
locators, shared by tests/e2e/test_example_sentences.py.

`POST /api/helpers/examples` takes `{language, target, context}` and answers 200 with
`{levels: [{level, sentences: [{sentence, russian}×5]}]}` for A1, A2, B1, B2, C1 and C2 in that
order. "Example sentences" sits in the compose card beside Save Capture and Make an Item and
opens a region named "Example sentences" at /captures/examples: a Language picker, an optional
context field, Generate, and one group per level (named by the level) with a list item per
sentence, each with its own "Make an Item". The `ExamplesApi` double answers the route per
test, so the reply never depends on the live server's FakeLlm.
"""

import re
from typing import Any

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.captures_screen import main

EXAMPLES_API = "/api/helpers/examples"
EXAMPLES_PATH = "/captures/examples"

EXAMPLE_SENTENCES = "Example sentences"
GENERATE = "Generate"
MAKE_AN_ITEM = "Make an Item"

LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
SENTENCES_PER_LEVEL = 5
_LEVEL_NAMES = re.compile(rf"^({'|'.join(LEVELS)})$")

PHRASE = "jump to conclusions"
CONTEXT = "Said in a code review about a hasty bug report."


def example(level: str, n: int) -> dict[str, str]:
    """The `n`th (1-based) sentence of `level`, distinct across the whole reply."""
    return {
        "sentence": f"{level} example {n}: don't jump to conclusions.",
        "russian": f"{level} пример {n}: не делай поспешных выводов.",
    }


EXAMPLES_REPLY: dict[str, Any] = {
    "levels": [
        {"level": level, "sentences": [example(level, n) for n in range(1, 6)]} for level in LEVELS
    ]
}


def examples_button(page: Page) -> Locator:
    """The compose card's "Example sentences" button."""
    return main(page).get_by_role("button", name=EXAMPLE_SENTENCES, exact=True)


def examples_pane(page: Page) -> Locator:
    return main(page).get_by_role("region", name=EXAMPLE_SENTENCES, exact=True)


def examples_language(page: Page, name: str) -> Locator:
    """A Language button in the examples pane (a picker with `aria-pressed`)."""
    return examples_pane(page).get_by_role("button", name=name, exact=True)


def examples_context(page: Page) -> Locator:
    """The optional context field, by the start of its label."""
    return examples_pane(page).get_by_role("textbox", name="Context", exact=False)


def generate_button(page: Page) -> Locator:
    return examples_pane(page).get_by_role("button", name=GENERATE, exact=True)


def level_group(page: Page, level: str) -> Locator:
    return examples_pane(page).get_by_role("group", name=level, exact=True)


def level_groups(page: Page) -> Locator:
    """Every level group in the pane, in page order."""
    return examples_pane(page).get_by_role("group", name=_LEVEL_NAMES)


def sentence_items(page: Page, level: str) -> Locator:
    return level_group(page, level).get_by_role("listitem")


def sentence_item(page: Page, sentence: str) -> Locator:
    return examples_pane(page).get_by_role("listitem").filter(has_text=sentence)


def is_examples(request: Request) -> bool:
    return request.method == "POST" and request.url.endswith(EXAMPLES_API)


class ExamplesApi:
    """Per-test double of the examples route: records each JSON body, then answers `reply` or,
    while `error` is set, a 502 AD-15 envelope with that code.
    """

    def __init__(
        self, page: Page, reply: dict[str, Any] = EXAMPLES_REPLY, *, error: str | None = None
    ) -> None:
        self.reply = reply
        self.error = error
        self.requests: list[dict[str, Any]] = []
        page.route(f"**{EXAMPLES_API}", self._handle)

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
                        "requestId": "atdd-examples",
                    }
                },
            )
            return
        route.fulfill(json=self.reply)

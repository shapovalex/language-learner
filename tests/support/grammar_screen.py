"""Check grammar in the shared Draft and Item editor: the proposed wire contract, replies and
locators, shared by tests/e2e/test_grammar_check.py.

`POST /api/helpers/grammar` takes `{language, category, target}` and answers 200 with
`{correct, corrected, explanation}`; `corrected` is null when the Target is correct and the
explanation is in Russian. "Check grammar" sits under the Target field of the Draft editor (a
form named "Draft"), and "Use correction" replaces the Target and the Draft's title. The
`GrammarApi` double answers the route per test, so the reply never depends on the live
server's FakeLlm.
"""

from typing import Any

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.captures_screen import main
from tests.support.items_screen import editor

GRAMMAR_API = "/api/helpers/grammar"

CHECK_GRAMMAR = "Check grammar"
USE_CORRECTION = "Use correction"

WRONG_TARGET = "He go to school."
CORRECTED_TARGET = "He goes to school."
EXPLANATION = "После «he» глагол в Present Simple получает окончание -s: «goes»."

INCORRECT_REPLY: dict[str, Any] = {
    "correct": False,
    "corrected": CORRECTED_TARGET,
    "explanation": EXPLANATION,
}


def check_grammar(page: Page) -> Locator:
    return editor(page).get_by_role("button", name=CHECK_GRAMMAR, exact=True)


def use_correction(page: Page) -> Locator:
    return editor(page).get_by_role("button", name=USE_CORRECTION, exact=True)


def draft_title(page: Page, target: str) -> Locator:
    """The Draft's header title: its Target, as an h1."""
    return main(page).get_by_role("heading", level=1, name=target, exact=True)


def is_grammar_check(request: Request) -> bool:
    return request.method == "POST" and request.url.endswith(GRAMMAR_API)


class GrammarApi:
    """Per-test double of the grammar route: records each JSON body, then answers `reply` or,
    while `error` is set, a 502 AD-15 envelope with that code.
    """

    def __init__(
        self, page: Page, reply: dict[str, Any] = INCORRECT_REPLY, *, error: str | None = None
    ) -> None:
        self.reply = reply
        self.error = error
        self.requests: list[dict[str, Any]] = []
        page.route(f"**{GRAMMAR_API}", self._handle)

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
                        "requestId": "atdd-grammar",
                    }
                },
            )
            return
        route.fulfill(json=self.reply)

"""Capture and translate on the Captures screen: the wire contract, a reply and locators,
shared by tests/e2e/test_capture_and_translate.py.

`POST /api/helpers/translate` takes `{language, target}` and answers 200 `{russian}`. "Capture
and translate" sits in the compose card beside Save Capture; the translation shows in the card
as "original → Russian". The Language picker (English | French, `aria-pressed` buttons) sits
beside the "Captures" heading and is remembered in localStorage under `CAPTURE_LANGUAGE_KEY`.
The `TranslateApi` double answers the route per test, so the reply never depends on the live
server's FakeLlm.
"""

from typing import Any

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.captures_screen import main

TRANSLATE_API = "/api/helpers/translate"
CAPTURE_LANGUAGE_KEY = "languagelab.captureLanguage"

CAPTURE_AND_TRANSLATE = "Capture and translate"
NOT_TRANSLATED = "Couldn't translate"
TRANSLATING = "Translating…"

PHRASE = "jump to conclusions"
RUSSIAN = "делать поспешные выводы"


def translate_button(page: Page) -> Locator:
    return main(page).get_by_role("button", name=CAPTURE_AND_TRANSLATE, exact=True)


def language_choice(page: Page, name: str) -> Locator:
    """A Language button of the picker beside the "Captures" heading."""
    return main(page).locator(".captures-header").get_by_role("button", name=name, exact=True)


def compose_card(page: Page) -> Locator:
    return main(page).locator(".compose-card")


def translation(page: Page) -> Locator:
    """The shown translation in the compose card."""
    return compose_card(page).locator(".compose-translation")


def translation_alert(page: Page) -> Locator:
    return compose_card(page).get_by_role("alert").filter(has_text=NOT_TRANSLATED)


def is_translate(request: Request) -> bool:
    return request.method == "POST" and request.url.endswith(TRANSLATE_API)


class TranslateApi:
    """Per-test double of the translate route: records each JSON body, then answers
    `{russian}` or, while `error` is set, a 502 AD-15 envelope with that code.
    """

    def __init__(self, page: Page, russian: str = RUSSIAN, *, error: str | None = None) -> None:
        self.russian = russian
        self.error = error
        self.requests: list[dict[str, Any]] = []
        page.route(f"**{TRANSLATE_API}", self._handle)

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
                        "requestId": "capture-and-translate",
                    }
                },
            )
            return
        route.fulfill(json={"russian": self.russian})

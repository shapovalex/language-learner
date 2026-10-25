"""7.2 browser boundary doubles; no application-state injection.

The API shape and accessible labels are proposed scaffold contracts. The real screen owns
recording, state changes, rendering and cleanup. This helper only supplies a microphone and
answers HTTP. The probe records scalar lifecycle counts, never a reference to a screen Blob
or Assessment, so it cannot itself retain the objects the screen should release.
"""

import base64
import copy
import json
import time
from collections.abc import Callable
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.captures_screen import main
from tests.support.pronunciation_screen import ReviewApi, review_card

LISTENING = "Listening… tap to stop"
CHECKING = "Checking…"
MIC_TITLE = "LanguageLab can't hear you"
MIC_BODY = "Allow microphone access for this site in Safari, then reload the page."
NOTHING_TITLE = "Couldn't hear that Attempt"
NOTHING_BODY = "Record again closer to the microphone."
FAILED_TITLE = "Couldn't assess that Attempt"
FAILED_BODY = "This Card isn't answered yet. Record again, or leave and come back later."
SAMPLES = Path(__file__).resolve().parents[1] / "fixtures/azure-assessment"


def assessment(locale: str = "en-US", *, overall: int = 79) -> dict[str, Any]:
    """Hand-built feedback for visual states, distinct from the real adapter fixtures."""
    common = {
        "locale": locale,
        "overall": overall,
        "accuracy": 81,
        "fluency": 86,
        "completeness": 100,
    }
    if locale == "fr-CA":
        return {
            **common,
            "prosody": None,
            "words": [
                {
                    "text": "bonjour",
                    "score": 54,
                    "errorType": "Mispronunciation",
                    "phonemes": [],
                    "positions": {"start": 95, "middle": 70, "end": 20},
                }
            ],
        }
    return {
        **common,
        "prosody": 72,
        "words": [
            {
                "text": "thought",
                "score": 54,
                "errorType": "Mispronunciation",
                "phonemes": [{"symbol": "θ", "score": 40}, {"symbol": "ɔ", "score": 95}],
                "positions": None,
            },
            {
                "text": "again",
                "score": 70,
                "errorType": "None",
                "phonemes": [{"symbol": "ə", "score": 70}],
                "positions": None,
            },
        ],
    }


def record_button(page: Page, name: str = "Record") -> Locator:
    return main(page).get_by_role("button", name=name, exact=True)


def score_ring(page: Page) -> Locator:
    return main(page).get_by_label("Overall score", exact=True)


def word_feedback(page: Page) -> Locator:
    return main(page).get_by_role("region", name="Word feedback", exact=True)


def level_meter(page: Page) -> Locator:
    return main(page).get_by_role("meter", name="Microphone level", exact=True)


def install_microphone(page: Page, *, denied: bool = False, mp4: bool = False) -> bytes:
    """A real stream plus deterministic MediaRecorder events carrying native probe bytes."""
    name = "en-weather.mp4-aac.mp4" if mp4 else "en-weather.webm-opus.webm"
    data = (SAMPLES / name).read_bytes()
    script = Path(__file__).with_name("fake_microphone.js").read_text()
    replacements = {
        "__PAYLOAD__": json.dumps(base64.b64encode(data).decode()),
        "__MIME__": json.dumps("audio/mp4" if mp4 else "audio/webm;codecs=opus"),
        "__DENIED__": json.dumps(denied),
    }
    for marker, value in replacements.items():
        script = script.replace(marker, value)
    page.add_init_script(script=script)
    return data


def mic_state(page: Page) -> dict[str, Any]:
    return page.evaluate("JSON.parse(JSON.stringify(window.__attemptMic))")


def is_attempt(request: Request) -> bool:
    return request.method == "POST" and urlparse(request.url).path.endswith("/attempt")


def multipart(request: Request) -> dict[str, Any]:
    headers = f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode()
    message = BytesParser(policy=default).parsebytes(headers + (request.post_data_buffer or b""))
    return {
        part.get_param("name", header="content-disposition"): {
            "filename": part.get_filename(),
            "content_type": part.get_content_type(),
            "data": part.get_payload(decode=True),
        }
        for part in message.iter_parts()
    }


class AttemptApi:
    """Compose the existing review double with an independently controllable Attempt reply."""

    def __init__(self, page: Page, *, lang: str = "en", cards=None) -> None:
        self.page = page
        self.lang = lang
        target = "bonjour" if lang == "fr" else "thought again"
        self.cards = cards or [review_card(target, category="sentence")]
        self.review = ReviewApi(page, lang=lang, due=self.cards)
        locale = "fr-CA" if lang == "fr" else "en-US"
        self.result = {"assessment": assessment(locale), "nothingHeard": False}
        self.failed = False
        self.hold = False
        self.attempts: list[dict[str, Any]] = []
        self._form_data: list[dict[str, Any]] = []
        self._held: list[Route] = []
        # WebKit interception omits binary file bytes (Playwright issue #14624).
        # Observe unchanged FormData, as the existing audio screen helpers do.
        page.expose_binding(
            "observeAttemptFormData", lambda source, body: self._form_data.append(body)
        )
        page.add_init_script("""(() => {
          const originalFetch = window.fetch.bind(window);
          window.fetch = async (url, options) => {
            const body = options?.body;
            if (body instanceof FormData && body.has('recording')) {
              const file = body.get('recording');
              await window.observeAttemptFormData({
                itemId: body.get('itemId'),
                recording: Array.from(new Uint8Array(await file.arrayBuffer())),
              });
            }
            return originalFetch(url, options);
          };
        })();""")
        page.route(f"**/api/pronunciation/{lang}/attempt", self._attempt)

    def _attempt(self, route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        parts = multipart(route.request)
        observed = self._form_data.pop(0)
        assert parts["itemId"]["data"].decode() == observed["itemId"]
        data = bytes(observed["recording"])
        if parts["recording"]["data"]:
            assert parts["recording"]["data"] == data
        parts["recording"]["data"] = data
        self.attempts.append(parts)
        if self.hold:
            self._held.append(route)
            return
        self._answer(route)

    def _answer(self, route: Route) -> None:
        if self.failed:
            body = {
                "error": {
                    "code": "assessment_failed",
                    "message": "Pronunciation assessment failed.",
                    "requestId": "test-attempt",
                }
            }
            route.fulfill(status=503, content_type="application/json", body=json.dumps(body))
        else:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(copy.deepcopy(self.result)),
            )

    def release(self) -> None:
        self.hold = False
        held, self._held = self._held, []
        for route in held:
            self._answer(route)

    def wait_for_attempts(self, count: int) -> None:
        deadline = time.monotonic() + 10
        while len(self.attempts) < count:
            if time.monotonic() > deadline:
                raise TimeoutError(f"only {len(self.attempts)} Attempt requests; wanted {count}")
            self.page.evaluate("0")


def finish_attempt(page: Page, *, retry: bool = False) -> None:
    """User interactions only; assertions remain in the calling test."""
    record_button(page, "Try again" if retry else "Record").click()
    with page.expect_response(lambda response: is_attempt(response.request)):
        record_button(page, LISTENING).click()


def observe_journey(action: Callable[[], None]) -> Exception | None:
    """Return a sync journey's failure to its outer criterion assertion; never retry it.

    Like settle() for async API operations, this makes missing controls, navigation errors
    and inner exact UI assertions observable from the primary test assertion. Assertions
    remain in the test body. None means the entire journey completed.
    """
    try:
        action()
    except Exception as error:  # noqa: BLE001 -- returned and asserted, never swallowed
        return error
    return None

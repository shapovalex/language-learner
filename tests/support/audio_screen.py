"""Story 6.1 browser audio contracts, provider doubles and Draft setup.

Since 2026-10-25 a new Draft makes its Reference audio automatically: one Preview once its
Voice list loads, accepted at once. `DraftAudioApi.open` and `.generate` wait for that clip
unless told not to (`auto=False`), so later explicit Previews never race it.

The proposed new region is named "Reference audio" (its visible heading can append
"· optional"). EXPERIENCE.md fixes Voice, Keep current, Use preview, Play audio preview,
and both error texts. "Preview" is the explicit synthesis action. These accessible names,
the voices response fields and the stale-Draft warning are scaffold choices for the builder.

Only API boundaries are stubbed: the real Draft UI creates/revokes Blob URLs, keeps the
candidate in memory and builds multipart uploads. MP3s are valid locally encoded silent
clips, not Azure recordings. Inspecting a native audio element uses its tag because HTML
exposes no implicit audio role; no style or layout selector is used.
"""

import re
import uuid
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import HTTP
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, Page, Request, Route, ViewportSize, expect

from tests.support.audio import MP3, PREVIEW_API, VOICES_API
from tests.support.captures_screen import API, CAPTURES_PATH, capture
from tests.support.drafts import drafted
from tests.support.items_screen import (
    GENERATE_API,
    choose,
    editor,
    field,
    generate_draft,
    is_blank_draft,
    is_generate,
    item_part,
    stub_duplicates,
    write_it_myself,
)
from tests.support.network import stub_api_json
from tests.support.regenerate_screen import USE_PREVIEW

AUDIO_REGION = "Reference audio"
VOICE_ERROR = "Couldn't load voices"
TTS_ERROR = "Couldn't make the audio. Current audio is unchanged."
STALE_AUDIO = "Audio no longer matches the text."
AUTO_ERROR = "Couldn't make the audio. The Draft will save without audio."
MAKING_AUDIO = "Making audio…"

EN_FIRST = "en-US-AndrewNeural"
EN_SECOND = "en-US-AvaNeural"
FR_FIRST = "fr-CA-SylvieNeural"
FR_SECOND = "fr-CA-JeanNeural"
LOCALE_KEYS = {"en-US": "languagelab.voice.en-US", "fr-CA": "languagelab.voice.fr-CA"}

# A synthetic two-locale catalog: it controls browser behavior, never claims to be live Azure.
CATALOG = {
    "en-US": [
        {"name": EN_FIRST, "locale": "en-US", "displayName": "Andrew"},
        {"name": EN_SECOND, "locale": "en-US", "displayName": "Ava"},
    ],
    "fr-CA": [
        {"name": FR_FIRST, "locale": "fr-CA", "displayName": "Sylvie"},
        {"name": FR_SECOND, "locale": "fr-CA", "displayName": "Jean"},
    ],
}


def audio_card(page: Page) -> Locator:
    return editor(page).get_by_role("region", name=re.compile(r"^Reference audio\b"))


def voice(page: Page) -> Locator:
    return audio_card(page).get_by_role("combobox", name="Voice", exact=True)


def preview_button(page: Page) -> Locator:
    return audio_card(page).get_by_role("button", name="Preview", exact=True)


def audio_button(page: Page, name: str) -> Locator:
    return audio_card(page).get_by_role("button", name=name, exact=True)


def voice_alert(page: Page) -> Locator:
    return audio_card(page).get_by_role("alert").filter(has_text=VOICE_ERROR)


def tts_alert(page: Page) -> Locator:
    return audio_card(page).get_by_role("alert").filter(has_text=TTS_ERROR)


def auto_alert(page: Page) -> Locator:
    return audio_card(page).get_by_role("alert").filter(has_text=AUTO_ERROR)


def waiting_save(page: Page) -> Locator:
    """Save to Anki while it waits for the automatic audio: the form's submit button."""
    making = editor(page).get_by_role("button", name=MAKING_AUDIO, exact=True)
    return making.and_(editor(page).locator("button[type=submit]"))


def is_preview(request: Request) -> bool:
    return request.method == "POST" and urlparse(request.url).path == PREVIEW_API


def is_voice_list(request: Request) -> bool:
    return request.method == "GET" and urlparse(request.url).path == VOICES_API


def rendered_audio_bytes(page: Page) -> list[bytes]:
    """The clips actually attached to native players in the audio card, in DOM order.

    Fetches only browser-local Blob URLs as a test probe. A missing or non-Blob source is
    represented by an empty byte string, so comparisons fail without inventing a clip.
    """
    arrays = (
        audio_card(page)
        .locator("audio")
        .evaluate_all(
            """async players => Promise.all(players.map(async player => {
          const source = player.currentSrc || player.src;
          if (!source.startsWith('blob:')) return [];
          const response = await fetch(source);
          return Array.from(new Uint8Array(await response.arrayBuffer()));
        }))"""
        )
    )
    return [bytes(value) for value in arrays]


def storage_values(page: Page) -> dict[str, str]:
    return page.evaluate("() => Object.fromEntries(Object.entries(localStorage))")


@dataclass(frozen=True)
class AudioSave:
    item: dict[str, Any]
    audio_file: bytes | None
    content_type: str


def audio_upload(request: Request) -> AudioSave:
    content_type = request.headers["content-type"]
    raw = f"Content-Type: {content_type}\r\n\r\n".encode() + (request.post_data_buffer or b"")
    message = BytesParser(policy=HTTP).parsebytes(raw)
    audio = next(
        (
            part.get_payload(decode=True)
            for part in message.iter_parts()
            if part.get_param("name", header="content-disposition") == "audioFile"
        ),
        None,
    )
    return AudioSave(item_part(request), audio, content_type)


class DraftAudioApi:
    """Per-page Voice, synthesis and multipart Save double, armed before any navigation."""

    def __init__(self, page: Page, text: str = "jump to conclusions") -> None:
        self.page = page
        self.capture = capture(text, "2026-10-24T20:00:00Z")
        self.voices_error = False
        self.preview_error = False
        self.save_error = False
        self.mp3 = MP3
        self.voice_requests: list[str] = []
        self.preview_requests: list[dict[str, Any]] = []
        self.saves: list[AudioSave] = []
        self._form_data: list[dict[str, Any]] = []
        # WebKit's interception protocol omits file bytes (Playwright issue #14624).
        # Observe the unchanged FormData before fetch. A separate un-intercepted app
        # journey proves the HTTP upload and saved playback bytes in both browsers.
        page.expose_binding(
            "observeAudioFormData", lambda source, body: self._form_data.append(body)
        )
        page.add_init_script("""const originalFetch = window.fetch.bind(window);
          window.fetch = async (url, options) => {
            const body = options?.body;
            if (body instanceof FormData && body.has('item')) {
              const file = body.get('audioFile');
              await window.observeAudioFormData({
                item: JSON.parse(body.get('item')),
                audio: file ? Array.from(new Uint8Array(await file.arrayBuffer())) : null,
              });
            }
            return originalFetch(url, options);
          };""")
        stub_api_json(page, API, {"captures": [self.capture]}, method="GET")
        stub_api_json(page, f"{API}/{self.capture['captureId']}", self.capture, method="GET")
        for language in ("en", "fr"):
            stub_duplicates(page, [], language)
        page.route(re.compile(r"/api/audio/voices(?:\?.*)?$"), self._voices)
        page.route(f"**{PREVIEW_API}", self._preview)
        page.route(re.compile(r"/api/items/(?:en|fr)$"), self._save)

    @staticmethod
    def _error(route: Route, code: str, status: int) -> None:
        route.fulfill(
            status=status,
            json={
                "error": {
                    "code": code,
                    "message": "The test provider is unavailable.",
                    "requestId": str(uuid.uuid4()),
                }
            },
        )

    def _voices(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        locale = parse_qs(urlparse(route.request.url).query).get("locale", [""])[0]
        self.voice_requests.append(locale)
        if self.voices_error:
            self._error(route, "tts_failed", 502)
            return
        route.fulfill(json={"voices": CATALOG.get(locale, [])})

    def _preview(self, route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        self.preview_requests.append(route.request.post_data_json)
        if self.preview_error:
            self._error(route, "tts_failed", 502)
            return
        route.fulfill(
            status=200,
            content_type="audio/mpeg",
            headers={"Cache-Control": "no-store"},
            body=self.mp3,
        )

    def _save(self, route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        wire = audio_upload(route.request)
        observed = self._form_data.pop(0)
        assert wire.item == observed["item"]
        data = bytes(observed["audio"]) if observed["audio"] is not None else None
        if wire.audio_file:  # Chromium also supplies the actual intercepted file bytes.
            assert wire.audio_file == data
        upload = AudioSave(wire.item, data, wire.content_type)
        self.saves.append(upload)
        if self.save_error:
            self._error(route, "anki_unavailable", 503)
            return
        route.fulfill(json={"itemId": upload.item["itemId"]})

    def _auto(self, auto: bool) -> AbstractContextManager[Any]:
        if not auto:
            return nullcontext()
        return self.page.expect_response(lambda response: is_preview(response.request))

    def open(
        self,
        language: str,
        viewport: ViewportSize,
        category: str = "Vocabulary",
        *,
        auto: bool = True,
    ) -> str:
        """Use the implemented blank-Draft flow; its response is existing setup, not new API.

        With `auto`, returns once the automatic Preview has answered and the card shows it.
        """
        page = self.page
        page.set_viewport_size(viewport)
        page.goto(f"{CAPTURES_PATH}/{self.capture['captureId']}")
        choose(page, "English" if language == "en" else "French", category)
        with page.expect_response(lambda response: is_blank_draft(response.request)) as drafted:
            with self._auto(auto):
                write_it_myself(page).click()
        if auto:
            expect(preview_button(page)).to_be_visible()
        field(page, "Russian meaning").fill("делать поспешные выводы")
        return drafted.value.json()["itemId"]

    def generate(
        self,
        language: str,
        viewport: ViewportSize,
        category: str = "Vocabulary",
        *,
        auto: bool = True,
    ) -> str:
        """Generate Draft with the generation stubbed; with `auto`, returns once the automatic
        Preview has answered and the card shows it."""
        page = self.page
        item_id = str(uuid.uuid4())
        reply = {"itemId": item_id, **drafted(category.lower(), self.capture["text"])}
        stub_api_json(page, GENERATE_API, reply, status=201, method="POST")
        page.set_viewport_size(viewport)
        page.goto(f"{CAPTURES_PATH}/{self.capture['captureId']}")
        choose(page, "English" if language == "en" else "French", category)
        with page.expect_response(lambda response: is_generate(response.request)):
            with self._auto(auto):
                generate_draft(page).click()
        if auto:
            expect(preview_button(page)).to_be_visible()
        else:
            expect(field(page, "Russian meaning")).to_be_visible()
        return item_id

    def synthesize(self) -> None:
        with self.page.expect_response(lambda response: is_preview(response.request)):
            preview_button(self.page).click()

    def preview_and_accept(self) -> None:
        self.synthesize()
        audio_button(self.page, USE_PREVIEW).click()

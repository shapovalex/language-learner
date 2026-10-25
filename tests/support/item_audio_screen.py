"""Story 6.2 existing-Item audio: per-page API doubles and Item detail audio locators.

The Item detail card reuses 6.1's region name "Reference audio" and its Voice, Keep current,
Use preview, stale and TTS-failure copy. "Regenerate audio" is the explicit synthesis action on
an existing Item (epic Done when 4, FR-23). "Remove audio" is the epic-delegated removal copy; its
pending note is "Audio will be removed when you save." with "Keep audio" to undo.

Only API boundaries are stubbed: the real Item detail screen reads the Item, plays its clip,
keeps Previews in memory and builds the multipart Save. The stored clip is SECOND_MP3 and every
Preview answers MP3, so a player's bytes say which clip it holds. Both are local silent clips.
"""

import re
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.audio import MP3, PREVIEW_API, SECOND_MP3, managed_name
from tests.support.audio_screen import CATALOG, AudioSave, audio_upload
from tests.support.captures_screen import main
from tests.support.items_screen import item_api, item_detail_path, stub_duplicates
from tests.support.maintain_items_screen import detail_wire

REGENERATE_AUDIO = "Regenerate audio"
REMOVE_AUDIO = "Remove audio"


def item_audio_card(page: Page) -> Locator:
    return main(page).get_by_role("region", name=re.compile(r"^Reference audio\b"))


def item_voice(page: Page) -> Locator:
    return item_audio_card(page).get_by_role("combobox", name="Voice", exact=True)


def card_button(page: Page, name: str) -> Locator:
    return item_audio_card(page).get_by_role("button", name=name, exact=True)


def card_alert(page: Page, text: str) -> Locator:
    return item_audio_card(page).get_by_role("alert").filter(has_text=text)


def player_bytes(page: Page) -> list[bytes]:
    """The clips attached to native players in the Item's audio card, in DOM order.

    Fetches each player's source as a test probe: a browser-local Blob or a same-origin
    /api/media URL (answered by the double). A missing source is an empty byte string, so a
    comparison fails without inventing a clip. HTML gives audio no implicit role: its tag is used.
    """
    arrays = (
        item_audio_card(page)
        .locator("audio")
        .evaluate_all(
            """async players => Promise.all(players.map(async player => {
          const source = player.currentSrc || player.src;
          if (!source) return [];
          const response = await fetch(source);
          if (!response.ok) return [];
          return Array.from(new Uint8Array(await response.arrayBuffer()));
        }))"""
        )
    )
    return [bytes(value) for value in arrays]


def record_object_urls(page: Page) -> None:
    """Record every Blob URL the page creates and revokes, in window.__objectUrls."""
    page.add_init_script("""window.__objectUrls = {created: [], revoked: []};
      const create = URL.createObjectURL.bind(URL);
      const revoke = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = (value) => {
        const url = create(value);
        window.__objectUrls.created.push(url);
        return url;
      };
      URL.revokeObjectURL = (url) => {
        window.__objectUrls.revoked.push(url);
        revoke(url);
      };""")


def object_urls(page: Page) -> dict[str, list[str]]:
    return page.evaluate("window.__objectUrls")


def is_media(request: Request) -> bool:
    return request.method == "GET" and urlparse(request.url).path.startswith("/api/media/")


class ItemAudioApi:
    """Per-page Item read, media, Voice, Preview and multipart Save double.

    The read answers the stored wire plus `audio` (the managed name, or None). A successful
    Save adopts exactly the browser's payload; `save_error` answers 503 and changes nothing.
    Armed before navigation; nothing is shared with the live server's fake store.
    """

    def __init__(
        self, page: Page, row: dict[str, Any], *, lang: str = "en", has_audio: bool = True
    ) -> None:
        self.page = page
        self.lang = lang
        self.item_id = row["itemId"]
        self.current = detail_wire(row)
        self.audio_name = managed_name(self.item_id, SECOND_MP3) if has_audio else None
        self.media = {self.audio_name: SECOND_MP3} if self.audio_name else {}
        self.preview_error = False
        self.save_error = False
        self.voices_error = False
        self.media_requests: list[str] = []
        self.voice_requests: list[str] = []
        self.preview_requests: list[dict[str, Any]] = []
        self.saves: list[AudioSave] = []
        self._form_data: list[dict[str, Any]] = []
        # WebKit's interception omits file bytes (Playwright issue #14624): observe FormData
        # before fetch, as tests/support/audio_screen.py's DraftAudioApi does.
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
        stub_duplicates(page, [], lang)
        page.route(f"**{item_api(lang, self.item_id)}", self._read)
        page.route(re.compile(r"/api/media/[^/?]+$"), self._media)
        page.route(re.compile(r"/api/audio/voices(?:\?.*)?$"), self._voices)
        page.route(f"**{PREVIEW_API}", self._preview)
        page.route(re.compile(rf"/api/items/{lang}$"), self._save)

    @staticmethod
    def _error(route: Route, code: str, status: int) -> None:
        route.fulfill(
            status=status,
            json={
                "error": {
                    "code": code,
                    "message": "The test double is unavailable.",
                    "requestId": str(uuid.uuid4()),
                }
            },
        )

    def _read(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        route.fulfill(json={**self.current, "audio": self.audio_name})

    def _media(self, route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        name = urlparse(route.request.url).path.rsplit("/", 1)[-1]
        self.media_requests.append(name)
        data = self.media.get(name)
        if data is None:
            self._error(route, "not_found", 404)
            return
        route.fulfill(status=200, content_type="audio/mpeg", body=data)

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
            body=MP3,
        )

    def _save(self, route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        wire = audio_upload(route.request)
        observed = self._form_data.pop(0) if self._form_data else {"audio": None}
        data = bytes(observed["audio"]) if observed["audio"] is not None else None
        if wire.audio_file:  # Chromium also supplies the intercepted file bytes.
            assert wire.audio_file == data
        upload = AudioSave(wire.item, data, wire.content_type)
        self.saves.append(upload)
        if self.save_error:
            self._error(route, "anki_unavailable", 503)
            return
        self.current = {k: v for k, v in upload.item.items() if k != "audio"}
        if upload.item.get("audio") == "remove":
            self.audio_name = None
        elif upload.item.get("audio") == "replace" and data is not None:
            self.audio_name = managed_name(self.item_id, data)
            self.media[self.audio_name] = data
        route.fulfill(json={"itemId": self.item_id})

    def open(self) -> None:
        self.page.goto(item_detail_path(self.lang, self.item_id))

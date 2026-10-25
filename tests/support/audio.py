"""Story 6.1 audio data and real Anki wiring over documented HTTP reply examples.

The MP3 clips are locally encoded silence, not recordings from Azure. The media
transport extends the existing collection double with bytes; it does not implement
any LanguageLab Save, read, naming, guarding or lock behavior.
"""

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from language_lab.adapters.anki.manifest import Manifest
from language_lab.app import create_app
from language_lab.domain.catalog import Language
from language_lab.domain.items import AudioIntent
from language_lab.settings import Settings
from tests.fakes.llm import FakeLlm
from tests.support.anki_state import Collection, item_note
from tests.support.captures import MANIFEST
from tests.support.hosts import app_client
from tests.support.item_delete import ObservedLock, wired_delete
from tests.support.items import VOCABULARY, content, note_type_of, stored_fields

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "azure"
MP3 = (FIXTURES / "preview.mp3").read_bytes()
SECOND_MP3 = (FIXTURES / "second-preview.mp3").read_bytes()
AZURE_KEY = "test-azure-key-never-send-to-browser"
AZURE_REGION = "eastus"
EN_VOICE = "en-US-AndrewNeural"
FR_VOICE = "fr-CA-SylvieNeural"
FR_FR_VOICE = "fr-FR-DeniseNeural"
PREVIEW_API = "/api/audio/preview"
VOICES_API = "/api/audio/voices"


def preview_body(**overrides: Any) -> dict[str, str]:
    return {"language": "en", "voice": EN_VOICE, "target": VOCABULARY["target"], **overrides}


def managed_name(item_id: str, data: bytes = MP3, *, prefix: str = MANIFEST.prefix) -> str:
    """Expected AD-7 name computed independently from the uploaded test bytes; the Prefix
    is lowercased (spike 2.2).
    """
    return f"{prefix.lower()}_{item_id}_{hashlib.sha256(data).hexdigest()[:12]}.mp3"


def replace_parts(item_id: str, data: bytes = MP3, **overrides: Any) -> dict[str, Any]:
    payload = {**VOCABULARY, "itemId": item_id, "audio": "replace", **overrides}
    return {
        "item": (None, json.dumps(payload), "application/json"),
        # This untrusted name deliberately disagrees with the expected AD-7 name.
        "audioFile": ("client-chosen-foreign.mp3", data, "audio/mpeg"),
    }


def audio_client(settings: Settings, store: Any, speech: Any = None) -> TestClient:
    """Wire the app with real Anki persistence and a controlled Speech port."""
    return app_client(
        create_app(settings, anki_store=store, llm=FakeLlm(), speech=speech),
        settings,
        raise_server_exceptions=False,
    )


class MediaRig:
    """Real guarded/gated adapter with byte-aware AnkiConnect replies and an observed lock."""

    def __init__(
        self,
        collection: Collection,
        *,
        media: dict[str, bytes] | None = None,
        replies: dict[str, Any] | None = None,
        state: str = "ready",
        manifest: Manifest = MANIFEST,
    ) -> None:
        self.collection = collection
        self.media = dict(media or {})
        collection.media.update(self.media)
        self.lock = ObservedLock()

        def store_media(body: dict[str, Any]) -> dict[str, Any]:
            """Like real Anki (spike 2.2, `anki/storeMediaFile.json`): stored and answered
            under the lowercased name.
            """
            params = body["params"]
            name = params["filename"].lower()
            self.media[name] = base64.b64decode(params["data"], validate=True)
            collection.media.add(name)
            return {"result": name, "error": None}

        def retrieve_media(body: dict[str, Any]) -> dict[str, Any]:
            data = self.media.get(body["params"]["filename"])
            value = False if data is None else base64.b64encode(data).decode("ascii")
            return {"result": value, "error": None}

        def delete_media(body: dict[str, Any]) -> dict[str, Any]:
            name = body["params"]["filename"]
            self.media.pop(name, None)
            collection.media.discard(name)
            return {"result": None, "error": None}

        answers = {
            "storeMediaFile": store_media,
            "retrieveMediaFile": retrieve_media,
            "deleteMediaFile": delete_media,
        } | (replies or {})
        self.store, self.replay = wired_delete(
            collection, lock=self.lock, replies=answers, state=state, manifest=manifest
        )


async def replace_audio(store: Any, item_id: str, data: bytes = MP3) -> None:
    """Future bytes argument resolves inside settle, so RED is an assertion-level failure."""
    await store.save_item(
        item_id, Language.EN, content(VOCABULARY), AudioIntent.REPLACE, audio_bytes=data
    )


def remove_parts(item_id: str, **overrides: Any) -> dict[str, Any]:
    """Story 6.2 Save with audio=remove: only the `item` part, never an audioFile."""
    payload = {**VOCABULARY, "itemId": item_id, "audio": "remove", **overrides}
    return {"item": (None, json.dumps(payload), "application/json")}


def stored_with_audio(collection: Collection, item_id: str, data: bytes = SECOND_MP3) -> str:
    """Put a stored English Vocabulary Item referencing its managed clip; return the name.

    The clip's bytes go to the MediaRig through its `media=` argument, not here.
    """
    name = managed_name(item_id, data)
    fields = {**stored_fields(VOCABULARY, item_id), "Audio": f"[sound:{name}]"}
    item_note(collection, MANIFEST, note_type_of("en", VOCABULARY), item_id, fields)
    return name


async def remove_audio(store: Any, item_id: str) -> None:
    """The remove intent resolves inside settle, so today's refusal is an outcome to assert."""
    await store.save_item(item_id, Language.EN, content(VOCABULARY), AudioIntent.REMOVE)

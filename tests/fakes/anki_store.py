"""Fake AnkiStore: the port in memory, kept in step with `ports/anki_store.py` (AD-1)."""

import asyncio
import hashlib
import re
from collections.abc import Collection
from datetime import datetime

from language_lab.domain.audio import validate_mp3
from language_lab.domain.captures import Capture
from language_lab.domain.catalog import UUID4, Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import AudioIntent, Item, ItemContent
from language_lab.domain.setup import SetupPreview, SetupState
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome

_MEDIA = re.compile(r"LanguageLab_" + UUID4[1:-1] + r"_[0-9a-f]{12}\.mp3")


class FakeAnkiStore:
    """`available` says whether AnkiConnect answers; `busy` makes every call wait out the lock.

    `setup_preview()` returns `preview` (an empty one by default). `setup_state()` returns its
    `state`, raises as `setup_preview()` does, and counts every call (`state_calls`).

    `setup_apply(plan_hash, repairs)` raises `plan_changed` unless the hash is the preview's
    items plus its offered `repairs` rows whose key is in `repairs` (as the adapter's), then makes
    `verified` (empty by default) the preview and returns it. With `apply_gated=True` each one
    stays in flight until `finish_apply()` ends it, oldest first. Counts every call
    (`apply_calls`) and the ones that returned a verification (`applies`).

    `sync()` returns `outcome`. With `gated=True` each `sync()` stays in flight until
    `finish()` ends it, oldest first. Counts every `sync()` call (`sync_calls`), the ones that
    returned an outcome (`syncs`), and how many run at once (`in_flight`, `max_in_flight`).

    `create_capture()` is create-or-noop by CaptureId over `captures` (AD-20): a known CaptureId
    returns the stored Capture unchanged. It raises `anki_busy` or `anki_unavailable` as the
    other methods do.

    `list_captures()` returns `captures` newest first by `created_at` (ties by CaptureId), as the
    adapter sorts. `get_capture()` returns the stored one or raises `not_found`. Both raise
    `anki_busy` or `anki_unavailable` as the other methods do.

    `delete_capture()` drops the CaptureId from `captures`; one it doesn't hold is no error. It
    raises `anki_busy` or `anki_unavailable` as the other methods do.

    `save_item()` is create-or-update by ItemId over `items`, each held as `(Language,
    ItemContent)` (AD-20). It raises `anki_busy` or `anki_unavailable` as the other methods do.

    `item_candidates()` returns the `items` of one Language and Category, in insertion order (as
    the adapter returns note order). `get_item()` returns the one of that Language or raises
    `not_found`. Both raise `anki_busy` or `anki_unavailable` as the other methods do.

    `delete_item()` removes only the matching Language's Item, tolerates an absent Item, and
    refuses writes when unavailable, busy or Setup is not ready, and removes matching audio.
    """

    def __init__(
        self,
        *,
        available: bool = True,
        busy: bool = False,
        gated: bool = False,
        outcome: SyncOutcome = SyncOutcome.OK,
        preview: SetupPreview | None = None,
        verified: SetupPreview | None = None,
        apply_gated: bool = False,
    ) -> None:
        self.available = available
        self.busy = busy
        self.gated = gated
        self.outcome = outcome
        self.preview = preview if preview is not None else SetupPreview()
        self.state_calls = 0
        self.sync_calls = 0
        self.syncs = 0
        self.in_flight = 0
        self.max_in_flight = 0
        self._gates: list[asyncio.Future[SyncOutcome | ErrorCode]] = []
        self.verified = verified if verified is not None else SetupPreview()
        self.apply_gated = apply_gated
        self.apply_calls = 0
        self.applies = 0
        self._apply_gates: list[asyncio.Future[ErrorCode | None]] = []
        self.captures: dict[str, Capture] = {}
        self.items: dict[str, tuple[Language, ItemContent]] = {}
        self.media: dict[str, bytes] = {}
        self.audio: dict[str, str] = {}

    async def reachable(self) -> bool:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        return self.available

    async def setup_state(self) -> SetupState:
        self.state_calls += 1
        return (await self.setup_preview()).state

    async def setup_preview(self) -> SetupPreview:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return self.preview

    async def setup_apply(self, plan_hash: str, repairs: Collection[str] = ()) -> SetupPreview:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        wanted = set(repairs)
        checked = tuple(r for r in self.preview.repairs if r.key in wanted)
        if plan_hash != _plan_hash((*self.preview.items, *checked)):
            raise AppError(ErrorCode.PLAN_CHANGED)
        self.apply_calls += 1
        if self.apply_gated:
            gate: asyncio.Future[ErrorCode | None] = asyncio.get_running_loop().create_future()
            self._apply_gates.append(gate)
            try:
                end = await gate
            finally:
                if gate in self._apply_gates:
                    self._apply_gates.remove(gate)
            if end is not None:
                raise AppError(end)
        self.preview = self.verified
        self.applies += 1
        return self.verified

    def finish_apply(self, end: ErrorCode | None = None) -> None:
        """End the oldest in-flight gated `setup_apply()`: verify, or raise an `ErrorCode`."""
        gate = self._apply_gates.pop(0)
        gate.set_result(end)

    async def create_capture(self, capture_id: str, text: str, created_at: datetime) -> Capture:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return self.captures.setdefault(capture_id, Capture(capture_id, text, created_at))

    async def list_captures(self) -> list[Capture]:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return sorted(
            self.captures.values(), key=lambda c: (c.created_at, c.capture_id), reverse=True
        )

    async def get_capture(self, capture_id: str) -> Capture:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        capture = self.captures.get(capture_id)
        if capture is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return capture

    async def delete_capture(self, capture_id: str) -> None:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        self.captures.pop(capture_id, None)

    async def save_item(
        self,
        item_id: str,
        language: Language,
        content: ItemContent,
        audio: AudioIntent = AudioIntent.KEEP,
        *,
        audio_bytes: bytes | None = None,
    ) -> None:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        if self.preview.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        if audio is AudioIntent.REPLACE:
            if audio_bytes is None:
                raise AppError(ErrorCode.VALIDATION_FAILED)
            validate_mp3(audio_bytes)
            name = f"LanguageLab_{item_id}_{hashlib.sha256(audio_bytes).hexdigest()[:12]}.mp3"
            self.media[name] = audio_bytes
            old = self.audio.get(item_id)
            self.audio[item_id] = name
            if old and old != name:
                self.media.pop(old, None)
        elif audio is not AudioIntent.KEEP or audio_bytes is not None:
            raise AppError(ErrorCode.VALIDATION_FAILED)
        self.items[item_id] = (language, content)

    async def get_media(self, name: str) -> bytes:
        if not _MEDIA.fullmatch(name):
            raise AppError(ErrorCode.NOT_FOUND)
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        if name not in self.media:
            raise AppError(ErrorCode.NOT_FOUND)
        return self.media[name]

    async def item_candidates(self, language: Language, category: Category) -> list[Item]:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return [
            Item(item_id, content, item_id in self.audio, self.audio.get(item_id))
            for item_id, (stored_language, content) in self.items.items()
            if stored_language is language and content.category is category
        ]

    async def get_item(self, language: Language, item_id: str) -> Item:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        stored = self.items.get(item_id)
        if stored is None or stored[0] is not language:
            raise AppError(ErrorCode.NOT_FOUND)
        return Item(item_id, stored[1], item_id in self.audio, self.audio.get(item_id))

    async def delete_item(self, language: Language, item_id: str) -> None:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        stored = self.items.get(item_id)
        if stored is not None and stored[0] is not language:
            return
        names = [
            name
            for name in self.media
            if name.startswith(f"LanguageLab_{item_id}_") and _MEDIA.fullmatch(name)
        ]
        if (stored is not None or names) and self.preview.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        self.items.pop(item_id, None)
        self.audio.pop(item_id, None)
        for name in names:
            self.media.pop(name, None)

    async def sync(self) -> SyncOutcome:
        self.sync_calls += 1
        if not self.gated:
            if self.busy:
                raise AppError(ErrorCode.ANKI_BUSY)
            if not self.available:
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            self.syncs += 1
            return self.outcome
        gate: asyncio.Future[SyncOutcome | ErrorCode] = asyncio.get_running_loop().create_future()
        self._gates.append(gate)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            end = await gate
        finally:
            self.in_flight -= 1
            if gate in self._gates:
                self._gates.remove(gate)
        if isinstance(end, ErrorCode):
            raise AppError(end)
        self.syncs += 1
        return end

    def finish(self, end: SyncOutcome | ErrorCode = SyncOutcome.OK) -> None:
        """End the oldest in-flight gated `sync()`: return a `SyncOutcome`, raise an `ErrorCode`."""
        gate = self._gates.pop(0)
        gate.set_result(end)

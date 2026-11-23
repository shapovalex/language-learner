"""Fake AnkiStore: the port in memory, kept in step with `ports/anki_store.py` (AD-1)."""

import asyncio
import dataclasses
import re
from collections.abc import Collection
from datetime import datetime

from language_lab.domain.audio import audio_upload, media_name, validate_mp3
from language_lab.domain.captures import Capture
from language_lab.domain.catalog import UUID4, Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import AudioIntent, Item, ItemContent, VocabularyContent
from language_lab.domain.pronunciation import PronounceCard, PronunciationQueue, Rating
from language_lab.domain.setup import SetupPreview, SetupState
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome

_MEDIA = re.compile(
    r"languagelab_"  # AD-7: the Prefix lowercased
    + UUID4[1:-1]
    + r"_[0-9a-f]{12}\.mp3"
)


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
    Reference audio names go in `audio`, example audio names in `example_audio` (emptied for a
    Vocabulary Item saved with a blank Example or ExampleRussian, or another Example and no new
    example bytes), both clips in `media`; a
    clip either still names is kept. `store_example_audio()` is the backfill's write: it
    returns False and writes nothing for an Item gone, changed or already with example audio.

    `item_candidates()` returns the `items` of one Language and Category, in insertion order (as
    the adapter returns note order). `get_item()` returns the one of that Language or raises
    `not_found`. Both raise `anki_busy` or `anki_unavailable` as the other methods do.

    `delete_item()` removes only the matching Language's Item, tolerates an absent Item, and
    refuses writes when unavailable, busy or Setup is not ready, and removes matching audio.

    `pronunciation_queue()` returns the Language's entries of `pronounce`, each `(Language,
    is_due, PronounceCard)`, due first then new, in list order (empty by default, so a live
    server's Pronunciation screen shows its empty state). `answer_card()` raises `not_found` for
    a card id not queued in that Language, returns True (alreadyAnswered) when `reps` differs,
    refuses when Setup is not ready, and otherwise records `(card_id, Rating)` in `answers` and
    drops the Card from the queue. Both raise `anki_busy` or `anki_unavailable` as the other
    methods do.

    `set_pronunciation_excluded()` adds the ItemId to `excluded` or drops it from there, raising
    `not_found` for an Item of no `items` entry in that Language and refusing when Setup is not
    ready, but only when the flag changes; each change is recorded in `exclusions`.
    `pronunciation_queue()` leaves out the excluded Items' cards, `answer_card()` raises
    `not_found` for one, and `get_item()` reports the flag.
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
        self.example_audio: dict[str, str] = {}
        self.pronounce: list[tuple[Language, bool, PronounceCard]] = []
        self.answers: list[tuple[int, Rating]] = []
        self.excluded: set[str] = set()
        self.exclusions: list[tuple[str, bool]] = []

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
        example_audio_bytes: bytes | None = None,
    ) -> None:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        if self.preview.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        data = audio_upload(audio, audio_bytes)
        vocabulary = isinstance(content, VocabularyContent)
        if example_audio_bytes is not None:
            if not vocabulary:
                raise AppError(ErrorCode.VALIDATION_FAILED)
            validate_mp3(example_audio_bytes)
        old = {self.audio.get(item_id), self.example_audio.get(item_id)}
        previous = self.items.get(item_id)
        old_example = getattr(previous[1], "example", None) if previous else None
        if data is not None:
            name = media_name("LanguageLab", item_id, data)
            self.media[name] = data
            self.audio[item_id] = name
        elif audio is AudioIntent.REMOVE:
            self.audio.pop(item_id, None)
        if example_audio_bytes is not None:
            name = media_name("LanguageLab", item_id, example_audio_bytes)
            self.media[name] = example_audio_bytes
            self.example_audio[item_id] = name
        elif vocabulary and (not _has_example(content) or old_example != content.example):
            self.example_audio.pop(item_id, None)
        kept = {self.audio.get(item_id), self.example_audio.get(item_id)}
        for name in old - kept:
            if name:
                self.media.pop(name, None)
        self.items[item_id] = (language, content)

    async def store_example_audio(
        self, language: Language, item_id: str, example: str, audio_bytes: bytes
    ) -> bool:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        validate_mp3(audio_bytes)
        stored = self.items.get(item_id)
        if stored is None or stored[0] is not language or item_id in self.example_audio:
            return False
        content = stored[1]
        if not isinstance(content, VocabularyContent) or not _has_example(content):
            return False
        if content.example != example:
            return False
        if self.preview.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        name = media_name("LanguageLab", item_id, audio_bytes)
        self.media[name] = audio_bytes
        self.example_audio[item_id] = name
        return True

    def _item(self, item_id: str, content: ItemContent, **extra: bool) -> Item:
        example = self.example_audio.get(item_id)
        return Item(
            item_id,
            content,
            item_id in self.audio,
            self.audio.get(item_id),
            has_example_audio=example is not None,
            example_audio=example,
            **extra,
        )

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
            self._item(item_id, content)
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
        return self._item(item_id, stored[1], pronunciation_excluded=item_id in self.excluded)

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
            if name.startswith(f"languagelab_{item_id}_") and _MEDIA.fullmatch(name)
        ]
        if (stored is not None or names) and self.preview.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        self.items.pop(item_id, None)
        self.audio.pop(item_id, None)
        self.example_audio.pop(item_id, None)
        for name in names:
            self.media.pop(name, None)

    async def pronunciation_queue(self, language: Language) -> PronunciationQueue:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        queued = [
            (is_due, card)
            for lang, is_due, card in self.pronounce
            if lang is language and card.item_id not in self.excluded
        ]
        due = [dataclasses.replace(card, is_new=False) for is_due, card in queued if is_due]
        new = [dataclasses.replace(card, is_new=True) for is_due, card in queued if not is_due]
        return PronunciationQueue(len(due), len(new), (*due, *new))

    async def answer_card(
        self, language: Language, card_id: int, reps: int, rating: Rating
    ) -> bool:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        entry = next(
            (e for e in self.pronounce if e[0] is language and e[2].card_id == card_id), None
        )
        # An excluded Item's card is suspended: out of the Pronounce scope, as the adapter's
        if entry is None or entry[2].item_id in self.excluded:
            raise AppError(ErrorCode.NOT_FOUND)
        if entry[2].reps != reps:
            return True
        if self.preview.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        self.answers.append((card_id, rating))
        self.pronounce.remove(entry)
        return False

    async def set_pronunciation_excluded(
        self, language: Language, item_id: str, excluded: bool
    ) -> None:
        if self.busy:
            raise AppError(ErrorCode.ANKI_BUSY)
        if not self.available:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        stored = self.items.get(item_id)
        if stored is None or stored[0] is not language:
            raise AppError(ErrorCode.NOT_FOUND)
        if (item_id in self.excluded) is excluded:
            return
        if self.preview.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        if excluded:
            self.excluded.add(item_id)
        else:
            self.excluded.discard(item_id)
        self.exclusions.append((item_id, excluded))

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


def _has_example(content: ItemContent) -> bool:
    return (
        isinstance(content, VocabularyContent)
        and bool(content.example.strip())
        and bool(content.example_russian.strip())
    )

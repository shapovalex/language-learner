"""`AnkiConnectStore`: the AnkiStore port over AnkiConnect. Each method is one use case, run
entirely under the Anki lock (AD-5).

With a `SetupGate` shared with the client (AD-19), every SetupState the store computes (the
startup `setup_state()`, each preview, each apply's verification) is set in the gate.

`migrations` (adapters/anki/migrations.py) run only inside a confirmed apply whose plan has a
Migrate item, after its Create and Repair items (FR-7, AD-3). The opt-in repairs the user
checked (entry 11) run last, under the same lock hold.

Create Capture (story 3.1) writes through `client.invoke`, so the Prefix guard and the setup gate
both apply to it (AD-4, AD-19).

List Captures and Get Capture (story 3.2) are reads through `client.invoke`, under one lock hold
each, and not gated (AD-19). Their only query is the exact Capture note type scope; the
CaptureId is matched in Python and never sent (AD-4). Anki ids stay here: a `Capture` has none.

Delete Capture (story 3.3) finds the note the same way and deletes it through `client.invoke`,
so the guard and the gate apply; a CaptureId no Capture holds writes nothing and succeeds.

Save Item (story 4.1) finds the note by ItemId the same way, in the exact scope of the Item's note
type, and then either updates its fields or adds it in the AD-6 keep order: the note into its
Pronunciation deck, then cards 0-2 to their Study decks. Every write goes through
`client.invoke`, so the guard and the gate apply. A failed card move leaves the cards in the
Pronunciation deck for Setup to report; a retry finds the note and updates it (AD-20).

The Item reads (story 4.3) are reads through `client.invoke`, under one lock hold each, and not
gated (AD-19). `item_candidates` sends only the exact scope of one Language/Category note type;
`get_item` the scopes of both Categories of the Language, with the ItemId matched in Python
(AD-4). Each note's fields are decoded through the codec, the alternatives split here (AD-10).

Delete Item (story 5.3) resolves both Language/Category scopes under the same lock, deletes
matching notes, then cleans matching managed media, including leftovers when notes are absent.
Every write is guarded and gated; any failure stops the sequence for a later retry.

The Pronunciation queue (story 7.1) is reads only, under one lock hold, not gated: one exact
`findCards` per Category (`pronounce_queue_query`), then `cardsInfo` and `notesInfo` for what
they found. A card Anki answers with a negative `queue` (suspended or buried) is dropped. The
Rating reads the card's `cardsInfo` (its scope and `reps`) and sends `answerCards` only when the
`reps` still match (AD-20), under the same lock hold; the answer is guarded and gated. The card
id is the one Anki id a feature sees (AD-8 amendment, story 7.1); the ease mapping is here only.
"""

import asyncio
import base64
import binascii
import re
from collections.abc import Collection, Iterator
from datetime import UTC, datetime
from typing import Any

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.codec import (
    decode_field,
    encode_field,
    join_alternatives,
    split_alternatives,
)
from language_lab.adapters.anki.guard import is_int, media_pattern
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import PRONOUNCE_ORD, STUDY_ORDS, Manifest
from language_lab.adapters.anki.migrations import Migration, run_migrations
from language_lab.adapters.anki.query import note_query, pronounce_queue_query
from language_lab.adapters.anki.setup_apply import run_plan, run_repairs
from language_lab.adapters.anki.setup_gate import SCHEMA_VERSION_FIELD, SetupGate, read_preview
from language_lab.domain.audio import audio_upload, media_name
from language_lab.domain.captures import Capture
from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import (
    AudioIntent,
    Item,
    ItemContent,
    SentenceContent,
    VocabularyContent,
)
from language_lab.domain.pronunciation import PronounceCard, PronunciationQueue, Rating
from language_lab.domain.setup import PlanAction, SetupPreview, SetupState, checked_repairs
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome

POLL_INTERVAL_S = 1.0
SYNC_BUDGET_S = 120.0  # a Sync with AnkiWeb can take far longer than any other action

# API v1 operation states (spike 2.2, Q7)
_SUCCEEDED = "succeeded"
_FAILED = "failed"
# Decided 2026-10-21: a dialog in Anki or a cancelled Sync ends the Sync at once
_GAVE_UP = frozenset({"waitingForUser", "cancelled"})
_AUTH_REQUIRED_TYPE = "authenticationRequired"

# The Capture note type's fields (manifest.py) and the stored CreatedAt format (AD-9)
_TEXT, _CREATED_AT, _CAPTURE_ID = "Text", "CreatedAt", "CaptureId"
_CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# The Item note types' fields Save writes besides the content (manifest.py)
_AUDIO, _ITEM_ID = "Audio", "ItemId"

# Anki's ease for each Rating (AnkiConnect `answerCards`): the only place the mapping lives
_EASE = {Rating.AGAIN: 1, Rating.HARD: 2, Rating.GOOD: 3, Rating.EASY: 4}
_NEW_TYPE = 0  # `cardsInfo.type` of a new card
_INTRADAY_QUEUE = 1  # a learning card due in epoch seconds, not a day number


def _field(info: dict[str, Any], name: str) -> str:
    """Field `name` of one `notesInfo` entry, decoded; `ANKI_UNAVAILABLE` when malformed."""
    fields = info.get("fields")
    field = fields.get(name) if isinstance(fields, dict) else None
    value = field.get("value") if isinstance(field, dict) else None
    if not isinstance(value, str):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return decode_field(value)


def _stored_capture(capture_id: str, info: dict[str, Any]) -> Capture:
    """The Capture a `notesInfo` entry holds, its fields decoded through the codec."""
    try:
        created_at = datetime.strptime(_field(info, _CREATED_AT).strip(), _CREATED_AT_FORMAT)
    except ValueError:
        raise AppError(ErrorCode.ANKI_UNAVAILABLE) from None
    return Capture(capture_id, _field(info, _TEXT), created_at.replace(tzinfo=UTC))


# The optional note fields of each Category, by ItemContent field name (manifest.py)
_OPTIONAL_FIELDS = {
    Category.VOCABULARY: {
        "hint": "Hint",
        "part_of_speech": "PartOfSpeech",
        "grammar": "Grammar",
        "example": "Example",
        "example_russian": "ExampleRussian",
        "mnemonic": "Mnemonic",
    },
    Category.SENTENCE: {"hint": "Hint", "note": "Note"},
}


def _content_fields(content: ItemContent) -> dict[str, str]:
    """The note fields `content` fills, as domain values (manifest.py names, AD-10)."""
    return {
        "Target": content.target,
        "Russian": content.russian,
        "RussianAlternatives": join_alternatives(content.russian_alternatives),
        **{name: getattr(content, key) for key, name in _OPTIONAL_FIELDS[content.category].items()},
    }


def _optional(info: dict[str, Any], name: str) -> str:
    """Field `name` of one `notesInfo` entry, decoded; `""` when the note lacks it."""
    fields = info.get("fields")
    if isinstance(fields, dict) and name not in fields:
        return ""
    return _field(info, name)


def _stored_item(info: dict[str, Any], category: Category, prefix: str) -> Item:
    """The Item a `notesInfo` entry holds: the inverse of `_content_fields`.

    The content is built without validation: a note edited in Anki (a blank Russian meaning,
    say) still reads back as it is, rather than failing the whole read.
    """
    model = VocabularyContent if category is Category.VOCABULARY else SentenceContent
    content = model.model_construct(
        category=category,
        target=_field(info, "Target"),
        russian=_field(info, "Russian"),
        russian_alternatives=split_alternatives(_optional(info, "RussianAlternatives")),
        **{key: _optional(info, name) for key, name in _OPTIONAL_FIELDS[category].items()},
    )
    has_audio = bool(_optional(info, _AUDIO).strip())
    audio = _audio_name(_optional(info, _AUDIO), prefix)
    return Item(_field(info, _ITEM_ID).strip(), content, has_audio, audio)


def _audio_name(value: str, prefix: str) -> str | None:
    match = re.fullmatch(r"\[sound:([^\]]+)\]", value)
    name = match.group(1) if match else None
    return name if name and media_pattern(prefix).fullmatch(name) else None


def _encoded(fields: dict[str, str]) -> dict[str, str]:
    return {name: encode_field(value) for name, value in fields.items()}


def _capture_model(manifest: Manifest) -> str:
    """The Prefix's Capture note type (manifest.py)."""
    return f"{manifest.prefix} Capture"


def _matching(infos: list[dict[str, Any]], name: str, value: str) -> Iterator[dict[str, Any]]:
    """The `notesInfo` entries whose decoded field `name` is `value`: an id matched in Python,
    never sent to Anki (AD-4).
    """
    return (info for info in infos if _field(info, name).strip() == value)


def _queued_cards(infos: Any, expected: int) -> list[dict[str, Any]]:
    """The `cardsInfo` entries still in the queue: each well formed, a card deleted since
    `findCards` (`{}`) skipped, a suspended or buried one (negative `queue`) dropped;
    `ANKI_UNAVAILABLE` on a malformed reply.
    """
    if not isinstance(infos, list) or len(infos) != expected:
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    queued: list[dict[str, Any]] = []
    for info in infos:
        if info == {}:
            continue
        if not isinstance(info, dict):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        keys = ("cardId", "note", "type", "queue", "due", "reps")
        if not all(is_int(info.get(key)) for key in keys):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        if info["queue"] < 0:
            continue
        queued.append(info)
    return queued


def _notes_by_id(infos: Any, expected: int) -> dict[int, dict[str, Any]]:
    """`notesInfo` entries by note id, a note deleted in between (`{}`) left out;
    `ANKI_UNAVAILABLE` on a malformed reply.
    """
    if not isinstance(infos, list) or len(infos) != expected:
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    by_id: dict[int, dict[str, Any]] = {}
    for info in infos:
        if info == {}:
            continue
        if not isinstance(info, dict) or not is_int(info.get("noteId")):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        by_id[info["noteId"]] = info
    return by_id


def _failure_outcome(poll: dict[str, Any]) -> SyncOutcome:
    """A failed operation's outcome, from its `error.data.type` (spike 2.2, Q3/Q4)."""
    error = poll.get("error")
    data = error.get("data") if isinstance(error, dict) else None
    kind = data.get("type") if isinstance(data, dict) else None
    if kind == _AUTH_REQUIRED_TYPE:
        return SyncOutcome.AUTH_REQUIRED
    return SyncOutcome.ANKIWEB_UNREACHABLE


class AnkiConnectStore:
    def __init__(
        self,
        client: AnkiConnectClient,
        lock: AnkiLock,
        *,
        manifest: Manifest | None = None,
        gate: SetupGate | None = None,
        migrations: tuple[Migration, ...] = (),
        poll_interval_s: float = POLL_INTERVAL_S,
        sync_budget_s: float = SYNC_BUDGET_S,
    ) -> None:
        self._client = client
        self._lock = lock
        self._manifest = manifest
        self._gate = gate
        self._migrations = migrations
        self._poll_interval_s = poll_interval_s
        self._sync_budget_s = sync_budget_s

    async def reachable(self) -> bool:
        async with self._lock.hold():
            try:
                await self._client.invoke("version")
            except AppError as exc:
                if exc.code is ErrorCode.ANKI_UNAVAILABLE:
                    return False
                raise
            return True

    async def setup_state(self) -> SetupState:
        """The SetupState, from reads only under the lock (AD-19), set in the gate. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        return (await self.setup_preview()).state

    async def setup_preview(self) -> SetupPreview:
        """Read the managed state and diff it against the manifest, with reads only, under one
        lock hold (AD-3, AD-5), with its SetupState, which is set in the gate. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            _, preview = await read_preview(self._client.invoke, manifest)
        self._set_gate(preview)
        return preview

    async def setup_apply(self, plan_hash: str, repairs: Collection[str] = ()) -> SetupPreview:
        """Re-diff, refuse a stale `plan_hash` and then a `newer_schema` Anki before any write,
        run the plan's Create and Repair items, then, when it has a Migrate item, the migrations
        and the SchemaVersion rewrite, then each checked opt-in repair, through the client's
        guarded, ungated path, and verify by a fresh diff, all under one lock hold (AD-3, AD-4,
        AD-5, AD-19). The hash covers the items plus the offered repair rows whose key is in
        `repairs`. Each fresh SetupState is set in the gate. Raises
        `AppError(PLAN_CHANGED | SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            state, before = await read_preview(self._client.invoke, manifest)
            self._set_gate(before)
            checked = checked_repairs(before, repairs)
            if _plan_hash((*before.items, *checked)) != plan_hash:
                raise AppError(ErrorCode.PLAN_CHANGED)
            if before.state is SetupState.NEWER_SCHEMA:
                raise AppError(ErrorCode.SETUP_REQUIRED)
            await run_plan(self._client.invoke_setup, manifest, state, before.items)
            if any(i.action is PlanAction.MIGRATE for i in before.items):
                await run_migrations(self._client.invoke_setup, manifest, self._migrations, state)
            await run_repairs(self._client.invoke_setup, checked)
            _, verified = await read_preview(self._client.invoke, manifest)
            self._set_gate(verified)
        return verified

    async def create_capture(self, capture_id: str, text: str, created_at: datetime) -> Capture:
        """Find the Capture by CaptureId (matched in Python, AD-4) and return it unchanged, or
        add it to `<Prefix>::Captures` and suspend its card (AD-6, AD-20), under one lock hold.
        Raises `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        model = _capture_model(manifest)
        created_at = created_at.astimezone(UTC).replace(microsecond=0)
        async with self._lock.hold():
            stored = await self._find_capture(manifest, capture_id)
            if stored is not None:
                return stored
            fields = {
                _TEXT: text,
                _CREATED_AT: created_at.strftime(_CREATED_AT_FORMAT),
                _CAPTURE_ID: capture_id,
                SCHEMA_VERSION_FIELD: str(manifest.schema_version),
            }
            note_id = await self._client.invoke(
                "addNote",
                note={
                    "deckName": manifest.card_deck(model, 0),
                    "modelName": model,
                    "fields": _encoded(fields),
                    "options": {"allowDuplicate": True},
                },
            )
            if not is_int(note_id):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            await self._client.invoke("suspend", cards=await self._note_cards(note_id))
        return Capture(capture_id, text, created_at)

    async def list_captures(self) -> list[Capture]:
        """Every Capture of the Prefix, decoded through the codec, newest first by CreatedAt
        (ties by CaptureId), under one lock hold. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            infos = await self._capture_infos(manifest)
        captures = [_stored_capture(_field(info, _CAPTURE_ID).strip(), info) for info in infos]
        captures.sort(key=lambda c: (c.created_at, c.capture_id), reverse=True)
        return captures

    async def get_capture(self, capture_id: str) -> Capture:
        """The Capture whose CaptureId is `capture_id`, matched in Python (AD-4), under one lock
        hold. Raises `AppError(NOT_FOUND | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            stored = await self._find_capture(manifest, capture_id)
        if stored is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return stored

    async def delete_capture(self, capture_id: str) -> None:
        """Delete every note whose CaptureId is `capture_id` (matched in Python, AD-4) with one
        `deleteNotes`, under one lock hold; with none, nothing is written. Raises
        `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            infos = await self._capture_infos(manifest)
            note_ids: list[int] = []
            for info in _matching(infos, _CAPTURE_ID, capture_id):
                note_id = info.get("noteId")
                if not is_int(note_id):
                    raise AppError(ErrorCode.ANKI_UNAVAILABLE)
                note_ids.append(note_id)
            if note_ids:
                await self._client.invoke("deleteNotes", notes=note_ids)

    async def save_item(
        self,
        item_id: str,
        language: Language,
        content: ItemContent,
        audio: AudioIntent = AudioIntent.KEEP,
        *,
        audio_bytes: bytes | None = None,
    ) -> None:
        """Update the note whose decoded ItemId is `item_id` (matched in Python, AD-4), or add
        it to its Pronunciation deck and move cards 0-2 to their Study decks (AD-6), under one
        lock hold. Replacement stores media first and cleans old managed media last; removal
        stores nothing, empties Audio, then cleans the old managed media last. A failure stops
        the sequence with no compensation: leftovers are Setup's `orphanMedia` repairs. Raises
        `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        audio_upload(audio, audio_bytes)
        manifest = self._require_manifest()
        model = manifest.item_note_type(language, content.category)
        fields = _content_fields(content)
        async with self._lock.hold():
            infos = await self._note_infos(manifest, model)
            stored = next(_matching(infos, _ITEM_ID, item_id), None)
            old_name = _audio_name(_optional(stored, _AUDIO), manifest.prefix) if stored else None
            name = None
            if audio_bytes is not None:
                name = media_name(manifest.prefix, item_id, audio_bytes)
                result = await self._client.invoke(
                    "storeMediaFile",
                    filename=name,
                    data=base64.b64encode(audio_bytes).decode("ascii"),
                )
                if result != name:
                    raise AppError(ErrorCode.ANKI_UNAVAILABLE)
                fields[_AUDIO] = f"[sound:{name}]"
            elif audio is AudioIntent.REMOVE:
                fields[_AUDIO] = ""
            if stored is not None:
                note_id = stored.get("noteId")
                if not is_int(note_id):
                    raise AppError(ErrorCode.ANKI_UNAVAILABLE)
                await self._client.invoke(
                    "updateNoteFields", note={"id": note_id, "fields": _encoded(fields)}
                )
            else:
                fields |= {
                    _AUDIO: fields.get(_AUDIO, ""),
                    _ITEM_ID: item_id,
                    SCHEMA_VERSION_FIELD: str(manifest.schema_version),
                }
                note_id = await self._client.invoke(
                    "addNote",
                    note={
                        "deckName": manifest.card_deck(model, PRONOUNCE_ORD),
                        "modelName": model,
                        "fields": _encoded(fields),
                        "options": {"allowDuplicate": True},
                    },
                )
                if not is_int(note_id):
                    raise AppError(ErrorCode.ANKI_UNAVAILABLE)
                for ord, card_id in (await self._cards_by_ord(note_id)).items():
                    if ord in STUDY_ORDS:
                        await self._client.invoke(
                            "changeDeck", cards=[card_id], deck=manifest.card_deck(model, ord)
                        )
            superseded = audio is AudioIntent.REMOVE or (name is not None and name != old_name)
            if old_name and superseded:
                await self._client.invoke("deleteMediaFile", filename=old_name)

    async def get_media(self, name: str) -> bytes:
        manifest = self._require_manifest()
        if not media_pattern(manifest.prefix).fullmatch(name):
            raise AppError(ErrorCode.NOT_FOUND)
        async with self._lock.hold():
            result = await self._client.invoke("retrieveMediaFile", filename=name)
            if result is False:
                raise AppError(ErrorCode.NOT_FOUND)
            if not isinstance(result, str):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            try:
                return base64.b64decode(result, validate=True)
            except ValueError, binascii.Error:
                raise AppError(ErrorCode.ANKI_UNAVAILABLE) from None

    async def item_candidates(self, language: Language, category: Category) -> list[Item]:
        """Every Item of the exact `language`/`category` note type scope, decoded, in note
        order, under one lock hold. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        model = manifest.item_note_type(language, category)
        async with self._lock.hold():
            infos = await self._note_infos(manifest, model)
        return [_stored_item(info, category, manifest.prefix) for info in infos]

    async def get_item(self, language: Language, item_id: str) -> Item:
        """The Item of `language` whose decoded ItemId is `item_id` (matched in Python, AD-4),
        from both Categories' exact scopes under one lock hold. Raises
        `AppError(NOT_FOUND | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        # Both scopes are always read, so the requests don't vary with where the Item is
        async with self._lock.hold():
            scopes = [
                (
                    category,
                    await self._note_infos(manifest, manifest.item_note_type(language, category)),
                )
                for category in Category
            ]
        for category, infos in scopes:
            info = next(_matching(infos, _ITEM_ID, item_id), None)
            if info is not None:
                return _stored_item(info, category, manifest.prefix)
        raise AppError(ErrorCode.NOT_FOUND)

    async def delete_item(self, language: Language, item_id: str) -> None:
        """Delete matching notes before their managed media, stopping at the first failure.

        Both exact Category scopes are resolved before any write, with the decoded ItemId
        matched in Python. Absent-note cleanup is retryable, but preserves media when another
        Language still owns the ItemId. All reads and guarded, Setup-gated writes share this
        one lock hold.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            note_ids: list[int] = []
            for category in Category:
                infos = await self._note_infos(
                    manifest, manifest.item_note_type(language, category)
                )
                for info in _matching(infos, _ITEM_ID, item_id):
                    note_id = info.get("noteId")
                    if not is_int(note_id):
                        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
                    note_ids.append(note_id)
            if note_ids:
                await self._client.invoke("deleteNotes", notes=note_ids)
            else:
                # Media names contain no Language: an absent Item in this Language must not
                # turn a wrong-Language request into cleanup of another Language's Item.
                for other_language in Language:
                    if other_language is language:
                        continue
                    for category in Category:
                        infos = await self._note_infos(
                            manifest, manifest.item_note_type(other_language, category)
                        )
                        if next(_matching(infos, _ITEM_ID, item_id), None) is not None:
                            return
            # AD-7 names are lowercase, and `getMediaFilesNames` matches case-sensitively
            stem = f"{manifest.prefix.lower()}_{item_id}_"
            names = await self._client.invoke("getMediaFilesNames", pattern=f"{stem}*")
            if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            managed = media_pattern(manifest.prefix)
            for name in sorted(set(names)):
                if name.startswith(stem) and managed.fullmatch(name):
                    await self._client.invoke("deleteMediaFile", filename=name)

    async def pronunciation_queue(self, language: Language) -> PronunciationQueue:
        """The Language's due then new Pronounce Cards, from reads only under one lock hold.

        Due Cards (any `type` but new) sort by their day-number `due`, intraday learning cards
        (due in epoch seconds) after them, ties by card id; new Cards by card id, which is their
        creation time. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            found: dict[int, Category] = {}
            for category in Category:
                model = manifest.item_note_type(language, category)
                query = pronounce_queue_query(
                    manifest, manifest.card_deck(model, PRONOUNCE_ORD), model, PRONOUNCE_ORD + 1
                )
                ids = await self._client.invoke("findCards", query=query)
                if not isinstance(ids, list) or not all(is_int(card_id) for card_id in ids):
                    raise AppError(ErrorCode.ANKI_UNAVAILABLE)
                for card_id in ids:
                    found.setdefault(card_id, category)
            if not found:
                return PronunciationQueue(0, 0, ())
            card_infos = await self._client.invoke("cardsInfo", cards=list(found))
            cards = _queued_cards(card_infos, len(found))
            note_ids = sorted({info["note"] for info in cards})
            notes = await self._client.invoke("notesInfo", notes=note_ids) if note_ids else []
        by_note = _notes_by_id(notes, len(note_ids))
        due: list[tuple[tuple[bool, int, int], PronounceCard]] = []
        new: list[tuple[int, PronounceCard]] = []
        for info in cards:
            note = by_note.get(info["note"])
            if note is None:  # deleted since `findCards`
                continue
            card_id = info["cardId"]
            card = PronounceCard(
                card_id=card_id,
                item_id=_field(note, _ITEM_ID).strip(),
                reps=info["reps"],
                category=found[card_id],
                target=_field(note, "Target"),
                audio=_audio_name(_optional(note, _AUDIO), manifest.prefix),
            )
            if info["type"] == _NEW_TYPE:
                new.append((card_id, card))
            else:
                key = (info["queue"] == _INTRADAY_QUEUE, info["due"], card_id)
                due.append((key, card))
        due.sort(key=lambda entry: entry[0])
        new.sort(key=lambda entry: entry[0])
        return PronunciationQueue(
            len(due), len(new), tuple(card for _, card in due) + tuple(card for _, card in new)
        )

    async def answer_card(
        self, language: Language, card_id: int, reps: int, rating: Rating
    ) -> bool:
        """Answer one Pronounce Card unless its `reps` moved on (then True: alreadyAnswered).

        The card must be ord 3 of one of the Language's Item note types, unsuspended and
        unburied, in its Pronunciation deck, else `NOT_FOUND`; its
        `reps` and the answer share one lock hold. `answerCards` must answer `[true]`, else
        `ANKI_UNAVAILABLE`. Raises `AppError(NOT_FOUND | SETUP_REQUIRED | ANKI_UNAVAILABLE |
        ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        models = {manifest.item_note_type(language, category) for category in Category}
        async with self._lock.hold():
            infos = await self._client.invoke("cardsInfo", cards=[card_id])
            if not isinstance(infos, list) or len(infos) != 1 or not isinstance(infos[0], dict):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            info = infos[0]
            model, queue = info.get("modelName"), info.get("queue")
            if model not in models or info.get("ord") != PRONOUNCE_ORD:
                raise AppError(ErrorCode.NOT_FOUND)  # `{}` too: a card Anki doesn't have
            # Suspended, buried or moved out of its Pronunciation deck since the queue read
            if not is_int(queue) or queue < 0:
                raise AppError(ErrorCode.NOT_FOUND)
            if info.get("deckName") != manifest.card_deck(model, PRONOUNCE_ORD):
                raise AppError(ErrorCode.NOT_FOUND)
            current = info.get("reps")
            if not is_int(current):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            if current != reps:
                return True
            answered = await self._client.invoke(
                "answerCards", answers=[{"cardId": card_id, "ease": _EASE[rating]}]
            )
            if answered != [True]:
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            return False

    async def _cards_by_ord(self, note_id: int) -> dict[int, int]:
        """Each card id of note `note_id` by its ord, from `notesInfo` and `cardsInfo`;
        `ANKI_UNAVAILABLE` on a malformed reply.
        """
        cards = await self._note_cards(note_id)
        card_infos = await self._client.invoke("cardsInfo", cards=cards)
        if not isinstance(card_infos, list):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        by_ord: dict[int, int] = {}
        for info in card_infos:
            card_id = info.get("cardId") if isinstance(info, dict) else None
            ord = info.get("ord") if isinstance(info, dict) else None
            if not is_int(card_id) or not is_int(ord):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            by_ord[ord] = card_id
        # Every card answered, and every Study ord among them: else a card would stay unmoved
        if len(by_ord) != len(cards) or not set(STUDY_ORDS) <= set(by_ord):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return by_ord

    async def _note_cards(self, note_id: int) -> list[Any]:
        """The card ids of note `note_id`, from `notesInfo`; `ANKI_UNAVAILABLE` on a malformed
        reply or a note with no cards.
        """
        infos = await self._client.invoke("notesInfo", notes=[note_id])
        if not isinstance(infos, list) or len(infos) != 1 or not isinstance(infos[0], dict):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        cards = infos[0].get("cards")
        if not isinstance(cards, list) or not cards:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return cards

    async def _capture_infos(self, manifest: Manifest) -> list[dict[str, Any]]:
        return await self._note_infos(manifest, _capture_model(manifest))

    async def _note_infos(self, manifest: Manifest, model: str) -> list[dict[str, Any]]:
        """The `notesInfo` entries of the exact `model` scope's `findNotes`, skipping notes
        deleted in between; `ANKI_UNAVAILABLE` on a malformed reply.
        """
        query = note_query(manifest, model)
        ids = await self._client.invoke("findNotes", query=query)
        if not isinstance(ids, list) or not all(is_int(note_id) for note_id in ids):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        if not ids:
            return []
        infos = await self._client.invoke("notesInfo", notes=ids)
        if not isinstance(infos, list) or len(infos) != len(ids):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        entries: list[dict[str, Any]] = []
        for info in infos:
            if info == {}:  # a note deleted since `findNotes`
                continue
            if not isinstance(info, dict):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            entries.append(info)
        return entries

    async def _find_capture(self, manifest: Manifest, capture_id: str) -> Capture | None:
        """The stored Capture whose decoded CaptureId is `capture_id`, from the exact Capture
        scope's `findNotes` and `notesInfo`; None when there is none.
        """
        info = next(_matching(await self._capture_infos(manifest), _CAPTURE_ID, capture_id), None)
        return None if info is None else _stored_capture(capture_id, info)

    def _set_gate(self, preview: SetupPreview) -> None:
        if self._gate is not None:
            self._gate.set(preview.state)

    def _require_manifest(self) -> Manifest:
        if self._manifest is None:
            raise RuntimeError("AnkiConnectStore was built without a manifest")
        return self._manifest

    async def sync(self) -> SyncOutcome:
        async with self._lock.hold():
            try:
                async with asyncio.timeout(self._sync_budget_s):
                    return await self._sync_to_end()
            except TimeoutError:
                return SyncOutcome.ANKIWEB_UNREACHABLE

    async def _sync_to_end(self) -> SyncOutcome:
        started = await self._client.invoke_v1("collection.sync")
        operation_id = started.get("operationId") if isinstance(started, dict) else None
        if not isinstance(operation_id, str):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        while True:
            poll = await self._client.invoke_v1("operations.get", operationId=operation_id)
            if not isinstance(poll, dict):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            state = poll.get("state")
            if state == _SUCCEEDED:
                return SyncOutcome.OK
            if state == _FAILED:
                return _failure_outcome(poll)
            if state in _GAVE_UP:
                return SyncOutcome.ANKIWEB_UNREACHABLE
            await asyncio.sleep(self._poll_interval_s)

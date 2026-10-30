"""SetupState and the write gate (AD-19, AD-3, NFR-1).

`SetupState` comes from the Setup preview's reads plus every managed note's `SchemaVersion`,
decoded through the codec. Precedence:

1. `newer_schema`: any managed note above the manifest's version.
2. `needs_migration`: any Migrate item, or any note below it, empty or not an integer.
3. `needs_setup`: any other plan item but a reading rule's Create: a missing seed note
   threatens nothing features write, so deleting one never blocks them.
4. `ready`.

Only manifest note types are read (exact `note_query`), so another Prefix's notes never count
(AD-4).

The same `notesInfo` answer gives the reading rule notes' decoded `RuleId`s, which the diff
matches against the seeded rules.

For the opt-in repairs (entry 11) the preview also reads, still reads only: the `Audio` and
`Example<n>Audio` names the same `notesInfo` answer references, the manifest note types' cards
(one `multi` of `findCards` beside `getMediaFilesNames` for `<prefix lowercased>_*`, then one
`cardsInfo`). They never change the SetupState.

`SetupGate(manifest)` is shared by the client and the store. `check(action, params, lookup)`
runs after the Prefix guard on every non-Setup request: reads (and `multi` of reads) pass, and
any write raises `AppError(SETUP_REQUIRED)` before it is sent unless the state is `ready`. An
unknown state (None) is computed first through `lookup`, the client's unguarded call: the
caller already holds the Anki lock. `updateNoteFields` is also refused when the note's stored
`SchemaVersion` isn't the manifest's, or when the update sets it to anything else (AD-3: only
migrations rewrite it). Setup's own apply writes through the client's ungated path.
"""

import dataclasses
import re
from collections.abc import Iterable, Mapping
from typing import Any

from language_lab.adapters.anki.codec import decode_field
from language_lab.adapters.anki.guard import READS, Lookup, inner_actions, is_int
from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.query import note_query
from language_lab.adapters.anki.setup_diff import AnkiState, CardState, ModelState, diff
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanAction, ResourceKind, SetupPreview, SetupState

SCHEMA_VERSION_FIELD = "SchemaVersion"
AUDIO_FIELD = "Audio"
RULE_ID_FIELD = "RuleId"
# The fields that may hold `[sound:]` tags: an Item's, then a reading rule's examples'
_AUDIO_FIELDS = (AUDIO_FIELD, "Example1Audio", "Example2Audio", "Example3Audio")
_SOUND = re.compile(r"\[sound:([^\]]+)\]")
_SUSPENDED_QUEUE = -1
_MODEL_READS = ("modelFieldNames", "modelTemplates", "modelStyling")
_INNER_VERSION = 6  # `multi` answers each inner action as `{result, error}` from version 6
_INTEGER = re.compile(r"[0-9]+")

type Read = tuple[str, dict[str, Any]]


# ---- the preview's reads -----------------------------------------------------------------


async def multi(lookup: Lookup, reads: list[Read]) -> list[Any]:
    """Send `reads` as one `multi` and return each inner `result`."""
    actions = [
        {"action": action, "version": _INNER_VERSION, "params": params} for action, params in reads
    ]
    replies = await lookup("multi", actions=actions)
    if not isinstance(replies, list) or len(replies) != len(reads):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    results = []
    for reply in replies:
        if not isinstance(reply, dict) or reply.get("error") is not None:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        results.append(reply.get("result"))
    return results


def _names(value: Any) -> frozenset[str]:
    if not isinstance(value, list) or not all(isinstance(n, str) for n in value):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return frozenset(value)


def _model_state(fields: Any, templates: Any, styling: Any) -> ModelState:
    """A note type from `modelFieldNames`, `modelTemplates` and `modelStyling` (spike 2.2)."""
    if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    if not isinstance(templates, dict) or not isinstance(styling, dict):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    sides: dict[str, tuple[str, str]] = {}
    for card, template in templates.items():
        if not isinstance(template, dict):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        front, back = template.get("Front"), template.get("Back")
        if not isinstance(front, str) or not isinstance(back, str):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        sides[card] = (front, back)
    css = styling.get("css")
    if not isinstance(css, str):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return ModelState(tuple(fields), sides, css)


async def read_state(lookup: Lookup, manifest: Manifest) -> AnkiState:
    """Anki's managed state, with reads only. Raises `AppError(ANKI_UNAVAILABLE)`."""
    deck_names, model_names = await multi(lookup, [("deckNames", {}), ("modelNames", {})])
    decks, models = _names(deck_names), _names(model_names)
    managed = [nt.name for nt in manifest.note_types if nt.name in models]
    preset_decks = [deck for deck in manifest.preset.decks if deck in decks]
    reads: list[Read] = []
    for name in managed:
        reads += [(action, {"modelName": name}) for action in _MODEL_READS]
    reads += [("getDeckConfig", {"deck": deck}) for deck in preset_decks]
    results = await multi(lookup, reads) if reads else []
    per_model = len(_MODEL_READS)
    managed_models = {
        name: _model_state(*results[i * per_model : (i + 1) * per_model])
        for i, name in enumerate(managed)
    }
    configs = results[len(managed) * per_model :]
    preset_configs = {deck: config for deck, config in zip(preset_decks, configs, strict=True)}
    if not all(isinstance(c, dict) for c in preset_configs.values()):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return AnkiState(decks, models, managed_models, preset_configs)


# ---- SchemaVersion -----------------------------------------------------------------------


def parse_version(stored: Any) -> int | None:
    """A stored `SchemaVersion` as an integer, decoded through the codec; None when it isn't one."""
    if not isinstance(stored, str):
        return None
    text = decode_field(stored).strip()
    return int(text) if _INTEGER.fullmatch(text) else None


def _stored_value(info: Any, name: str) -> Any:
    """The stored content of field `name` in one `notesInfo` entry; None when absent."""
    fields = info.get("fields") if isinstance(info, dict) else None
    field = fields.get(name) if isinstance(fields, dict) else None
    return field.get("value") if isinstance(field, dict) else None


def _stored_version(info: Any) -> int | None:
    """The `SchemaVersion` of one `notesInfo` entry."""
    return parse_version(_stored_value(info, SCHEMA_VERSION_FIELD))


def _sounds(info: Any) -> set[str]:
    """The media names one `notesInfo` entry's audio fields hold, decoded through the codec."""
    names: set[str] = set()
    for name in _AUDIO_FIELDS:
        stored = _stored_value(info, name)
        if isinstance(stored, str):
            names |= set(_SOUND.findall(decode_field(stored)))
    return names


def _rule_id(info: Any) -> str | None:
    """The decoded `RuleId` of one reading rule `notesInfo` entry; None when absent or empty."""
    stored = _stored_value(info, RULE_ID_FIELD)
    text = decode_field(stored).strip() if isinstance(stored, str) else ""
    return text or None


@dataclasses.dataclass(frozen=True)
class NoteReads:
    # manifest note type -> (note id, `SchemaVersion` or None when not an integer)
    versions: dict[str, tuple[tuple[int, int | None], ...]]
    audio: frozenset[str]  # every media name the notes' audio fields reference
    rule_ids: frozenset[str] = frozenset()  # the decoded RuleIds of the reading rule notes


def _manifest_types(manifest: Manifest, models: Iterable[str]) -> list[str]:
    """The manifest note types in `models`, in manifest order."""
    present = set(models)
    return [nt.name for nt in manifest.note_types if nt.name in present]


async def read_note_versions(
    lookup: Lookup, manifest: Manifest, models: Iterable[str]
) -> NoteReads:
    """Each manifest note type in `models` -> (note id, `SchemaVersion` or None when not an
    integer) of each of its notes, the media names their audio fields reference, and the
    reading rule notes' decoded `RuleId`s: one `multi` of `findNotes`, then one `notesInfo`.
    """
    types = _manifest_types(manifest, models)
    if not types:
        return NoteReads({}, frozenset())
    found = await multi(lookup, [("findNotes", {"query": note_query(manifest, t)}) for t in types])
    owners: dict[int, str] = {}
    for note_type, result in zip(types, found, strict=True):
        if not isinstance(result, list):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        owners |= dict.fromkeys(result, note_type)
    versions: dict[str, list[tuple[int, int | None]]] = {t: [] for t in types}
    audio: set[str] = set()
    rule_ids: set[str] = set()
    ids = list(owners)
    if ids:
        infos = await lookup("notesInfo", notes=ids)
        if not isinstance(infos, list) or len(infos) != len(ids):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        for note_id, info in zip(ids, infos, strict=True):
            # AnkiConnect answers `{}` for a note deleted since `findNotes`: it no longer counts
            if info != {}:
                versions[owners[note_id]].append((note_id, _stored_version(info)))
                audio |= _sounds(info)
                rule_id = _rule_id(info)
                if owners[note_id] == manifest.reading_rule_note_type and rule_id is not None:
                    rule_ids.add(rule_id)
    return NoteReads(
        {t: tuple(notes) for t, notes in versions.items() if notes},
        frozenset(audio),
        frozenset(rule_ids),
    )


def _card_state(info: Any) -> CardState | None:
    """One `cardsInfo` entry; None for `{}` (a card deleted since `findCards`)."""
    if info == {}:
        return None
    if not isinstance(info, dict):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    card_id, model, ord_, deck, queue = (
        info.get(k) for k in ("cardId", "modelName", "ord", "deckName", "queue")
    )
    if not (is_int(card_id) and is_int(ord_) and is_int(queue)):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    if not isinstance(model, str) or not isinstance(deck, str):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return CardState(card_id, model, ord_, deck, queue == _SUSPENDED_QUEUE)


async def read_leftovers(
    lookup: Lookup, manifest: Manifest, models: Iterable[str]
) -> tuple[tuple[CardState, ...], frozenset[str]]:
    """The cards of each manifest note type in `models` and the media named `<prefix>_*`
    (lowercased, AD-7; `getMediaFilesNames` matches case-sensitively): one
    `multi` of `findCards` and `getMediaFilesNames`, then one `cardsInfo` when there are cards.
    """
    types = _manifest_types(manifest, models)
    reads: list[Read] = [("findCards", {"query": note_query(manifest, t)}) for t in types]
    reads.append(("getMediaFilesNames", {"pattern": f"{manifest.prefix.lower()}_*"}))
    *found, media = await multi(lookup, reads)
    ids: list[int] = []
    for result in found:
        if not isinstance(result, list) or not all(is_int(i) for i in result):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        ids += result  # a card belongs to one note type
    cards: list[CardState] = []
    if ids:
        infos = await lookup("cardsInfo", cards=ids)
        if not isinstance(infos, list) or len(infos) != len(ids):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        cards = [card for info in infos if (card := _card_state(info)) is not None]
    return tuple(cards), _names(media)


def compute_state(
    preview: SetupPreview, versions: Iterable[int | None], schema_version: int
) -> SetupState:
    """The SetupState of `preview` with the managed notes' `versions` (precedence above)."""
    versions = list(versions)
    if any(v is not None and v > schema_version for v in versions):
        return SetupState.NEWER_SCHEMA
    migrate = any(i.action is PlanAction.MIGRATE for i in preview.items)
    if migrate or any(v is None or v < schema_version for v in versions):
        return SetupState.NEEDS_MIGRATION
    if any(i.kind is not ResourceKind.READING_RULE for i in preview.items):
        return SetupState.NEEDS_SETUP
    return SetupState.READY


async def read_preview(
    lookup: Lookup, manifest: Manifest, *, leftovers: bool = True
) -> tuple[AnkiState, SetupPreview]:
    """The managed state and its preview, with its `state`, from reads only. With
    `leftovers=False` the cards and media aren't read, so no repair row is offered: the
    SetupState never depends on them (AD-19).
    """
    state = await read_state(lookup, manifest)
    notes = await read_note_versions(lookup, manifest, state.models)
    cards: tuple[CardState, ...] = ()
    media: frozenset[str] = frozenset()
    if leftovers:
        cards, media = await read_leftovers(lookup, manifest, state.models)
    state = dataclasses.replace(
        state,
        note_versions=notes.versions,
        cards=cards,
        media=media,
        audio=notes.audio,
        reading_rules=notes.rule_ids,
    )
    preview = diff(manifest, state)
    versions = (v for per_type in notes.versions.values() for _, v in per_type)
    setup_state = compute_state(preview, versions, manifest.schema_version)
    return state, dataclasses.replace(preview, state=setup_state)


# ---- the gate ----------------------------------------------------------------------------


class SetupGate:
    def __init__(self, manifest: Manifest) -> None:
        self._manifest = manifest
        self.state: SetupState | None = None  # unknown until computed

    def set(self, state: SetupState) -> None:
        self.state = state

    async def check(self, action: Any, params: Mapping[str, Any], lookup: Lookup) -> None:
        """Return when `action` may be sent; raise `AppError(SETUP_REQUIRED)` otherwise.

        Runs after the Prefix guard, so `params` is well formed. `lookup` must not take the
        Anki lock. Raises `AppError(ANKI_UNAVAILABLE)` when an unknown state can't be read.
        """
        actions = inner_actions(params) if action == "multi" else [(action, params)]
        writes = [(a, p) for a, p in actions if a not in READS]
        if not writes:
            return
        if self.state is None:
            _, preview = await read_preview(lookup, self._manifest, leftovers=False)
            self.set(preview.state)
        if self.state is not SetupState.READY:
            raise AppError(ErrorCode.SETUP_REQUIRED)
        for write, write_params in writes:
            if write == "updateNoteFields":
                await self._require_current(write_params, lookup)

    async def _require_current(self, params: Mapping[str, Any], lookup: Lookup) -> None:
        """The note is stored at the manifest's SchemaVersion, and the update keeps it there."""
        current = self._manifest.schema_version
        note = params.get("note")
        if not isinstance(note, dict):
            raise AppError(ErrorCode.SETUP_REQUIRED)
        fields = note.get("fields")
        if isinstance(fields, dict) and SCHEMA_VERSION_FIELD in fields:
            if parse_version(fields[SCHEMA_VERSION_FIELD]) != current:
                raise AppError(ErrorCode.SETUP_REQUIRED)
        infos = await lookup("notesInfo", notes=[note.get("id")])
        if not isinstance(infos, list) or len(infos) != 1:
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        if _stored_version(infos[0]) != current:
            raise AppError(ErrorCode.SETUP_REQUIRED)

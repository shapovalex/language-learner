"""SetupState and the write gate (AD-19, AD-3, NFR-1).

`SetupState` comes from the Setup preview's reads plus every managed note's `SchemaVersion`,
decoded through the codec. Precedence:

1. `newer_schema`: any managed note above the manifest's version.
2. `needs_migration`: any Migrate item, or any note below it, empty or not an integer.
3. `needs_setup`: any other plan item.
4. `ready`.

Only manifest note types are read (exact `note_query`), so another Prefix's notes never count
(AD-4).

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
from language_lab.adapters.anki.guard import READS, Lookup, inner_actions
from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.query import note_query
from language_lab.adapters.anki.setup_diff import AnkiState, ModelState, diff
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanAction, SetupPreview, SetupState

SCHEMA_VERSION_FIELD = "SchemaVersion"
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


def _stored_version(info: Any) -> int | None:
    """The `SchemaVersion` of one `notesInfo` entry."""
    fields = info.get("fields") if isinstance(info, dict) else None
    field = fields.get(SCHEMA_VERSION_FIELD) if isinstance(fields, dict) else None
    return parse_version(field.get("value") if isinstance(field, dict) else None)


async def read_versions(
    lookup: Lookup, manifest: Manifest, models: Iterable[str]
) -> list[int | None]:
    """Every managed note's `SchemaVersion` (None when not an integer), for the manifest note
    types in `models`: one `multi` of `findNotes`, then one `notesInfo`.
    """
    present = set(models)
    types = [nt.name for nt in manifest.note_types if nt.name in present]
    if not types:
        return []
    found = await multi(lookup, [("findNotes", {"query": note_query(manifest, t)}) for t in types])
    ids: list[int] = []
    for result in found:
        if not isinstance(result, list):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        ids += result
    if not ids:
        return []
    infos = await lookup("notesInfo", notes=ids)
    if not isinstance(infos, list):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    # AnkiConnect answers `{}` for a note deleted since `findNotes`: it no longer counts
    return [_stored_version(info) for info in infos if info != {}]


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
    if preview.items:
        return SetupState.NEEDS_SETUP
    return SetupState.READY


async def read_preview(lookup: Lookup, manifest: Manifest) -> tuple[AnkiState, SetupPreview]:
    """The managed state and its preview, with its `state`, from reads only."""
    state = await read_state(lookup, manifest)
    preview = diff(manifest, state)
    versions = await read_versions(lookup, manifest, state.models)
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
            _, preview = await read_preview(lookup, self._manifest)
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

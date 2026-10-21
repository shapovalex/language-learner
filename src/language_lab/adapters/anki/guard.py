"""The AD-4 Prefix guard (NFR-1): no AnkiConnect write leaves the client unless it targets
something LanguageLab manages.

`PrefixGuard(manifest).check(action, params, lookup)` runs before every v6 request. Reads in
`READS` pass. A write passes only when its target is a manifest deck or note type (by exact
name, never by prefix match), the `<Prefix>` preset, an AD-7 media name, or notes and cards of
a manifest note type, looked up by id through `lookup` first. `multi` is checked action by
action. Anything else, an action the guard doesn't know included, raises `PrefixViolation`
before a request is sent: the guard fails closed.

`check_read_only` is what a client without a guard applies: reads only.

A `PrefixViolation` is a programming error. It carries no target name (AD-15) and surfaces as
the 500 `internal_error`.
"""

import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from language_lab.adapters.anki.manifest import Manifest

# `lookup(action, **params)`: an unguarded v6 call returning its `result`
type Lookup = Callable[..., Awaitable[Any]]

READS = frozenset(
    {
        "version",
        "deckNames",
        "deckNamesAndIds",
        "modelNames",
        "modelNamesAndIds",
        "modelFieldNames",
        "modelTemplates",
        "modelStyling",
        "findModelsByName",
        "getDeckConfig",
        "findNotes",
        "findCards",
        "notesInfo",
        "cardsInfo",
        "getMediaFilesNames",
    }
)

_UUID4 = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"

# Writes that name their note type in `modelName` (spike 2.2: AnkiConnect's model* family)
_MODEL_NAME_WRITES = ("modelField", "modelTemplate")
_MODEL_OBJECT_WRITES = frozenset({"updateModelTemplates", "updateModelStyling"})
_CARD_WRITES = frozenset({"suspend", "unsuspend"})
_NOTE_MEDIA_KEYS = ("audio", "video", "picture")


class PrefixViolation(Exception):  # noqa: N818 -- the name the architecture uses (AD-4)
    """A request outside the Prefix was refused before it was sent. Names no target (AD-15)."""

    def __init__(self) -> None:
        super().__init__("AnkiConnect request refused by the Prefix guard")


def _require(condition: bool) -> None:
    if not condition:
        raise PrefixViolation


def _ids(value: Any) -> list[int]:
    """A non-empty list of integer ids, or a violation."""
    _require(isinstance(value, list) and len(value) > 0)
    _require(all(isinstance(i, int) and not isinstance(i, bool) for i in value))
    return value


def _inner_actions(params: Mapping[str, Any]) -> list[tuple[Any, Mapping[str, Any]]]:
    actions = params.get("actions")
    _require(isinstance(actions, list))
    inner: list[tuple[Any, Mapping[str, Any]]] = []
    for entry in actions:
        _require(isinstance(entry, dict))
        inner_params = entry.get("params", {})
        _require(isinstance(inner_params, dict))
        inner.append((entry.get("action"), inner_params))
    return inner


def check_read_only(action: Any, params: Mapping[str, Any]) -> None:
    """What an unguarded client allows: reads, and `multi` of reads only."""
    if action == "multi":
        for inner, inner_params in _inner_actions(params):
            check_read_only(inner, inner_params)
        return
    _require(isinstance(action, str))
    _require(action in READS)


class PrefixGuard:
    def __init__(self, manifest: Manifest) -> None:
        self._prefix = manifest.prefix
        self._decks = frozenset(manifest.decks)
        self._note_types = frozenset(nt.name for nt in manifest.note_types)
        self._preset_deck = manifest.preset.decks[0]
        self._media = re.compile(rf"{re.escape(manifest.prefix)}_{_UUID4}_[0-9a-f]{{12}}\.mp3")

    async def check(self, action: Any, params: Mapping[str, Any], lookup: Lookup) -> None:
        """Return when `action` may be sent; raise `PrefixViolation` otherwise.

        Id-targeted writes call `lookup` (reads only) before they pass.
        """
        if action == "multi":
            for inner, inner_params in _inner_actions(params):
                await self.check(inner, inner_params, lookup)
            return
        _require(isinstance(action, str))
        if action in READS:
            return
        if self._name_targeted(action, params):
            return
        await self._id_targeted(action, params, lookup)

    def _is_deck(self, value: Any) -> bool:
        return isinstance(value, str) and value in self._decks

    def _is_note_type(self, value: Any) -> bool:
        return isinstance(value, str) and value in self._note_types

    def _is_decks(self, value: Any) -> bool:
        return isinstance(value, list) and len(value) > 0 and all(map(self._is_deck, value))

    def _is_media(self, value: Any) -> bool:
        return isinstance(value, str) and self._media.fullmatch(value) is not None

    def _require_note_media(self, note: Mapping[str, Any]) -> None:
        """A note's `audio`/`video`/`picture` files are stored as media: each must be AD-7."""
        for key in _NOTE_MEDIA_KEYS:
            if key not in note:
                continue
            media = note[key]
            _require(isinstance(media, list))
            _require(all(isinstance(m, dict) and self._is_media(m.get("filename")) for m in media))

    def _name_targeted(self, action: str, params: Mapping[str, Any]) -> bool:
        """True when `action` is a name-targeted write to a managed name; a violation when it is
        one to anything else; False when it isn't name-targeted.
        """
        if action == "createDeck":
            _require(self._is_deck(params.get("deck")))
        elif action == "setDeckConfigId":  # deleteDecks fails closed: it takes unmanaged subdecks
            _require(self._is_decks(params.get("decks")))
        elif action == "createModel" or action.startswith(_MODEL_NAME_WRITES):
            _require(self._is_note_type(params.get("modelName")))
        elif action in _MODEL_OBJECT_WRITES:
            model = params.get("model")
            _require(isinstance(model, dict) and self._is_note_type(model.get("name")))
        elif action == "cloneDeckConfigId":
            _require(params.get("name") == self._prefix)
        elif action == "addNote":
            note = params.get("note")
            _require(isinstance(note, dict))
            _require(self._is_note_type(note.get("modelName")))
            _require(self._is_deck(note.get("deckName")))
            self._require_note_media(note)
        elif action in ("storeMediaFile", "deleteMediaFile"):
            _require(self._is_media(params.get("filename")))
        else:
            return False
        return True

    async def _id_targeted(self, action: str, params: Mapping[str, Any], lookup: Lookup) -> None:
        if action == "updateNoteFields":
            note = params.get("note")
            _require(isinstance(note, dict))
            self._require_note_media(note)
            await self._require_managed(lookup, "notesInfo", "notes", _ids([note.get("id")]))
        elif action == "deleteNotes":
            await self._require_managed(lookup, "notesInfo", "notes", _ids(params.get("notes")))
        elif action == "changeDeck":
            _require(self._is_deck(params.get("deck")))
            await self._require_managed(lookup, "cardsInfo", "cards", _ids(params.get("cards")))
        elif action in _CARD_WRITES:
            await self._require_managed(lookup, "cardsInfo", "cards", _ids(params.get("cards")))
        elif action == "saveDeckConfig":
            await self._require_preset(params.get("config"), lookup)
        else:
            raise PrefixViolation  # unknown: fail closed

    async def _require_managed(self, lookup: Lookup, read: str, key: str, ids: list[int]) -> None:
        """Every note or card in `ids` exists and is of a manifest note type."""
        found = await lookup(read, **{key: ids})
        _require(isinstance(found, list) and len(found) == len(ids))
        _require(all(isinstance(e, dict) and self._is_note_type(e.get("modelName")) for e in found))

    async def _require_preset(self, config: Any, lookup: Lookup) -> None:
        """The config is the `<Prefix>` preset a managed deck already uses."""
        _require(isinstance(config, dict) and config.get("name") == self._prefix)
        config_id = config.get("id")
        _require(isinstance(config_id, int) and not isinstance(config_id, bool))
        current = await lookup("getDeckConfig", deck=self._preset_deck)
        _require(isinstance(current, dict) and current.get("name") == self._prefix)
        _require(current.get("id") == config_id)

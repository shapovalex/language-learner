"""An Anki collection in memory, answered as AnkiConnect would, for the Setup preview tests.

`managed_collection(manifest)` is a Prefix that Setup has already applied; `stock_collection()`
is an Anki with nothing LanguageLab manages. Tests change one thing in either, then replay it
through `collection_replies()` into an `AnkiConnectReplay`.

The reply shapes are the recorded ones from tests/fixtures/anki/ (spike 2.2): a preset is the
recorded `getDeckConfig` result with its id, name and bury flags replaced, and a full model is
shaped like the recorded `createModel` result. By default only reads are answered: a write
action gets AnkiConnect's "unsupported action" error, and the replay's `.sent` shows that it was
sent. With `writes=True` the collection also answers the writes Setup's apply sends
(`WRITE_ACTIONS`) and changes itself the way AnkiConnect changes Anki (story 2.7).

Notes (story 2.8): `add_note()` puts a note in the collection, and `managed_note()` puts one of
a manifest note type with its `SchemaVersion` field set. `findNotes` answers an exact
`note:"<type>"` query, `notesInfo` answers in the recorded shape, and with `writes=True` the
collection also answers `addNote` and `updateNoteFields` (`NOTE_WRITE_ACTIONS`).
"""

import copy
import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from language_lab.adapters.anki.manifest import Manifest
from tests.support.anki_connect import UNSUPPORTED, StubReply, anki_fixture

DEFAULT_DECK = "Default"
DEFAULT_PRESET = "Default"

# Every read the simulator answers. A preview may send these and nothing else (AC-5).
READ_ACTIONS = frozenset(
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
        "multi",
    }
)


# Every write the simulator answers with `collection_replies(..., writes=True)` (story 2.7)
WRITE_ACTIONS = frozenset(
    {
        "createDeck",
        "createModel",
        "updateModelTemplates",
        "updateModelStyling",
        "modelTemplateAdd",
        "cloneDeckConfigId",
        "setDeckConfigId",
        "saveDeckConfig",
    }
)


# The note writes the simulator answers with `writes=True` (story 2.8): what features send
NOTE_WRITE_ACTIONS = frozenset({"addNote", "updateNoteFields"})


@dataclass
class Model:
    fields: list[str]
    templates: dict[str, dict[str, str]]  # card name -> {"Front", "Back"}, in ord order
    css: str


@dataclass
class Collection:
    decks: dict[str, str] = field(default_factory=dict)  # deck name -> its preset's name
    # a key (the preset's name, unless two share one) -> deck config
    presets: dict[str, dict[str, Any]] = field(default_factory=dict)
    models: dict[str, Model] = field(default_factory=dict)
    notes: dict[int, Note] = field(default_factory=dict)  # note id -> note


@dataclass
class Note:
    model: str
    fields: dict[str, str]  # field name -> stored content, in the model's field order


_STOCK_MODELS = tuple(anki_fixture("modelNames")["response"]["result"])
_ids = itertools.count(1792093019000)


def preset_config(name: str, **overrides: Any) -> dict[str, Any]:
    """The recorded deck config (`getDeckConfig.json`), renamed, with every bury flag off.

    `overrides` sets keys by dotted path, e.g. `**{"rev.bury": True, "new.perDay": 50}`.
    """
    config = copy.deepcopy(anki_fixture("getDeckConfig")["response"]["result"])
    config["id"] = next(_ids)
    config["name"] = name
    config["new"]["bury"] = False
    config["rev"]["bury"] = False
    config["buryInterdayLearning"] = False
    for path, value in overrides.items():
        set_path(config, path, value)
    return config


def set_path(config: dict[str, Any], path: str, value: Any) -> None:
    """Set a dotted key (`"rev.bury"`) in a deck config."""
    *parents, leaf = path.split(".")
    node = config
    for key in parents:
        node = node[key]
    node[leaf] = value


def _stock_model() -> Model:
    return Model(
        ["Front", "Back"], {"Card 1": {"Front": "{{Front}}", "Back": "{{Back}}"}}, ".card {}"
    )


def stock_collection() -> Collection:
    """An Anki with only its own deck, preset and note types: nothing LanguageLab manages."""
    return Collection(
        decks={DEFAULT_DECK: DEFAULT_PRESET},
        presets={DEFAULT_PRESET: preset_config(DEFAULT_PRESET)},
        models={name: _stock_model() for name in _STOCK_MODELS},
    )


def apply_manifest(collection: Collection, manifest: Manifest) -> Collection:
    """`collection` with everything `manifest` declares, as a finished Setup leaves it."""
    collection.presets[manifest.preset.name] = preset_config(manifest.preset.name)
    for deck in manifest.decks:
        on_preset = deck in manifest.preset.decks
        collection.decks[deck] = manifest.preset.name if on_preset else DEFAULT_PRESET
    for note_type in manifest.note_types:
        collection.models[note_type.name] = Model(
            fields=[f.name for f in note_type.fields],
            templates={t.name: {"Front": t.front, "Back": t.back} for t in note_type.templates},
            css=note_type.css,
        )
    return collection


def managed_collection(manifest: Manifest) -> Collection:
    """A stock Anki in which Setup has applied `manifest`."""
    return apply_manifest(stock_collection(), manifest)


def add_note(collection: Collection, model: str, fields: dict[str, str]) -> int:
    """Put a note of `model` with `fields` (stored content) in `collection`; return its id."""
    note_id = next(_ids)
    collection.notes[note_id] = Note(model, dict(fields))
    return note_id


def managed_note(
    collection: Collection, manifest: Manifest, note_type: str, schema_version: str
) -> int:
    """Put a note of the manifest's `note_type` in `collection`, every field empty but
    `SchemaVersion`, stored as `schema_version` exactly (markup included); return its id.
    """
    declared = next(nt for nt in manifest.note_types if nt.name == note_type)
    fields = {f.name: "" for f in declared.fields}
    fields["SchemaVersion"] = schema_version
    return add_note(collection, note_type, fields)


_NOTE_QUERY = re.compile(r'note:"([^"]*)"')


def _find_notes(collection: Collection, query: str) -> list[int]:
    """Ids for an exact `note:"<type>"` query; any other query finds nothing."""
    match = _NOTE_QUERY.fullmatch(query)
    if match is None:
        return []
    return sorted(i for i, note in collection.notes.items() if note.model == match.group(1))


def _note_info(note_id: int, note: Note) -> dict[str, Any]:
    """A note as `notesInfo` returns it, shaped like the recorded `notesInfo` result."""
    recorded = anki_fixture("notesInfo")["response"]["result"][0]
    return {
        **copy.deepcopy(recorded),
        "noteId": note_id,
        "tags": [],
        "fields": {
            name: {"value": value, "order": order}
            for order, (name, value) in enumerate(note.fields.items())
        },
        "modelName": note.model,
        "cards": [note_id],
    }


def _answer_note_write(
    collection: Collection, action: str, params: dict[str, Any]
) -> dict[str, Any]:
    note = params.get("note", {})
    match action:
        case "addNote":
            model = collection.models.get(note.get("modelName", ""))
            if model is None or note.get("deckName") not in collection.decks:
                return _error("model or deck was not found")
            fields = {name: note.get("fields", {}).get(name, "") for name in model.fields}
            return _ok(add_note(collection, note["modelName"], fields))
        case "updateNoteFields":
            stored = collection.notes.get(note.get("id"))
            if stored is None:
                return _error("Note was not found")
            stored.fields.update(
                {k: v for k, v in note.get("fields", {}).items() if k in stored.fields}
            )
            return _ok(None)
    return dict(UNSUPPORTED)


def _full_model(name: str, model: Model) -> dict[str, Any]:
    """A model as `findModelsByName` returns it, shaped like the recorded `createModel` result."""
    recorded = anki_fixture("createModel")["response"]["result"]
    fld, tmpl = recorded["flds"][0], recorded["tmpls"][0]
    return {
        **copy.deepcopy(recorded),
        "name": name,
        "flds": [{**fld, "name": n, "ord": i} for i, n in enumerate(model.fields)],
        "tmpls": [
            {**tmpl, "name": card, "ord": i, "qfmt": sides["Front"], "afmt": sides["Back"]}
            for i, (card, sides) in enumerate(model.templates.items())
        ],
        "css": model.css,
    }


def _ok(result: Any) -> dict[str, Any]:
    return {"result": result, "error": None}


def _error(message: str) -> dict[str, Any]:
    return {"result": None, "error": message}


def _answer(collection: Collection, action: str, params: dict[str, Any]) -> dict[str, Any]:
    models, decks = collection.models, collection.decks
    model = models.get(params.get("modelName", ""))
    match action:
        case "version":
            return _ok(6)
        case "deckNames":
            return _ok(sorted(decks))
        case "deckNamesAndIds":
            return _ok({name: i for i, name in enumerate(sorted(decks), start=1)})
        case "modelNames":
            return _ok(sorted(models))
        case "modelNamesAndIds":
            return _ok({name: i for i, name in enumerate(sorted(models), start=1)})
        case "modelFieldNames" | "modelTemplates" | "modelStyling" if model is None:
            return _error(f"model was not found: {params.get('modelName')}")
        case "modelFieldNames":
            return _ok(list(model.fields))
        case "modelTemplates":
            return _ok(copy.deepcopy(model.templates))
        case "modelStyling":
            return _ok({"css": model.css})
        case "findModelsByName":
            names = params.get("modelNames", [])
            if any(name not in models for name in names):
                return _error("model was not found")
            return _ok([_full_model(name, models[name]) for name in names])
        case "getDeckConfig":
            preset = decks.get(params.get("deck", ""))
            # AnkiConnect answers `false` for a deck that doesn't exist
            return _ok(copy.deepcopy(collection.presets[preset]) if preset else False)
        case "findNotes":
            return _ok(_find_notes(collection, params.get("query", "")))
        case "notesInfo":
            notes = collection.notes
            # AnkiConnect answers `{}` for an id it doesn't have
            return _ok(
                [_note_info(i, notes[i]) if i in notes else {} for i in params.get("notes", [])]
            )
        case "findCards":
            return _ok([])  # the simulator holds no cards
        case "cardsInfo":
            return _ok([{} for _ in params.get("cards", [])])
        case "getMediaFilesNames":
            return _ok([])
    return dict(UNSUPPORTED)


def _preset_key(collection: Collection, config_id: Any) -> str | None:
    """The key of the preset whose config has `config_id`."""
    for key, config in collection.presets.items():
        if config["id"] == config_id:
            return key
    return None


def _answer_write(
    collection: Collection, action: str, params: dict[str, Any], *, refuse_save: bool
) -> dict[str, Any]:
    """A write as AnkiConnect v6 answers it (spike 2.2 reply shapes), applied to `collection`."""
    models, decks, presets = collection.models, collection.decks, collection.presets
    match action:
        case "createDeck":
            # Anki creates missing parents too, on the Default preset (config id 1)
            parts = params["deck"].split("::")
            for depth in range(1, len(parts) + 1):
                decks.setdefault("::".join(parts[:depth]), DEFAULT_PRESET)
            return _ok(next(_ids))
        case "createModel":
            name = params["modelName"]
            if name in models:
                return _error("Model name already exists")
            models[name] = Model(
                fields=list(params["inOrderFields"]),
                templates={
                    t["Name"]: {"Front": t["Front"], "Back": t["Back"]}
                    for t in params["cardTemplates"]
                },
                css=params.get("css", ""),
            )
            return _ok(_full_model(name, models[name]))
        case "updateModelTemplates" | "updateModelStyling":
            target = params["model"]
            model = models.get(target.get("name", ""))
            if model is None:
                return _error(f"model was not found: {target.get('name')}")
            if action == "updateModelStyling":
                model.css = target["css"]
                return _ok(None)
            # AnkiConnect updates the card templates that exist and ignores any other name
            for card, sides in target.get("templates", {}).items():
                if card in model.templates:
                    model.templates[card].update(
                        {side: sides[side] for side in ("Front", "Back") if side in sides}
                    )
            return _ok(None)
        case "modelTemplateAdd":
            model = models.get(params.get("modelName", ""))
            template = params["template"]
            if model is None:
                return _error(f"model was not found: {params.get('modelName')}")
            if template["Name"] in model.templates:
                return _error("template name already exists")
            model.templates[template["Name"]] = {
                "Front": template["Front"],
                "Back": template["Back"],
            }
            return _ok(None)
        case "cloneDeckConfigId":
            # Without `cloneFrom` Anki clones config id 1, its Default preset
            clone_from = params.get("cloneFrom")
            source = DEFAULT_PRESET if clone_from is None else _preset_key(collection, clone_from)
            if source is None:
                return _ok(False)
            config = copy.deepcopy(presets[source])
            config["id"] = next(_ids)
            config["name"] = params["name"]
            # Anki allows two presets with one name; the second gets its own key here
            key = (
                config["name"]
                if config["name"] not in presets
                else f"{config['name']}#{config['id']}"
            )
            presets[key] = config
            return _ok(config["id"])
        case "setDeckConfigId":
            key = _preset_key(collection, params.get("configId"))
            targets = params.get("decks", [])
            if key is None or any(deck not in decks for deck in targets):
                return _ok(False)
            for deck in targets:
                decks[deck] = key
            return _ok(True)
        case "saveDeckConfig":
            config = params["config"]
            key = _preset_key(collection, config.get("id"))
            if refuse_save or key is None:
                return _ok(False)  # as spike 2.2 recorded: `false`, error null, nothing saved
            presets[key] = copy.deepcopy(config)
            return _ok(True)
    return dict(UNSUPPORTED)


def collection_replies(
    collection: Collection, *, writes: bool = False, refuse_save: bool = False
) -> dict[str, StubReply]:
    """Replies for `AnkiConnectReplay`: every read in `READ_ACTIONS`, `multi` included.

    `writes=True` also answers `WRITE_ACTIONS` and `NOTE_WRITE_ACTIONS`, changing `collection`.
    `refuse_save=True` makes `saveDeckConfig` answer `false` and save nothing, as it did in
    spike 2.2 (Q5).
    """

    def answer(action: str, params: dict[str, Any]) -> dict[str, Any]:
        if writes and action in WRITE_ACTIONS:
            return _answer_write(collection, action, params, refuse_save=refuse_save)
        if writes and action in NOTE_WRITE_ACTIONS:
            return _answer_note_write(collection, action, params)
        return _answer(collection, action, params)

    def reply_to(action: str) -> Callable[[Any], Any]:
        return lambda body: answer(action, body.get("params", {}))

    def multi(body: Any) -> dict[str, Any]:
        inner = body.get("params", {}).get("actions", [])
        return _ok([answer(a["action"], a.get("params", {})) for a in inner])

    actions = READ_ACTIONS | WRITE_ACTIONS | NOTE_WRITE_ACTIONS if writes else READ_ACTIONS
    replies: dict[str, StubReply] = {action: reply_to(action) for action in actions}
    replies["multi"] = multi
    return replies


def sent_actions(sent: list[Any]) -> list[str]:
    """The v6 action of every request in an `AnkiConnectReplay.sent`, `multi`'s inner ones
    included, in order.
    """
    actions: list[str] = []
    for request in sent:
        body = request.body
        actions.append(body.get("action", body.get("method")))
        if body.get("action") == "multi":
            actions += [a["action"] for a in body.get("params", {}).get("actions", [])]
    return actions


def sent_queries(sent: list[Any]) -> list[str]:
    """Every `query` parameter the adapter sent, `multi`'s inner ones included."""
    bodies = [request.body for request in sent]
    for body in list(bodies):
        if body.get("action") == "multi":
            bodies += body.get("params", {}).get("actions", [])
    return [b["params"]["query"] for b in bodies if "query" in b.get("params", {})]


def sent_writes(sent: list[Any]) -> list[str]:
    """`sent_actions()` without the reads: every write the adapter sent, in order."""
    return [action for action in sent_actions(sent) if action not in READ_ACTIONS]

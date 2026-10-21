"""An Anki collection in memory, answered as AnkiConnect would, for the Setup preview tests.

`managed_collection(manifest)` is a Prefix that Setup has already applied; `stock_collection()`
is an Anki with nothing LanguageLab manages. Tests change one thing in either, then replay it
through `collection_replies()` into an `AnkiConnectReplay`.

The reply shapes are the recorded ones from tests/fixtures/anki/ (spike 2.2): a preset is the
recorded `getDeckConfig` result with its id, name and bury flags replaced, and a full model is
shaped like the recorded `createModel` result. Only reads are answered. A write action gets
AnkiConnect's "unsupported action" error, and the replay's `.sent` shows that it was sent.
"""

import copy
import itertools
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


@dataclass
class Model:
    fields: list[str]
    templates: dict[str, dict[str, str]]  # card name -> {"Front", "Back"}, in ord order
    css: str


@dataclass
class Collection:
    decks: dict[str, str] = field(default_factory=dict)  # deck name -> its preset's name
    presets: dict[str, dict[str, Any]] = field(default_factory=dict)  # name -> deck config
    models: dict[str, Model] = field(default_factory=dict)


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
        case "findNotes" | "findCards":
            return _ok([])  # the simulator holds no notes
        case "notesInfo" | "cardsInfo":
            return _ok([{} for _ in params.get("notes", params.get("cards", []))])
        case "getMediaFilesNames":
            return _ok([])
    return dict(UNSUPPORTED)


def collection_replies(collection: Collection) -> dict[str, StubReply]:
    """Replies for `AnkiConnectReplay`: every read in `READ_ACTIONS`, `multi` included."""

    def reply_to(action: str) -> Callable[[Any], Any]:
        return lambda body: _answer(collection, action, body.get("params", {}))

    def multi(body: Any) -> dict[str, Any]:
        inner = body.get("params", {}).get("actions", [])
        return _ok([_answer(collection, a["action"], a.get("params", {})) for a in inner])

    replies: dict[str, StubReply] = {action: reply_to(action) for action in READ_ACTIONS}
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

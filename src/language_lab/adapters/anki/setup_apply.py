"""The write steps of Setup's apply (FR-6, FR-8, AD-3): plan items into AnkiConnect v6 writes.

`run_plan(invoke, manifest, state, items)` runs every Create and Repair item of a plan diffed
from `state`, in this order, and skips Migrate (adapters/anki/migrations.py runs it after):

1. deck Create: `createDeck`, in manifest order (parents first).
2. note type Create: `createModel` with its fields, CSS and card templates, which covers that
   note type's templates Create too.
3. templates Repair: `updateModelTemplates` for the card templates Anki has, `modelTemplateAdd`
   for a missing one, and `updateModelStyling` for the CSS. An extra card template stays: its
   removal deletes cards, and no repair offers it.
4. the `<Prefix>` preset, when the plan has a preset item or a created deck belongs on it: the
   `<Prefix>` config a preset deck already uses, else a clone of Default (`cloneDeckConfigId`);
   `setDeckConfigId` for the preset decks not on it; then, for a preset item or a fresh clone,
   that config read back with `getDeckConfig`, the three bury flags set off and the rest left
   as it is (FR-8), and `saveDeckConfig`.
5. reading rule Create, in data order: `storeMediaFile` for each example's bundled MP3, by its
   AD-7 name (`media_name(prefix, rule id, bytes)`), then `addNote` of the reading rule note
   type into its deck, every field through the codec, each `Example<n>Audio` as
   `[sound:<name>]`, with its `RuleId` and the manifest's `SchemaVersion`. A store that doesn't
   answer its name skips that rule's note; the other rules go on.

`run_repairs(invoke, items)` runs the opt-in repair rows the user checked (entry 11), after the
plan and its migrations: `deleteMediaFile` for orphan media, `changeDeck` to the expected deck
for a misplaced card, `suspend` for an unsuspended Capture card, one write per row.

Every write is one `invoke` (the client's guarded, ungated path: Setup's apply writes while
the SetupState isn't `ready`), so each step fails alone. A failed step
(an `AppError` from a write, or a `false` answer where AnkiConnect reports success with `true`
or an id) doesn't end the run: the verification that follows reports what didn't take. A read
that fails raises `AppError(ANKI_UNAVAILABLE)`.
"""

import base64
import copy
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any

from language_lab.adapters.anki.codec import encode_field
from language_lab.adapters.anki.guard import is_int
from language_lab.adapters.anki.manifest import CardTemplate, Manifest, NoteType
from language_lab.adapters.anki.setup_diff import AnkiState
from language_lab.domain.audio import media_name
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.reading_rules import ReadingRule
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind

# `invoke(action, **params)`: one guarded, ungated v6 call returning its `result`
type Invoke = Callable[..., Awaitable[Any]]


def _set_path(config: dict[str, Any], path: str, value: Any) -> None:
    """Set a dotted key (`"rev.bury"`), creating any missing parent dict."""
    *parents, leaf = path.split(".")
    node = config
    for key in parents:
        child = node.get(key)
        if not isinstance(child, dict):
            child = node[key] = {}
        node = child
    node[leaf] = value


def _card_template(template: CardTemplate) -> dict[str, str]:
    return {"Name": template.name, "Front": template.front, "Back": template.back}


def _card_templates(note_type: NoteType) -> list[dict[str, str]]:
    return [_card_template(t) for t in note_type.templates]


async def try_write(invoke: Invoke, action: str, **params: Any) -> Any:
    """One write; `None` when it failed (an `AppError`), so the run goes on and verify reports
    it. A `PrefixViolation` propagates.
    """
    try:
        return await invoke(action, **params)
    except AppError:
        return None


class _PlanRun:
    def __init__(self, invoke: Invoke, manifest: Manifest, state: AnkiState) -> None:
        self._invoke = invoke
        self._manifest = manifest
        self._state = state
        self.created_decks: set[str] = set()

    async def _write(self, action: str, **params: Any) -> Any:
        """One write; `None` when it failed (an `AppError`), so the run goes on."""
        return await try_write(self._invoke, action, **params)

    async def create_deck(self, deck: str) -> None:
        if await self._write("createDeck", deck=deck) is not None:
            self.created_decks.add(deck)

    async def create_note_type(self, note_type: NoteType) -> None:
        await self._write(
            "createModel",
            modelName=note_type.name,
            inOrderFields=[f.name for f in note_type.fields],
            css=note_type.css,
            cardTemplates=_card_templates(note_type),
        )

    async def repair_templates(self, note_type: NoteType) -> None:
        model = self._state.managed_models.get(note_type.name)
        existing = model.templates if model is not None else {}
        update = {
            t.name: {"Front": t.front, "Back": t.back}
            for t in note_type.templates
            if t.name in existing
        }
        if update:
            await self._write(
                "updateModelTemplates", model={"name": note_type.name, "templates": update}
            )
        for template in note_type.templates:
            if template.name not in existing:
                await self._write(
                    "modelTemplateAdd",
                    modelName=note_type.name,
                    template=_card_template(template),
                )
        await self._write(
            "updateModelStyling", model={"name": note_type.name, "css": note_type.css}
        )

    async def preset(self, *, has_item: bool) -> None:
        preset = self._manifest.preset
        existing = [d for d in preset.decks if d in self._state.decks or d in self.created_decks]
        if not existing:
            return
        configs = self._state.preset_configs
        ours = [
            configs[d].get("id")
            for d in existing
            if d in configs and configs[d].get("name") == preset.name
        ]
        config_id = ours[0] if ours and is_int(ours[0]) else None
        cloned = False
        if config_id is None:
            config_id = await self._write("cloneDeckConfigId", name=preset.name)
            if not is_int(config_id):
                return  # the preset couldn't be made: verify reports it
            cloned = True
        moving = [d for d in existing if d not in configs or configs[d].get("id") != config_id]
        moved = True
        if moving:
            moved = await self._write("setDeckConfigId", decks=moving, configId=config_id) is True
        # The guard passes the save only once preset.decks[0] is on the config: a failed move
        # skips it, and verify reports the preset
        on_preset = preset.decks[0] not in moving or moved
        if (has_item or cloned) and preset.decks[0] in existing and on_preset:
            await self._save_bury_flags()

    async def _save_bury_flags(self) -> None:
        """Read the preset back, set only its bury flags, and save it (FR-8)."""
        preset = self._manifest.preset
        current = await self._invoke("getDeckConfig", deck=preset.decks[0])  # a read: may raise
        if not isinstance(current, dict):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        config = copy.deepcopy(current)
        for path, value in preset.bury_flags.items():
            _set_path(config, path, value)
        await self._write("saveDeckConfig", config=config)

    async def create_reading_rule(self, rule: ReadingRule) -> None:
        """Store the rule's example audio, then add its note; a failed store skips the note."""
        manifest = self._manifest
        model = manifest.reading_rule_note_type
        fields = {
            "Combination": rule.combination,
            "Transcription": rule.transcription,
            "Note": rule.note,
        }
        for n, example in enumerate(rule.examples, 1):
            name = media_name(manifest.prefix, rule.id, example.audio)
            data = base64.b64encode(example.audio).decode("ascii")
            if await self._write("storeMediaFile", filename=name, data=data) != name:
                return  # verify reports the rule, and the next plan offers it again
            fields |= {f"Example{n}": example.word, f"Example{n}Audio": f"[sound:{name}]"}
        fields |= {"RuleId": rule.id, "SchemaVersion": str(manifest.schema_version)}
        await self._write(
            "addNote",
            note={
                "deckName": manifest.card_deck(model, 0),
                "modelName": model,
                "fields": {name: encode_field(value) for name, value in fields.items()},
                "options": {"allowDuplicate": True},
            },
        )


async def run_plan(
    invoke: Invoke, manifest: Manifest, state: AnkiState, items: tuple[PlanItem, ...]
) -> None:
    """Run every Create and Repair item of `items` (diffed from `state`); skip Migrate."""
    run = _PlanRun(invoke, manifest, state)
    planned: Mapping[tuple[PlanAction, ResourceKind], set[str]] = {
        (action, kind): {i.name for i in items if i.action is action and i.kind is kind}
        for action in PlanAction
        for kind in ResourceKind
    }
    for deck in manifest.decks:
        if deck in planned[PlanAction.CREATE, ResourceKind.DECK]:
            await run.create_deck(deck)
    for note_type in manifest.note_types:
        if note_type.name in planned[PlanAction.CREATE, ResourceKind.NOTE_TYPE]:
            await run.create_note_type(note_type)
    for note_type in manifest.note_types:
        if note_type.name in planned[PlanAction.REPAIR, ResourceKind.TEMPLATES]:
            await run.repair_templates(note_type)
    has_preset_item = any(
        i.kind is ResourceKind.PRESET and i.action is not PlanAction.MIGRATE for i in items
    )
    if has_preset_item or run.created_decks & set(manifest.preset.decks):
        await run.preset(has_item=has_preset_item)
    for rule in manifest.reading_rules:
        if rule.combination in planned[PlanAction.CREATE, ResourceKind.READING_RULE]:
            await run.create_reading_rule(rule)


async def run_repairs(invoke: Invoke, items: Iterable[PlanItem]) -> None:
    """Run each checked opt-in repair row, in order, one write each."""
    for item in items:
        if item.kind is ResourceKind.ORPHAN_MEDIA:
            await try_write(invoke, "deleteMediaFile", filename=item.name)
        elif item.kind is ResourceKind.MISPLACED_CARD:
            expected = item.detail["expectedDeck"]
            await try_write(invoke, "changeDeck", cards=[int(item.name)], deck=expected)
        elif item.kind is ResourceKind.UNSUSPENDED_CARD:
            await try_write(invoke, "suspend", cards=[int(item.name)])

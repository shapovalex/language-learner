"""The write steps of Setup's apply (FR-6, FR-8, AD-3): plan items into AnkiConnect v6 writes.

`run_plan(invoke, manifest, state, items)` runs every Create and Repair item of a plan diffed
from `state`, in this order, and skips Migrate (entry 9):

1. deck Create: `createDeck`, in manifest order (parents first).
2. note type Create: `createModel` with its fields, CSS and card templates, which covers that
   note type's templates Create too.
3. templates Repair: `updateModelTemplates` for the card templates Anki has, `modelTemplateAdd`
   for a missing one, and `updateModelStyling` for the CSS. An extra card template stays (its
   removal deletes cards: entry 11's opt-in repairs).
4. the `<Prefix>` preset, when the plan has a preset item or a created deck belongs on it: the
   `<Prefix>` config a preset deck already uses, else a clone of Default (`cloneDeckConfigId`);
   `setDeckConfigId` for the preset decks not on it; then, for a preset item or a fresh clone,
   that config read back with `getDeckConfig`, the three bury flags set off and the rest left
   as it is (FR-8), and `saveDeckConfig`.

Every write is one `invoke` (the guarded client's), so each step fails alone. A failed step
(an `AppError` from a write, or a `false` answer where AnkiConnect reports success with `true`
or an id) doesn't end the run: the verification that follows reports what didn't take. A read
that fails raises `AppError(ANKI_UNAVAILABLE)`.
"""

import copy
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from language_lab.adapters.anki.manifest import Manifest, NoteType
from language_lab.adapters.anki.setup_diff import AnkiState
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind

# `invoke(action, **params)`: one guarded v6 call returning its `result`
type Invoke = Callable[..., Awaitable[Any]]


def _is_id(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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


def _card_templates(note_type: NoteType) -> list[dict[str, str]]:
    return [{"Name": t.name, "Front": t.front, "Back": t.back} for t in note_type.templates]


class _PlanRun:
    def __init__(self, invoke: Invoke, manifest: Manifest, state: AnkiState) -> None:
        self._invoke = invoke
        self._manifest = manifest
        self._state = state
        self.created_decks: set[str] = set()

    async def _write(self, action: str, **params: Any) -> Any:
        """One write; `None` when it failed (an `AppError`), so the run goes on."""
        try:
            return await self._invoke(action, **params)
        except AppError:
            return None

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
                    template={
                        "Name": template.name,
                        "Front": template.front,
                        "Back": template.back,
                    },
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
        config_id = ours[0] if ours and _is_id(ours[0]) else None
        cloned = False
        if config_id is None:
            config_id = await self._write("cloneDeckConfigId", name=preset.name)
            if not _is_id(config_id):
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

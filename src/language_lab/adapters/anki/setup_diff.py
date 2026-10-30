"""The Setup diff (AD-3): Anki's managed state against the manifest, as plan items.

Pure: `diff(manifest, state)` takes what the adapter read (`AnkiState`) and returns the
`SetupPreview`. Items go in kind order (deck, noteType, notes, templates, preset, readingRule),
each kind in manifest order.

- Create: a missing deck, note type (with its templates and CSS), or `<Prefix>` preset, and
  each seeded French reading rule (`manifest.reading_rules`, in data order) no note of the
  reading rule note type holds by its decoded `RuleId`. Setup only creates them: a rule note
  that differs from the data is the user's, and none is ever updated or deleted. None is offered
  while that note type's fields differ from the manifest's (its Migrate row comes first):
  `addNote` would drop the fields Anki lacks, `RuleId` included.
- Repair: a note type's card templates or CSS that differ from the files (a changed, missing
  or extra card template, or changed CSS), or the preset with a bury flag on, an existing
  preset deck not on it, or preset decks split across two configs named `<Prefix>`. Other
  deck options are the user's and never show up (FR-8).
- Migrate: an existing note type whose fields differ, order included (a schema change), and
  the notes of each manifest note type holding a note below the manifest's SchemaVersion
  (empty or not an integer included): their SchemaVersion is rewritten (entry 9).

Decks under the Prefix and note types named `<Prefix> …` that the manifest doesn't declare are
`unmanaged`: listed, never planned.

Opt-in repairs (entry 11) go in `repairs`, one row per resource, never in `items`: orphan
media (an AD-7 media name no managed note's decoded `Audio` or `Example<n>Audio` holds as
`[sound:<name>]` and no reading rule Create row of the same diff stores), sorted by name; then
each managed card in a deck other than `manifest.card_deck(note type, ord)`; then each
unsuspended Capture card; cards by id. Only manifest note types' cards count, and a card whose
ord its note type doesn't declare isn't offered.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from language_lab.adapters.anki.guard import media_pattern
from language_lab.adapters.anki.manifest import Manifest, NoteType
from language_lab.domain.audio import media_name
from language_lab.domain.reading_rules import ReadingRule
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupPreview, Unmanaged

_MISSING = object()


@dataclass(frozen=True)
class ModelState:
    fields: tuple[str, ...]
    templates: Mapping[str, tuple[str, str]]  # card name -> (Front, Back)
    css: str


@dataclass(frozen=True)
class CardState:
    """A card of a manifest note type, from `cardsInfo`."""

    id: int
    model: str
    ord: int
    deck: str
    suspended: bool


@dataclass(frozen=True)
class AnkiState:
    decks: frozenset[str]  # every deck name in Anki
    models: frozenset[str]  # every note type name in Anki
    managed_models: Mapping[str, ModelState] = field(default_factory=dict)  # manifest ones only
    preset_configs: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)  # deck -> config
    # manifest note type -> (note id, stored SchemaVersion or None when not an integer)
    note_versions: Mapping[str, tuple[tuple[int, int | None], ...]] = field(default_factory=dict)
    cards: tuple[CardState, ...] = ()  # every card of a manifest note type
    media: frozenset[str] = frozenset()  # media file names matching `<prefix lowercased>_*`
    # names in managed notes' decoded audio fields' `[sound:]` tags
    audio: frozenset[str] = frozenset()
    reading_rules: frozenset[str] = frozenset()  # the decoded RuleIds of the reading rule notes


def _dotted(config: Mapping[str, Any], path: str) -> Any:
    node: Any = config
    for key in path.split("."):
        if not isinstance(node, Mapping) or key not in node:
            return _MISSING
        node = node[key]
    return node


def _templates_differ(note_type: NoteType, model: ModelState) -> bool:
    expected = {t.name: (t.front, t.back) for t in note_type.templates}
    return dict(model.templates) != expected or model.css != note_type.css


def _preset_item(manifest: Manifest, state: AnkiState) -> PlanItem | None:
    preset = manifest.preset
    configs = [state.preset_configs[d] for d in preset.decks if d in state.preset_configs]
    ours = [c for c in configs if c.get("name") == preset.name]
    if not ours:
        return PlanItem(PlanAction.CREATE, ResourceKind.PRESET, preset.name)
    flags_off = all(
        _dotted(c, path) == value for c in ours for path, value in preset.bury_flags.items()
    )
    one_preset = len({c.get("id") for c in ours}) == 1
    if len(ours) != len(configs) or not one_preset or not flags_off:
        return PlanItem(PlanAction.REPAIR, ResourceKind.PRESET, preset.name)
    return None


def _is_under_prefix_deck(prefix: str, deck: str) -> bool:
    return deck == prefix or deck.startswith(f"{prefix}::")


def _repairs(manifest: Manifest, state: AnkiState, created: list[ReadingRule]) -> list[PlanItem]:
    media = media_pattern(manifest.prefix)
    # A rule Create re-stores its media under the same names: deleting them would strip it
    stored = {
        media_name(manifest.prefix, rule.id, example.audio)
        for rule in created
        for example in rule.examples
    }
    orphans = [
        PlanItem(PlanAction.REPAIR, ResourceKind.ORPHAN_MEDIA, name)
        for name in sorted(state.media)
        if media.fullmatch(name) is not None and name not in state.audio | stored
    ]
    note_types = {nt.name: nt for nt in manifest.note_types}
    misplaced: list[PlanItem] = []
    unsuspended: list[PlanItem] = []
    for card in sorted(state.cards, key=lambda c: c.id):
        note_type = note_types.get(card.model)
        if note_type is None:
            continue  # not a manifest note type: read-only
        template = next((t for t in note_type.templates if t.ord == card.ord), None)
        if template is None:
            continue  # a card template the manifest doesn't declare: not this story's repair
        where = {"noteType": card.model, "card": template.name, "deck": card.deck}
        expected = manifest.card_deck(card.model, card.ord)
        if card.deck != expected:
            misplaced.append(
                PlanItem(
                    PlanAction.REPAIR,
                    ResourceKind.MISPLACED_CARD,
                    str(card.id),
                    {**where, "expectedDeck": expected},
                )
            )
        if note_type.language is None and not card.suspended:
            unsuspended.append(
                PlanItem(PlanAction.REPAIR, ResourceKind.UNSUSPENDED_CARD, str(card.id), where)
            )
    return [*orphans, *misplaced, *unsuspended]


def _created_rules(manifest: Manifest, state: AnkiState) -> list[ReadingRule]:
    """The seeded rules no note holds, in data order; none while the reading rule note type
    exists with fields other than the manifest's.
    """
    name = manifest.reading_rule_note_type
    note_type = next(nt for nt in manifest.note_types if nt.name == name)
    model = state.managed_models.get(name)
    if name in state.models and model is not None:
        if model.fields != tuple(f.name for f in note_type.fields):
            return []
    return [rule for rule in manifest.reading_rules if rule.id not in state.reading_rules]


def diff(manifest: Manifest, state: AnkiState) -> SetupPreview:
    decks = [
        PlanItem(PlanAction.CREATE, ResourceKind.DECK, deck)
        for deck in manifest.decks
        if deck not in state.decks
    ]
    note_types: list[PlanItem] = []
    templates: list[PlanItem] = []
    for note_type in manifest.note_types:
        model = state.managed_models.get(note_type.name)
        if note_type.name not in state.models or model is None:
            note_types.append(PlanItem(PlanAction.CREATE, ResourceKind.NOTE_TYPE, note_type.name))
            templates.append(PlanItem(PlanAction.CREATE, ResourceKind.TEMPLATES, note_type.name))
            continue
        if model.fields != tuple(f.name for f in note_type.fields):
            note_types.append(PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, note_type.name))
        if _templates_differ(note_type, model):
            templates.append(PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, note_type.name))
    notes = [
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTES, note_type.name)
        for note_type in manifest.note_types
        if any(
            v is None or v < manifest.schema_version
            for _, v in state.note_versions.get(note_type.name, ())
        )
    ]
    preset = _preset_item(manifest, state)

    prefix = manifest.prefix
    managed_types = {nt.name for nt in manifest.note_types}
    unmanaged = [
        Unmanaged(ResourceKind.DECK, deck)
        for deck in sorted(state.decks)
        if _is_under_prefix_deck(prefix, deck) and deck not in manifest.decks
    ] + [
        Unmanaged(ResourceKind.NOTE_TYPE, model)
        for model in sorted(state.models)
        if model.startswith(f"{prefix} ") and model not in managed_types
    ]
    created = _created_rules(manifest, state)
    rules = [
        PlanItem(PlanAction.CREATE, ResourceKind.READING_RULE, rule.combination) for rule in created
    ]
    items = [*decks, *note_types, *notes, *templates, *([preset] if preset else []), *rules]
    return SetupPreview(
        items=tuple(items),
        unmanaged=tuple(unmanaged),
        repairs=tuple(_repairs(manifest, state, created)),
    )

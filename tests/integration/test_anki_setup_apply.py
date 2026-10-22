"""Story 2.7: the adapter applies the confirmed plan and verifies it (FR-6, FR-8, AD-3, AD-4).

`AnkiConnectStore.setup_apply(plan_hash)` is one use case under one hold of the Anki lock:

1. It reads and diffs again, and refuses a hash the fresh plan no longer has
   (`AppError(PLAN_CHANGED)`) before any write.
2. It runs every Create and Repair item through the guarded client. Migrate items wait for
   entry 9 (decided with the user, 2026-10-21).
3. It verifies by a fresh diff and returns that `SetupPreview`. Its items are the
   discrepancies.

The `<Prefix>` preset gets only its three bury flags set off; every other deck option is the
user's (FR-8). Spike 2.2 saw `saveDeckConfig` answer `false` and save nothing. Decided with the
user (2026-10-21): that is a failed step, the run goes on, and verify reports it.

Anki is the in-memory collection in tests/support/anki_state.py, answering reads and, with
`writes=True`, the writes apply sends, in the reply shapes recorded in tests/fixtures/anki/.
"""

import copy
from collections.abc import Callable, Mapping
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard, PrefixViolation
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest, build_manifest
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.setup import plan_hash
from tests.support.aio import settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import (
    DEFAULT_DECK,
    DEFAULT_PRESET,
    READ_ACTIONS,
    Collection,
    apply_manifest,
    collection_replies,
    managed_collection,
    sent_writes,
    set_path,
    stock_collection,
)
from tests.support.setup_collections import (
    MANIFEST,
    PREFIX,
    STUDY_LEAF,
    VOCABULARY,
    as_tuples,
    bury_flag_on,
    changed_css,
    changed_front,
    deck_on_default,
    field_removed,
    from_set_up,
    missing_card_template,
    missing_deck,
    missing_note_type,
    no_preset,
    two_prefix_presets,
    user_options,
)

DEV = "LanguageLabDev"
DEV_MANIFEST = build_manifest(DEV)

BURY_FLAGS: Mapping[str, bool] = MANIFEST.preset.bury_flags  # dotted path -> the value Setup sets

_MISSING = object()


def store_for(
    collection: Collection,
    *,
    manifest: Manifest = MANIFEST,
    guard: PrefixGuard | None = None,
    unguarded: bool = False,
    refuse_save: bool = False,
) -> tuple[AnkiConnectStore, AnkiConnectReplay]:
    """The real store over `collection`, through a client guarded by `guard` (by default the
    manifest's own `PrefixGuard`; none at all with `unguarded`).
    """
    replay = AnkiConnectReplay(collection_replies(collection, writes=True, refuse_save=refuse_save))
    if not unguarded and guard is None:
        guard = PrefixGuard(manifest)
    client = AnkiConnectClient(ANKI_URL, transport=replay.transport, guard=guard)
    return AnkiConnectStore(client, AnkiLock(), manifest=manifest), replay


def apply(collection: Collection, **options: Any) -> tuple[Any, list[Any]]:
    """Preview `collection`, then apply that plan's hash, as the user confirming it does.

    Returns the apply's outcome (the verification, or the exception) and everything sent.
    """
    store, replay = store_for(collection, **options)

    async def confirm_and_apply() -> Any:
        preview = await store.setup_preview()
        return await store.setup_apply(plan_hash(preview.items))

    return settle(confirm_and_apply()), replay.sent


def preview_items(collection: Collection) -> set[tuple[str, str, str]]:
    """A fresh preview of `collection`, as the user coming back to Setup sees it."""
    store, _ = store_for(collection)
    return as_tuples(settle(store.setup_preview()).items)


def dotted(config: Mapping[str, Any], path: str) -> Any:
    node: Any = config
    for key in path.split("."):
        if not isinstance(node, Mapping) or key not in node:
            return _MISSING
        node = node[key]
    return node


def without(config: Mapping[str, Any], paths: tuple[str, ...]) -> dict[str, Any]:
    """`config` without the keys at the dotted `paths`."""
    trimmed = copy.deepcopy(dict(config))
    for path in paths:
        *parents, leaf = path.split(".")
        node: Any = trimmed
        for key in parents:
            node = node.get(key, {})
        node.pop(leaf, None)
    return trimmed


def presets_named(collection: Collection, name: str) -> list[tuple[str, dict[str, Any]]]:
    """Every preset whose config is named `name`, with its key in the collection."""
    return [(key, c) for key, c in collection.presets.items() if c["name"] == name]


def under_prefix(collection: Collection, prefix: str) -> dict[str, Any]:
    """Everything of the collection under `prefix`, exactly as AD-4 scopes it, to compare."""
    decks = {
        d: p for d, p in collection.decks.items() if d == prefix or d.startswith(f"{prefix}::")
    }
    models = {n: m for n, m in collection.models.items() if n.startswith(f"{prefix} ")}
    presets = dict(presets_named(collection, prefix))
    return copy.deepcopy({"decks": decks, "models": models, "presets": presets})


@pytest.mark.p0
def test_apply_refuses_a_stale_plan_hash_before_any_write() -> None:
    """AC-1: a plan hash the fresh diff no longer has is `plan_changed`, and nothing is written."""
    collection = stock_collection()
    store, replay = store_for(collection)

    async def anki_changes_after_the_preview() -> Any:
        preview = await store.setup_preview()
        collection.decks[f"{PREFIX}::Study"] = DEFAULT_PRESET  # made in Anki Desktop meanwhile
        return await store.setup_apply(plan_hash(preview.items))

    outcome = settle(anki_changes_after_the_preview())

    assert getattr(outcome, "code", None) == "plan_changed"
    assert sent_writes(replay.sent) == []
    assert set(collection.decks) == {DEFAULT_DECK, f"{PREFIX}::Study"}
    assert not any(name.startswith(f"{PREFIX} ") for name in collection.models)


# label -> (the collection before apply, the verification's items after it): each change to a
# set-up Prefix (tests/support/setup_collections.py) is one apply can put right
APPLY_CASES: dict[str, tuple[Callable[[], Collection], set[tuple[str, str, str]]]] = {
    "empty-prefix": (stock_collection, set()),
    "empty-prefix-beside-dev": (
        lambda: apply_manifest(stock_collection(), DEV_MANIFEST),
        set(),
    ),
} | {
    label: (from_set_up(change), expected)
    for label, change, expected in [
        ("changed-template", changed_front, set()),
        ("changed-css", changed_css, set()),
        ("missing-card-template", missing_card_template, set()),
        ("missing-deck", missing_deck, set()),
        ("missing-note-type", missing_note_type, set()),
        ("bury-flag-on", bury_flag_on, set()),
        ("deck-on-default-preset", deck_on_default, set()),
        ("no-preset", no_preset, set()),
        ("two-prefix-presets", two_prefix_presets, set()),
        ("user-deck-options", user_options, set()),
        # Migrate waits for entry 9: apply skips it, so verify still shows it
        ("field-removed", field_removed, {("migrate", "noteType", VOCABULARY)}),
    ]
}


@pytest.mark.p0
@pytest.mark.parametrize(("build", "expected"), APPLY_CASES.values(), ids=APPLY_CASES.keys())
def test_apply_runs_the_plan_and_verifies_it_with_a_fresh_diff(
    build: Callable[[], Collection], expected: set[tuple[str, str, str]]
) -> None:
    """AC-2: after apply, verify finds nothing left but Migrate, and a second preview agrees."""
    collection = build()

    outcome, _ = apply(collection)

    assert as_tuples(outcome.items) == expected
    assert len(outcome.items) == len(expected)
    assert preview_items(collection) == expected
    assert outcome.unmanaged == ()


class SpyGuard(PrefixGuard):
    """The manifest's guard, recording every action it was asked about (`multi` unpacked)."""

    def __init__(self, manifest: Manifest) -> None:
        super().__init__(manifest)
        self.checked: list[str] = []

    async def check(self, action: Any, params: Mapping[str, Any], lookup: Any) -> None:
        if action != "multi":
            self.checked.append(action)
        await super().check(action, params, lookup)


@pytest.mark.p0
def test_apply_writes_only_through_the_prefix_guard() -> None:
    """AC-3: every write apply sends went through the guard, and Dev beside it is untouched."""
    collection = apply_manifest(stock_collection(), DEV_MANIFEST)
    dev_before = under_prefix(collection, DEV)
    guard = SpyGuard(MANIFEST)

    outcome, sent = apply(collection, guard=guard)

    checked_writes = [action for action in guard.checked if action not in READ_ACTIONS]
    assert checked_writes == sent_writes(sent) != []
    assert under_prefix(collection, DEV) == dev_before
    assert outcome.items == ()
    # Without a guard the client sends reads only, so the same apply can't write at all
    bare = stock_collection()
    bare_outcome, bare_sent = apply(bare, unguarded=True)
    assert isinstance(bare_outcome, PrefixViolation)
    assert sent_writes(bare_sent) == []


def _preset_repair() -> tuple[Collection, dict[str, Any]]:
    """A set-up Prefix whose preset has a flag on and the user's own options, one Study deck on
    Default, and Default changed by the user too. Returns it and the preset's config before.
    """
    collection = managed_collection(MANIFEST)
    ours = collection.presets[PREFIX]
    user_options = {"rev.bury": True, "new.perDay": 50, "lapse.leechFails": 3, "maxTaken": 30}
    for path, value in user_options.items():
        set_path(ours, path, value)
    collection.decks[STUDY_LEAF] = DEFAULT_PRESET
    set_path(collection.presets[DEFAULT_PRESET], "new.perDay", 99)
    return collection, copy.deepcopy(ours)


def _preset_create() -> tuple[Collection, dict[str, Any]]:
    """An empty Prefix whose Default preset the user changed, a bury flag included. Returns it
    and Default's config, which the new preset is cloned from.
    """
    collection = stock_collection()
    default = collection.presets[DEFAULT_PRESET]
    for path, value in {"rev.bury": True, "new.perDay": 99, "desiredRetention": 0.85}.items():
        set_path(default, path, value)
    return collection, copy.deepcopy(default)


# Keys Anki or apply may set on the preset itself; every other key must stay as it was
PRESET_OWN_KEYS = ("id", "name", "mod", "usn", *BURY_FLAGS)


@pytest.mark.p0
@pytest.mark.parametrize("build", [_preset_repair, _preset_create], ids=["repair", "create"])
def test_apply_sets_only_the_bury_flags_and_assigns_the_preset_to_managed_decks(
    build: Callable[[], tuple[Collection, dict[str, Any]]],
) -> None:
    """AC-4: the `<Prefix>` preset has the three bury flags off and every other option as before,
    is on every Study and Pronunciation deck, and Default and the other decks are untouched.
    """
    collection, options_before = build()
    default_before = copy.deepcopy(collection.presets[DEFAULT_PRESET])

    apply(collection)

    ours = presets_named(collection, PREFIX)
    key, preset = ours[0] if ours else ("", {})
    assert {path: dotted(preset, path) for path in BURY_FLAGS} == dict(BURY_FLAGS)
    assert len(ours) == 1
    assert without(preset, PRESET_OWN_KEYS) == without(options_before, PRESET_OWN_KEYS)
    assert {deck: collection.decks[deck] for deck in MANIFEST.preset.decks} == {
        deck: key for deck in MANIFEST.preset.decks
    }
    assert collection.presets[DEFAULT_PRESET] == default_before
    others = [deck for deck in MANIFEST.decks if deck not in MANIFEST.preset.decks]
    assert {deck: collection.decks[deck] for deck in others} == {
        deck: DEFAULT_PRESET for deck in others
    }


@pytest.mark.p1
def test_a_refused_preset_save_is_reported_by_verify_and_the_rest_still_applies() -> None:
    """AC-5: `saveDeckConfig` answering `false` (spike 2.2) leaves the preset as the one
    discrepancy; the template repair in the same plan still lands.
    """
    collection = managed_collection(MANIFEST)
    set_path(collection.presets[PREFIX], "rev.bury", True)
    changed_front(collection)
    produce = next(
        t
        for nt in MANIFEST.note_types
        if nt.name == VOCABULARY
        for t in nt.templates
        if t.name == "Produce"
    )

    outcome, sent = apply(collection, refuse_save=True)

    assert as_tuples(outcome.items) == {("repair", "preset", PREFIX)}
    assert collection.models[VOCABULARY].templates["Produce"]["Front"] == produce.front
    assert "saveDeckConfig" in sent_writes(sent)
    assert dotted(collection.presets[PREFIX], "rev.bury") is True


@pytest.mark.p1
def test_a_refused_preset_move_skips_the_save_and_verify_reports_the_preset() -> None:
    """AC-5: `setDeckConfigId` answering `false` leaves the decks on Default; the save, which the
    guard would refuse, isn't sent, and verify reports the preset instead of the run failing.
    """
    collection = managed_collection(MANIFEST)
    no_preset(collection)
    replies = collection_replies(collection, writes=True)
    replies["setDeckConfigId"] = {"result": False, "error": None}
    replay = AnkiConnectReplay(replies)
    client = AnkiConnectClient(ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST))
    store = AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST)

    async def confirm_and_apply() -> Any:
        preview = await store.setup_preview()
        return await store.setup_apply(plan_hash(preview.items))

    outcome = settle(confirm_and_apply())

    assert as_tuples(outcome.items) == {("create", "preset", PREFIX)}
    assert "setDeckConfigId" in sent_writes(replay.sent)
    assert "saveDeckConfig" not in sent_writes(replay.sent)

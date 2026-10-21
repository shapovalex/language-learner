"""Story 2.6: the adapter reads the managed state and diffs it against the manifest (AD-3).

`AnkiConnectStore(client, lock, manifest=...).setup_preview()` reads, under the Anki lock, the
note types (fields, templates, CSS), the decks, which preset each managed deck uses and that
preset's bury flags. It diffs them against the manifest into plan items (domain/setup.py):

- Create: a deck, note type, note type's templates and CSS, or the `<Prefix>` preset that
  doesn't exist. An empty Prefix previews 28 decks, 5 note types, 5 sets of templates and CSS,
  and the preset.
- Repair: a note type's templates or CSS that differ from the files, or a preset with a bury
  flag on or a Study or Pronunciation deck not using it. Other deck options are the user's
  (FR-8) and never show up.
- Migrate: an existing note type whose fields differ from the manifest (decided with the user,
  2026-10-21: field changes are schema changes; entry 9 makes them runnable).

Decks under the Prefix and note types named `<Prefix> …` that the manifest doesn't declare are
listed as `unmanaged`, read-only, and never become plan items. A preview sends no write.

Anki is the in-memory collection in tests/support/anki_state.py, which answers with the reply
shapes recorded in tests/fixtures/anki/ (spike 2.2).

Skipped until the preview exists. Un-skip a test, watch it fail, then implement. Hoist the
imports once it's green.
"""

from collections.abc import Callable
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest, build_manifest
from language_lab.adapters.anki.store import AnkiConnectStore
from tests.support.aio import settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import (
    DEFAULT_PRESET,
    READ_ACTIONS,
    Collection,
    Model,
    apply_manifest,
    collection_replies,
    managed_collection,
    preset_config,
    sent_actions,
    sent_queries,
    set_path,
    stock_collection,
)

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.6: un-skip with AnkiStore.setup_preview and the diff"
)

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)

VOCABULARY = f"{PREFIX} English Vocabulary"
SENTENCE = f"{PREFIX} French Sentence"
STUDY_LEAF = f"{PREFIX}::Study::English::Vocabulary::Produce"


def preview(collection: Collection, manifest: Manifest = MANIFEST) -> tuple[Any, list[Any]]:
    """`setup_preview()` against `collection`; returns the outcome and what was sent."""
    replay = AnkiConnectReplay(collection_replies(collection))
    client = AnkiConnectClient(ANKI_URL, transport=replay.transport)
    store = AnkiConnectStore(client, AnkiLock(), manifest=manifest)
    return settle(store.setup_preview()), replay.sent


def as_tuples(items: Any) -> set[tuple[str, str, str]]:
    return {(str(item.action), str(item.kind), item.name) for item in items}


# One change to a set-up Prefix, then the plan items it must preview
def _changed_front(c: Collection) -> None:
    c.models[VOCABULARY].templates["Produce"]["Front"] += "<hr>"


def _changed_css(c: Collection) -> None:
    c.models[SENTENCE].css += "\n.card { color: red; }"


def _missing_card_template(c: Collection) -> None:
    del c.models[VOCABULARY].templates["Pronounce"]


def _missing_deck(c: Collection) -> None:
    del c.decks[STUDY_LEAF]


def _missing_note_type(c: Collection) -> None:
    del c.models[f"{PREFIX} Capture"]


def _bury_flag_on(c: Collection) -> None:
    set_path(c.presets[PREFIX], "rev.bury", True)


def _deck_on_default(c: Collection) -> None:
    c.decks[STUDY_LEAF] = DEFAULT_PRESET


def _no_preset(c: Collection) -> None:
    del c.presets[PREFIX]
    for deck, preset in c.decks.items():
        if preset == PREFIX:
            c.decks[deck] = DEFAULT_PRESET


def _field_removed(c: Collection) -> None:
    c.models[VOCABULARY].fields.remove("Mnemonic")


def _field_added(c: Collection) -> None:
    c.models[SENTENCE].fields.append("Extra")


def _user_options(c: Collection) -> None:
    for path, value in {"new.perDay": 50, "rev.maxIvl": 3650, "desiredRetention": 0.85}.items():
        set_path(c.presets[PREFIX], path, value)


def _dev_prefix_set_up(c: Collection) -> None:
    apply_manifest(c, build_manifest(DEV))


def _empty_prefix_expected() -> set[tuple[str, str, str]]:
    return (
        {("create", "deck", deck) for deck in MANIFEST.decks}
        | {("create", "noteType", nt.name) for nt in MANIFEST.note_types}
        | {("create", "templates", nt.name) for nt in MANIFEST.note_types}
        | {("create", "preset", PREFIX)}
    )


CASES: dict[str, tuple[Callable[[], Collection], set[tuple[str, str, str]]]] = {
    "empty-prefix": (stock_collection, _empty_prefix_expected()),
    "empty-prefix-beside-dev": (
        lambda: apply_manifest(stock_collection(), build_manifest(DEV)),
        _empty_prefix_expected(),
    ),
    "set-up": (lambda: managed_collection(MANIFEST), set()),
}


def _from_set_up(change: Callable[[Collection], None]) -> Callable[[], Collection]:
    def build() -> Collection:
        collection = managed_collection(MANIFEST)
        change(collection)
        return collection

    return build


CASES |= {
    label: (_from_set_up(change), expected)
    for label, change, expected in [
        ("changed-template", _changed_front, {("repair", "templates", VOCABULARY)}),
        ("changed-css", _changed_css, {("repair", "templates", SENTENCE)}),
        ("missing-card-template", _missing_card_template, {("repair", "templates", VOCABULARY)}),
        ("missing-deck", _missing_deck, {("create", "deck", STUDY_LEAF)}),
        (
            "missing-note-type",
            _missing_note_type,
            {
                ("create", "noteType", f"{PREFIX} Capture"),
                ("create", "templates", f"{PREFIX} Capture"),
            },
        ),
        ("bury-flag-on", _bury_flag_on, {("repair", "preset", PREFIX)}),
        ("deck-on-default-preset", _deck_on_default, {("repair", "preset", PREFIX)}),
        ("no-preset", _no_preset, {("create", "preset", PREFIX)}),
        ("field-removed", _field_removed, {("migrate", "noteType", VOCABULARY)}),
        ("field-added", _field_added, {("migrate", "noteType", SENTENCE)}),
        ("user-deck-options", _user_options, set()),
        ("dev-prefix-beside", _dev_prefix_set_up, set()),
    ]
}


@RED_PHASE
@pytest.mark.p0
def test_preview_sends_only_reads_and_exact_scope_queries() -> None:
    """AC-5: a preview reads the managed state with reads only; no write action is sent."""
    collection = managed_collection(MANIFEST)
    collection.models[VOCABULARY].templates["Produce"]["Front"] += "<hr>"
    collection.decks[f"{PREFIX}::Old"] = DEFAULT_PRESET

    outcome, sent = preview(collection)

    assert [action for action in sent_actions(sent) if action not in READ_ACTIONS] == []
    assert not isinstance(outcome, Exception), outcome
    assert as_tuples(outcome.items) == {("repair", "templates", VOCABULARY)}
    exact = [f'deck:"{d}"' for d in MANIFEST.decks] + [
        f'note:"{nt.name}"' for nt in MANIFEST.note_types
    ]
    assert [q for q in sent_queries(sent) if not set(q.split(" ")) <= set(exact)] == []


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize("case", list(CASES))
def test_preview_diffs_the_manifest_into_create_repair_and_migrate_items(case: str) -> None:
    """AC-6: each difference from the manifest previews exactly its Create, Repair or Migrate."""
    build, expected = CASES[case]

    outcome, _ = preview(build())

    assert not isinstance(outcome, Exception), outcome
    assert as_tuples(outcome.items) == expected
    assert len(outcome.items) == len(expected)  # no item listed twice


@RED_PHASE
@pytest.mark.p1
def test_unrecognized_content_under_the_prefix_is_listed_read_only() -> None:
    """AC-8: unknown decks and note types under the Prefix are unmanaged, never plan items."""
    from language_lab.domain.setup import plan_hash

    collection = managed_collection(MANIFEST)
    collection.decks |= {
        f"{PREFIX}::Old stuff": DEFAULT_PRESET,
        f"{PREFIX}::Study::English::Idioms": PREFIX,
        f"{PREFIX}Archive": DEFAULT_PRESET,  # another name, not under the Prefix
    }
    collection.models[f"{PREFIX} Spanish Vocabulary"] = Model(["Front"], {}, "")
    collection.presets["Mine"] = preset_config("Mine")
    apply_manifest(collection, build_manifest(DEV))

    outcome, sent = preview(collection)

    assert not isinstance(outcome, Exception), outcome
    assert {(str(u.kind), u.name) for u in outcome.unmanaged} == {
        ("deck", f"{PREFIX}::Old stuff"),
        ("deck", f"{PREFIX}::Study::English::Idioms"),
        ("noteType", f"{PREFIX} Spanish Vocabulary"),
    }
    assert as_tuples(outcome.items) == set()
    clean, _ = preview(managed_collection(MANIFEST))
    assert plan_hash(outcome.items) == plan_hash(clean.items)
    assert [action for action in sent_actions(sent) if action not in READ_ACTIONS] == []

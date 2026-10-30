"""Story 2.6: the adapter reads the managed state and diffs it against the manifest (AD-3).

`AnkiConnectStore(client, lock, manifest=...).setup_preview()` reads, under the Anki lock, the
note types (fields, templates, CSS), the decks, which preset each managed deck uses and that
preset's bury flags. It diffs them against the manifest into plan items (domain/setup.py):

- Create: a deck, note type, note type's templates and CSS, or the `<Prefix>` preset that
  doesn't exist, and each seeded French reading rule no note holds by its `RuleId`. An empty
  Prefix previews 29 decks, 6 note types, 6 sets of templates and CSS, the preset and 46
  reading rules.
- Repair: a note type's templates or CSS that differ from the files, or a preset with a bury
  flag on or a Study or Pronunciation deck not using it. Other deck options are the user's
  (FR-8) and never show up.
- Migrate: an existing note type whose fields differ from the manifest (decided with the user,
  2026-10-21: field changes are schema changes; entry 9 makes them runnable).

Decks under the Prefix and note types named `<Prefix> …` that the manifest doesn't declare are
listed as `unmanaged`, read-only, and never become plan items. A preview sends no write.

Anki is the in-memory collection in tests/support/anki_state.py, which answers with the reply
shapes recorded in tests/fixtures/anki/ (spike 2.2).
"""

from collections.abc import Callable
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest, build_manifest
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.setup import plan_hash
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
    stock_collection,
)
from tests.support.setup_collections import (
    DELETED_RULE,
    MANIFEST,
    PREFIX,
    SENTENCE,
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
    rule_deleted,
    two_prefix_presets,
    user_options,
)

DEV = "LanguageLabDev"


def preview(collection: Collection, manifest: Manifest = MANIFEST) -> tuple[Any, list[Any]]:
    """`setup_preview()` against `collection`; returns the outcome and what was sent."""
    replay = AnkiConnectReplay(collection_replies(collection))
    client = AnkiConnectClient(ANKI_URL, transport=replay.transport)
    store = AnkiConnectStore(client, AnkiLock(), manifest=manifest)
    return settle(store.setup_preview()), replay.sent


# One change to a set-up Prefix, then the plan items it must preview
def _field_added(c: Collection) -> None:
    c.models[SENTENCE].fields.append("Extra")


def _fields_reordered(c: Collection) -> None:
    fields = c.models[VOCABULARY].fields
    fields[0], fields[1] = fields[1], fields[0]


def _extra_card_template(c: Collection) -> None:
    c.models[SENTENCE].templates["Card 5"] = {"Front": "{{Target}}", "Back": "{{Russian}}"}


# cards.css and an Understand front as v0.5.0 shipped them, before story 4.4's Studio look
V0_5_0_CSS = (
    "/* Working styles for the managed note types; "
    "epic-capture-to-item owns the final look. */\n"
    """.card {
  font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 22px;
  line-height: 1.4;
  text-align: center;
  color: #1f1f1f;
  background-color: #ffffff;
}

.card.nightMode,
.nightMode .card {
  color: #e8e8e8;
  background-color: #1f1f1f;
}

.prompt {
  font-size: 28px;
}

.hint,
.meta,
.note {
  font-size: 16px;
  opacity: 0.75;
}

.example {
  margin-top: 12px;
  font-style: italic;
}
"""
)
V0_5_0_UNDERSTAND_FRONT = '<div class="prompt">{{Target}}</div>\n{{Audio}}\n'


def _v0_5_0_templates(c: Collection) -> None:
    for nt in MANIFEST.note_types:
        model = c.models[nt.name]
        model.css = V0_5_0_CSS
        if "Understand" in model.templates:
            model.templates["Understand"]["Front"] = V0_5_0_UNDERSTAND_FRONT


def _dev_prefix_set_up(c: Collection) -> None:
    apply_manifest(c, build_manifest(DEV))


def _empty_prefix_expected() -> set[tuple[str, str, str]]:
    return (
        {("create", "deck", deck) for deck in MANIFEST.decks}
        | {("create", "noteType", nt.name) for nt in MANIFEST.note_types}
        | {("create", "templates", nt.name) for nt in MANIFEST.note_types}
        | {("create", "preset", PREFIX)}
        | {("create", "readingRule", rule.combination) for rule in MANIFEST.reading_rules}
    )


CASES: dict[str, tuple[Callable[[], Collection], set[tuple[str, str, str]]]] = {
    "empty-prefix": (stock_collection, _empty_prefix_expected()),
    "empty-prefix-beside-dev": (
        lambda: apply_manifest(stock_collection(), build_manifest(DEV)),
        _empty_prefix_expected(),
    ),
    "set-up": (lambda: managed_collection(MANIFEST), set()),
}


CASES |= {
    label: (from_set_up(change), expected)
    for label, change, expected in [
        ("changed-template", changed_front, {("repair", "templates", VOCABULARY)}),
        ("changed-css", changed_css, {("repair", "templates", SENTENCE)}),
        ("missing-card-template", missing_card_template, {("repair", "templates", VOCABULARY)}),
        ("missing-deck", missing_deck, {("create", "deck", STUDY_LEAF)}),
        (
            "missing-note-type",
            missing_note_type,
            {
                ("create", "noteType", f"{PREFIX} Capture"),
                ("create", "templates", f"{PREFIX} Capture"),
            },
        ),
        ("bury-flag-on", bury_flag_on, {("repair", "preset", PREFIX)}),
        ("deck-on-default-preset", deck_on_default, {("repair", "preset", PREFIX)}),
        ("no-preset", no_preset, {("create", "preset", PREFIX)}),
        ("two-prefix-presets", two_prefix_presets, {("repair", "preset", PREFIX)}),
        ("field-removed", field_removed, {("migrate", "noteType", VOCABULARY)}),
        ("field-added", _field_added, {("migrate", "noteType", SENTENCE)}),
        ("fields-reordered", _fields_reordered, {("migrate", "noteType", VOCABULARY)}),
        ("extra-card-template", _extra_card_template, {("repair", "templates", SENTENCE)}),
        (
            "v0.5.0-templates",
            _v0_5_0_templates,
            {("repair", "templates", nt.name) for nt in MANIFEST.note_types},
        ),
        ("user-deck-options", user_options, set()),
        ("rule-deleted", rule_deleted, {("create", "readingRule", DELETED_RULE.combination)}),
        ("dev-prefix-beside", _dev_prefix_set_up, set()),
    ]
}


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
    # A note type's name has spaces: an exact `note:"<type>"` query is whole (story 2.8)
    assert [
        q for q in sent_queries(sent) if q not in exact and not set(q.split(" ")) <= set(exact)
    ] == []


@pytest.mark.p0
@pytest.mark.parametrize("case", list(CASES))
def test_preview_diffs_the_manifest_into_create_repair_and_migrate_items(case: str) -> None:
    """AC-6: each difference from the manifest previews exactly its Create, Repair or Migrate."""
    build, expected = CASES[case]

    outcome, _ = preview(build())

    assert not isinstance(outcome, Exception), outcome
    assert as_tuples(outcome.items) == expected
    assert len(outcome.items) == len(expected)  # no item listed twice


@pytest.mark.p1
def test_unrecognized_content_under_the_prefix_is_listed_read_only() -> None:
    """AC-8: unknown decks and note types under the Prefix are unmanaged, never plan items."""
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

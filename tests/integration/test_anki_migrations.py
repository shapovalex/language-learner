"""Story 2.9: schema migrations and full-sync steps in the Anki adapter (FR-7, AD-3, AD-4, AD-17,
AD-19).

A migration is an ordered step keyed by SchemaVersion: `Migration(from_version, steps)` takes
notes from `from_version` to `from_version + 1`. `AddField(note_type, field)` appends a field
with `modelFieldAdd` (spike 2.2: no modal, and no `index`, since it inserts there), and is
skipped when Anki already has it. `AnkiConnectStore(..., migrations=)` takes the list; the
production one (adapters/anki/migrations.py) is empty at SchemaVersion 1, so these tests build
a test-only v1 to v2 (and v2 to v3) migration and a manifest at that version.

- **Preview.** The field change is today's Migrate `noteType` row, and each note type holding a
  note below the manifest's SchemaVersion gets a Migrate `notes` row (decided with the user,
  2026-10-21). The state is `needs_migration` (story 2.8).
- **Never at startup.** Computing the state and previewing are reads only.
- **Apply.** Inside a confirmed plan only: each migration in `from_version` order, then
  `updateNoteFields` setting each older note's SchemaVersion to the manifest's, all through the
  Prefix guard and the ungated Setup path. A note whose SchemaVersion is empty, not an integer,
  or below the first migration's counts as the first migration's version (decided with the
  user, 2026-10-21).
- **Sync first.** A field change needs a one-way full sync, so `SetupService` awaits a Sync
  through the SyncRequester before such a plan, outside the Anki lock (AD-3, AD-17).
- **Full sync required.** Spike 2.2 (Q2) recorded that Sync doesn't report it: the Sync after a
  field change ended `succeeded`. So Setup sets it on the SyncRequester, and later Syncs keep it
  until the user clears it (tests/api/test_setup_migrations.py).

Anki is the in-memory collection in tests/support/anki_state.py; Sync is replayed from the
recorded v1 exchanges.
"""

import dataclasses
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard, PrefixViolation
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import SCHEMA_VERSION, Field, Manifest, build_manifest
from language_lab.adapters.anki.migrations import AddField, Migration
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupState, plan_hash
from language_lab.features.setup.service import SetupService
from language_lab.features.sync.service import SyncService
from tests.support.aio import run
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay, StubReply, recorded_v1_sync
from tests.support.anki_state import (
    READ_ACTIONS,
    Collection,
    apply_manifest,
    collection_replies,
    managed_collection,
    managed_note,
    sent_actions,
    sent_writes,
)

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)
DEV_MANIFEST = build_manifest(DEV)

VOCABULARY = f"{PREFIX} English Vocabulary"
SENTENCE = f"{PREFIX} French Sentence"
DEV_VOCABULARY = f"{DEV} English Vocabulary"
READING_RULE = f"{PREFIX} French Reading Rule"  # its seeded notes are at BASE too

BASE = SCHEMA_VERSION  # what Anki was set up at
NEXT = BASE + 1
V1_METHODS = frozenset({"collection.sync", "operations.get"})


def manifest_at(version: int, *extra: str) -> Manifest:
    """The manifest at SchemaVersion `version`, with `extra` hidden fields appended to the
    English Vocabulary note type: what a release with that migration would ship.
    """
    note_types = tuple(
        dataclasses.replace(nt, fields=(*nt.fields, *(Field(f, hidden=True) for f in extra)))
        if nt.name == VOCABULARY
        else nt
        for nt in MANIFEST.note_types
    )
    return dataclasses.replace(MANIFEST, schema_version=version, note_types=note_types)


V2 = manifest_at(NEXT, "Extra1")


def add_field(from_version: int, field: str) -> Migration:
    """`Migration(from_version, (AddField(<English Vocabulary>, field),))`."""
    return Migration(from_version=from_version, steps=(AddField(VOCABULARY, field),))


def to_v2() -> tuple[Migration, ...]:
    return (add_field(BASE, "Extra1"),)


def wired(
    collection: Collection,
    *,
    manifest: Manifest = V2,
    migrations: tuple[Migration, ...] = (),
    sync: dict[str, StubReply] | None = None,
) -> tuple[Any, AnkiConnectReplay]:
    """The real client and store over `collection` (writes answered), with `migrations` and,
    when given, `sync`'s v1 replies. Returns (store, replay).
    """
    gate = SetupGate(manifest)
    replay = AnkiConnectReplay(collection_replies(collection, writes=True) | (sync or {}))
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(manifest), gate=gate
    )
    store = AnkiConnectStore(
        client, AnkiLock(), manifest=manifest, gate=gate, migrations=migrations, poll_interval_s=0
    )
    return store, replay


async def preview_then_apply(store: Any) -> Any:
    preview = await store.setup_preview()
    return await store.setup_apply(plan_hash(preview.items))


def older_anki() -> Collection:
    """Anki set up at `BASE`: two English Vocabulary notes and one French Sentence note."""
    collection = managed_collection(MANIFEST)
    for _ in range(2):
        managed_note(collection, MANIFEST, VOCABULARY, str(BASE))
    managed_note(collection, MANIFEST, SENTENCE, str(BASE))
    return collection


def versions(collection: Collection, note_type: str = VOCABULARY) -> list[str]:
    """The stored SchemaVersion of each note of `note_type`, in id order."""
    notes = sorted(collection.notes.items())
    return [note.fields["SchemaVersion"] for _, note in notes if note.model == note_type]


def field_names_added(replay: AnkiConnectReplay) -> list[str]:
    """`fieldName` of every `modelFieldAdd` sent, in order, `multi`'s inner ones included."""
    bodies = [request.body for request in replay.sent]
    for body in list(bodies):
        if body.get("action") == "multi":
            bodies += body.get("params", {}).get("actions", [])
    return [b["params"]["fieldName"] for b in bodies if b.get("action") == "modelFieldAdd"]


# ---- preview (AC-1, AC-3) ----------------------------------------------------------------


@pytest.mark.p0
def test_an_older_anki_previews_its_migration_as_migrate_rows() -> None:
    """AC-1: the field change is a Migrate noteType row, and each note type with older notes a
    Migrate notes row (the seeded reading rules' included); the state is needs_migration.
    """
    store, _ = wired(older_anki(), migrations=to_v2())

    preview = run(store.setup_preview())

    notes = ResourceKind.NOTES
    assert set(preview.items) == {
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, VOCABULARY),
        PlanItem(PlanAction.MIGRATE, notes, VOCABULARY),
        PlanItem(PlanAction.MIGRATE, notes, SENTENCE),
        PlanItem(PlanAction.MIGRATE, notes, READING_RULE),
    }
    assert preview.state is SetupState.NEEDS_MIGRATION


@pytest.mark.p0
def test_migrations_never_run_at_startup_or_on_a_preview() -> None:
    """AC-3: the startup state and a preview send no write; every SchemaVersion stays."""
    collection = older_anki()
    store, replay = wired(collection, migrations=to_v2())

    async def startup_then_visit() -> None:
        await store.setup_state()
        await store.setup_preview()

    run(startup_then_visit())

    assert sent_writes(replay.sent) == []
    assert versions(collection) == [str(BASE)] * 2
    assert versions(collection, SENTENCE) == [str(BASE)]


# ---- apply (AC-4 to AC-8) ----------------------------------------------------------------


@pytest.mark.p0
def test_a_confirmed_plan_runs_its_migration_and_verifies() -> None:
    """AC-4: the field is added, each older note is stamped with the manifest's SchemaVersion,
    and verify finds nothing left: ready.
    """
    collection = older_anki()
    store, _ = wired(collection, migrations=to_v2())

    verified = run(preview_then_apply(store))

    assert versions(collection) + versions(collection, SENTENCE) == [str(NEXT)] * 3
    vocabulary = next(nt for nt in V2.note_types if nt.name == VOCABULARY)
    assert collection.models[VOCABULARY].fields == [f.name for f in vocabulary.fields]
    assert verified.items == ()
    assert verified.state is SetupState.READY


@pytest.mark.p0
def test_migrations_run_in_schema_version_order() -> None:
    """AC-5: given out of order, v1 to v2 still runs before v2 to v3."""
    collection = older_anki()
    later, first = add_field(NEXT, "Extra2"), add_field(BASE, "Extra1")
    store, replay = wired(
        collection, manifest=manifest_at(NEXT + 1, "Extra1", "Extra2"), migrations=(later, first)
    )

    run(preview_then_apply(store))

    assert field_names_added(replay) == ["Extra1", "Extra2"]
    assert versions(collection) == [str(NEXT + 1)] * 2


@pytest.mark.p0
def test_a_second_run_after_a_migration_changes_nothing() -> None:
    """AC-6: after the migration the preview is empty, and applying it sends no write."""
    store, replay = wired(older_anki(), migrations=to_v2())

    async def twice() -> tuple[Any, list[Any]]:
        await preview_then_apply(store)
        before = len(replay.sent)
        again = await store.setup_preview()
        await store.setup_apply(plan_hash(again.items))
        return again, replay.sent[before:]

    again, second_run = run(twice())

    assert sent_writes(second_run) == []
    assert again.items == ()


@pytest.mark.p0
def test_a_migration_stays_inside_the_prefix() -> None:
    """AC-7: a LanguageLabDev note beside keeps its SchemaVersion and its note type its fields;
    every write names a manifest note type or one of its notes.
    """
    collection = apply_manifest(older_anki(), DEV_MANIFEST)
    managed_note(collection, DEV_MANIFEST, DEV_VOCABULARY, str(BASE))
    dev_fields = list(collection.models[DEV_VOCABULARY].fields)
    store, replay = wired(collection, migrations=to_v2())

    run(preview_then_apply(store))

    assert versions(collection, DEV_VOCABULARY) == [str(BASE)]
    assert collection.models[DEV_VOCABULARY].fields == dev_fields
    ours = {nt.name for nt in V2.note_types}
    for request in replay.sent:
        body = request.body
        if body.get("action") == "modelFieldAdd":
            assert body["params"]["modelName"] in ours
        if body.get("action") == "updateNoteFields":
            assert collection.notes[body["params"]["note"]["id"]].model in ours


@pytest.mark.p1
@pytest.mark.parametrize("stored", ["", "abc", str(BASE - 1)], ids=["empty", "not-int", "below"])
def test_a_note_with_no_migration_path_is_migrated_from_the_first_version(stored: str) -> None:
    """AC-8: an empty, non-integer or too-old SchemaVersion counts as the first migration's,
    and the note ends at the manifest's.
    """
    collection = managed_collection(MANIFEST)
    managed_note(collection, MANIFEST, VOCABULARY, stored)
    store, _ = wired(collection, migrations=to_v2())

    run(preview_then_apply(store))

    assert versions(collection) == [str(NEXT)]


# ---- Sync around a field change (AC-9, AC-14) --------------------------------------------


@pytest.mark.p0
def test_setup_syncs_outside_the_lock_before_a_field_changing_plan() -> None:
    """AC-9: through the real SetupService and SyncService over one Anki lock, the Sync is sent
    before the plan's first write (a Sync awaited inside the lock would wait it out: anki_busy).
    """
    store, replay = wired(older_anki(), migrations=to_v2(), sync=recorded_v1_sync("normal"))
    sync = SyncService(store, enabled=True)
    setup = SetupService(
        store, sync=sync, prefix=PREFIX, azure_configured=True, openrouter_configured=True
    )

    async def confirm() -> None:
        plan = await setup.plan()
        await setup.apply(plan["planHash"])

    run(confirm())

    actions = sent_actions(replay.sent)
    writes = [i for i, a in enumerate(actions) if a not in READ_ACTIONS | V1_METHODS]
    first_write = writes[0] if writes else len(actions)
    assert "collection.sync" in actions[:first_write]
    assert writes, "the migration wrote nothing"


@pytest.mark.p0
def test_full_sync_required_survives_a_sync_that_ends_ok() -> None:
    """AC-14: replaying the Sync recorded right after a field change (it ends `succeeded`),
    the flag Setup set stays in the last status.
    """
    store, _ = wired(
        managed_collection(MANIFEST),
        manifest=MANIFEST,
        sync=recorded_v1_sync("after-field-change"),
    )
    sync = SyncService(store, enabled=True)

    async def flag_then_sync() -> Any:
        sync.set_full_sync_required(True)
        await sync.request_and_wait()
        return sync.last_status()

    status = run(flag_then_sync())

    assert status.full_sync_required is True
    assert status.outcome == "ok"


# ---- secondary branches ------------------------------------------------------------------


@pytest.mark.p1
def test_only_note_types_holding_older_notes_get_a_notes_row() -> None:
    """AC-1: a note type whose notes are all current, or which has none, gets no notes row."""
    collection = managed_collection(MANIFEST)
    managed_note(collection, MANIFEST, VOCABULARY, str(BASE))
    managed_note(collection, MANIFEST, SENTENCE, str(NEXT))
    store, _ = wired(collection, migrations=to_v2())

    preview = run(store.setup_preview())

    notes_rows = [i.name for i in preview.items if i.kind is ResourceKind.NOTES]
    assert notes_rows == [VOCABULARY, READING_RULE]


@pytest.mark.p1
def test_a_plan_without_a_migrate_item_never_rewrites_a_schema_version() -> None:
    """AC-4: only migrations rewrite SchemaVersion: a Create plan sends no updateNoteFields."""
    collection = managed_collection(MANIFEST)
    managed_note(collection, MANIFEST, VOCABULARY, str(BASE))
    del collection.decks[f"{PREFIX}::Captures"]
    store, replay = wired(collection, manifest=MANIFEST, migrations=to_v2())

    verified = run(preview_then_apply(store))

    assert "updateNoteFields" not in sent_writes(replay.sent)
    assert verified.state is SetupState.READY


@pytest.mark.p1
def test_a_partial_rerun_only_rewrites_the_schema_versions() -> None:
    """AC-6: the field is already there, the notes still older: no modelFieldAdd, only the
    SchemaVersion rewrite.
    """
    collection = apply_manifest(older_anki(), V2)
    store, replay = wired(collection, migrations=to_v2())

    verified = run(preview_then_apply(store))

    assert set(sent_writes(replay.sent)) == {"updateNoteFields"}
    assert versions(collection) + versions(collection, SENTENCE) == [str(NEXT)] * 3
    assert verified.items == ()


@pytest.mark.p1
def test_a_migration_step_outside_the_manifest_is_refused_before_it_is_sent() -> None:
    """AC-7: an AddField naming a note type the manifest doesn't declare is a PrefixViolation,
    and nothing of it is sent.
    """
    collection = apply_manifest(older_anki(), V2)
    stray = Migration(from_version=BASE, steps=(AddField("Other", "Extra1"),))
    store, replay = wired(collection, migrations=(stray,))

    with pytest.raises(PrefixViolation):
        run(preview_then_apply(store))

    assert sent_writes(replay.sent) == []

"""Schema migrations (FR-7, AD-3): ordered steps keyed by SchemaVersion, run only inside a
confirmed Setup apply, never at startup or on a preview.

`Migration(from_version, steps)` takes notes from `from_version` to `from_version + 1`. Its
steps are `AddField(note_type, field)`: append a field with `modelFieldAdd` (spike 2.2: no
modal; no `index`, since it inserts there), skipped when Anki's note type already has it.

`add_fields(invoke, manifest, migrations, state)` runs their steps sorted by `from_version`, from
the lowest effective version among the notes below the manifest's SchemaVersion (none: from the
first migration) up to the manifest's. `stamp_versions(invoke, manifest, state)` then sets
each such note's `SchemaVersion` to the manifest's with `updateNoteFields`. Setup's apply adds
the fields before its Create and Repair items and stamps after them: a card template may name
a field only once the note type has it. A note's effective version is its stored integer when it is
at least the first migration's `from_version`; an empty, non-integer or lower one counts as the
first's.

Every write is one `invoke` (the client's guarded, ungated Setup path). A `PrefixViolation`
propagates; a failed write (`AppError`) doesn't end the run: the verification reports it.

`build_migrations(prefix)` is the production list. v1 to v2 appends `ExampleAudio` to both
Vocabulary note types (their Example card template comes with the templates Repair).
"""

from collections.abc import Iterable
from dataclasses import dataclass

from language_lab.adapters.anki.manifest import EXAMPLE_AUDIO_FIELD, Manifest, build_manifest
from language_lab.adapters.anki.setup_apply import Invoke, try_write
from language_lab.adapters.anki.setup_diff import AnkiState
from language_lab.adapters.anki.setup_gate import SCHEMA_VERSION_FIELD
from language_lab.domain.catalog import Category, Language


@dataclass(frozen=True)
class AddField:
    note_type: str  # the full note type name
    field: str


@dataclass(frozen=True)
class Migration:
    from_version: int
    steps: tuple[AddField, ...]


def build_migrations(prefix: str) -> tuple[Migration, ...]:
    """The production migrations for `prefix`'s note types, names from the manifest (AD-3)."""
    manifest = build_manifest(prefix)
    vocabulary = (manifest.item_note_type(lang, Category.VOCABULARY) for lang in Language)
    return (Migration(1, tuple(AddField(name, EXAMPLE_AUDIO_FIELD) for name in vocabulary)),)


def _effective(version: int | None, first: int) -> int:
    return version if version is not None and version >= first else first


def _older(state: AnkiState, current: int) -> list[tuple[int, int | None]]:
    """(note id, stored version) of every managed note below `current`."""
    return [
        (note_id, version)
        for notes in state.note_versions.values()
        for note_id, version in notes
        if version is None or version < current
    ]


async def _add_field(invoke: Invoke, step: AddField, fields: dict[str, list[str]]) -> None:
    present = fields.setdefault(step.note_type, [])
    if step.field in present:
        return
    await try_write(invoke, "modelFieldAdd", modelName=step.note_type, fieldName=step.field)
    present.append(step.field)


async def add_fields(
    invoke: Invoke, manifest: Manifest, migrations: Iterable[Migration], state: AnkiState
) -> None:
    """Run the steps of the migrations Anki's older notes need (module docstring)."""
    current = manifest.schema_version
    ordered = sorted(migrations, key=lambda m: m.from_version)
    if not ordered:
        return
    older = _older(state, current)
    first = ordered[0].from_version
    start = min((_effective(v, first) for _, v in older), default=first)
    fields = {name: list(model.fields) for name, model in state.managed_models.items()}
    for migration in ordered:
        if start <= migration.from_version < current:
            for step in migration.steps:
                await _add_field(invoke, step, fields)


async def stamp_versions(invoke: Invoke, manifest: Manifest, state: AnkiState) -> None:
    """Set every managed note below the manifest's SchemaVersion to it."""
    current = manifest.schema_version
    for note_id, _ in _older(state, current):
        await try_write(
            invoke,
            "updateNoteFields",
            note={"id": note_id, "fields": {SCHEMA_VERSION_FIELD: str(current)}},
        )

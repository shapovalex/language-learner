"""Schema migrations (FR-7, AD-3): ordered steps keyed by SchemaVersion, run only inside a
confirmed Setup apply, never at startup or on a preview.

`Migration(from_version, steps)` takes notes from `from_version` to `from_version + 1`. Its
steps are `AddField(note_type, field)`: append a field with `modelFieldAdd` (spike 2.2: no
modal; no `index`, since it inserts there), skipped when Anki's note type already has it.

`run_migrations(invoke, manifest, migrations, state)` runs them sorted by `from_version`, from
the lowest effective version among the notes below the manifest's SchemaVersion (none: from the
first migration) up to the manifest's, then sets each such note's `SchemaVersion` to the
manifest's with `updateNoteFields`. A note's effective version is its stored integer when it is
at least the first migration's `from_version`; an empty, non-integer or lower one counts as the
first's.

Every write is one `invoke` (the client's guarded, ungated Setup path). A `PrefixViolation`
propagates; a failed write (`AppError`) doesn't end the run: the verification reports it.

`build_migrations(prefix)` is the production list: empty at SchemaVersion 1.
"""

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any

from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.setup_diff import AnkiState
from language_lab.adapters.anki.setup_gate import SCHEMA_VERSION_FIELD
from language_lab.domain.errors import AppError

# `invoke(action, **params)`: one guarded, ungated v6 call returning its `result`
type Invoke = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class AddField:
    note_type: str  # the full note type name
    field: str


@dataclass(frozen=True)
class Migration:
    from_version: int
    steps: tuple[AddField, ...]


def build_migrations(prefix: str) -> tuple[Migration, ...]:
    """The production migrations for `prefix`'s note types: none at SchemaVersion 1."""
    del prefix  # names derive from it once a migration exists
    return ()


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


async def _write(invoke: Invoke, action: str, **params: Any) -> None:
    """One write; a failure (`AppError`) is left to verify. A `PrefixViolation` propagates."""
    try:
        await invoke(action, **params)
    except AppError:
        pass


async def _add_field(invoke: Invoke, step: AddField, fields: dict[str, list[str]]) -> None:
    present = fields.setdefault(step.note_type, [])
    if step.field in present:
        return
    await _write(invoke, "modelFieldAdd", modelName=step.note_type, fieldName=step.field)
    present.append(step.field)


async def run_migrations(
    invoke: Invoke, manifest: Manifest, migrations: Iterable[Migration], state: AnkiState
) -> None:
    """Run the migrations Anki's older notes need, then stamp them with the manifest's
    SchemaVersion (module docstring).
    """
    current = manifest.schema_version
    ordered = sorted(migrations, key=lambda m: m.from_version)
    older = _older(state, current)
    if ordered:
        first = ordered[0].from_version
        start = min((_effective(v, first) for _, v in older), default=first)
        fields = {name: list(model.fields) for name, model in state.managed_models.items()}
        for migration in ordered:
            if start <= migration.from_version < current:
                for step in migration.steps:
                    await _add_field(invoke, step, fields)
    for note_id, _ in older:
        await _write(
            invoke,
            "updateNoteFields",
            note={"id": note_id, "fields": {SCHEMA_VERSION_FIELD: str(current)}},
        )

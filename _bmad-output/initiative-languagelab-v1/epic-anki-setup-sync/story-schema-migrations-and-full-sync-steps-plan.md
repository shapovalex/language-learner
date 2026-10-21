---
title: 'Schema migrations and full-sync steps'
type: 'feature'
ticket: '9'
created: '2026-10-21'
status: 'built'
baseline_revision: '0d116a697830b8f32878a78135be4eab87df16f2'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-9.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Setup can preview a field change (Migrate `noteType`) but never runs it, never rewrites a note's `SchemaVersion`, and nothing tells the user a field change needs a one-way full sync (FR-7, AD-3, AD-17, epic Done-when 2 and 3); the 18 red-phase ATDD leaves (23 cases) for story 2.9 are skipped.

**Approach:** Ordered migrations keyed by SchemaVersion (`adapters/anki/migrations.py`) run only inside a confirmed apply, after the Create/Repair items, then stamp every older note with the manifest's SchemaVersion. Setup awaits a Sync through the SyncRequester (outside the Anki lock) before a field-changing plan, refuses with `409 sync_required` when it doesn't end OK, then sets `full_sync_required` on the SyncRequester; readiness shows it as a `fullSync` check and tile until the user clicks "I've uploaded". The ATDD checklist's "Decisions" and "Defaults taken without a question" are the spec for names, wire keys and copy.

## Boundaries & Constraints

**Always:**
- Migrations never run at startup or on a preview: `setup_state()`/`setup_preview()`/the gate's on-demand compute stay reads only.
- Every migration write goes through `invoke_setup` (Prefix guard, ungated); a `PrefixViolation` propagates (never swallowed by `_write`).
- Effective version of a note: its stored integer if ≥ the first migration's `from_version`, else (empty, non-integer, too low) the first's. Migrations run sorted by `from_version`, from the lowest effective version among older notes (no older notes: from the first), up to the manifest's version.
- `AddField` is skipped when Anki's note type already has the field; no `index` sent.
- `PlanItem.requires_full_sync` is a property (MIGRATE + NOTE_TYPE only): plan hash and item equality unchanged.
- The Sync before apply runs in `SetupService` before `anki.setup_apply()` (never inside the lock); `OK` and `DISABLED` proceed.
- The `fullSync` tile never disables Apply and never adds "Fix the failing check to continue."

**Never:**
- No production migration (the list is empty at SchemaVersion 1); no opt-in repairs (entry 11); no change to the 2.8 gate precedence; no weakening of any ATDD first assertion; Setup never calls `AnkiStore.sync` directly.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Older Anki previewed | notes at v1, manifest v2 + migration 1→2 | Migrate noteType + Migrate notes per type holding older notes; `needs_migration`; no write | None |
| Confirmed apply | that plan's hash | Sync, then `modelFieldAdd`, `updateNoteFields` SchemaVersion→"2"; verify empty, `ready`; `fullSyncRequired: true` | Write failure → verify reports it |
| Second run | after migration | empty preview, no write | None |
| Partial re-run | field present, notes at v1 | only the SchemaVersion rewrites | None |
| Sync fails first | `auth_required` / `ankiweb_unreachable` / `anki_unavailable` | nothing applied | `409 sync_required` |
| Dev mode | Sync `DISABLED` | applies; full sync flag set | None |
| Non-manifest step | `AddField("Other", …)` | nothing sent | `PrefixViolation` |
| User uploaded | POST `/api/setup/full-sync/uploaded` | 204; `fullSync` ok again | None |

</frozen-after-approval>

## Code Map

- `domain/setup.py` -- `ResourceKind.NOTES = "notes"` (name = the note type); `PlanItem.requires_full_sync` property.
- `domain/errors.py` -- `SYNC_REQUIRED = "sync_required"`, message "Anki couldn't sync with AnkiWeb. Sync in Anki Desktop, then apply again."; `app.py` `_APP_ERROR_STATUS` → 409.
- `domain/sync.py`, `ports/sync_requester.py`, `features/sync/service.py`, `tests/fakes/sync_requester.py` -- `set_full_sync_required(required)`. `SyncService` keeps the flag; every status it records/returns carries it; `last_status()` with no Sync yet returns `SyncStatus(DISABLED, True)` when flagged (dev mode), else None.
- `adapters/anki/migrations.py` (new) -- frozen `AddField(note_type, field)`, `Migration(from_version, steps)`, `build_migrations(prefix) -> ()`, and `run_migrations(invoke, manifest, migrations, state)` per the Always rules.
- `adapters/anki/setup_diff.py` -- `AnkiState.note_versions: Mapping[str, tuple[tuple[int, int | None], ...]]` (type → (note id, version)); `diff` adds a Migrate `notes` row per manifest type with any version None or < `manifest.schema_version`, placed after the noteType rows. Update the module docstring.
- `adapters/anki/setup_gate.py` -- replace `read_versions` with a per-type read (same one `multi` of `findNotes` + one `notesInfo`; keep ids; skip `{}`); `read_preview` fills `note_versions` before `diff` and flattens them for `compute_state`.
- `adapters/anki/store.py` -- `migrations=()` kwarg; `setup_apply` runs `run_migrations(self._client.invoke_setup, …, state)` after `run_plan` when the plan has any Migrate item. `setup_apply.py`/`ports/anki_store.py` docstrings drop "Migrate waits for entry 9".
- `features/setup/service.py`, `routes.py` -- `SetupService(anki, *, sync: SyncRequester, …)`; `PlanRow.requiresFullSync` (all rows, discrepancies too); `ApplyResult.fullSyncRequired`; readiness 4th check `{"id": "fullSync", "ok": not (status and status.full_sync_required)}`; `_apply` reads `setup_preview()`, syncs when any item requires it, raises `SYNC_REQUIRED` unless OK/DISABLED, applies, then sets the flag; `full_sync_uploaded()`; route `POST /full-sync/uploaded` → 204.
- `app.py` -- pass `sync=sync` and `migrations=build_migrations(prefix)`.
- `tests/unit/test_setup_apply_service.py` -- pass a `FakeSyncRequester`.
- `static/api.js` -- `request` returns null on 204; `fullSyncUploaded()`.
- `static/screens/setup.js`, `static/css/studio.css` -- `fullSync` tile (warning style, shown only failing, title + fix + "I've uploaded" → POST then re-read readiness); `failing` excludes `fullSync`; `["notes", "Notes"]` after Note types; a row group with any `requiresFullSync` gets "Needs a full sync afterwards."; `DISCREPANCY_KINDS.notes`, `EXPECTED_FOUND["migrate:notes"]`; re-read readiness after a result with `fullSyncRequired`.
- `docs/anki.md` -- a short "Full sync after a migration" section: upload in Anki Desktop, then "I've uploaded".

## Tasks & Acceptance

**Execution:**
- [x] Domain, errors, port, fakes, `SyncService` -- flag, kind, code -- AC-2, AC-11, AC-14.
- [x] `migrations.py`, `setup_diff.py`, `setup_gate.py`, `store.py` -- notes rows, run migrations -- AC-1, AC-3..8.
- [x] `features/setup/*`, `app.py`, unit test -- Sync first, refusal, flag, check, route -- AC-9..15; update whole-body tests in `tests/api/test_setup_plan.py`, `test_setup_apply.py`, `test_setup_readiness.py`.
- [x] `api.js`, `setup.js`, `studio.css` -- tile, Notes rows, marker -- AC-16..18.
- [x] `docs/anki.md` -- upload step.
- [x] Three ATDD files -- remove `RED_PHASE` and the `type: ignore` comments, hoist in-body imports; add the checklist's "Secondary branches" as P1 tests (unit: hash unaffected by `requires_full_sync`; integration: no notes row for a type without older notes, Create-only plan sends no `updateNoteFields`, partial re-run, non-manifest step → `PrefixViolation`; API: dev mode proceeds, `anki_unavailable` refused; E2E: apply with `fullSyncRequired` brings the tile, `migrate:notes` discrepancy copy).

**Acceptance Criteria:**
- Given the 23 story 2.9 cases un-skipped, when `make test` runs, then all pass, no 2.9 `RED_PHASE` remains, and nothing regresses.
- Given `make lint`, then ruff check and format are clean.

## Implementation Notes

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 5, false 0, maybe-false 0. Two patched by the implementer, four rejected.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| The full-sync flag is lost when `setup_apply` raises after `modelFieldAdd` succeeded (verify or a later step fails) | medium | patch | `service.py` `_apply` sets the flag only on return; `store.setup_apply` runs migrations, then a verify read that can raise `anki_unavailable`/`anki_busy`. Fix: set the flag on any `AppError` but `plan_changed`/`setup_required` (both refuse before any write), then re-raise; plus a P1 test (unit: the gated fake apply can't be finished from outside a TestClient request). |
| The Sync and a `sync_required` refusal come before the store's `plan_changed` and `newer_schema` refusals | low | patch | `_apply` syncs from a fresh preview without comparing the hash or checking the state. Direct correction: Sync only when the hash matches and the state isn't `newer_schema`; plus a P1 API test. |
| The flag is set from the plan, even when no migration wrote anything (production list empty; a user-edited field) | low | rejected | This follows the checklist default ("after a run whose plan had such a row"). A user's own field edit in Anki Desktop needs a full sync anyway, which Anki asks for on its next sync, so the tile adds no harm. |
| A note type Created in the same apply counts as having no fields, so an `AddField` on it sends a `modelFieldAdd` that Anki rejects | low | rejected | Needs a deleted managed note type plus a migration step on that type. The rejected write is swallowed and the end state is right, and the fix adds logic. |
| SchemaVersion is rewritten one note at a time (plus a guard `notesInfo` per note), all under the one lock hold | low | rejected | No production migration exists. Apply is a rare, user-confirmed run that already holds the lock throughout. Batching needs guard changes (it does a lookup per inner action). Revisit with the first real migration. |
| A failed "I've uploaded" POST is silent: the tile comes back with no message | low | rejected | A local POST rarely fails, the tile returns with its button so the user can retry, and the checklist sets no copy for it. |

## Verification

**Commands:**
- `make test` -- expected: all pass
- `make lint` -- expected: clean
- `grep -rn "RED_PHASE" tests/integration/test_anki_migrations.py tests/api/test_setup_migrations.py tests/e2e/test_setup_full_sync.py` -- expected: no output

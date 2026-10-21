---
runScope: 'story'
runKey: 'story-2-9'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.9'
storyKey: '2-9'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 9)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-9.md'
generatedTestFiles:
  - 'tests/integration/test_anki_migrations.py'
  - 'tests/api/test_setup_migrations.py'
  - 'tests/e2e/test_setup_full_sync.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md (Done when 2 and 3)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-3 Setup flow and SchemaVersion, AD-4, AD-5, AD-17, AD-19)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-7)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Full sync required state)'
  - '_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md (Q1, Q2, Surprises)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-8.md (format, conventions)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{client,guard,store,setup_diff,setup_apply,setup_gate,manifest}.py, domain/{setup,sync,errors}.py, ports/{anki_store,sync_requester}.py, features/setup/{routes,service}.py, features/sync/service.py, app.py'
  - 'src/language_lab/static/screens/setup.js'
  - 'tests/README.md, tests/fakes/{anki_store,sync_requester}.py, tests/support/{anki_state,anki_connect,aio,clock,hosts,network}.py'
  - 'tests/integration/test_anki_setup_state.py, tests/api/{test_setup_state,test_setup_apply}.py, tests/e2e/test_setup_state.py'
  - 'tests/fixtures/anki/: sync-normal, sync-after-field-change, modelFieldAdd'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'Migrations are ordered steps keyed by SchemaVersion; an older Anki previews a field change as a Migrate noteType row and each note type holding older notes as a Migrate notes row, with the state needs_migration' }
  - { id: 'AC-2', idSource: 'generated', text: 'Field-changing steps are flagged: each plan row carries requiresFullSync, true only for a Migrate noteType row' }
  - { id: 'AC-3', idSource: 'generated', text: 'Migrations never run at startup: computing the SetupState and previewing send no write and leave every SchemaVersion as stored' }
  - { id: 'AC-4', idSource: 'generated', text: 'A confirmed plan runs its migration: the field is added, every older note''s SchemaVersion is rewritten to the manifest''s, and verify finds nothing with the state ready' }
  - { id: 'AC-5', idSource: 'generated', text: 'Migrations run in SchemaVersion order' }
  - { id: 'AC-6', idSource: 'generated', text: 'A second run is a no-op: after the migration the preview is empty and applying it sends no write' }
  - { id: 'AC-7', idSource: 'generated', text: 'Migrations stay inside the Prefix: another Prefix''s notes keep their SchemaVersion and every write targets a manifest name' }
  - { id: 'AC-8', idSource: 'generated', text: 'A note whose SchemaVersion is empty, not an integer, or below the first migration''s is migrated from the first version and stamped with the manifest''s' }
  - { id: 'AC-9', idSource: 'generated', text: 'Before a plan with a field-changing step, Setup awaits a Sync through SyncRequester, outside the Anki lock, before its first write' }
  - { id: 'AC-10', idSource: 'generated', text: 'A plan without a field-changing step applies without a Sync' }
  - { id: 'AC-11', idSource: 'generated', text: 'When that Sync does not end OK, apply is refused with 409 sync_required before any write' }
  - { id: 'AC-12', idSource: 'generated', text: 'The apply result of a plan with a field-changing step says fullSyncRequired' }
  - { id: 'AC-13', idSource: 'generated', text: 'Readiness reports fullSync as its own check from the last Sync status: passing until a field-changing apply, failing after it' }
  - { id: 'AC-14', idSource: 'generated', text: 'Full sync required survives later Syncs that end OK, as recorded after a field change (spike 2.2, Q2)' }
  - { id: 'AC-15', idSource: 'generated', text: 'POST /api/setup/full-sync/uploaded clears it: 204, and the fullSync check passes again' }
  - { id: 'AC-16', idSource: 'generated', text: 'Setup shows the Full sync required warning tile only while the fullSync check fails, without disabling Apply' }
  - { id: 'AC-17', idSource: 'generated', text: 'The tile''s I''ve uploaded button clears it' }
  - { id: 'AC-18', idSource: 'generated', text: 'The change list shows Migrate notes rows under Notes and marks a field-changing row as needing a full sync' }
---

# ATDD Checklist: Story 2.9, Schema migrations and full-sync steps

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 9 (`risk = "high"`). There is no story file, so this checklist holds the criteria. AC-1 to AC-18 follow the ticket's description and verify clause in source order:
  - "ordered migrations keyed by SchemaVersion shown as Migrate rows" is AC-1 and AC-5.
  - "run only inside a confirmed plan, never at startup" is AC-3 and AC-4.
  - "rewriting a note's SchemaVersion only there" is AC-4 (2.8's gate already refuses it elsewhere).
  - "flags field-changing steps requires full sync" is AC-2.
  - "awaits a Sync through SyncRequester outside the Anki lock before applying them" is AC-9, with AC-10 and AC-11 from the decisions below.
  - "tells the user to upload in Anki Desktop" is AC-12 and AC-16.
  - "shows the Full sync required readiness tile from the last Sync status" is AC-13, AC-14 and AC-16.
  - Verify: "runs once after confirmation and is a no-op on a second run" is AC-6; "stays inside the Prefix" is AC-7; "per the spike's recorded sync results" is AC-14.
  - AC-8, AC-15, AC-17 and AC-18 come from the decisions below.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in stories 2.1 to 2.8 (dev-only, NFR-11).
- **Test design:** none for epic 2. Priorities follow the ticket's risk (high), epic Done when 2 and 3, FR-7, AD-3 and AD-19.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - Changed: `domain/setup.py` (`ResourceKind.NOTES`, `PlanItem.requires_full_sync`), `domain/errors.py` (`SYNC_REQUIRED`), `ports/sync_requester.py` (`set_full_sync_required`), `features/sync/service.py` (keeps the flag), `adapters/anki/{setup_diff,setup_gate,setup_apply,store}.py` (Migrate notes rows, running migrations), `features/setup/{service,routes}.py` (Sync before a field change, `fullSync` check, `fullSyncRequired`, the clear route), `app.py` (passes the SyncRequester to Setup, 409 for `sync_required`), `static/screens/setup.js`, `static/css/studio.css`, `tests/fakes/{anki_store,sync_requester}.py`.
  - New: `adapters/anki/migrations.py` (`Migration`, `AddField`, the production list, empty at SchemaVersion 1).
  - Tests (done in this run): `tests/support/anki_state.py` answers `modelFieldAdd` with `writes=True` (appends the field to the model and to its notes, or inserts at `index`).

### Decisions taken with the user (2026-10-21)

| Question | Decision |
| --- | --- |
| Spike 2.2 showed Sync never reports a pending full sync (v1 says `succeeded` even then). What clears the tile? | **The user confirms on the tile.** An "I've uploaded" button POSTs to clear the flag in memory. |
| The Sync before a field-changing step doesn't end OK. | **Refuse apply** before any write with `409 sync_required`, so the one-way upload can't overwrite AnkiWeb changes Anki hasn't pulled. With Sync disabled (dev mode) apply goes on. |
| How do migrations show in the change list? | **Per resource.** Today's Migrate `noteType` row stays (now runnable, flagged `requiresFullSync`), plus a Migrate row of a new kind `notes` per note type whose notes need their SchemaVersion rewritten. |
| A note whose SchemaVersion is empty, not an integer, or below the first migration's. | **Treat it as the lowest version.** Every migration from the first runs on it, then it is stamped with the manifest's SchemaVersion. |

### Defaults taken without a question

- **Domain:** `ResourceKind.NOTES = "notes"`; its name is the note type. `PlanItem.requires_full_sync` is a property, true for `MIGRATE` + `NOTE_TYPE` only, so it doesn't change item equality or the plan hash. `ErrorCode.SYNC_REQUIRED = "sync_required"`, mapped to 409, with a fixed message along the lines of "Anki couldn't sync with AnkiWeb. Sync in Anki Desktop, then apply again."
- **Migrations** in `adapters/anki/migrations.py`:
  - `AddField(note_type: str, field: str)` appends a field with `modelFieldAdd` (no `index`: spike 2.2 Surprises), skipped when Anki already has it.
  - `Migration(from_version: int, steps: tuple[AddField, ...])` takes notes from `from_version` to `from_version + 1`.
  - Production names derive from the Prefix (say `build_migrations(prefix)`), empty at SchemaVersion 1.
  - `AnkiConnectStore(..., migrations=())` takes them; tests pass a test-only v1→v2 (and v2→v3) migration with a manifest built by `dataclasses.replace`.
- **Preview:** a Migrate `notes` row per manifest note type holding any note below the manifest's SchemaVersion, empty or non-integer included. The state rules of 2.8 are unchanged (`needs_migration`).
- **Apply** (inside the one lock hold, after the stale-hash and `newer_schema` refusals): the Create and Repair items as today, then each migration in `from_version` order from the lowest stored version (a note with no path counts as the first migration's `from_version`; with no notes, from the first), then `updateNoteFields` through the ungated path setting `SchemaVersion` to the manifest's on each older note. Each step goes through the Prefix guard.
- **Sync first:** `SetupService(anki, sync=SyncRequester, ...)`. `apply(plan_hash)` reads the preview; if a row `requires_full_sync`, it awaits `sync.request_and_wait()` before `anki.setup_apply()` (so outside the lock), and raises `AppError(SYNC_REQUIRED)` unless the status is `OK` or `DISABLED`. After a run whose plan had such a row, it calls `sync.set_full_sync_required(True)`.
- **SyncRequester:** `set_full_sync_required(required: bool)`. From then on `last_status()` carries `full_sync_required=required`, across later Syncs, until set again. The fake mirrors it.
- **Wire:**
  - Plan rows gain `"requiresFullSync": bool`.
  - The apply result gains `"fullSyncRequired": bool`, true when the run's plan had a field-changing row.
  - Readiness gains a fourth check `{"id": "fullSync", "ok": not required}` (Done when 2: each check reports on its own).
  - `POST /api/setup/full-sync/uploaded` answers 204 and clears the flag.
- **Screen:**
  - The `fullSync` tile shows only while it fails (EXPERIENCE.md: "shown only in this state"), in a warning style: "Full sync required" / "Open Anki Desktop, sync, and choose Upload to AnkiWeb.", with an "I've uploaded" button. It doesn't disable Apply.
  - After an apply whose result has `fullSyncRequired`, the screen re-reads readiness so the tile appears.
  - Change rows of kind `notes` go under "Notes", after "Note types". A row with `requiresFullSync` says "Needs a full sync afterwards." (default copy; not in the UX docs).

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and the screen state is stubbed at the network. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 2.8).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | v2 manifest + v1→v2 adding a Vocabulary field; Anki at v1 with Vocabulary and Sentence notes | the preview's items are Migrate noteType (Vocabulary) and Migrate notes (Vocabulary, Sentence) |
| AC-2 | API | P0 | Fake preview with Migrate noteType, Migrate notes and Create deck rows | each row's `requiresFullSync` |
| AC-3 | Integration | P0 | The AC-1 Anki: `setup_state()` then `setup_preview()` | no write sent |
| AC-4 | Integration | P0 | The AC-1 Anki: preview, apply its hash | every note's SchemaVersion is "2" |
| AC-5 | Integration | P0 | v3 manifest with 1→2 and 2→3, notes at 1 and 2 | `modelFieldAdd` fields sent in order `[Extra1, Extra2]` |
| AC-6 | Integration | P0 | Apply, then a fresh preview and an apply of its hash | no write sent by the second apply |
| AC-7 | Integration | P0 | A `LanguageLabDev` note at 1 beside | the Dev note keeps "1" |
| AC-8 | Integration | P1 | A note stored "", "abc", "0" | it is stamped "2" |
| AC-9 | Integration | P0 | Real SetupService, SyncService and store over one lock, Sync replayed from `sync-normal` | `collection.sync` is sent before the first write |
| AC-10 | API | P1 | Fake preview with Create and Repair rows only | the fake's `sync_calls` is 0 |
| AC-11 | API | P0 | Fake Sync ending `auth_required` / `ankiweb_unreachable` | status 409, code `sync_required` |
| AC-12 | API | P0 | Fake preview with a Migrate noteType row | the apply body's `fullSyncRequired` is true |
| AC-13 | API | P0 | Readiness, apply a field-changing plan, readiness | `fullSync` ok goes true → false |
| AC-14 | Integration | P0 | Real SyncService over the store, Sync replayed from `sync-after-field-change` | `last_status().full_sync_required` stays true |
| AC-15 | API | P0 | Apply a field-changing plan, POST the clear route, readiness | `fullSync` ok is true |
| AC-16 | E2E | P0 | Stubbed readiness with `fullSync` failing | the warning tile with its copy is visible |
| AC-17 | E2E | P0 | Click "I've uploaded" | the tile is gone and the POST was sent |
| AC-18 | E2E | P1 | Stubbed plan with Migrate noteType and notes rows | a "Notes" group lists the notes row |

### Secondary branches for green-phase automation

- AC-1: a Migrate `notes` row only for note types holding older notes; a note type with no notes and current fields gives no row.
- AC-2: `requires_full_sync` doesn't change `plan_hash` (unit).
- AC-3: the lifespan's startup refresh over the real store sends no write (covered by AC-3's `setup_state()` path).
- AC-4: a Create plan with no Migrate rows never sends `updateNoteFields` (only migrations rewrite SchemaVersion).
- AC-6: a partial re-run (field already added, notes still at 1) sends no `modelFieldAdd`, only the SchemaVersion rewrite.
- AC-7: a migration step naming a non-manifest note type is a `PrefixViolation` before it is sent.
- AC-9: the Sync goes through `SyncRequester`, never `AnkiStore.sync` from Setup.
- AC-11: dev mode (`DISABLED`) proceeds; `anki_unavailable` from the Sync is refused the same way; the screen shows the refusal's message.
- AC-12/AC-13: `tests/api/test_setup_apply.py` and `tests/api/test_setup_readiness.py` compare whole bodies, so they gain `fullSyncRequired: false` and the `fullSync` check in green phase; `tests/api/test_setup_plan.py` gains `requiresFullSync` on each row.
- AC-16: an apply whose result has `fullSyncRequired` re-reads readiness and brings up the tile; the tile doesn't add "Fix the failing check to continue."
- AC-18: a `migrate:notes` discrepancy row's expected/found copy.

## TDD red phase (current)

Red-phase scaffolds are generated, each marked `pytest.mark.skip` through a module-level `RED_PHASE` marker:

- Integration: 9 tests (11 cases) in `tests/integration/test_anki_migrations.py`.
- API: 6 tests (8 cases) in `tests/api/test_setup_migrations.py`.
- E2E: 3 tests (4 cases) in `tests/e2e/test_setup_full_sync.py`.

Names that don't exist yet (`migrations.Migration`, `AddField`, `ResourceKind("notes")`) are reached inside the tests, so collection passes while they are skipped.

**Red check (2026-10-21):** each file was run with `RED_PHASE` removed. 21 of 23 cases failed for the expected reasons:

- `ModuleNotFoundError: language_lab.adapters.anki.migrations` (10).
- `AnkiConnectStore` has no `migrations=` (AC-14).
- `'notes' is not a valid ResourceKind` (AC-1, AC-2).
- Apply answered 200 instead of 409 `sync_required`; no Sync before a field change; no `fullSyncRequired`; no `fullSync` check; no clear route.
- The tile, the "I've uploaded" button and the "Notes" row weren't found.

The 2 cases that passed are baselines that hold today: a plan without a field change makes no Sync (AC-10), and no tile shows when `fullSync` passes (AC-16).

The rest of the suite still passes with the extended `anki_state.py` (`make test-fast`: 444 passed).

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `test_anki_migrations.py::test_an_older_anki_previews_its_migration_as_migrate_rows` |
| AC-2 | `test_setup_migrations.py::test_each_plan_row_says_whether_it_requires_a_full_sync` |
| AC-3 | `test_anki_migrations.py::test_migrations_never_run_at_startup_or_on_a_preview` |
| AC-4 | `test_anki_migrations.py::test_a_confirmed_plan_runs_its_migration_and_verifies` |
| AC-5 | `test_anki_migrations.py::test_migrations_run_in_schema_version_order` |
| AC-6 | `test_anki_migrations.py::test_a_second_run_after_a_migration_changes_nothing` |
| AC-7 | `test_anki_migrations.py::test_a_migration_stays_inside_the_prefix` |
| AC-8 | `test_anki_migrations.py::test_a_note_with_no_migration_path_is_migrated_from_the_first_version` |
| AC-9 | `test_anki_migrations.py::test_setup_syncs_outside_the_lock_before_a_field_changing_plan` |
| AC-10 | `test_setup_migrations.py::test_only_a_field_changing_plan_syncs_before_it_applies` |
| AC-11 | `test_setup_migrations.py::test_a_sync_that_fails_before_a_field_change_refuses_the_apply` |
| AC-12 | `test_setup_migrations.py::test_the_apply_result_says_a_full_sync_is_required` |
| AC-13 | `test_setup_migrations.py::test_readiness_reports_full_sync_required_after_a_field_changing_apply` |
| AC-14 | `test_anki_migrations.py::test_full_sync_required_survives_a_sync_that_ends_ok` |
| AC-15 | `test_setup_migrations.py::test_the_user_clears_full_sync_required_once_uploaded` |
| AC-16 | `e2e/test_setup_full_sync.py::test_the_full_sync_required_tile_shows_only_while_its_check_fails` |
| AC-17 | `e2e/test_setup_full_sync.py::test_ive_uploaded_clears_the_full_sync_required_tile` |
| AC-18 | `e2e/test_setup_full_sync.py::test_the_change_list_shows_notes_rows_and_marks_a_full_sync` |

## Next steps (task-by-task activation)

1. **Domain:** add `ResourceKind.NOTES`, `PlanItem.requires_full_sync` and `ErrorCode.SYNC_REQUIRED` (409 in `app.py`).
2. **Migrations:**
   - Add `adapters/anki/migrations.py` and `migrations=` on the store.
   - Add the Migrate `notes` rows to the preview, then run migrations and the SchemaVersion rewrite in apply.
   - Un-skip AC-1 and AC-3 to AC-8.
3. **Sync:**
   - Add `set_full_sync_required` to the port, `SyncService` and the fake.
   - Give `SetupService` the SyncRequester: Sync before a field-changing plan, refuse on failure, set the flag after.
   - Add the `fullSync` check, `fullSyncRequired`, `requiresFullSync` and `POST /api/setup/full-sync/uploaded`.
   - Un-skip AC-2, AC-9 to AC-15, and update `test_setup_plan.py`, `test_setup_apply.py` and `test_setup_readiness.py` for the new keys.
4. **Screen:** add the warning tile with its button, the "Notes" kind and the full-sync marker in `setup.js` and `studio.css`. Un-skip AC-16 to AC-18.
5. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoints:**
  - GET /api/setup/plan rows add `"requiresFullSync"`.
  - POST /api/setup/apply adds `"fullSyncRequired"`, and can answer `409 sync_required`.
  - GET /api/setup/readiness adds `{"id": "fullSync", "ok"}`.
  - New: POST /api/setup/full-sync/uploaded, 204.
- **UI:** the Full sync required warning tile with "I've uploaded", the "Notes" change rows and the "Needs a full sync afterwards." marker.
- **Wiring to check in review:** `create_app` passes its `SyncService` to `SetupService` and the production migrations to the store. API tests use the fake store and don't prove the migrations wiring.

## Validation (step 5)

- Prerequisites: the criteria come from entry 9; the framework is pytest and pytest-playwright; the dev environment runs.
- Every leaf test's docstring names exactly one declared AC, and each AC has exactly one leaf. Parametrized cases are cases of that leaf.
- Each leaf's first assertion is the criterion-defining one. Setup calls (preview, apply, readiness reads) stay unasserted before it.
- One exception: AC-17 clicks "I've uploaded" before its assertion, because the transition needs the click; in red phase the click is what times out.
- AC-9, AC-13, AC-14 and AC-15 run their transitions (plan then apply; readiness before and after; flag then Sync; apply then clear).
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were removed.

## Completion

- **Risks and assumptions:**
  - Sync can't confirm the upload (spike 2.2, Q2), so the tile relies on the user saying they uploaded. A user who clicks without uploading clears it wrongly; AnkiWeb then still asks in Anki Desktop.
  - The Sync before a field change is a second read of the preview in `SetupService.apply`. A plan that changes between that read and `setup_apply` is still refused by the hash check.
  - No production migration exists at SchemaVersion 1, so everything is proven with a test-only v1→v2 migration. Device acceptance (entry 13) cites this CI evidence for Done when 3.
  - The "Needs a full sync afterwards." and "I've uploaded" copy are defaults, not from the UX docs.
- **Next workflow:** `bmad-build` for story 2.9.

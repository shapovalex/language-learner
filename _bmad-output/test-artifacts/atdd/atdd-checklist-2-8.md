---
runScope: 'story'
runKey: 'story-2-8'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.8'
storyKey: '2-8'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 8)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-8.md'
generatedTestFiles:
  - 'tests/integration/test_anki_setup_state.py'
  - 'tests/api/test_setup_state.py'
  - 'tests/e2e/test_setup_state.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md (Done when 4; Notes 2026-10-14 on newer_schema)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-2, AD-3 SchemaVersion, AD-4, AD-15, AD-19)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-7.md (format, conventions)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'No UX copy for newer_schema in EXPERIENCE.md or the mockups: the epic note of 2026-10-14 is the source'
  - 'src/language_lab/adapters/anki/{client,guard,store,setup_diff,setup_apply,manifest,codec,query}.py, ports/anki_store.py, domain/{setup,errors}.py, features/setup/{routes,service}.py, app.py'
  - 'src/language_lab/static/screens/setup.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_state,anki_connect,aio,clock,lifespan,probes,network}.py'
  - 'tests/integration/test_anki_setup_apply.py, tests/api/{test_setup_apply,test_setup_plan,test_sync_lifespan}.py, tests/e2e/test_setup_apply.py'
  - 'tests/fixtures/anki/: findNotes, notesInfo'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'SetupState is ready, needs_setup, needs_migration or newer_schema, computed from the managed state and each managed note''s SchemaVersion read through the codec' }
  - { id: 'AC-2', idSource: 'generated', text: 'SetupState is computed at startup, without failing startup when Anki is down' }
  - { id: 'AC-3', idSource: 'generated', text: 'SetupState is computed again on each Setup visit (preview) and after every apply, and the gate follows it' }
  - { id: 'AC-4', idSource: 'generated', text: 'Every non-Setup write is refused with setup_required, before it is sent, unless SetupState is ready' }
  - { id: 'AC-5', idSource: 'generated', text: 'Reads stay allowed in every SetupState' }
  - { id: 'AC-6', idSource: 'generated', text: 'An unknown SetupState (none computed yet) is computed by the first gated write before it decides' }
  - { id: 'AC-7', idSource: 'generated', text: 'Setup''s own apply is not gated: it writes while the state is needs_setup' }
  - { id: 'AC-8', idSource: 'generated', text: 'The adapter refuses to update a note whose stored SchemaVersion differs from the manifest''s, even while ready' }
  - { id: 'AC-9', idSource: 'generated', text: 'A gated write surfaces as the 409 setup_required envelope' }
  - { id: 'AC-10', idSource: 'generated', text: 'GET /api/setup/plan carries the SetupState as "state"' }
  - { id: 'AC-11', idSource: 'generated', text: 'Apply refuses a newer_schema Anki with setup_required before any write' }
  - { id: 'AC-12', idSource: 'generated', text: 'Setup shows the newer_schema blocking alert in place of the change list, with Apply hidden' }
---

# ATDD Checklist: Story 2.8, SetupState and the write gate

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 8 (`risk = "medium"`). There is no story file, so this checklist holds the criteria. AC-1 to AC-12 follow the ticket's description in source order, with the verify clauses folded in:
  - "each state from fixtures" is AC-1.
  - "at startup, after every apply, and on each Setup visit" is AC-2 (startup) and AC-3 (visit, apply).
  - "a non-Setup write gated in every state but ready" is AC-4 (adapter) and AC-9 (the 409 envelope).
  - "a read allowed" is AC-5.
  - "a mismatched-SchemaVersion note update refused" is AC-8.
  - "Playwright shows the newer_schema alert" is AC-12.
  - AC-6 comes from the decision below on an unknown state, AC-7 is the "non-Setup" half of the gate, and AC-11 is AD-19's "an older release never writes a newer schema" applied to Setup's own apply (default below).

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in stories 2.1, 2.6 and 2.7 (dev-only, NFR-11).
- **Test design:** none for epic 2. Priorities follow the ticket's risk (medium), epic Done when 4 (non-Setup writes return `409 setup_required` unless `ready`), NFR-1 and AD-19.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - Changed: `domain/setup.py` (`SetupState`, `SetupPreview.state`), `ports/anki_store.py` (`setup_state()`), `adapters/anki/client.py` (`gate=`, an ungated write path for Setup), `adapters/anki/store.py` (`gate=`, sets the state), `adapters/anki/setup_apply.py` (writes through the ungated path), `tests/fakes/anki_store.py`, `features/setup/{service,routes}.py` (`state` in the plan, startup refresh), `app.py` (gate wiring, startup, 409 for `setup_required`), `static/screens/setup.js`, `static/css/studio.css`.
  - New: `adapters/anki/setup_gate.py` (`SetupGate`).
  - Tests (done in this run): `tests/support/anki_state.py` holds notes (`add_note`, `managed_note`; `findNotes` on an exact `note:` query, `notesInfo`, and with `writes=True` `addNote` and `updateNoteFields`); `tests/support/probes.py` gains `GATED_ROUTE`.

### Decisions taken with the user (2026-10-21)

| Question | Decision |
| --- | --- |
| Where does the write gate sit, given no port method writes outside Setup yet? | **In the client, like the Prefix guard.** `AnkiConnectClient.invoke` checks a `SetupGate` on every write. Setup's apply writes through an ungated path. Every later feature write is gated without opting in. |
| What state does a note with an empty or non-integer SchemaVersion give? | **`needs_migration`.** It counts as an older note: writes stay gated and Apply stays available, so a migration (entry 9) can rewrite it. |
| What if SetupState isn't known yet (e.g. Anki down at startup)? | **Compute on demand.** The first gated write reads the state before it decides, so a late Anki doesn't need a Setup visit. |
| What shows on `newer_schema`? | **The alert replaces the change list.** "Anki was set up by a newer LanguageLab. Install the latest release." in the failing-tile style, with Apply hidden. |

### Defaults taken without a question

- **Domain:** `SetupState(StrEnum)` in `domain/setup.py`: `READY = "ready"`, `NEEDS_SETUP = "needs_setup"`, `NEEDS_MIGRATION = "needs_migration"`, `NEWER_SCHEMA = "newer_schema"`. `SetupPreview` gains `state: SetupState` (default `READY`, which is what an empty preview is).
- **Computing it**, from the preview's reads plus, for each manifest note type in Anki, `findNotes` with `note_query()` and `notesInfo`. Each note's `SchemaVersion` is `decode_field(value).strip()` parsed as an integer, against `manifest.schema_version`. Precedence:
  1. `newer_schema`: any note above the manifest's version.
  2. `needs_migration`: any Migrate item, or any note below it or not an integer.
  3. `needs_setup`: any other plan item.
  4. `ready`.

  Only manifest note types are read, so a `LanguageLabDev` note never counts toward `LanguageLab` (AD-4).
- **Port:** `AnkiStore.setup_state() -> SetupState`, reads only under the lock. `setup_preview()` returns the state in `SetupPreview.state`, and `setup_apply()` returns the verification with its fresh state.
- **Gate:** `SetupGate(manifest)` in `adapters/anki/setup_gate.py`, with `.state: SetupState | None` (None until computed) and `.set(state)`.
  - It is shared by `AnkiConnectClient(url, *, transport=None, guard=None, gate=None)` and `AnkiConnectStore(client, lock, *, manifest=None, gate=None)`.
  - The store calls `gate.set()` after `setup_state()`, each `setup_preview()` and each `setup_apply()` verification.
  - `client.invoke(action, ...)` with a gate: reads (and `multi` of reads) pass. Any other action, and any write inside a `multi`, raises `AppError(SETUP_REQUIRED)` before it is sent unless the state is `ready`. While the state is None, the gate reads it first through the unguarded lookup (the call already holds the lock, so it doesn't take it again).
  - `updateNoteFields` (with a gate, in `ready`): the gate reads the note with `notesInfo` and refuses with `SETUP_REQUIRED` when its decoded `SchemaVersion` isn't the manifest's.
  - The Prefix guard still runs first on every request. A client without a gate behaves as today, so the 2.6 and 2.7 tests keep passing.
  - Setup's apply passes the client's ungated path (say `invoke_setup`, any name) to `run_plan`.
- **Apply on `newer_schema`:** `setup_apply` raises `AppError(SETUP_REQUIRED)` after its fresh diff and before any write, when the fresh state is `newer_schema`. The screen hides Apply, so this only guards a stale or hand-sent POST.
- **Startup:** the lifespan starts `SetupService.refresh_state()` (any name) as a task that calls `anki.setup_state()`, logs a failure without its text, and never fails or delays startup. Shutdown cancels it if it still runs.
- **Routes:** GET /api/setup/plan gains `"state"`. `app.py` maps `setup_required` to 409.
- **Fake:** `FakeAnkiStore.setup_state()` returns `self.preview.state`, raises as `setup_preview()` does, and counts `state_calls`.
- **Screen:** when the plan's `state` is `newer_schema`, a `role="alert"` block in the failing-tile style, with the copy above, takes the change list's place, and Apply setup is not rendered. The unmanaged rows and the study footer stay.

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and the screen state is stubbed at the network. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 2.7).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | 15-row table: set up (no notes, every type current, version in editor markup, with NBSP, a newer Dev note beside), empty Prefix, missing deck, older/empty/non-integer version, field change, missing deck plus older note, newer note, newer beside older, newer plus missing deck | `setup_state()` is the expected state |
| AC-2 | API (lifespan) | P0 | Lifespan with the fake, Anki up and down | the fake's `state_calls` is 1 and startup didn't raise |
| AC-3 | Integration | P0 | Gate set `ready`, stock Anki: preview, then apply | the gate's states are `[needs_setup, ready]` |
| AC-4 | Integration | P0 | `addNote` with the gate in each of the four states | the outcome's code is `setup_required`, or none when `ready` |
| AC-5 | Integration | P0 | `findNotes` with the gate in each of the four states | it returns the note's id |
| AC-6 | Integration | P1 | Gate unknown over a set-up, an empty and a newer-schema Anki, then `addNote` | the outcome's code, then the gate's computed state |
| AC-7 | Integration | P0 | Gate `needs_setup`, stock Anki, preview and apply | the apply raised nothing |
| AC-8 | Integration | P0 | Gate `ready`, `updateNoteFields` on a note stored older, newer, empty, current | the outcome's code is `setup_required`, or none when current |
| AC-9 | API | P0 | Probe route raising `AppError(SETUP_REQUIRED)` | status 409 |
| AC-10 | API | P0 | Fake preview in each of the four states | the body's `state` |
| AC-11 | Integration | P0 | A newer note and a missing deck: preview, then apply its hash | the outcome's code is `setup_required` |
| AC-12 | E2E | P0 | Stubbed plan with a Migrate item and `state: "newer_schema"` | the alert with the copy is visible |

### Secondary branches for green-phase automation

- AC-4: a `multi` holding one write is refused whole, nothing sent; a `multi` of reads passes in every state.
- AC-4: a non-Setup write in `ready` still meets the Prefix guard (a `LanguageLabDev` target is `PrefixViolation`, not `setup_required`).
- AC-8: a non-Setup `updateNoteFields` that sets `SchemaVersion` to anything but the manifest's is refused (AD-3: only migrations rewrite it).
- AC-6: Anki down while the gate computes on demand is `anki_unavailable`, and the state stays unknown.
- AC-2: startup returns while a gated `setup_state()` is still in flight, and shutdown cancels it.
- AC-3: `setup_state()` itself sets the gate (startup path).
- AC-10: the existing `tests/api/test_setup_plan.py` compares the whole body, so it gains `"state": "ready"` in green phase.
- AC-12: `newer_schema` with failing readiness still hides Apply and shows no "Fix the failing check" reason; coming back with a finished apply status still shows the alert.

## TDD red phase (current)

Red-phase scaffolds are generated, each marked `pytest.mark.skip` through a module-level `RED_PHASE` marker:

- Integration: 8 tests (33 cases) in `tests/integration/test_anki_setup_state.py`.
- API: 3 tests (7 cases) in `tests/api/test_setup_state.py`.
- E2E: 1 test in `tests/e2e/test_setup_state.py`.

Names that don't exist yet (`SetupGate`, `SetupState`) are imported inside the tests, so collection passes while they are skipped.

**Red check (2026-10-21):** each file was run with `RED_PHASE` removed. All 41 cases failed for the expected reasons:

- `ModuleNotFoundError: language_lab.adapters.anki.setup_gate`.
- `ImportError: SetupState`.
- `FakeAnkiStore` has no `state_calls`.
- The probe's `setup_required` came back as 500 instead of 409.
- The `newer_schema` alert wasn't found.

The rest of the suite still passes with the extended `anki_state.py`.

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `test_anki_setup_state.py::test_setup_state_is_computed_from_the_plan_and_each_notes_schema_version` |
| AC-2 | `test_setup_state.py::test_startup_computes_setup_state_once_and_starts_even_when_anki_is_down` |
| AC-3 | `test_anki_setup_state.py::test_the_gate_follows_each_setup_visit_and_each_apply` |
| AC-4 | `test_anki_setup_state.py::test_a_non_setup_write_is_refused_unless_setup_state_is_ready` |
| AC-5 | `test_anki_setup_state.py::test_reads_stay_allowed_in_every_setup_state` |
| AC-6 | `test_anki_setup_state.py::test_an_unknown_state_is_computed_by_the_first_gated_write` |
| AC-7 | `test_anki_setup_state.py::test_setups_own_apply_is_not_gated` |
| AC-8 | `test_anki_setup_state.py::test_a_note_update_is_refused_when_its_schema_version_differs` |
| AC-9 | `test_setup_state.py::test_a_gated_write_is_the_409_setup_required_envelope` |
| AC-10 | `test_setup_state.py::test_the_plan_carries_the_setup_state` |
| AC-11 | `test_anki_setup_state.py::test_apply_refuses_a_newer_schema_before_any_write` |
| AC-12 | `e2e/test_setup_state.py::test_newer_schema_shows_the_blocking_alert_in_place_of_the_change_list` |

## Next steps (task-by-task activation)

1. **Domain and port:**
   - Add `SetupState` and `SetupPreview.state`, plus `AnkiStore.setup_state()` with its fake (`state_calls`).
   - Compute the state in the adapter.
   - Un-skip AC-1.
2. **Gate:**
   - Add `adapters/anki/setup_gate.py` and wire `gate=` into the client and the store.
   - Give Setup's apply the ungated path.
   - Un-skip AC-3 to AC-8 and AC-11.
3. **App:**
   - Map `setup_required` to 409.
   - Add `state` to the plan.
   - Refresh the state at startup, and build the gate in `create_app`.
   - Un-skip AC-2, AC-9 and AC-10, and update `test_setup_plan.py` for `state`.
4. **Screen:**
   - Add the `newer_schema` alert to `setup.js`, with its style in `studio.css`.
   - Un-skip AC-12.
5. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoints:**
  - GET /api/setup/plan adds `"state"`.
  - No new route.
  - `409 setup_required` comes from the `AppError` map in `app.py`.
- **UI:** the `newer_schema` alert on the Setup screen, replacing the change list, with Apply hidden.
- **Wiring to check in review:** `create_app` builds one `SetupGate(manifest)` and passes it to both the client and the store. Tests inject the fake store, so nothing here proves that wiring.

## Validation (step 5)

- Prerequisites: the criteria come from entry 8; the framework is pytest and pytest-playwright; the dev environment runs.
- Every leaf test's docstring names exactly one declared AC, and each AC has exactly one leaf. Parametrized cases are cases of that leaf.
- Each leaf's first assertion is the criterion-defining one. Setup calls (preview, lifespan start) stay unasserted before it.
- AC-3 and AC-6 run their transitions (visit then apply; an unknown state, then a write).
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were removed.

## Completion

- **Risks and assumptions:**
  - AC-11's choice of `setup_required` for apply on `newer_schema` is a default, not a user decision. The fixed message "Setup isn't complete yet." reads oddly there, but the screen never shows it, because Apply is hidden.
  - On-demand computing makes the first gated write after a cold start slower by one state read.
- **Next workflow:** `bmad-build` for story 2.8.

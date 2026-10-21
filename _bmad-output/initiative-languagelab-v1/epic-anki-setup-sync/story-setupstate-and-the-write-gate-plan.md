---
title: 'SetupState and the write gate'
type: 'feature'
ticket: '8'
created: '2026-10-21'
status: 'built'
baseline_revision: '52c6488c52785b7b9978550b5e5dc88dbccc758a'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-8.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing stops a feature write to an Anki that isn't set up, is mid-migration, or was set up by a newer release (AD-19, NFR-1, epic Done-when 4); the 12 red-phase ATDD leaves (41 cases) for story 2.8 are skipped.

**Approach:** Compute `SetupState` in the adapter from the preview's reads plus every managed note's decoded `SchemaVersion`; a `SetupGate` shared by client and store refuses non-Setup writes with `setup_required` unless `ready` (and any `updateNoteFields` on a note at another version), Setup's apply writes ungated, the lifespan computes the state at startup, the plan carries `"state"`, and Setup shows the `newer_schema` alert. The ATDD checklist's "Decisions", "Defaults taken without a question" and "Secondary branches" are the spec for names, precedence, copy and behaviour.

## Boundaries & Constraints

**Always:**
- Precedence: `newer_schema` > `needs_migration` (Migrate item, or a note below / empty / non-integer) > `needs_setup` (any other item) > `ready`. Only manifest note types are read (exact `note_query`).
- The Prefix guard runs before the gate on every request; the gate refuses before anything is sent. A client with no gate behaves exactly as today.
- Gate on-demand compute and note lookups use the client's unguarded raw lookup (the caller already holds the lock; never take it again).
- Startup state refresh never fails or delays startup; its failure is logged without exception text; shutdown cancels it.
- Copy exactly: "Anki was set up by a newer LanguageLab. Install the latest release." (`role="alert"`, failing-tile style).

**Never:**
- No migration writes (entry 9), no new product write routes, no change to `tests/support/anki_state.py` reply shapes, no weakening of any ATDD first assertion.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Non-Setup write, not ready | `addNote` / `multi` with a write | nothing sent | `AppError(SETUP_REQUIRED)` → 409 |
| Read in any state | `findNotes`, `multi` of reads | answered | None |
| State unknown | first gated write | state computed, then decided | Anki down → `anki_unavailable`, state stays None |
| Note at other version, `ready` | `updateNoteFields` (or one setting `SchemaVersion` ≠ manifest) | nothing sent | `SETUP_REQUIRED` |
| Out-of-Prefix write, `ready` | `LanguageLabDev` target | nothing sent | `PrefixViolation` (guard first) |
| Apply on newer schema | fresh diff shows newer note | no write | `SETUP_REQUIRED` |
| Startup, Anki down | lifespan | app starts; one `setup_state()` call | logged warning |

</frozen-after-approval>

## Code Map

- `domain/setup.py` -- add `SetupState(StrEnum)`; `SetupPreview.state: SetupState = READY`.
- `adapters/anki/setup_gate.py` (new) -- `SetupGate(manifest)`: `.state`, `.set()`, `async check(action, params, lookup)`; also home for the pure `compute_state(preview, versions, schema_version)` and an async `read_versions(lookup, manifest, models)` (one `multi` of `findNotes` per managed type present, then one `notesInfo` when ids exist; `decode_field(...).strip()` → int or None). Use `guard.READS` and `guard._inner_actions` (make public if needed) to classify writes.
- `adapters/anki/store.py` -- `_read_state`/`_multi` take a lookup today via `self._client.invoke`; move them to module-level functions over a lookup (e.g. in `setup_diff.py` or `setup_gate.py`) so the gate's on-demand compute reuses them. Add `setup_state()`; `setup_preview()` returns the state and sets the gate; `setup_apply()` raises `SETUP_REQUIRED` on fresh `newer_schema` after the hash check, runs `run_plan(self._client.invoke_setup, ...)`, verifies with state, sets the gate. `gate=None` kwarg.
- `adapters/anki/client.py` -- `gate=None` kwarg; `invoke` = guard (or read-only) then gate check with `self._invoke_raw`; `invoke_setup` = guard only. Update module docstring.
- `adapters/anki/setup_apply.py` -- docstring only ("guarded, ungated").
- `ports/anki_store.py`, `tests/fakes/anki_store.py`, `tests/unit/test_anki_store_port.py` -- `setup_state()`; fake returns `self.preview.state`, raises as preview, counts `state_calls`.
- `features/setup/service.py`, `routes.py` -- `Plan.state`; `refresh_state()` (log on `AppError`/`Exception` without text via `logging.getLogger("language_lab.setup")`); `aclose()` cancels it.
- `app.py` -- `_APP_ERROR_STATUS[SETUP_REQUIRED] = 409`; one `SetupGate(manifest)` into client and store; lifespan starts `setup.refresh_state()` as a task after `scheduler.start()` (don't await).
- `static/screens/setup.js`, `static/css/studio.css` -- `newerSchemaAlert()` in `planSection` replacing the change list when `state === "newer_schema"`; `updateActions` hides Apply then; `place`/`reread` show the list view (not a result) on `newer_schema`. Reuse `.readiness-tile-fail` colours (`studio.css:467`).
- `tests/api/test_setup_plan.py` -- whole-body compare gains `"state": "ready"`.

## Tasks & Acceptance

**Execution:**
- [x] `domain/setup.py`, port, fake, port test -- `SetupState`, `setup_state()`, `state_calls` -- AC-1/2/10 depend on it.
- [x] `adapters/anki/setup_gate.py`, `client.py`, `store.py`, `setup_apply.py` -- state compute, gate, ungated apply path -- AC-1, AC-3..8, AC-11.
- [x] `features/setup/*`, `app.py`, `tests/api/test_setup_plan.py` -- 409 map, `state` in plan, startup refresh, gate wiring -- AC-2, AC-9, AC-10.
- [x] `static/screens/setup.js`, `static/css/studio.css` -- newer_schema alert, Apply hidden -- AC-12.
- [x] Three ATDD files -- remove `RED_PHASE`, hoist in-body imports; add the checklist's "Secondary branches" as P1 tests (multi with a write refused whole; Dev target in `ready` is `PrefixViolation`; update setting `SchemaVersion` refused; on-demand with Anki down stays None; `setup_state()` sets the gate; startup cancel at shutdown; E2E newer_schema with failing readiness and with a finished status).

**Acceptance Criteria:**
- Given the 41 story 2.8 cases un-skipped, when `make test` runs, then all pass, no 2.8 `RED_PHASE` remains, and nothing regresses.
- Given `make lint`, then ruff check and format are clean.

## Implementation Notes

- `read_state`/`multi` moved from `store.py` into `setup_gate.py` (with `read_versions`, `compute_state` and `read_preview`); `guard._inner_actions` is now public `inner_actions`.
- `setup_apply` also sets the gate from its fresh pre-write diff (before the hash check), not only after verify.
- `SetupService.start_refresh()` starts the `refresh_state()` task; the lifespan calls it after `scheduler.start()`. A failure logs only the error code (or a fixed line), never exception text.
- Two pre-2.8 tests adjusted for new legitimate behaviour: `test_anki_setup_preview.py` (exact `note:"<type>"` queries contain spaces, so they're accepted whole) and `test_anki_prefix_guard.py::test_composed_app_client_rejects_an_out_of_prefix_write` (the managed write goes through `invoke_setup`; it now also asserts the gate is wired, since `invoke` no longer sends a write whose state can't be read).
- Secondary branches added as P1: 4 integration tests (9 cases), 1 API test, 2 E2E tests.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 1, false 0, maybe-false 0. Both patched by the implementer.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A stale Setup page whose apply gets 409 `setup_required` (fresh `newer_schema`, unchanged hash) keeps the old change list with Apply enabled, and the alert never shows | medium | patch | `setup.js` `apply()` re-reads only for `plan_changed`; the hash is from items only, so a newer note passes the hash check. Re-read on `setup_required` too, plus a P1 E2E case. |
| The `SetupService.apply` docstring omits `setup_required` | low | patch | `service.py` docstring; the port docstring was already updated. Direct correction. |

## Design Notes

Gate check, given `(action, params, lookup)`: collect actions (`multi` → inner); if all in `READS` return. If `state is None`, `state = compute_state(...)` from `read_state(lookup, manifest)` + `read_versions`, then `set`. If `state != READY` raise `SETUP_REQUIRED`. For each `updateNoteFields`: `notesInfo(notes=[id])` → decoded `SchemaVersion` must equal manifest's, and if the update's fields carry `SchemaVersion`, its decoded value must too.

Plan JSON: `"state": str(preview.state)`, placed after `planHash`.

## Verification

**Commands:**
- `make test` -- expected: all pass, 0 skipped among the 2.8 files
- `make lint` -- expected: clean
- `grep -rn "RED_PHASE" tests/integration/test_anki_setup_state.py tests/api/test_setup_state.py tests/e2e/test_setup_state.py` -- expected: no output

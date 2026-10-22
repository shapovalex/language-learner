---
title: 'Refactor sweep'
type: 'refactor'
ticket: '14'
created: '2026-10-21'
status: 'built'
baseline_revision: '4f4259a797a95a717c894b5e3f68b801d2485f11'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Entries 1–13 left duplicated code behind in the Anki adapter, the Setup service and screen, and their tests: three copies of the "write that swallows `AppError`" helper and two `Invoke` aliases, four spellings of "an int, not a bool", the repair-key selection in both store and service, and Setup test helpers and constants copied across five e2e and four integration files. The deferred-work entries for this epic are behavior changes or Mac Mini measurements, not cleanups, so they stay out.

**Approach:** Collapse each duplicate onto one definition beside its callers, move copied test helpers into `tests/support`, and change no behavior.

## Boundaries & Constraints

**Always:** No HTTP status, JSON body, log line, AnkiConnect request (action, params, order), or screen text changes. Tests change only by imports and by calling the moved helpers; no assertion is edited, added or removed. Keep the module docstrings' contracts true (edit their wording only where a moved name appears).

**Never:** Deferred-work entries (persisting the full-sync flag, `read_leftovers` cost, `decode_field` blank lines, v1 Sync cancel). Rejected review findings that change behavior. The `wired(...)` store builders in the integration tests (their return shapes differ; a shared builder needs wrappers for no gain). New features or new tests.

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/setup_apply.py` -- `Invoke` alias (39), `_is_id` (42), `_PlanRun._write` (69), `_try` (182), `modelTemplateAdd` dict (104-110) duplicating `_card_templates` (58).
- `src/language_lab/adapters/anki/migrations.py` -- own `Invoke` (31) and `_write` (66), same body as `_try`.
- `src/language_lab/adapters/anki/setup_gate.py` -- `_is_int` (188); `present`/`types` lines repeated in `read_note_versions` (163-164) and `read_leftovers` (214-215).
- `src/language_lab/adapters/anki/guard.py` -- int-not-bool spelled inline at 76 and 202; imported by setup_gate and setup_diff already.
- `src/language_lab/adapters/anki/client.py` -- `_invoke_raw` and `invoke_v1` both check `error` and return `result` after `_post`.
- `src/language_lab/adapters/anki/store.py` -- `setup_apply` selects checked repairs inline (101-102).
- `src/language_lab/domain/setup.py` -- home for the shared repair selection.
- `src/language_lab/features/setup/service.py` -- `_checked` (120); `plan_hash` imported twice (34-35); `aclose` cancels two tasks with the same block (250-259).
- `src/language_lab/static/screens/setup.js` -- the plan-error handler written in `toggle`, `reread` and the first `readPlan()`; `error?.name === "ApiError" && error.code === …` twice in `apply`.
- `tests/integration/test_anki_setup_apply.py` / `test_anki_setup_preview.py` -- 12 identical collection mutators, `_from_set_up`, `as_tuples`.
- `tests/integration/test_anki_migrations.py:120` / `test_anki_setup_repairs.py:90` -- identical `run[T]`; `tests/support/aio.py` has `settle`.
- `tests/integration/test_anki_prefix_guard.py:45` / `test_anki_setup_repairs.py:67` -- `media_name`, differing only in default prefix.
- `tests/e2e/test_setup_{apply,full_sync,preview,repairs,state}.py` -- repeated route constants, `PREFIX`, copy strings, `readiness(...)`, `item`, `plan`, `open_setup`, the idle status literal; `test_setup_state.py:59-71` re-spells `newer_schema_plan()`.
- `tests/api/test_setup_apply.py`, `test_setup_state.py` -- the `settings_factory` / `app_client(create_app(...))` pair that `client_over` in `test_setup_migrations.py:47` and `test_setup_repairs.py:54` already wraps.

## Tasks & Acceptance

**Execution:**
- [x] `adapters/anki/guard.py` -- add public `is_int(value)`; use it in `_ids` and `_require_preset` -- one int check.
- [x] `adapters/anki/setup_apply.py` -- keep `Invoke`; add public `try_write(invoke, action, **params) -> Any` (None on `AppError`), used by `_PlanRun._write` and `run_repairs`; drop `_try`; `_is_id` → `guard.is_int`; add `_card_template(t)` used by `_card_templates` and `modelTemplateAdd` -- one tolerant write, one template shape.
- [x] `adapters/anki/migrations.py` -- import `Invoke` and `try_write`; drop its own.
- [x] `adapters/anki/setup_gate.py` -- `_is_int` → `guard.is_int`; extract `_manifest_types(manifest, models)` for both readers.
- [x] `adapters/anki/client.py` -- `_post` returns `result` after the `error` check; `_invoke_raw` and `invoke_v1` drop their copies.
- [x] `domain/setup.py` + `adapters/anki/store.py` + `features/setup/service.py` -- add `checked_repairs(preview, keys)`; store and service use it; service drops `_checked`, imports `plan_hash` once (as `_plan_hash`, since `apply` shadows it), and folds `aclose`'s blocks into `_cancel(task)`.
- [x] `static/screens/setup.js` -- extract `planFailed(error)` (with `replanning = false`, harmless in the two other paths) and `isApiError(error, code)`.
- [x] `tests/support/setup_collections.py` (new) -- the shared mutators, `_from_set_up` (as `from_set_up`) and `as_tuples`; both integration files import them; preview-only mutators stay.
- [x] `tests/support/aio.py` -- add `run[T]`; `tests/support/anki_state.py` -- add `media_name(prefix)` without a default; callers pass their prefix.
- [x] `tests/support/setup_screen.py` (new) -- route constants, `PREFIX`, `PLAN_HASH`, `IDLE`, shared copy strings, `readiness(...)` covering the variants' keyword args, `item`, `plan`, `open_setup`; the five e2e files import them and keep file-specific constants; `test_setup_state.py` calls `newer_schema_plan()` and `PLAN_HASH`.
- [x] `tests/api/test_setup_apply.py`, `test_setup_state.py` -- use one `client_over` from a shared spot (`tests/support/app_env.py` if it fits) instead of the repeated pair.

**Acceptance Criteria:**
- Given the cleanup, when `make lint`, `make test` and `make test-webkit` run, then all pass with the same test count as at the baseline.
- Given `git diff` of `tests/`, when it is read, then no assertion line was edited, added or removed.
- Given the source, when `grep -rn "not isinstance(.*bool)" src/language_lab/adapters` runs, then one definition is found.

## Implementation Notes

- The shared integration mutators lost their leading underscore (`changed_front`, …) since they are now imported; both files also import `PREFIX`, `MANIFEST`, `VOCABULARY`, `SENTENCE`, `STUDY_LEAF` from `tests/support/setup_collections.py`.
- `client_over(settings_factory, store, **settings)` lives in `tests/support/hosts.py` beside `app_client`, not `app_env.py` (which is about `.env` files and avoids importing the app). The local `client_over` wrappers in `tests/api/test_setup_migrations.py` and `test_setup_repairs.py` and their inline pairs were left as they were (outside this plan's file list).
- E2E: `tests/e2e/test_setup_repairs.py` keeps its own `PLAN` regex and `open_setup` (it answers the plan per query string); its `UNCHECKED_HASH` became the shared `PLAN_HASH` (same value). The preview E2E now also stubs the apply status as idle through the shared `open_setup` (the screen treated a missing/idle status the same).
- Baseline: 650 tests (`make test`), 275 E2E under Chromium + WebKit; unchanged after.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 2, false 0, maybe-false 0. One patched, one rejected.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Three functions named `client_over` (shared in `tests/support/hosts.py`, local ones in `tests/api/test_setup_migrations.py:47` and `test_setup_repairs.py:54` with another signature and return type), and the inline `settings_factory` / `app_client(create_app(...))` pair left at five call sites in those files | low | patch | Confirmed in the diff; the Code Map names both files, so the duplication the Problem targets remains and the name now means two things. Fix: the local helpers become `client_and_store` over the shared `client_over`, and the inline pairs call it. |
| The preview E2E now stubs `GET /api/setup/apply/status` as idle through the shared `open_setup`; before, it reached the live server | low | reject | The live server is a fresh app with no run, so it answered `{"state": "idle", "result": null}`, the same body the stub gives: the screen gets the same input and every assertion is unchanged. The status route is covered by `tests/api/test_setup_apply.py`. Keeping the old wiring needs a new `open_setup` parameter. |

## Verification

**Commands:**
- `make lint` -- expected: no ruff findings
- `make test` -- expected: all pass, count equal to baseline
- `make test-webkit` -- expected: all pass

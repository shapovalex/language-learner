---
title: 'Refactor sweep'
type: 'refactor'
ticket: '5'
created: '2026-10-22'
status: 'built'
baseline_revision: '08d502da6af6c7fab389030818b94dca4a1d2b1e'
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

**Problem:** Entries 1–3 left duplicated code in the Capture adapter, the Captures screen and their tests. The adapter has four copies of the Capture scope query, two inline int-not-bool checks while `guard.is_int` already exists, and two CaptureId matches. `captures.js` re-spells `element`, `errorMessage`, `isApiError` and `skeleton` from `setup.js`, and has three `ApiError`-code checks and two near-identical failure-copy functions. The three Capture integration files copy `wired`, `code_of`, `sent_bodies`, the Prefix constants and the arrange helpers. The two API files copy `store_with`. The three E2E files copy route constants, copy strings, locators, `capture()`, `unsaved_alert` (already in `tests/support/unsaved.py`) and `horizontal_overflow`. This epic's deferred-work entries (the real `suspend`/`deleteNotes` fixtures) need Mac Mini replies, so they are not cleanups and stay out.

**Approach:** Collapse each duplicate onto one definition beside its callers. Move copied test helpers into `tests/support`. Change no behavior.

## Boundaries & Constraints

**Always:** No HTTP status, JSON body, log line, AnkiConnect request (action, params, order) or screen text changes, and no DOM structure or class change. Tests change only by imports and by calling the moved helpers. No assertion is edited, added or removed. Keep the module docstrings' and header comments' contracts true, editing their wording only where a moved name appears.

**Never:** Deferred-work entries. Rejected review findings (prefix-stripping on in-flight typing, non-UUID CaptureIds, malformed `CaptureId` fields). Sharing the route's `_UUID4` with the guard's (the copy is deliberate, AD-1). Generalizing `#confirm-dialog` with `#unsaved-alert`. New features or new tests.

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/store.py` -- `create_capture` (164: `model`), `list_captures` (202), `get_capture` (213) and `delete_capture` (226) each build `note_query(manifest, f"{manifest.prefix} Capture")`. The int checks are at 185 and 232. `_find_capture` (~262) and `delete_capture`'s loop both match `_field(info, _CAPTURE_ID).strip() == capture_id`. `guard.is_int` is at `adapters/anki/guard.py:73`.
- `src/language_lab/static/screens/setup.js` -- `element` (108), `skeleton` (130, label "Checking Anki and your keys…"), `errorMessage` (396), `isApiError` (401). The network fallback literal is also at 673.
- `src/language_lab/static/screens/captures.js` -- `element` (81), `errorMessage` (88), `skeleton` (94), `failureCopy` / `deleteFailureCopy` (113–125), and the `ApiError` code checks in them and in `loadDetail` (`not_found`).
- `src/language_lab/static/api.js` -- holds `ApiError`. `tests/api/test_app.py:88-95` requires that only `api.js` contain `fetch(`, so a new module without fetch is fine.
- `tests/integration/test_anki_captures.py`, `test_anki_capture_reads.py`, `test_anki_capture_delete.py` -- identical `wired` bodies (only the return annotation differs), `code_of`, `sent_bodies` (reads and delete), `PREFIX`, `DEV`, `MANIFEST`, `DEV_MANIFEST`, `CAPTURE_QUERY`, `VOCABULARY`, `GATED_STATES` and `TEXT`. `_dev_capture_with_the_id` and `_other_captures` differ only in their CreatedAt literal (both are `"…Z"` strings).
- `tests/api/test_captures_read.py:51`, `test_captures_delete.py:37` -- identical `store_with`.
- `tests/e2e/test_captures_{compose,list,delete}.py` -- `CAPTURES_PATH`, `API`, `COMPOSE_LABEL`/`LABEL`, `SAVE`, `NO_SELECTION`, `NOT_IN_ANKI`, `UNSAVED_ALERT`; `capture()`; `main`, `compose_box`, `rows`, `detail`, `is_save`; `unsaved_alert` (vs `tests/support/unsaved.py:74`); `horizontal_overflow` (list, delete; inline in compose:207). Pattern: `tests/support/setup_screen.py`.

## Tasks & Acceptance

**Execution:**
- [x] `adapters/anki/store.py` -- `_capture_infos(manifest)` and `_find_capture(manifest, capture_id)` build the scope query themselves, so no method spells it. `create_capture` keeps `model` for `addNote`. Use `guard.is_int` for both id checks. Add `_matching(infos, capture_id)`, which yields the entries whose decoded CaptureId matches, for `_find_capture` and `delete_capture` -- one scope, one int check, one match.
- [x] `static/dom.js` (new) -- `element(tag, className, text)` and `skeleton(label)`. Both screens import them and drop their copies. Setup's skeleton comment stays at its call -- one DOM helper set.
- [x] `static/api.js` -- export `isApiError(error, code)` and `errorMessage(error)`, with the "LanguageLab could not reach the server." fallback. `setup.js` (including line 673) and `captures.js` use them and drop their copies -- one envelope reading.
- [x] `static/screens/captures.js` -- fold `failureCopy`/`deleteFailureCopy` into one `failureCopy(error, unreachable, title)`, where `unreachable` is the `[title, body]` pair. Use `isApiError` for `not_found`.
- [x] `tests/support/captures.py` (new) -- `PREFIX`, `DEV`, `MANIFEST`, `DEV_MANIFEST`, `CAPTURE_QUERY`, `VOCABULARY`, `GATED_STATES`, `TEXT`, `wired`, `code_of`, `sent_bodies`, `other_captures(collection, created_at)` and `dev_capture_with_the_id(collection, capture_id, created_at)`. The three integration files import them and keep their file-specific constants. Their local arrange functions become thin parametrize entries over the shared ones with the file's own literal.
- [x] `tests/support/captures.py` -- also `store_with(*captures)` (a `FakeAnkiStore` holding them), which both API files import.
- [x] `tests/support/captures_screen.py` (new) -- the shared route constants, copy strings, `capture()`, the locators, `is_save` and `horizontal_overflow`. The three E2E files import them. The list and delete files import `unsaved_alert` from `tests/support/unsaved.py`. Compose's `LABEL` becomes the shared name.

**Acceptance Criteria:**
- Given the cleanup, when `make lint`, `make test` and `make test-webkit` run, then all pass with the same test counts as at the baseline.
- Given `git diff` of `tests/`, when it is read, then no assertion line was edited, added or removed.
- Given `src/language_lab`, when it is searched for `prefix} Capture"` in `store.py`, `function element` in `static/`, and `could not reach the server` in `static/`, then each has one definition.

## Implementation Notes

- Implemented directly in the session (no subagent), from the plan.
- Store: `_capture_model(manifest)` names the note type once; `create_capture` uses it for `addNote` and `_capture_infos` for the query, so `prefix} Capture"` appears once in `store.py`.
- `api.js` also exports `NETWORK_FALLBACK`. `setup.js:673` (the health line) uses the constant, not `errorMessage`, since `errorMessage` would show an envelope's message there.
- `unsaved_alert`: `tests/support/unsaved.py`'s version matches any `alertdialog`, and the delete E2E has the delete confirmation open too. So the title-matched version from the list and delete files moved into `tests/support/captures_screen.py` instead. Compose keeps importing the one in `unsaved.py`, as before.
- Shared test helpers sit in `tests/support/captures.py` (integration wiring and `store_with`) and `tests/support/captures_screen.py` (E2E). Local arrange functions are one-line wrappers that pass each file's CreatedAt literal.
- Review patch: `tests/support/unsaved.py`'s `unsaved_alert` now matches the alert by its title (`ALERT_TITLE`, fixed in `index.html`). It is the only definition, and the list and delete files import it, as the plan's task says. `captures_screen.py` no longer has one.
- Baseline and after: `make test` 772 passed, `make test-webkit` 385 passed, `make lint` clean. `git diff -- tests` has no added or removed `assert` or `expect(` line.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 1, false 0, maybe-false 0. One patched.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| The task said list and delete import `unsaved_alert` from `tests/support/unsaved.py`; instead a second, title-matched copy moved into `captures_screen.py`, so two helpers with different semantics remain | low | patch | Confirmed: `unsaved.py:74` matched any `alertdialog`. Fix: `unsaved.py` matches by `ALERT_TITLE` (the dialog's fixed accessible name), the copy is gone, and list and delete import the shared one. `make lint`, `make test` (772) and `make test-webkit` (385) pass. |

## Verification

**Commands:**
- `make lint` -- expected: no ruff findings
- `make test` -- expected: all pass, count equal to baseline
- `make test-webkit` -- expected: all pass

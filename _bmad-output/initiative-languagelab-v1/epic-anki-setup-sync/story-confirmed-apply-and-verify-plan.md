---
title: 'Confirmed apply and verify'
type: 'feature'
ticket: '7'
created: '2026-10-21'
status: 'built'
baseline_revision: '47e82d7b3d371febe06295d6c3865d4731afc585'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-7.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Setup can preview but not change Anki (FR-6, AD-3); the 14 red-phase ATDD leaves (29 cases) for story 2.7 are skipped.

**Approach:** Add `AnkiStore.setup_apply(plan_hash)` (re-diff, refuse stale, run Create/Repair through the guarded client, verify by fresh diff, one lock hold), `SetupService.apply`/`apply_status` with a kept, shielded task, `POST /api/setup/apply` + `GET /api/setup/apply/status`, `plan_changed` (409), and the Setup screen's Apply, progress card and verification banners. The ATDD checklist's "Decisions", "Defaults taken without a question" and "Implementation contract" are the spec for names, write payloads, copy and states.

## Boundaries & Constraints

**Always:**
- Every write goes through `self._client.invoke` (guarded); the hash check happens before any write; reads that fail raise `anki_unavailable`.
- A failed write step (`AppError` from a write, or `saveDeckConfig` → `false`) does not end the run; verify reports it.
- The preset save reads the config with `getDeckConfig`, sets only the three `BURY_FLAGS` paths, and saves that config; never a second clone on Repair. Default preset and user options untouched (FR-8).
- Created Study/Pronunciation decks are put on the `<Prefix>` preset even with no preset item.
- Service keeps the run task; requests await it via `asyncio.shield`; a second POST mid-run awaits the same run; a run that raises isn't recorded.
- Screen copy exactly as the checklist and E2E constants; `mount` starts `getApplyStatus()` before `getHealth()`; polling stops on unmount.

**Never:**
- No Migrate writes (entry 9), no opt-in repairs or template removal (entry 11), no `deleteDecks`.
- Don't weaken any ATDD first assertion; don't edit `tests/support/anki_state.py` reply shapes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty Prefix (± Dev beside) | stock Anki | verified, no items; Dev untouched | None |
| Each repairable drift | AC-2 table rows | verified, no items | None |
| Field removed | Migrate in plan | verification = that Migrate | None |
| Stale hash | Anki changed after preview | `plan_changed`, no write; route 409 | AppError handler |
| Refused save | `saveDeckConfig` → false | verification = preset Repair; other items applied | continue |
| Client disconnects | request cancelled mid-run | run finishes; status `finished` with result | shield |
| Anki down/busy | — | 503 envelope | AppError handler |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/errors.py` -- add `PLAN_CHANGED` + fixed message. `app.py:112` `_APP_ERROR_STATUS` gains `PLAN_CHANGED: 409`.
- `src/language_lab/adapters/anki/store.py` -- add `setup_apply`; reuse `_read_state`, `diff`, `self._lock.hold()` (pattern of `setup_preview`). Writes are single `invoke` calls (not `multi`) so each step can fail alone. A new `adapters/anki/setup_apply.py` for the per-item write steps is fine if store.py grows too much.
- `src/language_lab/adapters/anki/guard.py` -- read only. `saveDeckConfig` passes only when `getDeckConfig(deck=manifest.preset.decks[0])` is already the `<P>` config with the same id ⇒ `setDeckConfigId` must run before the save, and only save when `preset.decks[0]` exists.
- `src/language_lab/adapters/anki/manifest.py` -- `NoteType.fields[].name`, `.templates[].{name,front,back}`, `.css`; `Preset.{name,bury_flags,decks}`; `Manifest.decks` parents first. Don't change.
- `src/language_lab/ports/anki_store.py`, `tests/fakes/anki_store.py` -- add `setup_apply`; fake gains `verified=`, `apply_gated=`, `apply_calls`, `applies`, `finish_apply()` per the checklist contract (mirror `gated`/`finish`).
- `src/language_lab/features/setup/{service,routes,__init__}.py` -- `ApplyResult`, `ApplyStatus` TypedDicts; request body a pydantic model with `planHash: str`.
- `src/language_lab/static/{api.js,screens/setup.js,css/studio.css}` -- `applySetup(planHash)` (POST JSON), `getApplyStatus()`; screen states; classes `progress-card`, `verification-banner-verified`, `verification-banner-discrepancy`, `button-disabled` per DESIGN.md (`ux-languagelab/DESIGN.md` lines ~578, 614–615; reuse `.button`, `change-row`).
- Existing tests compatible: `tests/e2e/test_setup_preview.py` asserts no button inside the change list and no Apply on an empty plan — keep it so (Apply sits in the readiness card / outside the list); update its module docstring line 13.
- Tests to update: `tests/unit/test_anki_store_port.py:40` exact set + `setup_apply`; `tests/unit/test_errors.py` code set + `plan_changed`; architecture AD-15 code list + `plan_changed`.

## Tasks & Acceptance

**Execution:**
- [x] `domain/errors.py`, `app.py`, `tests/unit/test_errors.py`, architecture AD-15 -- `plan_changed` → 409.
- [x] `ports/anki_store.py`, `tests/fakes/anki_store.py`, `tests/unit/test_anki_store_port.py` -- port method and fake per contract -- AC-6..9 depend on it.
- [x] `adapters/anki/store.py` (+ optional `setup_apply.py`) -- `setup_apply` per Design Notes -- AC-1..5.
- [x] `features/setup/*` -- `apply`, `apply_status`, two routes -- AC-6..9.
- [x] `static/api.js`, `static/screens/setup.js`, `static/css/studio.css` -- Apply button + disabled reason, progress card, banners, Run Setup again, 409 re-read with inline alert, status on mount with 1 s polling -- AC-10..14.
- [ ] The four ATDD files -- remove `RED_PHASE`, hoist in-body imports; add backlog P1: AC-14 `finished-anki-changed` (E2E), screen 409 re-read (E2E), second POST awaits same run (unit), 503/422 on apply (API). Fix `test_setup_preview.py` docstring.

**Acceptance Criteria:**
- Given the 29 story 2.7 cases un-skipped, when `make test` runs, then all pass, no 2.7 `RED_PHASE` remains, and nothing regresses.
- Given `make lint`, then ruff check and format are clean.

## Implementation Notes

- Write steps live in `adapters/anki/setup_apply.py` (`run_plan`); `store.setup_apply` holds the lock once around re-diff, hash check, `run_plan`, and the verify read.
- The preset save's `getDeckConfig` goes through `invoke` and raises on failure (a read); every other step swallows `AppError` and returns `None`.
- `SetupService.aclose()` cancels a run still going at shutdown (wired into the app lifespan).
- Backlog P1 added: unit second-POST-awaits-same-run; API 503 (busy/unavailable) and 422 (three bodies); E2E `finished-anki-changed` and the 409 re-read with inline alert.
- Verified: `make test` 510 passed, 0 skipped; `make lint` clean; no `RED_PHASE` in the four 2.7 files.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 3, false 2, maybe-false 0. Four patched by the implementer.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A failed `setDeckConfigId` still leads to `saveDeckConfig`, which the guard refuses with `PrefixViolation`, so the run ends with a 500 | medium | patch | `_write` swallows the `AppError`; `getDeckConfig(decks[0])` then returns Default, and `_require_preset` raises. Skip the save when `decks[0]` was moved and the move didn't answer `true`. |
| A plan re-read that fails after a 409 or a finished poll leaves a disabled Apply and no progress card | low | patch | `reread`'s error path keeps `view = "applying"`; `updateActions` shows a disabled button. The plan-error branch now clears the actions. |
| `setup.aclose()` runs only if `sync.aclose()` doesn't raise, before the client closes | low | patch | `app.py` lifespan, same `try`. Cancel the setup run first. |
| `test_anki_store_port.py` docstring has a broken line wrap | low | patch | Cosmetic; re-wrapped. |
| A second POST while a run is going gets that run's result, whatever its hash | false | reject | The checklist decision says "A second apply while one runs awaits the same run"; this is the specified behaviour. |
| The plan's last Execution task is unticked | false | reject | The fix edits this build's plan; the work itself is done (grep and diff). |

## Design Notes

`setup_apply` under one hold: `state = _read_state`; `before = diff`; if `plan_hash(before.items) != plan_hash` raise `PLAN_CHANGED`. Then, from `before.items`:
1. deck Create → `createDeck` each, manifest order.
2. noteType Create → `createModel(modelName, inOrderFields, css, cardTemplates=[{Name, Front, Back}])`; skip its templates Create.
3. templates Repair → `updateModelTemplates(model={name, templates:{card:{Front,Back}}})` for cards in the read state, `modelTemplateAdd(modelName, template)` per missing card, `updateModelStyling(model={name, css})`.
4. Preset, when a preset item exists or a created deck is in `preset.decks`: config id = the `<P>`-named config of the first existing preset deck (state read), else `cloneDeckConfigId(name=P)` (int id, else step failed); `setDeckConfigId(decks=<existing preset decks not on that id>, configId)`; then, if a preset item exists or the config was just cloned, `getDeckConfig(deck=preset.decks[0])`, set `BURY_FLAGS` paths (create missing dicts), `saveDeckConfig(config)`.
"Existing preset decks" = in state.decks or created successfully. Then `verified = diff(manifest, await _read_state())`, return it.

## Verification

**Commands:**
- `make test` -- expected: all pass, 0 skipped among the 2.7 files
- `make lint` -- expected: clean
- `grep -rn "RED_PHASE" tests/integration/test_anki_setup_apply.py tests/unit/test_setup_apply_service.py tests/api/test_setup_apply.py tests/e2e/test_setup_apply.py` -- expected: no output

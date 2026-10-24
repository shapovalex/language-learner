---
title: 'Delete Items and verify Maintain Items on the released wheel'
type: 'feature'
ticket: '3'
created: '2026-10-24'
status: 'built'
baseline_revision: '2806fefb05e3436122c9a56e06a915114a390fee'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-5-3.md'
  - '{project-root}/_bmad-output/test-artifacts/acceptance/maintain-items-acceptance-5-3.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Item detail cannot delete an Item. Epic 5 also needs released-wheel evidence for editing, fresh reads, regeneration, search and deletion.

**Approach:** Reuse the Capture confirmation for permanent Item deletion, add a guarded DELETE use case with retryable media cleanup, activate the existing ATDD coverage, and prepare the human acceptance handoff with automated evidence.

## Boundaries & Constraints

**Always:**
- `DELETE /api/items/{lang}/{itemId}` returns empty 204 after cleanup, including repeat requests. Malformed ItemId returns 404 like detail reads; unknown Language returns 422. Failures use the existing AD-15 envelope.
- Under one shared Anki lock, resolve decoded ItemId in the Language's exact Category scopes; delete matching notes through the guarded client before enumerating/deleting matching managed media. Stop on any failure, with no compensation (AD-4/5/6/7). Cleanup still runs when the note is already gone; SetupGate applies to every write.
- Confirmation names the persisted Target, lists Understand, Produce, Write and Pronounce, explains history removal and no undo, and starts focus on Cancel. Preserve Capture dialog behavior, focus trapping and busy protection.
- Cancel/Escape and failure preserve local edits and Previews. Failure shows an inline alert and allows a newly confirmed retry. Success clears deleted-Item dirty state and navigates to a freshly read Language Items list without saving the buffer.
- The user performs the released-wheel checks on the Mac mini with LanguageLabDev, phone and desktop, reviewed Cards and a test media clip. Keep unobserved results pending; automated replay cannot establish real history deletion or actual Anki reply shapes.

**Never:** Audio generation/Preview, Voice, stale-audio warnings, new dependencies, unrelated refactors, ticket-file edits, fabricated manual passes, or a production release during this build. Push the feature branch and create a PR as instructed by AGENTS.md.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cancel | Unsaved Target/meaning/Preview | Persisted Target named; buffer retained; no DELETE | Focus returns to Delete |
| Pending | Confirm twice, Escape/back | One request; dialog stays busy with disabled buttons | Outcome stays on detail |
| Note failure | deleteNotes fails | Note/media unchanged; no cleanup | Existing error envelope |
| Partial cleanup | Note gone; second media deletion fails | Stop; next confirmation cleans leftovers | Inline error retains buffer |
| Isolation | Other Item/Language/Prefix present | Only scoped note and Prefix_ItemId managed filenames removed | Guard rejects unsafe writes |
| Repeat/absent | No matching note | Cleanup leftovers; then empty 204 | Cleanup errors still propagate |

</frozen-after-approval>

## Code Map

- `src/language_lab/features/items/routes.py`, `service.py` — add DELETE and service delegation beside get/save; reuse UUID4 validation and error mapping.
- `src/language_lab/ports/anki_store.py`, `tests/fakes/anki_store.py` — add matching `delete_item(language, item_id)` contract and fake behavior.
- `src/language_lab/adapters/anki/store.py` — reuse `_note_infos`, `_matching`, `_field`, integer validation, manifest scopes and `_lock.hold`; never call another lock-taking store method inside deletion.
- `src/language_lab/adapters/anki/guard.py`, `setup_gate.py` — existing guarded deleteNotes/deleteMediaFile and `media_pattern`; retain central boundary and readiness enforcement.
- `src/language_lab/static/api.js` — add deleteItem through shared request helper.
- `src/language_lab/static/screens/item-detail.js` — reuse loaded `item.target`, buffer/Preview state, mounted checks, renderEditor and router dirty handling; keep Save/regeneration contracts.
- `src/language_lab/static/router.js` — `confirmDestructive` already handles busy, Escape, back and focus; extend body safely for DOM content while preserving string callers.
- `src/language_lab/static/screens/captures.js` — reference `onDelete` and failure copy; retain existing behavior. `static/css/studio.css` provides destructive buttons/chips/dialog styles.
- `tests/support/item_delete.py`, `delete_item_screen.py` — existing real guarded adapter/replay and browser doubles. History evidence is outside the replay model.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/features/items/routes.py`, `service.py`, `src/language_lab/ports/anki_store.py`, `tests/fakes/anki_store.py` — add DELETE contract and delegation.
- [x] `src/language_lab/adapters/anki/store.py` — implement ordered deletion and validated media enumeration, including absent-note cleanup.
- [x] `src/language_lab/static/api.js`, `router.js`, `screens/item-detail.js` — wire Delete, structured confirmation, inline errors, safe retry and refreshed navigation; adjust `static/css/studio.css` only if needed.
- [x] `tests/api/test_items_delete.py`, `tests/integration/test_anki_item_delete.py`, `tests/e2e/test_item_delete.py` — activate 12 ATDD leaves, observe RED/GREEN; add meaningful boundary cases for validation, non-ready states, both Categories, malformed replies, no media, retries, lock release/contention, French routing and pending navigation.
- [x] `_bmad-output/test-artifacts/acceptance/maintain-items-acceptance-5-3.md` — link automated evidence and clarify release handoff; leave device/Anki results not run until observed.

**Acceptance Criteria:**
- Given activated ATDD AC-1 through AC-12, when run, then all pass with no module skips.
- Given existing Capture deletion and Item edit/search/regeneration flows, when regression tests run, then they remain green.
- Given a released wheel and the prepared acceptance record, when the user runs the five epic checks, then actual outcomes and reply fixtures can be recorded; until then manual acceptance stays pending.

## Implementation Notes

- Added guarded note-first deletion and validated media cleanup, including absent-note retries; added DELETE delegation and fake/adapter port parity.
- Reused the shared confirmation with safe DOM content and a div body; pending programmatic navigation is blocked like browser back. Cancellation and failures retain edit/Preview state.
- Automated verification: 47 deletion checks pass; full suite 1058 passed; Ruff lint/format and whitespace checks pass. Initial full run exposed the old port-method registry, now updated.
- Matrix audit: Cancel is covered by `test_cancel_preserves_edits_and_the_confirmation_traps_keyboard_focus` and Preview-retention cases; Pending by duplicate-submit and pending-navigation tests; Note failure by `test_note_delete_failure_stops_before_any_media_delete`; Partial cleanup by `test_media_failure_stops_and_retry_cleans_leftovers_after_note_is_gone`; Isolation by scoped-deletion, filename-filter and Prefix-guard tests; Repeat/absent by French repeat-delete, both-Category and absent-note cleanup tests. All ran and passed in the primary agent's 47-test verification.
- [Acceptance handoff](../../test-artifacts/acceptance/maintain-items-acceptance-5-3.md) and [automated evidence](../../test-artifacts/atdd/implementation-validation-5-3.json) retain manual released-wheel and real-Anki acceptance as not run.

- Review fix: wrong-Language absent-note requests now preserve media owned by another Language; four added adapter cases and the strengthened API case pass. Final verification: 51 deletion checks and 1062 full-suite tests passed; Ruff lint/format and whitespace checks passed. Nothing deferred; manual release acceptance remains pending.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 1, medium 0, low 0, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence |
|---|---|---|---|
| Absent requested-Language Item cleanup removes an existing other-Language Item's media | high | patch | Reproduced `delete_item(EN, FrenchItemId)` against the guarded replay: French note retained, three media files removed, success returned. Before absent-note cleanup, preserve media when the ItemId is owned by another Language. Fixed with an exact other-Language ownership lookup before absent-note cleanup; four added adapter cases and the strengthened API case pass. All 1062 regression tests pass. |

## Verification

- `.venv/bin/pytest tests/api/test_items_delete.py tests/integration/test_anki_item_delete.py tests/e2e/test_item_delete.py -q` — all deletion checks pass.
- `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` — clean.
- `.venv/bin/pytest -q` and `git diff --check` — regression suite passes and no whitespace errors.

---
runScope: 'story'
runKey: 'story-5-3'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-24'
storyId: '5.3'
storyKey: '5-3'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-maintain-items/tickets.toml (entry 3)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-5-3.md'
generatedTestFiles:
  - 'tests/api/test_items_delete.py'
  - 'tests/integration/test_anki_item_delete.py'
  - 'tests/e2e/test_item_delete.py'
inputDocuments:
  - '_bmad/config.toml (resolved core and modules.tea)'
  - 'AGENTS.md'
  - '_bmad-output/initiative-languagelab-v1/epic-maintain-items/tickets.toml (entry 3)'
  - '_bmad-output/initiative-languagelab-v1/epic-maintain-items/epic-maintain-items.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-4, AD-5, AD-6, AD-7, AD-8, AD-13, AD-19)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-25, AC11, AC12, AC21)'
  - 'pyproject.toml'
  - 'tests/conftest.py'
  - 'tests/e2e/conftest.py'
  - 'tests/README.md'
  - '.agents/skills/bmod-tea/knowledge/data-factories.md'
  - '.agents/skills/bmod-tea/knowledge/component-tdd.md'
  - '.agents/skills/bmod-tea/knowledge/test-quality.md'
  - '.agents/skills/bmod-tea/knowledge/test-healing-patterns.md'
  - '.agents/skills/bmod-tea/knowledge/test-levels-framework.md'
  - '.agents/skills/bmod-tea/knowledge/test-priorities-matrix.md'
  - '.agents/skills/bmod-tea/knowledge/ci-burn-in.md'
acceptanceCriteria:
  - {"id": "AC-1", "idSource": "generated", "text": "Delete opens a reusable alertdialog naming the persisted Target, its four Cards and their review history, with Delete permanently and Cancel."}
  - {"id": "AC-2", "idSource": "generated", "text": "Item deletion is Prefix guarded and refuses a write unless SetupState is ready, leaving the note and media unchanged."}
  - {"id": "AC-3", "idSource": "generated", "text": "The complete Item delete use case, including media cleanup, holds the shared Anki lock."}
  - {"id": "AC-4", "idSource": "generated", "text": "Delete removes only the Language-scoped Item note and its four Cards, then every matching Prefix_ItemId_* media file, preserving other Items and Prefixes."}
  - {"id": "AC-5", "idSource": "generated", "text": "Cancel preserves the Item and local edits, sends no DELETE and returns focus to Delete; Escape and keyboard focus follow the reusable confirmation pattern."}
  - {"id": "AC-6", "idSource": "generated", "text": "A failed note deletion stops the sequence and returns an error without attempting media deletion."}
  - {"id": "AC-7", "idSource": "generated", "text": "A media cleanup failure stops the sequence; retry tolerates the already-deleted note and finishes remaining matching media cleanup."}
  - {"id": "AC-8", "idSource": "generated", "text": "While DELETE is pending the confirmation remains open, its buttons are disabled and duplicate submissions are prevented."}
  - {"id": "AC-9", "idSource": "generated", "text": "A failed DELETE keeps Item detail and local edits, shows an inline error and allows a newly confirmed retry."}
  - {"id": "AC-10", "idSource": "generated", "text": "On phone, confirmed deletion returns to the refreshed Language Items list without the deleted Item or a spurious unsaved-changes prompt."}
  - {"id": "AC-11", "idSource": "generated", "text": "On desktop, confirmed deletion returns to the refreshed Language Items list while preserving unrelated Items."}
  - {"id": "AC-12", "idSource": "generated", "text": "DELETE /api/items/{lang}/{itemId} returns 204 with no body and removes the Item from subsequent reads."}
---

# ATDD Checklist: Story 5.3 — Delete Items and verify Maintain Items on the released wheel

## Preflight

Create mode inferred from the request. Approved high-risk ticket entry 3, after 5.1, 5.2 and 3.3; no leaf story file. All criterion ids are generated in source order from the description/verify clause with architecture and UX constraints. The registry above covers automated product behavior. The ticket also requires a human released-wheel acceptance run of all five epic Done-when checks: this is a separate pending handoff, never an automated pass.

Stack: backend (Python manifest/pytest), with a static UI tested by Python Playwright. Configured framework and local .venv are present. There is no epic-5 or system test design in test-design/ or the legacy test-artifacts root. Priorities derive from high-risk destructive behavior and AD-6 isolation.

Playwright-utils/Pact flags are true, but package/runner/relevance gates are closed: no Node manifest, Playwright JS runner or Pact artifacts. Core plus backend knowledge fragments apply. Browser recording is unnecessary for unimplemented standard CRUD controls. Reuse Capture deletion's confirmation and the Items test factories.

Proposed minimum contract: DELETE /api/items/{lang}/{itemId} -> 204, including already-gone Items so partial cleanup is retryable. AnkiStore.delete_item(language, item_id) runs under one lock; exact Language/Category-scoped lookup, Prefix guard and SetupGate precede writes. Delete note before cleanup; no compensation. Failure is the existing AD-15 error envelope. Generated selectors use the canonical EXPERIENCE.md Delete copy and reusable Capture dialog behavior.

## Generation mode

AI generation from approved requirements and source; Python pytest/Playwright patterns.

## Strategy

One primary skipped leaf per criterion. API: AC-12. Adapter integration: AC-2, AC-3, AC-4, AC-6, AC-7. Browser: AC-1, AC-5, AC-8, AC-9, AC-10, AC-11. All P0 due to destructive-action integrity; guard, isolation and failure checks stay below the browser layer. Secondary branches are green-phase checklist work. Manual release evidence remains pending.

## Generation and aggregation

Execution mode `auto`, capability probing enabled: available subagents selected. The skill explicitly requested parallel workers, which produced API/adapter and browser outputs independently. Both output registries match preflight exactly. All 12 P0 leaves are module-skipped, the pytest equivalent of test.skip. No production files or dependencies changed.

| Criterion | Primary scaffold |
| --- | --- |
| AC-1 | `tests/e2e/test_item_delete.py::test_delete_names_the_stored_item_and_all_four_cards` |
| AC-2 | `tests/integration/test_anki_item_delete.py::test_setup_gate_refuses_delete_and_preserves_note_cards_and_media` |
| AC-3 | `tests/integration/test_anki_item_delete.py::test_delete_holds_one_shared_lock_through_the_last_media_write` |
| AC-4 | `tests/integration/test_anki_item_delete.py::test_delete_removes_only_the_scoped_note_cards_and_matching_media_in_order` |
| AC-5 | `tests/e2e/test_item_delete.py::test_cancel_preserves_edits_and_the_confirmation_traps_keyboard_focus` |
| AC-6 | `tests/integration/test_anki_item_delete.py::test_note_delete_failure_stops_before_any_media_delete` |
| AC-7 | `tests/integration/test_anki_item_delete.py::test_media_failure_stops_and_retry_cleans_leftovers_after_note_is_gone` |
| AC-8 | `tests/e2e/test_item_delete.py::test_pending_delete_keeps_the_dialog_disabled_and_ignores_duplicate_submit` |
| AC-9 | `tests/e2e/test_item_delete.py::test_failed_delete_retains_the_buffer_and_a_new_confirmation_can_retry` |
| AC-10 | `tests/e2e/test_item_delete.py::test_phone_delete_returns_to_a_refreshed_list_without_an_unsaved_prompt` |
| AC-11 | `tests/e2e/test_item_delete.py::test_desktop_delete_refreshes_the_list_and_preserves_the_other_item` |
| AC-12 | `tests/api/test_items_delete.py::test_delete_item_answers_204_and_subsequent_reads_leave_it_out` |


## Factories and mock requirements

New `tests/support/item_delete.py` composes the real guarded Anki adapter, replay collection,
SetupGate and observed shared Anki lock. Valid AD-7 filenames include current and leftover
media. AC-4 uses the same ItemId for the English target, French control and second-Prefix
control, proving Language/Prefix isolation. Histories are outside the replay model.

New `tests/support/delete_item_screen.py` supplies canonical accessible locators and a
page-local GET/DELETE double. It counts list refreshes and all mutation requests, retains
local test data after a failed DELETE and removes only the target row on success. Helpers
reuse existing settings, ItemContent, live server, network and keyboard fixtures. Browser
coverage tests client behavior; it does not claim to establish real Anki deletion.
No new packages, authentication fixtures or data-testid attributes are required.

## Implementation checklist and green-phase follow-up

- [ ] AC-1: reuse the Capture alertdialog from the router on Item detail. Canonical Delete
  copy names the persisted Target, 4 Cards and history; list Understand, Produce, Write,
  Pronounce and no undo. Keep description and title accessible. Green phase: Sentence,
  French, long/special-character Target, small-screen dialog fit and a missing Item.
- [ ] AC-2: route all deletes through guarded client.invoke and SetupGate. Add the other
  non-ready states, malicious/out-of-Prefix lookup and malformed notes/media replies.
- [ ] AC-3: hold the shared Anki lock from lookup through the final cleanup. The primary
  scaffold records a single hold and every transport request inside it. Add contention
  with Save/Sync and the anki_busy timeout, including lock release after failure.
- [ ] AC-4: resolve the note only within the requested Language's managed Category types;
  decode ItemId with the shared codec. Delete that note before deleting every matching
  managed media filename, including unreferenced leftovers; do not compensate on failure.
  Add both Categories, empty Audio with leftovers, no media, markup in ItemId and a
  matching note disappearing between reads. Preserve Prefix guard validation of names.
- [ ] AC-5: Cancel/Escape preserve the buffer and restore focus; trap focus with safe default
  Cancel. Add browser back and scrim behavior according to the reused confirmation.
- [ ] AC-6: propagate note-deletion failure and attempt no media writes. Add network and
  busy errors and confirm the existing AD-15 envelope without echoing content.
- [ ] AC-7: stop on the first media failure; retry cleanup when the note is already gone.
  Do not treat not-found as an early return before leftover cleanup. Add repeated success,
  already-missing media, enumeration failure and Setup-required cleanup on an absent note.
- [ ] AC-8: keep the busy dialog open with labels unchanged, both buttons disabled and
  Escape unable to close it. Add browser-back/in-flight navigation coverage.
- [ ] AC-9: follow Capture deletion's inline failure pattern. Anki-unavailable copy is a
  scaffold default reused from Captures. Keep edits and ItemId after failure; a new Delete
  confirmation retries. Add generic envelope and network-failure copy.
- [ ] AC-10/AC-11: after success clear deleted Item dirty state and navigate to a freshly
  read Language Items list. Do not Save local edits or show a discard prompt on this
  successful deletion. Preserve unrelated rows. Add French routing and late-read races.
- [ ] AC-12: add DELETE /api/items/{lang}/{itemId}, ItemService.delete and the AnkiStore
  port/fake/adapter delete_item(language, item_id) method; answer 204 with no body after
  cleanup. Add malformed UUID, unknown Language, repeated DELETE and 409/503 envelopes;
  keep port/fake/adapter signatures aligned.
- [ ] Complete [the released-wheel acceptance record](../acceptance/maintain-items-acceptance-5-3.md)
  with the user after implementation and release. It covers all five epic Done-when
  checks, reviewed Cards, identity/history preservation during edits, deletion isolation
  and real AnkiConnect reply comparisons. Every manual result is currently not run.

## Activation and handoff

There is no leaf story file to edit. Pass epic-maintain-items/tickets.toml entry 3,
this checklist, generatedTestFiles and the pending acceptance record to bmad-build.
Remove the module skip for the current task (keep remaining leaves skipped), confirm
RED, implement, confirm GREEN and refactor. Retain the existing Capture deletion, Items
edit/Save, search and regenerate suites. Implementation effort is not estimated by ATDD;
this is the approved high-risk story with a separate human acceptance requirement.

```sh
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest tests/api/test_items_delete.py tests/integration/test_anki_item_delete.py tests/e2e/test_item_delete.py -q
.venv/bin/pytest tests/api/test_captures_delete.py tests/integration/test_anki_capture_delete.py tests/e2e/test_captures_delete.py tests/api/test_items_save.py tests/e2e/test_item_edit.py tests/e2e/test_item_regenerate.py -q
```

Python runner adaptation: adapter actions resolve the future method inside a coroutine so
settle captures the absent-method outcome and the criterion assertion fails directly.
Browser journeys currently fail on the missing Delete action before the outcome matcher;
Python Playwright has no outer promise matcher. This is a recorded validation limitation,
not proof of the subsequent state transitions. Re-observe those transitions during build.


## Validation and completion (2026-10-24)

- Registry/leaf validation passed: exactly 12 generated ids and one P0 scaffold per id.
  Worker registries matched in order, ids, idSource and text. No placeholder assertions.
- Normal run: **12 skipped**, 0 errors. Module skips remain in source for task activation.
- Temporary activation: **12 failed**, 0 setup errors. API AC-12 first fails at 405 rather
  than 204. Adapter checks fail at the promised gate/lock/deletion assertions because
  delete_item is absent. Revised AC-7 was reactivated independently and first fails at
  remaining media after retry; both calls execute before that assertion.
- All six browser journeys load the existing editor/list, then fail at the missing Delete
  button. Their subsequent transitions remain to be observed during implementation;
  this Python adaptation does not satisfy the literal outer-promise assertion pattern.
- Chromium initially could not launch inside the sandbox. Rerunning with the necessary
  browser/server permission removed that environment error; all final failures are in
  test bodies. No browser recording sessions or test servers remain running.
- Neighbouring Capture delete, Item Save/edit and regeneration regressions: **77 passed**.
- Ruff lint/format passed across **307 Python files**. git diff --check passed.
- [Validation evidence](atdd-validation-5-3.json) records per-leaf first failures and counts.
  The real-Anki released-wheel acceptance is **not run** and remains a build handoff.

ATDD scaffolding is complete. Next workflow: bmad-build for Epic 5, Story 3; then release
and run the human acceptance record. This workflow does not mark the story implemented.

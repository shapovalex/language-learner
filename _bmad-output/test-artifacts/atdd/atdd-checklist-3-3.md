---
runScope: 'story'
runKey: 'story-3-3'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-22'
storyId: '3.3'
storyKey: '3-3'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-captures/tickets.toml (entry 3)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-3-3.md'
generatedTestFiles:
  - 'tests/integration/test_anki_capture_delete.py'
  - 'tests/api/test_captures_delete.py'
  - 'tests/e2e/test_captures_delete.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-captures/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-captures/epic-captures.md (Done when 3; Notes 2026-10-21)'
  - '_bmad-output/initiative-languagelab-v1/epic-captures/story-captures-list-and-capture-detail-plan.md'
  - '_bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md (CAP-3; Assumptions, Capture delete dialog)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-13)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-4, AD-5, AD-6, AD-19)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Key strings: Capture detail, Delete; Alert dialog; Buttons busy state; Accessibility Floor; Interaction Primitives)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Delete.dc.html, S-NewItem.dc.html, S-CapturesDesk.dc.html'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-3-2.md (format, conventions)'
  - 'No test design for epic 3: test-design/test-design-epic-3.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{store,guard}.py, ports/anki_store.py, features/captures/{routes,service}.py, app.py (_APP_ERROR_STATUS)'
  - 'src/language_lab/static/{router,api}.js, static/index.html (#unsaved-alert), static/screens/captures.js, static/css/studio.css (.alert-dialog)'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_state,anki_connect,aio,network,navigation,keys,unsaved,viewports}.py'
  - 'tests/integration/{test_anki_captures,test_anki_capture_reads}.py, tests/api/test_captures_read.py, tests/e2e/{test_captures_list,test_unsaved_alert}.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'delete_capture deletes only the note with that CaptureId (and its card); other Captures, other managed notes and another Prefix''s Capture stay; the CaptureId is matched in Python, never in a query (AD-4)' }
  - { id: 'AC-2', idSource: 'generated', text: 'A repeated delete of a Capture already gone succeeds and sends no deleteNotes' }
  - { id: 'AC-3', idSource: 'generated', text: 'delete_capture is behind the setup gate: a gated Anki is setup_required, no write is sent and the note stays (AD-19)' }
  - { id: 'AC-4', idSource: 'generated', text: 'DELETE /api/captures/{captureId} is 204 with no body and only that Capture is gone' }
  - { id: 'AC-5', idSource: 'generated', text: 'DELETE for a CaptureId no Capture holds is 204 (a retried delete succeeds)' }
  - { id: 'AC-6', idSource: 'generated', text: '"Delete Capture" in Capture detail opens the alert dialog "Delete this Capture?" with the body "This removes the Capture from Anki. Items you made from it stay." and Delete permanently and Cancel' }
  - { id: 'AC-7', idSource: 'generated', text: 'Cancel closes the dialog with no DELETE sent and keeps the Capture' }
  - { id: 'AC-8', idSource: 'generated', text: 'On the phone, Delete permanently deletes the Capture and lands on /captures, the list without it' }
  - { id: 'AC-9', idSource: 'generated', text: 'On desktop, after Delete permanently nothing is selected (the hint shows) and the Capture is gone from the list' }
  - { id: 'AC-10', idSource: 'generated', text: 'Keyboard: focus starts on Cancel, Tab / Shift+Tab stay within the dialog, Esc cancels, and focus returns to "Delete Capture"' }
  - { id: 'AC-11', idSource: 'generated', text: 'While the DELETE is in flight the dialog stays open with Delete permanently disabled and its label kept' }
  - { id: 'AC-12', idSource: 'generated', text: 'A failed delete closes the dialog, keeps the Capture, and shows the inline alert "Not deleted — Anki isn''t reachable" / "Make sure Anki Desktop is open on the Mac mini, then try again."' }
---

# ATDD Checklist: Story 3.3, Delete a Capture after confirmation

## Run context

- **Story source:** epic-captures `tickets.toml`, entry 3 (`risk = "low"`, after entry 2). There is no story file, so this checklist holds the criteria. AC-1 to AC-12 follow the ticket's description in source order, with the verify clauses folded in:
  - "only the targeted note deleted, other Captures and non-managed notes untouched" is AC-1.
  - "a repeated delete succeeding" is AC-2 (adapter) and AC-5 (API).
  - "behind the setup gate and Prefix guard" is AC-3. The guard applies through `client.invoke`, and it already passes `deleteNotes` on notes of a manifest note type (`guard.py`).
  - "Cancel keeping the Capture" is AC-7, "Delete permanently removing it from the list" AC-8 and AC-9, "keyboard focus behavior" AC-10, and "the error state" AC-12.

  AC-11 and AC-12's copy come from decisions taken with the user. All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screens run through pytest-playwright, as in epics 1 to 3 (dev-only, NFR-11).
- **Test design:** none for epic 3. Priorities follow the ticket's risk (low) and epic Done when 3. Every criterion is on the delete path the ticket names, so all are P0.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - Changed: `ports/anki_store.py` (`delete_capture`), `adapters/anki/store.py`, `tests/fakes/anki_store.py` (port, adapter and fake together), `tests/unit/test_anki_store_port.py` (the method set), `features/captures/{service,routes}.py`, `static/api.js` (`deleteCapture`), `static/router.js` and `static/index.html` (the reusable confirmation dialog), `static/screens/captures.js`, `static/css/studio.css`.
  - Tests (done in this run): `tests/support/anki_state.py` answers `deleteNotes` with `writes=True`. It removes the notes and their cards, answers `null`, and ignores ids it doesn't have. The reply is hand-built from AnkiConnect's documented one and gets checked at the acceptance run (entry 4), as the epic's Notes decided.

### Decisions taken with the user (2026-10-22)

| Question | Decision |
| --- | --- |
| What does the dialog do while the DELETE is in flight? | **It stays open, busy.** Delete permanently is disabled and keeps its label (EXPERIENCE.md busy rule), and Cancel is disabled too. The dialog closes when the DELETE answers, with success or failure. |
| Where and how does a failed delete show its error? | **An inline alert in Capture detail.** The dialog closes and the detail keeps the Capture. It shows `role="alert"` "Not deleted — Anki isn't reachable" / "Make sure Anki Desktop is open on the Mac mini, then try again." Any other code shows "Not deleted" with the envelope's message. There is no Try again: Delete Capture is right there and asks again. |

### Defaults taken without a question

- **Port:** `delete_capture(capture_id) -> None`. It raises `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`, and a CaptureId no Capture holds returns `None`.
- **Adapter:** one lock hold:
  - Run `_capture_infos(note_query(manifest, "<Prefix> Capture"))`, then match each entry's decoded, stripped CaptureId in Python.
  - When something matches, send `deleteNotes` with the `noteId` of every match, normally one. Create Capture prevents duplicates under the lock, but if a CaptureId appears twice, both notes are that Capture.
  - With no match, send no write.
  - The gate applies at `deleteNotes` (the reads go first, as in Create Capture). So a gated Anki with nothing to delete returns success. With the Capture present it is `setup_required`.
- **Fake:** `delete_capture()` pops the CaptureId from `captures`, with no error when it is absent. It raises `anki_busy` or `anki_unavailable` as the other methods do.
- **Route:** DELETE /api/captures/{captureId} answers 204 with no body. A CaptureId that isn't a lowercase canonical UUIDv4 was never a Capture, so it is 404 `not_found` without calling the store, as GET does. `SETUP_REQUIRED` is already 409.
- **Dialog (router):**
  - The router gets a reusable destructive confirmation, for example `confirmDestructive({title, body, confirmLabel, onConfirm})` or a promise-returning `confirm(...)`, so Item delete in epic-maintain-items reuses it.
  - It is built on the existing `.alert-dialog`: either `#unsaved-alert` generalized, or a sibling `<dialog role="alertdialog">` with `aria-labelledby` and `aria-describedby`.
  - Its behavior: Delete permanently (destructive) comes first and Cancel (secondary) second, as in S-Delete. Focus starts on Cancel and Tab cycles over the two buttons (`cycleFocus`). Esc and a forced close count as Cancel. Focus returns to the trigger.
  - The unsaved alert's behavior and tests stay unchanged.
- **Screen:**
  - Capture detail shows a "Delete Capture" button. Per S-NewItem it is in the header on the phone, and after the "Captured …" line on desktop. Use the `button-destructive-text` style.
  - It is shown only when the Capture is loaded: not on "This Capture isn't in Anki.", the loading state or a failed detail.
  - After a successful delete:
    - drop the Capture from `list.captures` and `list.saved`;
    - navigate to `/captures` through the router, a same-screen update that keeps the compose text;
    - move focus to the "Captures" heading (`tabindex="-1"`), since the button is gone.

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`. List and detail contents, the failed DELETE and the pending DELETE are stubbed at the network (by method). A delete that succeeds runs against the live server, on a Capture the test saves itself, so no 204 has to be stubbed. Execution is **sequential**, in this session, with no subagents (as in stories 3.1 and 3.2).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | The target Capture (its CaptureId in editor markup), two other Captures, a Vocabulary note, and a `LanguageLabDev` Capture with the same CaptureId | the collection's notes are exactly the others |
| AC-2 | Integration | P0 | Delete, then delete again (the transition is the second call) | (outcome, writes sent by the second call) is (None, []) |
| AC-3 | Integration | P0 | Gate `needs_setup` / `needs_migration` / `newer_schema`, Capture present | the code is `setup_required` |
| AC-4 | API | P0 | Fake holding the target and one other | status 204 |
| AC-5 | API | P0 | Fake without the target | status 204 (today 405: no DELETE route) |
| AC-6 | E2E | P0 | Desktop, stubbed detail, click "Delete Capture" | the "Delete this Capture?" alertdialog is visible |
| AC-7 | E2E | P0 | Open the dialog, then Cancel | the dialog is hidden (then no DELETE was recorded) |
| AC-8 | E2E | P0 | Phone, live server: save, open, Delete permanently | the URL is /captures |
| AC-9 | E2E | P0 | Desktop, live server: save, open, Delete permanently | the hint "Choose a Capture to see it here." is visible |
| AC-10 | E2E | P0 | Open the dialog from the keyboard (focus "Delete Capture", Enter) | Cancel is focused |
| AC-11 | E2E | P0 | DELETE held, Delete permanently pressed | Delete permanently is disabled |
| AC-12 | E2E | P0 | DELETE stubbed 503 `anki_unavailable` | the "Not deleted — Anki isn't reachable" alert is visible |

### Secondary branches for green-phase automation

- AC-1: Anki down is `anki_unavailable` (written, in the integration file). A `{}` notesInfo entry is skipped. A malformed reply is `anki_unavailable`. A guard refusal can't happen, since the scope is exact, so it isn't tested here (`test_anki_prefix_guard.py` covers `deleteNotes`).
- AC-3: a gated Anki with no such Capture returns success (no write needed).
- AC-4: an unreachable fake is 503 and keeps the Capture (written). `create_app(settings)` with no injected store has the DELETE route (written). GET after DELETE is 404.
- AC-5: `capture-1` is 404 `not_found` and never reaches the store (written).
- AC-6: the dialog has `role="alertdialog"` with labelled title and description. Delete permanently is styled destructive. The dialog fits `viewports.ALL` without horizontal scroll.
- AC-7: Cancel returns focus to "Delete Capture". After Cancel the dialog opens again, and a second Cancel also sends nothing.
- AC-8: unsaved compose text survives the delete, with no unsaved alert (same-screen navigation). After the delete, focus is on the "Captures" heading. A reload doesn't bring the Capture back (asserted in AC-8's leaf).
- AC-9: iPad landscape behaves the same. The header count drops by one ("N Captures · newest first").
- AC-10: WebKit uses Alt+Tab (`tests/support/keys.py`), and `make test-webkit` covers it. A browser back while the dialog is open closes it as Cancel.
- AC-11: a second press while busy sends no second DELETE (asserted as `len(deletes) == 1`). Cancel is disabled while busy.
- AC-12: a non-`anki_unavailable` failure (for example 503 `anki_busy`) shows "Not deleted" with the envelope's message. A 409 `setup_required` shows its envelope message. A network failure shows "LanguageLab could not reach the server." Delete Capture then opens the dialog again. On the phone the alert sits on the detail screen.
- No Delete Capture shows on "This Capture isn't in Anki." or while the detail loads.

## TDD red phase (current)

Red-phase scaffolds are generated, each file skipped by a module-level `pytestmark = pytest.mark.skip(reason=...)`:

- Integration: 3 primary tests (5 cases) and 1 secondary in `tests/integration/test_anki_capture_delete.py`.
- API: 2 primary tests and 3 secondaries in `tests/api/test_captures_delete.py`.
- E2E: 7 tests in `tests/e2e/test_captures_delete.py`.

**Red check (2026-10-22):** each file was run with its skip marker removed. All 18 cases failed for the expected reasons:

- `AttributeError: 'AnkiConnectStore' object has no attribute 'delete_capture'`.
- DELETE /api/captures/{id} answered 405 Method Not Allowed: only GET is routed there.
- The "Delete Capture" button wasn't found, so each E2E test timed out on its click or focus. In AC-8 and AC-9 the live-server Save and opening the row worked first.

Afterwards the skip markers were restored. `make test-fast` passed (561 passed, 11 skipped). The new E2E file collected as 7 skipped, and the 3.1 and 3.2 Captures E2E files still pass (34 passed). `ruff check` and `ruff format --check` are clean.

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `integration/test_anki_capture_delete.py::test_delete_capture_deletes_only_the_note_with_that_capture_id` |
| AC-2 | `integration/test_anki_capture_delete.py::test_a_repeated_delete_succeeds_and_sends_no_write` |
| AC-3 | `integration/test_anki_capture_delete.py::test_a_gated_anki_refuses_delete_capture_and_keeps_the_note` |
| AC-4 | `api/test_captures_delete.py::test_delete_removes_the_capture_and_answers_204` |
| AC-5 | `api/test_captures_delete.py::test_a_retried_delete_of_a_capture_already_gone_is_204` |
| AC-6 | `e2e/test_captures_delete.py::test_delete_capture_opens_the_confirmation_dialog` |
| AC-7 | `e2e/test_captures_delete.py::test_cancel_closes_the_dialog_and_keeps_the_capture` |
| AC-8 | `e2e/test_captures_delete.py::test_on_the_phone_delete_permanently_lands_on_the_list_without_it` |
| AC-9 | `e2e/test_captures_delete.py::test_on_desktop_after_delete_nothing_is_selected` |
| AC-10 | `e2e/test_captures_delete.py::test_the_dialog_keeps_keyboard_focus_and_esc_cancels` |
| AC-11 | `e2e/test_captures_delete.py::test_while_the_delete_is_in_flight_the_dialog_stays_open_and_busy` |
| AC-12 | `e2e/test_captures_delete.py::test_a_failed_delete_keeps_the_capture_and_shows_the_error` |

## Next steps (task-by-task activation)

1. **Port, adapter and fake:**
   - Add `delete_capture` to `AnkiStore`, `AnkiConnectStore` and `FakeAnkiStore`, and extend `tests/unit/test_anki_store_port.py`.
   - Un-skip the integration file (AC-1 to AC-3).
2. **Service and route:**
   - Add `CaptureService.delete` and the DELETE route (204; a malformed id is 404 before the store).
   - Un-skip the API file (AC-4, AC-5).
3. **Dialog, API client and screen:**
   - Add the reusable confirmation dialog in `router.js` and `index.html`, and `deleteCapture` in `api.js`.
   - Add Delete Capture, the busy state, the post-delete navigation and the failure alert in `captures.js`, styled in `studio.css`.
   - Un-skip the E2E file (AC-6 to AC-12).
4. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test`, `uv run ruff check` and `uv run ruff format --check`.

## Implementation guidance

- **Endpoint:** DELETE /api/captures/{captureId} answers 204, 404 `not_found` (malformed id only), 409 `setup_required`, or 503 `anki_unavailable` / `anki_busy`.
- **UI:**
  - "Delete Capture" in Capture detail.
  - The confirmation dialog: title, body, Delete permanently and Cancel, focus on Cancel, the Tab trap, Esc, and focus returned on close.
  - The busy state while the delete is in flight.
  - After success: /captures without the Capture (desktop: the hint).
  - The inline failure alert in detail.
- **Wiring to check in review:**
  - `create_app` serves DELETE for the injected and the built store.
  - `api.js`'s 204 path (`request` returns `null`) is used.
  - The unsaved alert still behaves as story 1.7's tests pin it (`tests/e2e/test_unsaved_alert.py`).
  - The CaptureId never appears in a query.

## Validation (step 5)

- Prerequisites: the criteria come from entry 3; the framework is pytest and pytest-playwright; the dev environment runs.
- Every leaf test's docstring names exactly one declared AC, and each AC has exactly one primary leaf. Parametrized cases (AC-3's gate states) are cases of that leaf. Secondary tests are marked p1, under "Secondary cases (green phase)".
- Each leaf's first assertion is the criterion-defining one. Setup actions stay unasserted before it: arranging the collection, stubbing, `goto`, the live-server Save and opening the row, and the first delete in AC-2.
  - AC-2's and AC-7's transitions (the second delete, Cancel) come before their first assertion.
  - AC-4's DELETE response is checked first by status only.
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were restored with their skip markers.

## Completion

- **Risks and assumptions:**
  - Reusing `#unsaved-alert` for the delete dialog risks story 1.7's guard behavior: the shared `pendingAnswer`, the forced-close handling, and `describeLoss`. Keep the unsaved-alert tests green, or use a sibling dialog that shares the focus-trap and Esc code.
  - The DELETE on the live server changes the session-shared fake. AC-8 and AC-9 delete only the Capture they saved, with a unique text, so other tests' rows aren't affected.
  - The real `deleteNotes` reply (`null`) is hand-built until entry 4's acceptance run.
  - AC-10 presses Enter on the focused button to open the dialog, so `trigger` must be the "Delete Capture" button for focus to return to it.
- **Next workflow:** `bmad-build` for story 3.3.

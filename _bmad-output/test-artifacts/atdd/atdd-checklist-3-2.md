---
runScope: 'story'
runKey: 'story-3-2'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-22'
storyId: '3.2'
storyKey: '3-2'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-captures/tickets.toml (entry 2)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-3-2.md'
generatedTestFiles:
  - 'tests/integration/test_anki_capture_reads.py'
  - 'tests/api/test_captures_read.py'
  - 'tests/e2e/test_captures_list.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-captures/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-captures/epic-captures.md (Done when 2; Notes 2026-10-21)'
  - '_bmad-output/initiative-languagelab-v1/epic-captures/story-tracer-save-a-capture-from-the-captures-screen-plan.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-4, AD-9, AD-13, AD-15, AD-19, Consistency Conventions)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Captures copy, Capture detail copy, List row, Skeleton, Captures empty, Back link, Responsive & Platform)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Captures.dc.html, S-CapturesDesk.dc.html'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-3-1.md (format, conventions)'
  - 'No test design for epic 3: test-design/test-design-epic-3.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{client,store,query,codec,guard}.py, ports/anki_store.py, domain/{captures,errors}.py, features/captures/{routes,service}.py, app.py'
  - 'src/language_lab/static/{router,api}.js, static/screens/{captures,setup}.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_state,anki_connect,aio,network,navigation,viewports,live_server}.py, tests/support/fixtures/{live_server,logs}.py'
  - 'tests/integration/test_anki_captures.py, tests/api/{test_captures,test_request_log}.py, tests/e2e/{test_captures_compose,test_setup_readiness}.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'list_captures returns every Capture of the Prefix with its fields decoded through the codec, from the exact Capture note-type scope only; Anki ids stay in the adapter' }
  - { id: 'AC-2', idSource: 'generated', text: 'list_captures is newest first by CreatedAt' }
  - { id: 'AC-3', idSource: 'generated', text: 'get_capture returns the Capture with that CaptureId, matched in Python and never sent in a query (AD-4)' }
  - { id: 'AC-4', idSource: 'generated', text: 'get_capture of an unknown CaptureId is not_found' }
  - { id: 'AC-5', idSource: 'generated', text: 'GET /api/captures is 200 with {captures: [{captureId, text, createdAt}]}, newest first' }
  - { id: 'AC-6', idSource: 'generated', text: 'GET /api/captures/{captureId} is 200 with that Capture' }
  - { id: 'AC-7', idSource: 'generated', text: 'GET /api/captures/{captureId} for a CaptureId no Capture holds is 404 not_found, from the Capture route' }
  - { id: 'AC-8', idSource: 'generated', text: 'On the phone the list sits under the compose box with "Newest first", one row per Capture, newest first' }
  - { id: 'AC-9', idSource: 'generated', text: 'On the phone, opening a row lands on /captures/<captureId>, the Capture detail as its own screen with the "‹ Captures" back link (route added in router.js)' }
  - { id: 'AC-10', idSource: 'generated', text: 'On desktop and iPad landscape (≥ 1024px) list and detail are two panes with the open Capture selected and "N Captures · newest first"' }
  - { id: 'AC-11', idSource: 'generated', text: 'Rows show relative creation time in the browser time zone ("Today · 21:14", "Yesterday · 19:40", "Oct 5 · 12:31", "Oct 4, 2025 · 22:05"); detail reads "Captured today · 21:14"' }
  - { id: 'AC-12', idSource: 'generated', text: 'The list shows a skeleton ("Loading Captures…") while it loads' }
  - { id: 'AC-13', idSource: 'generated', text: 'With no Captures, "No Captures yet." shows under the compose box' }
  - { id: 'AC-14', idSource: 'generated', text: 'A newly saved Capture tops the list' }
  - { id: 'AC-15', idSource: 'generated', text: 'On desktop with no Capture open the right pane reads "Choose a Capture to see it here."' }
  - { id: 'AC-16', idSource: 'generated', text: 'A Capture that is not in Anki shows "This Capture isn''t in Anki." with the back link' }
---

# ATDD Checklist: Story 3.2, Captures list and Capture detail

## Run context

- **Story source:** epic-captures `tickets.toml`, entry 2 (`risk = "low"`, after entry 1). There is no story file, so this checklist holds the criteria. AC-1 to AC-16 follow the ticket's description in source order, with the verify clauses folded in:
  - "ordering" is AC-2 (adapter) and AC-5 (API).
  - "codec decoding of Anki-editor markup" is AC-1 and AC-3.
  - "an unknown CaptureId returning not_found" is AC-4 (adapter) and AC-7 (API).
  - "the list newest first, skeleton and empty state" is AC-8, AC-12 and AC-13.
  - "a saved Capture at the top" is AC-14.
  - "opening one landing on its detail (own screen on phone, selected pane on desktop)" is AC-9 and AC-10.

  AC-15 and AC-16 come from decisions taken with the user. All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screens run through pytest-playwright, as in epics 1 to 3 (dev-only, NFR-11).
- **Test design:** none for epic 3. Priorities follow the ticket's risk (low) and epic Done when 2. Every criterion is on the list/detail path the ticket names, so all are P0.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - Changed: `ports/anki_store.py` (`list_captures`, `get_capture`), `adapters/anki/store.py`, `tests/fakes/anki_store.py` (port, adapter and fake together), `features/captures/{service,routes}.py`, `app.py` (`NOT_FOUND` → 404 in `_APP_ERROR_STATUS`), `static/api.js` (`listCaptures`, `getCapture`), `static/router.js` (the `/captures/<captureId>` route), `static/screens/captures.js`, `static/css/studio.css`.
  - Tests (done in this run):
    - `tests/support/network.py`: `stub_api_error`, `stub_api_json` and `HeldRoute` take `method=`. Requests with another method go on to the server. Without it, behavior is unchanged.
    - `tests/e2e/test_captures_compose.py`: its stubs, the held route and the first-fails route now act on POST only. Once the screen GETs the list, an all-methods stub would answer the list too: a second `role="alert"`, or the held GET answered with the Save body. Still 10 passed.

### Decisions taken with the user (2026-10-22)

| Question | Decision |
| --- | --- |
| At what width do Captures switch to two panes? | **≥ 1024px.** iPad landscape (1180) and desktop get two panes. iPad portrait (820) and phone get list, then detail as its own screen. |
| What is in the desktop right pane with no Capture open? | **A hint:** "Choose a Capture to see it here." |
| What does /captures/<id> show for a Capture not in Anki? | **An inline message and the back link:** "This Capture isn't in Anki." with "‹ Captures". On desktop the list stays, with nothing selected. |
| How are times beyond Today/Yesterday written? | **The year only when it isn't this year.** Rows: "Oct 5 · 12:31", or "Oct 5, 2025 · 12:31" in another year. Detail: "Captured today · …", "Captured yesterday · …", "Captured Oct 5 · …". Browser time zone, 24-hour, `en-US` month names. |

### Defaults taken without a question

- **Port:** `list_captures() -> list[Capture]`, newest first by `created_at`. `get_capture(capture_id) -> Capture`, which raises `AppError(NOT_FOUND)`. Both raise `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`. Neither is gated: they are reads (AD-19 gates writes). With no Capture note type, `findNotes` finds nothing, so the list is empty.
- **Adapter:** one lock hold. `findNotes` with `note_query(manifest, "<Prefix> Capture")`, then `notesInfo` when it found notes, skipping `{}` entries. Each entry is decoded with the existing `_stored_capture` (CaptureId stripped). `get_capture` reuses `_find_capture`. Sorting is by `created_at` descending; ties keep CaptureId order, so the order is deterministic.
- **Fake:** `list_captures()` sorts `captures` by `created_at` descending. `get_capture()` raises `not_found` for an unknown id. Both raise `anki_busy` or `anki_unavailable` as the other methods do.
- **Routes:** GET /api/captures answers `{"captures": [...]}`. Each item has the POST body's shape and its `createdAt` format. GET /api/captures/{captureId} answers that body. A CaptureId that isn't a lowercase canonical UUIDv4 is 404 `not_found` without calling the store. `NOT_FOUND` maps to 404 in `_APP_ERROR_STATUS` (today an `AppError(NOT_FOUND)` would be 500).
- **Screen:**
  - The router adds `/captures/<captureId>` to the captures screen, as `{captureId}`.
  - The list is a `<ul aria-label="Captures">`, and each row's whole body is one link to `/captures/<captureId>`, with the text and the time.
  - The open row carries `aria-current="page"`.
  - The detail is an `<article>` with the text and the "Captured …" line.
  - The skeleton is a `role="status"` reading "Loading Captures…", as Setup's.
  - The header reads "Newest first" below 1024px and "N Captures · newest first" from 1024px ("1 Capture · newest first" for one).
  - The back link "‹ Captures" shows on the separate detail screen only (below 1024px).
  - After a successful Save the list is re-read (or the saved Capture is prepended), so it tops the list.
  - A list load failure shows an inline `role="alert"` with the envelope's message and Try again, as Setup does.

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and list contents, failures and pending states are stubbed at the network (GET only). Execution is **sequential**, in this session, with no subagents (as in story 3.1).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | Two Captures, one plain with codec-escaped text and one in editor markup, plus a Vocabulary note and a `LanguageLabDev` Capture | the returned set is exactly the two decoded Captures |
| AC-2 | Integration | P0 | Three Captures added in non-chronological order | the CaptureIds come back newest, middle, oldest |
| AC-3 | Integration | P0 | The target in editor markup among two others | `get_capture` returns the decoded Capture |
| AC-4 | Integration | P0 | No Captures, other Captures, or a Dev-Prefix Capture with the same id | the outcome's code is `not_found` |
| AC-5 | API | P0 | Fake holding three Captures, out of order | status 200 |
| AC-6 | API | P0 | GET the middle one | status 200 |
| AC-7 | API | P0 | Unknown UUIDv4, or `capture-1` | the request log line is (404, the Capture route's template); the missing route also gives 404, so status alone isn't red |
| AC-8 | E2E | P0 | Phone, list stubbed with three | the rows contain the three texts in order |
| AC-9 | E2E | P0 | Phone, click the second row (the transition) | the URL is /captures/<its id> |
| AC-10 | E2E | P0 | Desktop, /captures/<second id> | that row has `aria-current="page"` |
| AC-11 | E2E | P0 | Desktop, Toronto time zone, clock fixed at 2026-10-22 21:30, five Captures | the rows contain the five time strings in order |
| AC-12 | E2E | P0 | GET held | the "Loading Captures…" status is visible |
| AC-13 | E2E | P0 | Phone, list stubbed empty | "No Captures yet." is visible |
| AC-14 | E2E | P0 | Live server: save a unique text (no wait for the list: it tops it either way) | the first row contains it |
| AC-15 | E2E | P0 | Desktop, /captures, list stubbed | the hint is visible |
| AC-16 | E2E | P0 | Phone, detail GET stubbed 404 `not_found` | "This Capture isn't in Anki." is visible |

### Secondary branches for green-phase automation

- AC-1: an empty Capture scope sends no `notesInfo`. A `{}` entry (deleted meanwhile) is skipped. A malformed CreatedAt is `anki_unavailable`. Anki down is `anki_unavailable`. A gated Anki (`needs_setup`) still lists, since reads aren't gated.
- AC-2: equal CreatedAt values get a stable order.
- AC-5 / AC-6: an unreachable fake gives 503 `anki_unavailable` on both routes. `create_app(settings)` with no injected store has both routes (503 with no Anki listening).
- AC-7: `capture-1` never reaches the store.
- AC-9: deep-linking /captures/<id> on the phone renders the detail screen. Browser back returns to the list. Opening a row with unsaved compose text raises the Capture unsaved alert (router guard).
- AC-10: clicking a row on desktop selects it and shows its detail with no full reload. At iPad landscape (1180×820) there are two panes, and at iPad portrait (`viewports.TABLET`) the phone layout. The header reads "1 Capture · newest first" for one.
- AC-11: detail "Captured yesterday · 19:40", "Captured Oct 5 · 12:31", and "Captured Oct 4, 2025 · 22:05".
- AC-12: a list load failure shows the inline alert with Try again, and Try again reloads.
- AC-14: the same holds at phone width.
- AC-15: there is no hint below 1024px.
- AC-16: on desktop the list stays with nothing selected.
- Widths: list and detail at `viewports.ALL` with no horizontal scroll. Long text wraps.

## TDD red phase (current)

Red-phase scaffolds are generated, each file skipped by a module-level `pytestmark = pytest.mark.skip(reason=...)`:

- Integration: 4 tests (6 cases) in `tests/integration/test_anki_capture_reads.py`.
- API: 3 tests (4 cases) in `tests/api/test_captures_read.py`.
- E2E: 9 tests in `tests/e2e/test_captures_list.py`.

**Red check (2026-10-22):** each file was run with its skip marker removed. All 19 cases failed for the expected reasons:

- `AttributeError: 'AnkiConnectStore' object has no attribute 'list_captures'` / `'get_capture'`.
- GET /api/captures and /api/captures/{id} answering 404 from the shell catch-all (`/{path:path}`), not 200 from a Capture route.
- The "Captures" list, its rows, the article, the "Loading Captures…" status, "No Captures yet.", the hint and the not-found message not found. AC-9 times out on the row click, its transition.

Afterwards `make test-fast` passed (540 passed, 10 skipped), the new E2E file collected as 9 skipped, and the compose E2E file passed with its POST-only stubs (10 passed).

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `integration/test_anki_capture_reads.py::test_list_captures_returns_every_capture_decoded_from_the_exact_scope` |
| AC-2 | `integration/test_anki_capture_reads.py::test_list_captures_is_newest_first_by_created_at` |
| AC-3 | `integration/test_anki_capture_reads.py::test_get_capture_returns_the_capture_matched_in_python` |
| AC-4 | `integration/test_anki_capture_reads.py::test_get_capture_of_an_unknown_capture_id_is_not_found` |
| AC-5 | `api/test_captures_read.py::test_get_lists_the_captures_newest_first` |
| AC-6 | `api/test_captures_read.py::test_get_one_capture_by_its_capture_id` |
| AC-7 | `api/test_captures_read.py::test_an_unknown_capture_id_is_404_not_found` |
| AC-8 | `e2e/test_captures_list.py::test_on_the_phone_the_list_is_under_the_compose_box_newest_first` |
| AC-9 | `e2e/test_captures_list.py::test_on_the_phone_a_capture_opens_as_its_own_screen_with_a_back_link` |
| AC-10 | `e2e/test_captures_list.py::test_on_desktop_list_and_detail_are_two_panes_with_the_open_capture_selected` |
| AC-11 | `e2e/test_captures_list.py::test_creation_times_read_relative_to_today_in_the_browsers_time_zone` |
| AC-12 | `e2e/test_captures_list.py::test_the_list_shows_a_skeleton_while_it_loads` |
| AC-13 | `e2e/test_captures_list.py::test_with_no_captures_the_empty_state_is_under_the_compose_box` |
| AC-14 | `e2e/test_captures_list.py::test_a_newly_saved_capture_tops_the_list` |
| AC-15 | `e2e/test_captures_list.py::test_on_desktop_with_no_capture_open_the_right_pane_shows_a_hint` |
| AC-16 | `e2e/test_captures_list.py::test_a_capture_that_isnt_in_anki_shows_a_message_and_the_back_link` |

## Next steps (task-by-task activation)

1. **Port, adapter and fake:**
   - Add `list_captures` and `get_capture` to `AnkiStore`, `AnkiConnectStore` and `FakeAnkiStore`, and extend `tests/unit/test_anki_store_port.py` if it lists methods.
   - Un-skip the integration file (AC-1 to AC-4).
2. **Service and routes:**
   - Add `CaptureService.list` and `CaptureService.get`, the two GET routes, and `NOT_FOUND` → 404.
   - Un-skip the API file (AC-5 to AC-7).
3. **Router, API client and screen:**
   - Add the `/captures/<captureId>` route, `listCaptures` and `getCapture`, and the list, detail, layouts and states in `captures.js` and `studio.css`.
   - Un-skip the E2E file (AC-8 to AC-16).
4. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoints:**
  - GET /api/captures: 200 `{captures: [{captureId, text, createdAt}]}`, or 503.
  - GET /api/captures/{captureId}: 200 `{captureId, text, createdAt}`, 404 `not_found`, or 503.
- **UI:**
  - The list under the compose box, with its header, skeleton and empty state.
  - Phone: the separate detail screen with "‹ Captures".
  - ≥ 1024px: two panes, with the selected row and the hint.
  - Relative time formatting in the browser's time zone.
- **Wiring to check in review:**
  - `create_app` serves both GET routes for the injected and the built store.
  - The shell catch-all still serves /captures/<id> as the SPA.
  - The reads never send the CaptureId in a query.

## Validation (step 5)

- Prerequisites: the criteria come from entry 2; the framework is pytest and pytest-playwright; the dev environment runs.
- Every leaf test's docstring names exactly one declared AC, and each AC has exactly one leaf. Parametrized cases are cases of that leaf.
- Each leaf's first assertion is the criterion-defining one. Setup actions stay unasserted before it: arranging the collection, stubbing, `goto`, filling the box, and `expect_response` waits.
  - AC-7's first assertion pairs the status with the route template, since a missing route is also 404.
  - AC-9's row click is its transition. AC-14 runs its transition: a Save, then the list.
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were restored with their skip markers.

## Completion

- **Risks and assumptions:**
  - On desktop, opening another Capture goes through the router. Unless the screen keeps its mount across `/captures` ↔ `/captures/<id>`, unsaved compose text raises the unsaved alert, or is lost. The plan should keep the compose box mounted across selection changes.
  - The list reads every Capture's `notesInfo` per load. That is fine at personal scale (decided 2026-10-21, as for the lookup).
  - AC-7 depends on the request log carrying the route template (story 1.x, AD-15).
  - AC-11 pins `en-US` and America/Toronto through `browser_context_args` and `page.clock.set_fixed_time`, so the formatter must use the browser's local time zone, not UTC.
- **Next workflow:** `bmad-build` for story 3.2.

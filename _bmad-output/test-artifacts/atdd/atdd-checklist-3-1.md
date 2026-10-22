---
runScope: 'story'
runKey: 'story-3-1'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-22'
storyId: '3.1'
storyKey: '3-1'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-captures/tickets.toml (entry 1)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-3-1.md'
generatedTestFiles:
  - 'tests/integration/test_anki_captures.py'
  - 'tests/api/test_captures.py'
  - 'tests/e2e/test_captures_compose.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-captures/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-captures/epic-captures.md (Done when 1 and 4; Notes 2026-10-21)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-4, AD-5, AD-6, AD-8, AD-9, AD-13, AD-19, AD-20, Consistency Conventions)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Captures copy, Anki unreachable, Alert dialog, Inline alert, Buttons)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Captures.dc.html'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-8.md (format, conventions)'
  - 'No test design for epic 3: test-design/test-design-epic-3.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{client,guard,setup_gate,store,query,codec,manifest,lock}.py, ports/anki_store.py, domain/errors.py, app.py, features/setup/routes.py'
  - 'src/language_lab/static/{router,api}.js, static/screens/captures.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_state,anki_connect,aio,network,unsaved,navigation,hosts}.py, tests/support/fixtures/{live_server,api}.py'
  - 'tests/integration/test_anki_setup_state.py, tests/api/test_setup_state.py, tests/e2e/{test_setup_state,test_unsaved_alert}.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'A new CaptureId adds a Capture note to <Prefix>::Captures with Text, CreatedAt (ISO UTC with Z), CaptureId and SchemaVersion written through the codec and allowDuplicate true, then suspends its card (AD-6)' }
  - { id: 'AC-2', idSource: 'generated', text: 'The CaptureId lookup queries only the exact Capture note-type scope and filters notesInfo in Python; no user text or CaptureId enters a query (AD-4)' }
  - { id: 'AC-3', idSource: 'generated', text: 'A CaptureId already in Anki returns the stored Capture unchanged and writes nothing (AD-20)' }
  - { id: 'AC-4', idSource: 'generated', text: 'create_capture is behind the setup gate: unless ready it is setup_required with no note written' }
  - { id: 'AC-5', idSource: 'generated', text: 'A failing Anki returns anki_unavailable with no note, and a failed addNote sends no suspend' }
  - { id: 'AC-6', idSource: 'generated', text: 'POST /api/captures with a client-generated UUIDv4 CaptureId and text is 201 with the saved Capture (wired in app.py)' }
  - { id: 'AC-7', idSource: 'generated', text: 'CreatedAt is set by the server, ISO 8601 UTC with Z; a client createdAt is ignored' }
  - { id: 'AC-8', idSource: 'generated', text: 'Blank text or a CaptureId that is not a lowercase canonical UUIDv4 is validation_failed, and nothing is saved' }
  - { id: 'AC-9', idSource: 'generated', text: 'The Captures screen has the compose box per S-Captures, with Save disabled while the text is blank' }
  - { id: 'AC-10', idSource: 'generated', text: 'Save sends the text with a browser-generated UUIDv4 CaptureId and clears the box on success' }
  - { id: 'AC-11', idSource: 'generated', text: 'The CaptureId is generated once per composition and kept across retries; the next composition gets a new one' }
  - { id: 'AC-12', idSource: 'generated', text: 'Save is disabled while a Save is in flight' }
  - { id: 'AC-13', idSource: 'generated', text: 'Unsaved text marks the screen dirty through router.setDirty, and the router alert shows the Capture variant "This Capture isn''t saved."' }
  - { id: 'AC-14', idSource: 'generated', text: 'A successful Save clears the dirty state' }
  - { id: 'AC-15', idSource: 'generated', text: 'On anki_unavailable the text stays and the inline alert shows the EXPERIENCE.md copy with Try again; the Capture is never reported as saved' }
---

# ATDD Checklist: Story 3.1, Tracer: save a Capture from the Captures screen

## Run context

- **Story source:** epic-captures `tickets.toml`, entry 1 (`risk = "medium"`, after 1.7 and 2.8). There is no story file, so this checklist holds the criteria. AC-1 to AC-15 follow the ticket's description in source order, with the verify clauses folded in:
  - "a new Capture added then suspended" is AC-1.
  - "the same CaptureId posted twice making one note" is AC-3.
  - "empty text refused" is AC-8.
  - "a gated or failing Anki returning its error with no note" is AC-4 (gated) and AC-5 (failing).
  - "Save clearing the box on success" is AC-10.
  - "leaving with unsaved text raising the alert with the Capture copy" is AC-13.
  - "the error copy with text kept and Try again" is AC-15.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in epics 1 and 2 (dev-only, NFR-11).
- **Test design:** none for epic 3. Priorities follow the ticket's risk (medium), epic Done when 1 and 4, and AD-4, AD-6, AD-19 and AD-20. Every criterion is on the Capture save path, so all are P0.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - New: `domain/captures.py` (`Capture`), `features/captures/{routes,service}.py`.
  - Changed: `ports/anki_store.py` (`create_capture`), `adapters/anki/store.py`, `tests/fakes/anki_store.py` (port, adapter and fake together), `app.py` (wire the router), `static/api.js` (`createCapture`), `static/screens/captures.js`, `static/router.js` (the Capture alert copy), `static/css/studio.css`.
  - Tests (done in this run): `tests/support/anki_state.py`. `addNote` now gives the note one card per template in its deck. It refuses an empty first field, and a duplicate first field unless `options.allowDuplicate` is set, with AnkiConnect's error texts. `capture_note()` stores a Capture as Create Capture leaves it. The rest of the suite still passes with this.

### Decisions taken with the user (2026-10-22)

| Question | Decision |
| --- | --- |
| The router's unsaved alert needs a Capture variant. What is its body? | **"This Capture isn't saved."** It mirrors the Draft variant and echoes no text. |
| How is whitespace in Capture text treated? | **Refuse blank, store as typed.** Empty or whitespace-only text is `validation_failed`, and Save stays disabled for it. Anything else is stored exactly as typed, and the codec turns newlines into `<br>`. |

### Defaults taken without a question

- **Domain:** `Capture(capture_id: str, text: str, created_at: datetime)`, a frozen dataclass in `domain/captures.py`. `created_at` is timezone-aware UTC, to the second.
- **Port:** `AnkiStore.create_capture(capture_id, text, created_at) -> Capture` returns the stored Capture: the new one, or on a retry the existing one, unchanged. Raises `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
- **Adapter**, all under one lock hold:
  1. `findNotes` with `note_query(manifest, "<Prefix> Capture")`, then `notesInfo` when it found notes.
  2. Match on `decode_field(CaptureId).strip()`. When found, return it with `Text` decoded and `CreatedAt` decoded, stripped and parsed. Nothing is written.
  3. Otherwise `addNote` with `deckName` `<Prefix>::Captures` and the Capture model. Its fields, each through `encode_field`: `Text`, `CreatedAt` (`YYYY-MM-DDTHH:MM:SSZ`), `CaptureId` and `SchemaVersion` (the manifest's). `options: {"allowDuplicate": true}`.
  4. Read the new note's cards with `notesInfo` (its `cards`). The query builder has no `nid:` scope, by design.
  5. `suspend` those cards.

  Every write goes through `client.invoke`, so the Prefix guard and the setup gate apply with no extra code.
- **Service:** `CaptureService(anki)` sets `created_at` to `datetime.now(UTC)` with microseconds dropped. The route never takes it from the request.
- **Route:** POST /api/captures takes `{captureId, text}`, camelCase on the wire, and extra keys are ignored. It answers **201** with `{captureId, text, createdAt}` on both the first save and a retry.
  - Validation returns 422 `validation_failed` for: a `captureId` that doesn't fullmatch the lowercase canonical UUIDv4 pattern (the same one `guard.media_pattern` uses), or `text` that is missing or blank once stripped.
  - `setup_required` (409), `anki_unavailable` and `anki_busy` (503) already come from the `AppError` map in `app.py`.
- **Fake:** `FakeAnkiStore.captures: dict[str, Capture]`. `create_capture()` is create-or-noop by CaptureId and raises `anki_busy` or `anki_unavailable` as the other methods do.
- **Screen:**
  - A `<textarea>` labelled "New Capture" with the S-Captures placeholder, and the Primary button "Save Capture". The h1 "Captures" stays.
  - The CaptureId is `crypto.randomUUID()`, made when a composition starts and replaced only after a successful Save.
  - While the text is non-blank: `setDirty({kind: "capture", count: 1, target: ""})`. Blank text gives `setDirty(null)`, and so does a successful Save.
  - On success the box clears and focus returns to it.
  - On failure a `role="alert"` inline alert sits at the box:
    - `anki_unavailable`: the title "Not saved — Anki isn't reachable", the EXPERIENCE.md body, and Try again.
    - Any other code: the title "Not saved", the envelope's fixed message, and Try again.

    A new Save attempt clears the alert.
- **Router:** in `describeLoss`, kind `"capture"` gives "This Capture isn't saved.".

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and failure and in-flight states are stubbed at the network. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 2.14).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | Set-up Anki with no Capture, or with another Capture holding the same text; `create_capture` with markup characters and a newline in the text | the writes sent are `["addNote", "suspend"]` |
| AC-2 | Integration | P0 | No Captures, three other Captures, or a `LanguageLabDev` Capture with the same CaptureId | the queries sent are exactly `{note:"LanguageLab Capture"}` |
| AC-3 | Integration | P0 | A Capture with that CaptureId stored plain, or in editor markup (`<div>`, `<b>`, `&nbsp;`); create it again with other text and time | no write sent |
| AC-4 | Integration | P0 | Gate in `needs_setup`, `needs_migration` or `newer_schema` | the outcome's code is `setup_required` |
| AC-5 | Integration | P0 | Anki refusing connections; `addNote` answering an error | the outcome's code is `anki_unavailable` |
| AC-6 | API | P0 | POST with a fresh UUIDv4 and text, over the fake | status 201 |
| AC-7 | API | P0 | POST carrying `createdAt: 2000-01-01T00:00:00Z` | the body's `createdAt` fullmatches `YYYY-MM-DDTHH:MM:SSZ` |
| AC-8 | API | P0 | 8 cases: empty, whitespace or missing text; missing, uppercase, non-UUID, v1 or unhyphenated CaptureId | status 422 |
| AC-9 | E2E | P0 | Open Captures | Save Capture is disabled |
| AC-10 | E2E | P0 | Type, then Save, against the live server's fake | the box is empty |
| AC-11 | E2E | P0 | The first POST answers 503 `anki_unavailable`, then Try again, then a second composition | the retry's CaptureId equals the first's |
| AC-12 | E2E | P0 | The POST held | Save Capture is disabled |
| AC-13 | E2E | P0 | Type, then the Setup pill | the alert contains "This Capture isn't saved." |
| AC-14 | E2E | P0 | Type, Save (waiting for the response), then the Setup pill | the URL is /setup |
| AC-15 | E2E | P0 | POST stubbed 503 `anki_unavailable` | the inline alert contains "Not saved — Anki isn't reachable" |

### Secondary branches for green-phase automation

- AC-1: `CreatedAt` is formatted from a non-UTC aware datetime by converting to UTC first. Sub-second precision is dropped.
- AC-1 / AC-5: a `suspend` that fails is `anki_unavailable`, and the note stays unsuspended (a tolerated AD-6 leftover). A retry with that CaptureId finds it and writes nothing, so its card stays unsuspended until Setup's opt-in repair (story 2.11) suspends it. Worth a test and a line in the plan.
- AC-2: an empty Capture scope (no notes) sends no `notesInfo` for the lookup. A `{}` entry in `notesInfo` (a note deleted meanwhile) is skipped.
- AC-4: with an unknown gate state (None), the first `create_capture` computes it on demand (story 2.8), so a set-up Anki saves.
- AC-4 / AC-6: the route maps `setup_required` to 409 and `anki_unavailable` to 503 with the fixed messages. The fake's `available=False` gives the 503.
- AC-6: a POST retried with the same CaptureId and different text is 201 with the first text and `createdAt` (through the fake).
- AC-6: `create_app(settings)` with no injected store has the route, which proves the wiring.
- AC-13: every leave path in `tests/support/unsaved.LEAVE_PATHS` (phone Menu row, back link, browser back; tablet and desktop pill) raises the Capture alert. Discard leaves and drops the text. Reloading with unsaved text raises the browser's own `beforeunload` prompt. Clearing the box by hand clears the dirty state.
- AC-15: another code (e.g. `setup_required`) shows "Not saved" with the envelope's message and Try again. Try again re-sends the current text with the same CaptureId (AC-11 covers the id).
- Widths: the compose box at `viewports.ALL` (phone, tablet, desktop).

## TDD red phase (current)

Red-phase scaffolds are generated, each file skipped by a module-level `pytestmark = pytest.mark.skip(reason=...)`:

- Integration: 5 tests (12 cases) in `tests/integration/test_anki_captures.py`.
- API: 3 tests (10 cases) in `tests/api/test_captures.py`.
- E2E: 7 tests in `tests/e2e/test_captures_compose.py`.

`language_lab.domain.captures` doesn't exist yet, so `Capture` is imported inside the tests and collection passes while they are skipped.

**Red check (2026-10-22):** each file was run with its skip marker removed. All 29 cases failed for the expected reasons:

- `AttributeError: 'AnkiConnectStore' object has no attribute 'create_capture'`.
- `ModuleNotFoundError: language_lab.domain.captures`.
- POST /api/captures answering 405 instead of 201 or 422, with no `createdAt`.
- The "New Capture" textbox and the "Save Capture" button not found.

Afterwards `make test-fast` passed: 512 passed, 22 skipped.

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `integration/test_anki_captures.py::test_a_new_capture_is_added_then_its_card_suspended` |
| AC-2 | `integration/test_anki_captures.py::test_the_capture_id_lookup_queries_only_the_exact_capture_scope` |
| AC-3 | `integration/test_anki_captures.py::test_an_existing_capture_id_returns_the_stored_capture_and_writes_nothing` |
| AC-4 | `integration/test_anki_captures.py::test_a_gated_anki_refuses_create_capture_before_any_write` |
| AC-5 | `integration/test_anki_captures.py::test_a_failing_anki_returns_anki_unavailable_with_no_note` |
| AC-6 | `api/test_captures.py::test_post_saves_a_capture_under_the_clients_capture_id` |
| AC-7 | `api/test_captures.py::test_the_server_sets_created_at_in_utc_and_ignores_the_clients` |
| AC-8 | `api/test_captures.py::test_a_blank_text_or_a_non_canonical_capture_id_is_validation_failed` |
| AC-9 | `e2e/test_captures_compose.py::test_save_is_disabled_while_the_compose_box_is_blank` |
| AC-10 | `e2e/test_captures_compose.py::test_save_sends_a_new_uuid4_capture_id_and_clears_the_box` |
| AC-11 | `e2e/test_captures_compose.py::test_a_retry_keeps_the_capture_id_and_the_next_composition_gets_a_new_one` |
| AC-12 | `e2e/test_captures_compose.py::test_save_is_disabled_while_a_save_is_in_flight` |
| AC-13 | `e2e/test_captures_compose.py::test_leaving_with_unsaved_text_raises_the_alert_with_the_capture_copy` |
| AC-14 | `e2e/test_captures_compose.py::test_a_successful_save_clears_the_unsaved_state` |
| AC-15 | `e2e/test_captures_compose.py::test_anki_unreachable_keeps_the_text_and_shows_the_error_with_try_again` |

## Next steps (task-by-task activation)

1. **Domain, port, adapter and fake:**
   - Add `domain/captures.py`, `AnkiStore.create_capture`, `AnkiConnectStore.create_capture` and `FakeAnkiStore.create_capture` with `captures`.
   - Un-skip the integration file (AC-1 to AC-5).
2. **Feature and route:**
   - Add `features/captures/{service,routes}.py` and wire `captures_router` in `create_app`.
   - Un-skip the API file (AC-6 to AC-8).
3. **Screen and router:**
   - Add `createCapture` to `api.js`, the compose box to `captures.js`, its style to `studio.css`, and the `"capture"` kind to `describeLoss` in `router.js`.
   - Un-skip the E2E file (AC-9 to AC-15).
4. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoints:** POST /api/captures (201 with `{captureId, text, createdAt}`; 422 `validation_failed`; 409 `setup_required`; 503 `anki_unavailable` or `anki_busy`).
- **UI:**
  - The Captures compose box: "New Capture", the placeholder, and "Save Capture".
  - The inline error alert with Try again.
  - The Capture variant of the router's unsaved alert.
- **Wiring to check in review:**
  - `create_app` includes the captures router for both the injected and the built store.
  - `create_capture` writes only through `client.invoke`, never `invoke_setup`, so the gate applies.

## Validation (step 5)

- Prerequisites: the criteria come from entry 1; the framework is pytest and pytest-playwright; the dev environment runs.
- Every leaf test's docstring names exactly one declared AC, and each AC has exactly one leaf. Parametrized cases are cases of that leaf.
- Each leaf's first assertion is the criterion-defining one. Setup actions stay unasserted before it: arranging the collection, filling the box, and `expect_response` waits.
- AC-11 and AC-14 run their transitions (a failure, then a retry, then a new composition; a Save, then a leave).
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were removed.

## Completion

- **Risks and assumptions:**
  - Keeping the CaptureId across retries means that if a Save times out after Anki stored it, and the user edits the text before Try again, the retry returns the first text (AD-20 noop). The edit is lost without a message. That is acceptable for a tracer, but the plan should note it.
  - The lookup reads every Capture's `notesInfo` on each Save (decided 2026-10-21). That is fine at personal scale.
  - The real `suspend` reply and `addNote` with `options.allowDuplicate` are hand-built here, and are checked against real responses at acceptance (entry 4).
  - 201 on a retry, rather than 200, is a default.
- **Next workflow:** `bmad-build` for story 3.1.

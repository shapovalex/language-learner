---
runScope: 'story'
runKey: 'story-4-1'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-22'
storyId: '4.1'
storyKey: '4-1'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/tickets.toml (entry 1)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-4-1.md'
generatedTestFiles:
  - 'tests/unit/test_items_domain.py'
  - 'tests/integration/test_anki_item_save.py'
  - 'tests/api/test_drafts_blank.py'
  - 'tests/api/test_items_save.py'
  - 'tests/e2e/test_make_an_item.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/epic-capture-to-item.md (Done when 1 and 5; Notes 2026-10-08, 2026-10-22)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-4, AD-5, AD-6, AD-8, AD-9, AD-10, AD-11, AD-12, AD-13, AD-19, AD-20, Consistency Conventions)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-11, FR-12, FR-18, FR-20, NFR-3); addendum.md (A3 fields)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Key strings: Capture detail, Draft; Text-source choice; Segmented control; Buttons; Success banner; State Patterns: Anki unreachable, Unsaved Draft, Saved from a Capture, Save failed)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-NewItem.dc.html, C-Draft.dc.html, S-DraftPhone.dc.html'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-3-1.md (format, conventions)'
  - 'No test design for epic 4: test-design/test-design-epic-4.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{client,guard,setup_gate,store,query,codec,manifest}.py, ports/anki_store.py, domain/{catalog,captures,errors}.py, features/captures/{routes,service}.py, app.py'
  - 'src/language_lab/static/{router,api,dom}.js, static/screens/captures.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_state,anki_connect,aio,captures,captures_screen,network,unsaved,navigation,viewports}.py, tests/support/fixtures/live_server.py'
  - 'tests/integration/test_anki_captures.py, tests/api/test_captures.py, tests/e2e/test_captures_list.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'ItemContent is one flat Pydantic union discriminated by category, camelCase on the wire: Vocabulary and Sentence content validate with their own fields and dump back unchanged (AD-11)' }
  - { id: 'AC-2', idSource: 'generated', text: 'ItemContent refuses an alternative containing a comma (AD-10), a blank Target or Russian meaning, and an unknown category' }
  - { id: 'AC-3', idSource: 'generated', text: 'normalize_text applies NFC, casefold, trims surrounding whitespace and Unicode punctuation, collapses inner whitespace, and maps apostrophe variants to an ASCII apostrophe; diacritics stay significant (AD-12)' }
  - { id: 'AC-4', idSource: 'generated', text: 'A new ItemId adds one note of its Language/Category note type, fields through the codec, to the Pronunciation deck with allowDuplicate true, then moves cards 0-2 to their Study decks: exactly four Cards in the right decks (AD-6 keep order)' }
  - { id: 'AC-5', idSource: 'generated', text: 'The ItemId lookup queries only the exact note-type scope; no ItemId or user text is sent outside addNote, and neither a same-Target Item nor another Prefix''s Item with the same ItemId matches (AD-4)' }
  - { id: 'AC-6', idSource: 'generated', text: 'A Save whose ItemId is already stored updates that note''s fields with updateNoteFields only: no second note, no card moved, Audio and SchemaVersion not sent (AD-20)' }
  - { id: 'AC-7', idSource: 'generated', text: 'save_item is behind the setup gate: unless ready it is setup_required with nothing written (AD-19)' }
  - { id: 'AC-8', idSource: 'generated', text: 'A failing Anki is anki_unavailable with no note, and a failed addNote sends no changeDeck' }
  - { id: 'AC-9', idSource: 'generated', text: 'POST /api/drafts/blank is 201 {itemId} with a fresh lowercase UUIDv4 each call, touching no Anki (AD-8)' }
  - { id: 'AC-10', idSource: 'generated', text: 'POST /api/items/<lang> with a multipart item JSON part (ItemContent + itemId + audio keep) is 200 {itemId}, saved under that ItemId with its Language and content (wired in app.py)' }
  - { id: 'AC-11', idSource: 'generated', text: 'A comma alternative, blank Target or Russian meaning, unknown category, non-canonical itemId, or missing or malformed item part is 422 validation_failed, and nothing is saved' }
  - { id: 'AC-12', idSource: 'generated', text: 'Capture detail has the Make an Item pane: Use as is (chosen) or Custom value, Language and Category pickers, and Write it myself, disabled with "Choose a Language and Category." or "Enter the custom value." until they are met' }
  - { id: 'AC-13', idSource: 'generated', text: 'Write it myself opens the Draft editor at /captures/<captureId>/new with Target prefilled by the chosen text and every other field of the Category editable and empty, "From Capture “…”" and the chip "Draft — not saved yet"' }
  - { id: 'AC-14', idSource: 'generated', text: 'The Draft marks the screen dirty through router.setDirty, so leaving raises the unsaved alert "This Draft isn''t saved."' }
  - { id: 'AC-15', idSource: 'generated', text: 'Save to Anki sends the Draft''s ItemId with audio keep and the fields (alternatives one per line), and returns to the same Capture with the success banner; an English Vocabulary and a French Sentence Item are saved from one Capture' }
  - { id: 'AC-16', idSource: 'generated', text: 'A failed Save keeps the Draft editor and its edits with the inline alert "Not saved — Anki isn''t reachable", and a retry sends the same ItemId (AD-20)' }
  - { id: 'AC-17', idSource: 'generated', text: '/captures/<captureId>/new with no Draft in memory is replaced by /captures/<captureId>, the Capture detail with the Make an Item pane (AD-13)' }
---

# ATDD Checklist: Story 4.1, Tracer: save a hand-filled Item from a Capture

## Run context

- **Story source:** epic-capture-to-item `tickets.toml`, entry 1 (`risk = "high"`, after 1.7, 2.4, 2.8 and 3.2). There is no story file, so this checklist holds the criteria. AC-1 to AC-17 follow the ticket's description in source order, with the verify clauses folded in:
  - "one Save making one note with exactly four Cards in the right Study and Pronunciation decks" is AC-4.
  - "a retried Save with the same ItemId updating that note" is AC-6.
  - "comma-containing alternatives refused" is AC-2 (domain) and AC-11 (API).
  - "a gated Anki writing nothing" is AC-7.
  - "a Vocabulary and a Sentence Item saved from one Capture, each returning to it with the success banner" is AC-15.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in epics 1 to 3 (dev-only, NFR-11).
- **Test design:** none for epic 4. Priorities follow the ticket's risk (high), epic Done when 1 and 5, and AD-4, AD-6, AD-19 and AD-20. Every criterion is on the Save path, so all are P0.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - New: `domain/items.py` (`ItemContent`, `AudioIntent`, `normalize_text`), `features/drafts/{routes,service}.py`, `features/items/{routes,service}.py`.
  - Changed: `ports/anki_store.py` (`save_item`), `adapters/anki/store.py`, `tests/fakes/anki_store.py` (port, adapter and fake together), `app.py` (wire both routers), `static/api.js` (`blankDraft`, `saveItem`), `static/screens/captures.js` (the pane, the Draft editor), `static/router.js` (the `/captures/<id>/new` route), `static/css/studio.css`.
  - Tests (done in this run):
    - `tests/support/anki_state.py`: `item_note()` puts an Item as Save leaves it, with four cards in their decks.
    - `tests/support/items.py`: Item wire data and the expected stored fields.
    - `tests/support/items_screen.py`: the pane and editor locators, and `item_part()` for the Save's multipart body.
    - The tests README lists them.

### Decisions taken with the user (2026-10-22)

| Question | Decision |
| --- | --- |
| What does "Write it myself" put in Target? | **Prefilled.** Target holds the chosen text (the Capture text for Use as is, or the custom value). Every other field is empty. |
| How does the Draft editor take Russian alternatives? | **One per line.** A textarea labelled "Alternatives". Blank lines are dropped, and a comma in a line is refused at Save. |
| What does /captures/<id>/new show with no Draft in memory (a reload, a direct visit)? | **Back to the Capture.** The URL is replaced with /captures/<id>, the Capture detail with the Make an Item pane. |

### Defaults taken without a question

- **Domain (`domain/items.py`):**
  - `ItemContent` is the union of a Vocabulary model and a Sentence model, discriminated by `category`, with camelCase aliases.
    - Vocabulary: `target`, `russian`, `russianAlternatives: list[str]`, `hint`, `partOfSpeech`, `grammar`, `example`, `exampleRussian`, `mnemonic`.
    - Sentence: `target`, `russian`, `russianAlternatives`, `hint`, `note`.
  - `target` and `russian` must be non-blank. Anki refuses an empty first field, and the Produce and Write fronts show the Russian meaning. An alternative containing `,` is refused.
  - `AudioIntent(StrEnum)`: `KEEP`, `REPLACE`, `REMOVE`.
  - `normalize_text(text) -> str` per AD-12. This story only tests it; entry 3 uses it.
- **Port:** `AnkiStore.save_item(item_id: str, language: Language, content: ItemContent, audio: AudioIntent) -> None`. Raises `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`. Only `KEEP` is built; `REPLACE` and `REMOVE` are epic-reference-audio's.
- **Adapter**, all under one lock hold:
  1. `findNotes` with `note_query(manifest, "<Prefix> <Language> <Category>")`, then `notesInfo`. Match on `decode_field(ItemId).strip()`.
  2. Found: `updateNoteFields` with the content's fields through the codec (alternatives via `join_alternatives`). Send neither `Audio` (keep) nor `SchemaVersion`, since the gate refuses a SchemaVersion change.
  3. Not found:
     - `addNote` into `manifest.card_deck(model, 3)` with every field through the codec, `Audio` empty, `ItemId`, `SchemaVersion`, and `options: {"allowDuplicate": true}`.
     - Then `cardsInfo` (or `notesInfo` `cards` plus `cardsInfo`) to map each card to its ord.
     - Then `changeDeck` of cards 0-2 to `manifest.card_deck(model, ord)`. The tests allow one `changeDeck` per deck, or any split.

  Every write goes through `client.invoke`, so the Prefix guard and the setup gate apply with no extra code.
- **Fake:** `FakeAnkiStore.items: dict[str, tuple[Language, ItemContent]]`. `save_item()` is create-or-update by ItemId, and raises `anki_busy` or `anki_unavailable` as the other methods do.
- **Blank Draft route:** POST /api/drafts/blank → **201** `{itemId}` (`str(uuid.uuid4())`). No body and no Anki call. Entry 2 adds the generated Draft beside it.
- **Save route:** POST /api/items/{lang} (`en` | `fr`).
  - The request is `multipart/form-data` with an `item` part holding JSON: ItemContent plus `itemId` (lowercase canonical UUIDv4) and `audio`.
  - It answers **200** `{itemId}` for a create and an update alike.
  - Invalid input is 422 `validation_failed`, including a JSON body instead of multipart. `setup_required` (409), `anki_unavailable` and `anki_busy` (503) come from the existing `AppError` map.
- **Screen, Make an Item pane** (`captures.js` detail):
  - A `<section>` labelled by its "Make an Item" heading (role `region`).
  - The radio pair "Use as is" (checked) / "Custom value", with its textbox named "Custom value" and the hint "Write it in the language you're learning, not in Russian.".
  - Picker buttons with `aria-pressed`: English, French; Vocabulary, Sentence. None is pressed at first.
  - A **button** "Write it myself", styled as a link. It is a button because it has to be disabled with a reason, which a link can't be.
  - The reason text sits next to it: "Choose a Language and Category." or "Enter the custom value.".
  - Its click POSTs /api/drafts/blank, then navigates to /captures/<id>/new.
- **Screen, Draft editor:** the captures screen keeps the Draft in module memory across `/captures/<id>` ↔ `/captures/<id>/new` (`update`), and never puts it in the URL, `history.state` or storage (AD-13).
  - It contains:
    - A `<form aria-label="Draft">`.
    - "From Capture “<text>”".
    - The Language and Category.
    - The chip "Draft — not saved yet".
    - Labelled fields: Target, Russian meaning, Alternatives, Part of speech, Grammar, Hint, Example, Example in Russian, Mnemonic (Vocabulary); Target, Russian meaning, Alternatives, Hint, Note (Sentence).
    - Discard, and the Primary "Save to Anki".
  - On open it calls `setDirty({kind: "draft", count: 1, target})`.
  - After a successful Save it calls `setDirty(null)` and then `navigate("/captures/<id>", {flash: "Saved “<Target>” to Anki. Make another Item from this Capture, or delete it."})`.
  - A failed Save shows a `role="alert"` inline alert in the form:
    - `anki_unavailable`: the Capture copy, "Not saved — Anki isn't reachable" plus the EXPERIENCE.md body.
    - Any other code: "Not saved" with the envelope's message.

    The Draft and its ItemId stay, so Save again re-sends the same ItemId.
- **Router:** a route `/captures/<id>/new` → the captures screen with `{captureId, draft: true}`. With no Draft in memory, the screen calls `history.replaceState` to `/captures/<id>`.

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and failure states are stubbed at the network. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 3.3).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Unit | P0 | Vocabulary and Sentence wire dicts, every field filled | the dump `by_alias` equals the wire dict |
| AC-2 | Unit | P0 | 5 cases: a comma in a Vocabulary or Sentence alternative, blank target, blank russian, unknown category | `ValidationError` raised |
| AC-3 | Unit | P0 | 11 cases: case and space, surrounding and Unicode punctuation, inner punctuation kept, inner whitespace, four apostrophes, NFC, casefold | `normalize_text(text) == expected` |
| AC-4 | Integration | P0 | Set-up Anki; save en/fr × Vocabulary/Sentence under a new ItemId | the new note's cards by ord equal the four expected decks |
| AC-5 | Integration | P0 | No Items, another Item, an Item with the same Target, a `LanguageLabDev` Item with the same ItemId | the queries sent are exactly `{note:"LanguageLab English Vocabulary"}` |
| AC-6 | Integration | P0 | An Item with that ItemId stored plain, or with the ItemId in editor markup, and an `Audio` value | the writes sent are `["updateNoteFields"]` |
| AC-7 | Integration | P0 | Gate in `needs_setup`, `needs_migration` or `newer_schema` | the outcome's code is `setup_required` |
| AC-8 | Integration | P0 | Anki refusing connections; `addNote` answering an error | the outcome's code is `anki_unavailable` |
| AC-9 | API | P0 | Two POSTs over an unavailable fake | the first is 201 |
| AC-10 | API | P0 | en Vocabulary, fr Sentence, over the fake | status 200 |
| AC-11 | API | P0 | 9 cases: comma alternative, blank target or russian, unknown category, uppercase, non-UUID or v1 itemId, item part not JSON, no item part | status 422 |
| AC-12 | E2E | P0 | Capture detail at phone and desktop widths | Write it myself is disabled |
| AC-13 | E2E | P0 | English Vocabulary or Sentence, Use as is, Write it myself | Target has the Capture text |
| AC-14 | E2E | P0 | Open a blank Draft, then the Setup pill | the alert contains "This Draft isn't saved." |
| AC-15 | E2E | P0 | Phone and desktop: en Vocabulary (custom value, two alternatives), then fr Sentence (custom value) from one Capture, against the live server's fake | the success banner for the Vocabulary Target is visible |
| AC-16 | E2E | P0 | Save stubbed 503 `anki_unavailable`, then unstubbed and saved again | the form's alert contains "Not saved — Anki isn't reachable" |
| AC-17 | E2E | P0 | Go straight to /captures/<id>/new | the URL is /captures/<id> |

### Secondary branches for green-phase automation

- AC-2: a Sentence carrying a Vocabulary-only key such as `mnemonic`. Whether ItemContent forbids extra keys is not pinned here; AD-11 makes only the generation models strict.
- AC-4: the `addNote` `fields` sent are already codec-encoded (a test that compares the sent payload, not only the stored note).
- AC-6 / AC-7: an existing note whose `SchemaVersion` differs from the manifest's is refused by the gate's `updateNoteFields` check (AD-19).
- AC-8 (p1, written): a `changeDeck` that fails after `addNote` is `anki_unavailable` and leaves the cards in the Pronunciation deck (a tolerated AD-6 leftover). A retry updates the note and moves nothing, so Setup's repair (story 2.11) has to move the cards. Worth a line in the plan.
- AC-10 (p1, written):
  - A retried Save with the same ItemId replaces the content (AD-20).
  - `create_app(settings)` with no injected store has the route, which proves the wiring.
  - An unavailable store is 503 with nothing saved.
- AC-10: `setup_required` from the store is 409. `audio: "replace"` or `"remove"` is not tested until epic-reference-audio.
- AC-11 (p1, written): a JSON body instead of multipart is 422.
- AC-13 (p1, written): a second "Write it myself" from the same Capture issues a new ItemId.
- AC-14: every leave path in `tests/support/unsaved.LEAVE_PATHS`. Discard (in the editor) asks through `router.confirmLeave()` and goes back to the Capture. Reloading raises the browser's own `beforeunload` prompt.
- AC-15 (p1, written): opening and editing a blank Draft sends no Save (FR-18).
- AC-15: the banner clears when the Capture is left or the next Draft opens (EXPERIENCE.md Success banner).
- AC-16:
  - Another code (e.g. `setup_required`) shows "Not saved" with the envelope's message.
  - Save to Anki is disabled while a Save is in flight.
  - A comma in an alternative line is refused before or at Save, with the edits kept.
- Widths: the phone sticky action bar (S-DraftPhone): Discard and Save to Anki pinned to the viewport bottom, with no horizontal overflow at `viewports.ALL`.

## TDD red phase (current)

Red-phase scaffolds are generated, each file skipped by a module-level `pytestmark = pytest.mark.skip(reason=...)`:

- Unit: 4 tests (19 cases) in `tests/unit/test_items_domain.py`.
- Integration: 6 tests (16 cases) in `tests/integration/test_anki_item_save.py`.
- API: 1 test in `tests/api/test_drafts_blank.py`, and 6 tests (15 cases) in `tests/api/test_items_save.py`.
- E2E: 8 tests (11 cases) in `tests/e2e/test_make_an_item.py`.

`language_lab.domain.items` doesn't exist yet, so it is imported inside the tests and in `tests/support/items.py`, and collection passes while they are skipped.

**Red check (2026-10-22):** each file was run as a copy with its skip marker removed. All 62 cases failed for the expected reasons:

- `ModuleNotFoundError: language_lab.domain.items` (19).
- `AttributeError: 'AnkiConnectStore' object has no attribute 'save_item'` (16).
- POST /api/drafts/blank and POST /api/items/<lang> answering 405 instead of 201, 200, 422 or 503 (16).
- The "Make an Item" pane's controls not found, and /captures/<id>/new falling back to /captures (11).

Afterwards `make test-fast` passed: 579 passed, 51 skipped.

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `unit/test_items_domain.py::test_item_content_is_one_type_discriminated_by_category` |
| AC-2 | `unit/test_items_domain.py::test_item_content_refuses_a_comma_alternative_or_a_blank_required_field` |
| AC-3 | `unit/test_items_domain.py::test_normalize_text_applies_the_ad12_rules` |
| AC-4 | `integration/test_anki_item_save.py::test_a_new_item_id_makes_one_note_with_four_cards_in_their_decks` |
| AC-5 | `integration/test_anki_item_save.py::test_the_item_id_lookup_queries_only_the_exact_note_type_scope` |
| AC-6 | `integration/test_anki_item_save.py::test_a_retried_save_with_the_same_item_id_updates_that_note` |
| AC-7 | `integration/test_anki_item_save.py::test_a_gated_anki_refuses_save_item_before_any_write` |
| AC-8 | `integration/test_anki_item_save.py::test_a_failing_anki_returns_anki_unavailable_with_no_note` |
| AC-9 | `api/test_drafts_blank.py::test_a_blank_draft_issues_a_fresh_item_id` |
| AC-10 | `api/test_items_save.py::test_save_stores_the_item_under_its_item_id` |
| AC-11 | `api/test_items_save.py::test_an_invalid_item_is_validation_failed_and_nothing_is_saved` |
| AC-12 | `e2e/test_make_an_item.py::test_write_it_myself_waits_for_a_language_a_category_and_a_custom_value` |
| AC-13 | `e2e/test_make_an_item.py::test_write_it_myself_opens_a_blank_draft_with_the_target_prefilled` |
| AC-14 | `e2e/test_make_an_item.py::test_leaving_the_draft_editor_raises_the_unsaved_draft_alert` |
| AC-15 | `e2e/test_make_an_item.py::test_a_vocabulary_and_a_sentence_item_are_saved_from_one_capture` |
| AC-16 | `e2e/test_make_an_item.py::test_a_failed_save_keeps_the_draft_and_a_retry_sends_the_same_item_id` |
| AC-17 | `e2e/test_make_an_item.py::test_the_draft_route_with_no_draft_in_memory_shows_the_capture` |

The P1 tests named in the secondary branches each name one of these ACs in their docstring. The P0 test in the table is that AC's primary scaffold.

## Next steps (task-by-task activation)

1. **Domain:**
   - Add `domain/items.py`.
   - Un-skip `tests/unit/test_items_domain.py` (AC-1 to AC-3).
2. **Port, adapter and fake:**
   - Add `AnkiStore.save_item`, `AnkiConnectStore.save_item`, and `FakeAnkiStore.save_item` with `items`. `tests/unit/test_anki_store_port.py` keeps the three in step.
   - Un-skip the integration file (AC-4 to AC-8).
3. **Features and routes:**
   - Add `features/drafts` (blank) and `features/items` (Save), and wire both routers in `create_app`.
   - Un-skip both API files (AC-9 to AC-11).
4. **Screen and router:**
   - Add `blankDraft` and `saveItem` (FormData with the `item` part) to `api.js`.
   - Add the pane and the Draft editor to `captures.js`, their styles to `studio.css`, and the `/captures/<id>/new` route to `router.js`.
   - Un-skip the E2E file (AC-12 to AC-17).
5. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoints:**
  - POST /api/drafts/blank: 201 `{itemId}`.
  - POST /api/items/{lang}, multipart `item`:
    - 200 `{itemId}`.
    - 422 `validation_failed`.
    - 409 `setup_required`.
    - 503 `anki_unavailable` or `anki_busy`.
- **UI:**
  - The Make an Item pane: text choice, pickers, "Write it myself" with its reasons.
  - The Draft editor: header, chip, fields per Category, Discard, Save to Anki, and the inline error alert.
  - The success flash on the Capture.
- **Wiring to check in review:**
  - `create_app` includes the drafts and items routers for both the injected and the built store.
  - `save_item` writes only through `client.invoke`, never `invoke_setup`, so the gate applies.
  - `changeDeck` targets are manifest decks, so the guard passes them.

## Validation (step 5)

- Prerequisites: the criteria come from entry 1; the framework is pytest and pytest-playwright; the dev environment runs.
- Every test's docstring names exactly one declared AC. Each AC has exactly one P0 primary leaf, and parametrized cases are cases of that leaf.
- Each primary leaf's first assertion is the criterion-defining one. Setup actions stay unasserted before it: arranging the collection, choosing in the pane, and the `expect_response` / `expect_request` waits.
- AC-6, AC-14, AC-15 and AC-16 run their transitions:
  - AC-6: a stored Item, then a Save.
  - AC-14: an open Draft, then a leave.
  - AC-15: a Save, then a return to the Capture, then a second Draft.
  - AC-16: a failure, then a retry.
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were removed.

## Completion

- **Risks and assumptions:**
  - The real `changeDeck` and `updateNoteFields` replies, and `cardsInfo` for a fresh note's ords, are hand-built. They are checked against real replies at acceptance (entry 4).
  - A Save whose `changeDeck` fails leaves Pronounce-deck cards for Study Exercises, and a retry doesn't move them (AD-6 tolerates it). Setup's repairs are relied on, so story 2.11's leftover detection should cover "an Item card in the wrong deck". If it doesn't, ticket it.
  - The Draft lives only in the captures screen's memory, so a reload of the editor loses it (decided: back to the Capture). The unsaved alert's `beforeunload` prompt warns first.
  - 200 for both a create and an update, and `{itemId}` as the whole answer, are defaults.
  - "Write it myself" is a button, not a link, so it can be disabled with a reason.
- **Next workflow:** `bmad-build` for story 4.1.

---
runScope: 'story'
runKey: 'story-4-3'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-22'
storyId: '4.3'
storyKey: '4-3'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/tickets.toml (entry 3)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-4-3.md'
generatedTestFiles:
  - 'tests/integration/test_anki_item_reads.py'
  - 'tests/unit/test_anki_store_port.py (test_anki_store_port_adds_the_item_reads_and_the_fake_matches)'
  - 'tests/api/test_items_read.py'
  - 'tests/e2e/test_duplicate_warning.py'
  - 'tests/e2e/test_item_detail.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/tickets.toml (entry 3)'
  - '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/epic-capture-to-item.md (Done when 3; Notes 2026-10-08, 2026-10-22)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-1, AD-4, AD-8, AD-9, AD-10, AD-11, AD-12, AD-13, AD-15, AD-19, AD-20, Consistency Conventions)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-19, FR-22, FR-23, AC8)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Information Architecture; Key strings: Duplicate, Item detail; Bottom sheet; Alert dialog; State Patterns)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Duplicate.dc.html, S-ItemDetail.dc.html; DESIGN.md (Bottom sheet)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-4-2.md (format, conventions, decisions)'
  - 'No test design for epic 4: test-design/test-design-epic-4.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/domain/{items,catalog,errors}.py, ports/anki_store.py, adapters/anki/{store,query,codec}.py, features/items/{routes,service}.py, features/captures/routes.py'
  - 'src/language_lab/static/{api,router}.js, static/screens/{captures,make-item,items}.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{items,items_screen,captures,captures_screen,anki_state,network,unsaved,hosts,live_server,drafts}.py, tests/support/fixtures/logs.py'
  - 'tests/api/test_items_save.py, tests/integration/test_anki_item_save.py, tests/e2e/{test_make_an_item,test_generate_draft}.py, tests/unit/test_anki_store_port.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'AnkiStore.item_candidates(language, category) returns every Item of that Language and Category, each with its ItemId and its fields decoded through the codec into ItemContent, and no Item of the other Category, the other Language, or another Prefix (AD-4, AD-9, AD-10)' }
  - { id: 'AC-2', idSource: 'generated', text: 'Both Item reads send only the exact note-type scope queries of query.py, and no request carries the Target, the ItemId or any other user text (AD-4)' }
  - { id: 'AC-3', idSource: 'generated', text: 'AnkiStore.get_item(language, item_id) returns the Item whose decoded ItemId matches, in either Category of that Language; an ItemId no Item of that Language holds (absent, in the other Language, under another Prefix) is not_found' }
  - { id: 'AC-4', idSource: 'generated', text: 'Both Item reads write nothing and answer under every gated SetupState, as the Capture reads do (AD-19)' }
  - { id: 'AC-5', idSource: 'generated', text: 'The AnkiStore port, its fake and the AnkiConnect adapter declare item_candidates(language, category) -> list[Item] and get_item(language, item_id) -> Item (AD-1)' }
  - { id: 'AC-6', idSource: 'generated', text: 'GET /api/items/<lang>/duplicates?category=&target= is 200 {matches: [{itemId, ...ItemContent}]} holding each Item of that Language and Category whose normalized Target equals the normalized target: case, surrounding punctuation, whitespace, apostrophe variants and Unicode composition ignored (AD-12)' }
  - { id: 'AC-7', idSource: 'generated', text: 'A Target that differs in diacritics or inside the text, and an equal Target in the other Language or the other Category, is not a match (FR-19, AD-12)' }
  - { id: 'AC-8', idSource: 'generated', text: 'itemId= excludes the Item''s own ItemId from the matches, and the other matches stay (AD-12)' }
  - { id: 'AC-9', idSource: 'generated', text: 'A missing or blank target, a missing or unknown category, an unknown Language or an itemId that isn''t a lowercase UUIDv4 is 422 validation_failed, and Anki is not read' }
  - { id: 'AC-10', idSource: 'generated', text: 'GET /api/items/<lang>/<itemId> is 200 {itemId, ...ItemContent}, flat like the Draft and the Save (AD-11)' }
  - { id: 'AC-11', idSource: 'generated', text: 'An ItemId no Item of that Language holds, or one that isn''t a UUIDv4, is 404 not_found' }
  - { id: 'AC-12', idSource: 'generated', text: 'Save to Anki on a Draft first asks GET duplicates with the Draft''s Language, Category, current Target and ItemId; with no match it saves at once, and no sheet is shown' }
  - { id: 'AC-13', idSource: 'generated', text: 'With a match, the duplicate sheet (S-Duplicate) shows "Possible duplicate · <Language> · <Category>", "You already have an Item with this text", the match''s Target and Russian meaning, "Nothing has been saved yet. You can still create a second Item." and Open existing, Cancel and Create anyway, and nothing is saved' }
  - { id: 'AC-14', idSource: 'generated', text: 'Create anyway saves the Draft under its ItemId and returns to the Capture with the success banner: creation is never blocked (FR-19)' }
  - { id: 'AC-15', idSource: 'generated', text: 'Cancel closes the sheet and keeps the Draft in the editor with nothing saved; after the Target is edited, Save to Anki checks again with the new Target' }
  - { id: 'AC-16', idSource: 'generated', text: 'Open existing asks about the unsaved Draft, and on Discard opens /<lang>/items/<itemId> of the match' }
  - { id: 'AC-17', idSource: 'generated', text: 'Item detail at /<lang>/items/<itemId> (S-ItemDetail) reads the Item and shows its values view-only: Target as the heading, the Category, each field''s value, no editable field, and "‹ English Items"' }
  - { id: 'AC-18', idSource: 'generated', text: 'Item detail of an ItemId Anki doesn''t hold shows "This Item isn''t in Anki.", and a failed read shows an alert with Try again, which reads again' }
---

# ATDD Checklist: Story 4.3, Duplicate warning, Item read, and view-only Item detail

## Run context

- **Story source:** epic-capture-to-item `tickets.toml`, entry 3 (`risk = "medium"`, after entry 2, merged in PR #42). There is no story file, so this checklist holds the criteria. AC-1 to AC-18 follow the ticket's description in source order, with the verify clauses folded in:
  - "a normalized match (case, punctuation, whitespace, apostrophe variants) found in the same Language and Category" is AC-6.
  - "diacritics kept significant, matches in the other Language or Category not returned" is AC-7.
  - "the Item's own ItemId excluded" is AC-8.
  - "the sheet's three choices" is AC-13.
  - "Create anyway saving" is AC-14.
  - "Open existing landing on the Item detail with its values" is AC-16 and AC-17.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in epics 1 to 4 (dev-only, NFR-11).
- **Test design:** none for epic 4. Priorities follow the ticket's risk (medium), epic Done when 3, and AD-4 and AD-12. AC-4 (reads not gated), AC-5 (port shape) and AC-18 (Item detail failure states) are P1. Every other criterion is P0.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - Changed: `domain/items.py` (`Item`), `ports/anki_store.py`, `adapters/anki/store.py` and `tests/fakes/anki_store.py` (`item_candidates`, `get_item`), `features/items/{routes,service}.py` (the duplicate read and the Item read), `static/api.js` (`findDuplicates`, `getItem`), `static/router.js` (the Item detail route), `static/screens/{captures,make-item}.js` (the check at Save and the sheet).
  - New: the Item detail screen module (for example `static/screens/item-detail.js`).
  - Tests (done in this run):
    - `tests/support/duplicates.py`: stored Items on the wire, `stored_item()`, `store_with_items()`.
    - `tests/support/items_screen.py`: the duplicate sheet and Item detail copy, locators and the duplicates stub.
    - The two Item E2E files stub an empty duplicate read in `open_capture`, so their Saves aren't stopped by Items earlier tests left in the session's fake.

### Decision taken with the user (2026-10-22)

| Question | Decision |
| --- | --- |
| When does the duplicate sheet appear for a new Item? | **At Save to Anki.** Save first checks the Draft's current Target. A match opens the sheet: Create anyway saves, Cancel goes back to the editor, Open existing goes to Item detail. If the Target is edited after Create anyway was chosen, the check runs again at the next Save. Nothing is read from Anki while the user types. |

### Defaults taken without a question

- **Domain (`domain/items.py`):** `Item(item_id: str, content: ItemContent)`, a frozen dataclass. On the wire it is `{itemId, ...ItemContent}`, flat like the Draft and the Save.
- **Port:**
  - `item_candidates(language: Language, category: Category) -> list[Item]`: every Item of that note type, in `findNotes` order (oldest note first).
  - `get_item(language: Language, item_id: str) -> Item`: matched in Python over both Categories of the Language, `AppError(NOT_FOUND)` when none.
  - Both are reads under one lock hold and not gated (AD-19), like `list_captures` and `get_capture`. Both raise `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
- **Adapter:** the queries are `note_query(manifest, <note type>)`, the same as Save's ItemId lookup. The Prefix-specific note type already confines a search to the Prefix, so no deck term is added. A note is decoded through the codec: `RussianAlternatives` split by the adapter (AD-10), markup and entities removed (AD-9). Missing optional fields come back as `""`.
- **Fake:** `item_candidates` and `get_item` read `items` (already `{item_id: (Language, ItemContent)}` since 4.1), in insertion order. They raise `anki_busy` or `anki_unavailable` as the other methods do.
- **Service (`ItemService`):**
  - `duplicates(language, category, target, item_id=None) -> list[Item]`: the candidates whose `normalize_text(Target)` equals `normalize_text(target)`, with `item_id` left out. The adapter's order is kept.
  - `get(language, item_id) -> Item`.
- **Routes:**
  - GET `/api/items/<lang>/duplicates?category=&target=&itemId=`: `category` and `target` are required, `target` non-blank, and `itemId` is an optional lowercase UUIDv4. The reply is 200 `{matches: [{itemId, ...ItemContent}]}`. Invalid input is 422 `validation_failed`. Like every query string, the Target is never logged (AD-15).
  - GET `/api/items/<lang>/<itemId>`: 200 `{itemId, ...ItemContent}`. A malformed ItemId is 404 `not_found` without reaching Anki, as Captures does.
  - Anki down is 503 `anki_unavailable`, through the existing mapping.
- **Screen, the check at Save:**
  - Save to Anki asks `findDuplicates(language, category, target, itemId)` before the Save, with the Draft's current values. Save to Anki is busy while it waits.
  - No match: Save goes ahead.
  - A failed check shows the Save's own inline alert (for `anki_unavailable`, "Not saved — Anki isn't reachable"), and nothing is saved.
  - After Create anyway, the Save skips the check while the normalized Target stays the same, so a failed Save's retry doesn't ask again.
- **Screen, the sheet:**
  - A `role="dialog"` named "You already have an Item with this text". The overline is "Possible duplicate · English · Vocabulary" (or French, or Sentence).
  - Each match is shown as a card with its Target and Russian meaning, in the server's order.
  - The body is "Nothing has been saved yet. You can still create a second Item."
  - The buttons are the Primary "Open existing", the Secondary "Cancel" and the text button "Create anyway". With several matches, Open existing opens the first.
  - It is a bottom sheet on the phone and a centered dialog from tablet width up (EXPERIENCE.md Bottom sheet). Focus starts on Open existing (the Primary) and stays trapped. Esc, the scrim and Cancel close it.
- **Screen, Open existing:**
  - Calls `router.confirmLeave()` for the dirty Draft (AD-13). Discard drops the Draft and navigates to `/<lang>/items/<itemId>`.
  - Keep editing leaves the screen unchanged, with the sheet still open.
- **Screen, Item detail:**
  - The route is `/en/items/<itemId>` or `/fr/items/<itemId>`. The English area's nav is current.
  - It re-reads on every mount (AD-13). While loading it shows a skeleton with "Loading Item…" (`role="status"`).
  - The `h1` is the Target. Then the Category ("Vocabulary" / "Sentence"), then each filled field under the Draft editor's labels ("Russian meaning", "Alternatives", "Part of speech", "Grammar", "Hint", "Example", "Example in Russian", "Mnemonic"; for a Sentence, "Note"). No textbox, and no Save changes, Delete or Regenerate (those are epic-maintain-items').
  - The back link "‹ English Items" (or "‹ French Items") goes to `/<lang>/items`.
  - `not_found` shows "This Item isn't in Anki." Any other failure shows an inline error alert with the envelope's message and "Try again".

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and the duplicate read, the Item read and the generated Draft are stubbed at the network for the screen tests. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 4.2).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | A collection with Items of every note type, one stored in editor markup, and a LanguageLabDev Item, read per Language and Category | the returned ItemIds equal that note type's |
| AC-2 | Integration | P0 | Each read, with a Target and an ItemId stored | the sent queries equal the note types' exact queries |
| AC-3 | Integration | P0 | An English Vocabulary and an English Sentence Item, each read by ItemId | the returned ItemId is the one asked for |
| AC-4 | Integration | P1 | Each read under `needs_setup`, `needs_migration` and `newer_schema` | no write action is sent |
| AC-5 | Unit | P1 | Port, fake and adapter | the fake's and the adapter's signatures equal the port's |
| AC-6 | API | P0 | 6 cases: case, surrounding punctuation, inner whitespace, apostrophe variants, decomposed accents, all together | the match's `itemId` is the stored Item's |
| AC-7 | API | P0 | 4 cases: diacritics, an inner difference, the other Language, the other Category | `matches` is empty |
| AC-8 | API | P0 | The Draft's own Item and another Item with the same Target | `matches` holds only the other's ItemId |
| AC-9 | API | P0 | 8 cases: no target, blank target, no category, unknown category, unknown Language, malformed, uppercase, v1 itemId, over an unavailable Anki | status 422 |
| AC-10 | API | P0 | An English Vocabulary and a French Sentence Item | status 200 |
| AC-11 | API | P0 | 3 cases: absent, in the other Language, not a UUID | status 404 |
| AC-12 | E2E | P0 | A generated Draft with an empty duplicate stub, then Save | the check's query carries the Draft's Category, Target and ItemId |
| AC-13 | E2E | P0 | One match, at phone and desktop widths | the sheet is visible |
| AC-14 | E2E | P0 | The sheet, then Create anyway | a Save is sent with the Draft's ItemId |
| AC-15 | E2E | P0 | The sheet, Cancel, edit the Target, Save again | the sheet is hidden after Cancel |
| AC-16 | E2E | P0 | The sheet, Open existing, Discard | the unsaved alert is visible |
| AC-17 | E2E | P0 | /en/items/<itemId> with the read stubbed, Vocabulary and Sentence | the heading is the Target |
| AC-18 | E2E | P1 | `not_found`, then `anki_unavailable` and Try again | the not-in-Anki copy is visible |

### Secondary branches for green-phase automation

- AC-1:
  - Missing optional fields come back as `""`. An empty `RussianAlternatives` comes back as `[]`.
  - (p1, written) A note deleted between `findNotes` and `notesInfo` is skipped, and a malformed reply is `anki_unavailable`.
- AC-3:
  - (p0, written) An ItemId no English Item holds (absent, a French Item's, a LanguageLabDev Item's) is `not_found`.
  - (p1, written) A failing Anki is `anki_unavailable`.
- AC-6:
  - Several matches come back in note order.
  - (p1, written) Neither the Target nor the query string is in any log line (AD-15).
- AC-9: an `itemId` left empty (`itemId=`) is treated as absent.
- AC-10: (p1, written) Anki down is 503 `anki_unavailable`, for both reads.
- AC-12:
  - Save to Anki is busy (disabled) while the check is in flight.
  - (p1, written) A failed check shows the Save's alert and sends no Save.
- AC-13:
  - Focus starts on Open existing and is trapped.
  - Esc and a scrim tap close the sheet like Cancel.
  - On the phone the sheet is pinned to the bottom of the viewport, and on the desktop it is centered, with no horizontal overflow at `viewports.ALL`.
  - With several matches, each is listed and Open existing opens the first.
  - The overline names French and Sentence for a French Sentence Draft.
- AC-14: (p1, written) a failed Save after Create anyway, retried, sends no second check while the Target is unchanged.
- AC-15: Cancel returns focus to Save to Anki.
- AC-16: Keep editing leaves the sheet open and the Draft as it was.
- AC-17:
  - The English nav is current.
  - "‹ English Items" goes to /en/items.
  - A French Item's back link is "‹ French Items".
  - Empty fields are not shown.
  - (p1, written) The Item is read again on every mount, so a value changed in Anki shows the next time (FR-22).
- AC-18: "Loading Item…" shows while the read is in flight.

## TDD red phase (current)

Red-phase scaffolds are generated. Each new file is skipped by a module-level `pytestmark = pytest.mark.skip(reason=...)`, and the port test by its own `@pytest.mark.skip`:

- Integration: 7 tests (17 cases) in `tests/integration/test_anki_item_reads.py`.
- Unit: 1 test in `tests/unit/test_anki_store_port.py` (`test_anki_store_port_adds_the_item_reads_and_the_fake_matches`).
- API: 8 tests (27 cases) in `tests/api/test_items_read.py`.
- E2E:
  - 7 tests (8 cases) in `tests/e2e/test_duplicate_warning.py`.
  - 3 tests (4 cases) in `tests/e2e/test_item_detail.py`.

`Item` and the two reads don't exist yet. `Item` is imported inside `tests/support/duplicates.py` and the port test, so collection passes while they are skipped.

**Red check (2026-10-22):** each file was run as a copy with its skip marker removed. All 57 cases failed for the expected reasons:

- `AttributeError`: `AnkiConnectStore` has no `item_candidates` (7) or `get_item` (10).
- `ImportError`: `Item` from `language_lab.domain.items` (1).
- The duplicate read answers 404, so `matches` is missing (11), and the invalid reads are 404, not 422 (8).
- The Item read answers 404 (3 for 200, 2 for 503).
- No route answered the not-found reads (3). See the note below.
- On screen:
  - No duplicate check sent (1).
  - No sheet (2), so its buttons weren't found (3).
  - No Save alert (1), and no second-check guard (1).
  - Item detail not shown, not found and failed-read states (4).

The first AC-11 run passed: a path no route matches is also 404 `not_found`. AC-11 now first asserts that the request log's route template is the Item read's, and fails.

Afterwards `make test-fast` passed (681 passed, 45 skipped), and so did `tests/e2e/test_make_an_item.py` and `tests/e2e/test_generate_draft.py` (24 passed). `ruff check` and `ruff format --check` are clean.

### Other changes in this run

- `open_capture()` in `tests/e2e/test_make_an_item.py` and `tests/e2e/test_generate_draft.py` now stubs an empty duplicate read. The live server's `FakeAnkiStore` is shared by the session, so once Save checks for duplicates, an Item an earlier test saved with the same Target would open the sheet and stop those Saves. Until the check exists, the stub is never hit.
- `tests/support/items_screen.py` has the sheet and Item detail copy and locators, and `stub_duplicates()`. Playwright runs the newest route first, so a test's later stub overrides an earlier one.
- The tests README lists `duplicates.py` and the new `items_screen.py` helpers.

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `integration/test_anki_item_reads.py::test_item_candidates_returns_every_item_of_the_language_and_category_decoded` |
| AC-2 | `integration/test_anki_item_reads.py::test_the_item_reads_send_only_exact_note_type_queries_and_no_user_text` |
| AC-3 | `integration/test_anki_item_reads.py::test_get_item_returns_the_item_matched_in_python_in_either_category` |
| AC-4 | `integration/test_anki_item_reads.py::test_the_item_reads_write_nothing_and_answer_when_anki_is_gated` |
| AC-5 | `unit/test_anki_store_port.py::test_anki_store_port_adds_the_item_reads_and_the_fake_matches` |
| AC-6 | `api/test_items_read.py::test_duplicates_returns_the_item_whose_normalized_target_matches` |
| AC-7 | `api/test_items_read.py::test_a_target_that_differs_or_another_language_or_category_is_no_match` |
| AC-8 | `api/test_items_read.py::test_the_drafts_own_item_id_is_left_out_of_the_matches` |
| AC-9 | `api/test_items_read.py::test_an_invalid_duplicate_read_is_validation_failed_and_anki_is_not_read` |
| AC-10 | `api/test_items_read.py::test_get_item_returns_the_item_flat_with_its_item_id` |
| AC-11 | `api/test_items_read.py::test_get_item_of_an_item_id_no_item_of_the_language_holds_is_not_found` |
| AC-12 | `e2e/test_duplicate_warning.py::test_save_checks_the_current_target_first_and_saves_when_nothing_matches` |
| AC-13 | `e2e/test_duplicate_warning.py::test_a_match_opens_the_duplicate_sheet_and_nothing_is_saved` |
| AC-14 | `e2e/test_duplicate_warning.py::test_create_anyway_saves_the_draft_and_returns_to_the_capture` |
| AC-15 | `e2e/test_duplicate_warning.py::test_cancel_keeps_the_draft_and_an_edited_target_is_checked_again` |
| AC-16 | `e2e/test_duplicate_warning.py::test_open_existing_asks_about_the_draft_then_opens_the_match` |
| AC-17 | `e2e/test_item_detail.py::test_item_detail_shows_the_items_values_view_only` |
| AC-18 | `e2e/test_item_detail.py::test_item_detail_of_an_item_id_anki_doesnt_hold_says_so` |

The extra tests named in the secondary branches (marked "written") each name one of these ACs in their docstring. The test in the table is that AC's primary scaffold.

## Next steps (task-by-task activation)

1. **Domain and port:**
   - Add `Item` to `domain/items.py`.
   - Add `item_candidates()` and `get_item()` to `ports/anki_store.py`, `adapters/anki/store.py` and `tests/fakes/anki_store.py`. Add both to the exact method set in story 2.6's port test.
   - Un-skip the port test (AC-5) and `tests/integration/test_anki_item_reads.py` (AC-1 to AC-4).
2. **Feature:**
   - Add `ItemService.duplicates()` and `ItemService.get()`.
   - Add GET `/api/items/{lang}/duplicates` before GET `/api/items/{lang}/{item_id}` in `features/items/routes.py`.
   - Un-skip `tests/api/test_items_read.py` (AC-6 to AC-11).
3. **Screen, the check and the sheet:**
   - Add `findDuplicates` and `getItem` to `api.js`.
   - In `captures.js` / `make-item.js`: the check at Save to Anki, the sheet, Create anyway, Cancel, and Open existing through `router.confirmLeave()`.
   - Un-skip `tests/e2e/test_duplicate_warning.py` (AC-12 to AC-16).
4. **Screen, Item detail:**
   - Add the `/(en|fr)/items/<itemId>` route to `router.js` and the view-only screen module.
   - Un-skip `tests/e2e/test_item_detail.py` (AC-17, AC-18).
5. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoints:**
  - GET `/api/items/<lang>/duplicates?category=&target=&itemId=`: 200 `{matches: [{itemId, ...ItemContent}]}`; 422 `validation_failed`.
  - GET `/api/items/<lang>/<itemId>`: 200 `{itemId, ...ItemContent}`; 404 `not_found`.
  - Both: 503 `anki_unavailable` when Anki is down.
- **Adapter:** `findNotes` with `note_query()` only, then `notesInfo`, decoded through the codec. The ItemId and the Target are matched in Python, never sent (AD-4).
- **Service:** `normalize_text()` on both sides (AD-12). Leave out `item_id`.
- **UI:**
  - The sheet: `role="dialog"` named "You already have an Item with this text", with the overline, the match cards, the reassurance, then Open existing / Cancel / Create anyway.
  - Item detail: `h1` Target, the Category, the field values, the back link.
- **Wiring to check in review:**
  - The duplicates route is declared before the `{item_id}` route.
  - The Target is in no log line.
  - Open existing clears the Draft only after the router's Discard.

## Validation (step 5)

- Prerequisites: the criteria come from entry 3; the framework is pytest and pytest-playwright; the dev environment runs.
- Every test's docstring names exactly one declared AC. Each AC has exactly one primary leaf, and parametrized cases are cases of that leaf.
- Each primary leaf's first assertion is the criterion-defining one:
  - Setup stays unasserted before it. `open_sheet()` asserts nothing.
  - The unimplemented reads are opaque until then. The API leaves read `matches` with `.get`, so they fail on an assertion, not a `KeyError`.
- The transition criteria run their transitions:
  - AC-12: a Target edit, then Save.
  - AC-14: Create anyway.
  - AC-15: Cancel, an edit, then Save again.
  - AC-16: Open existing, then Discard.
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were removed.

## Completion

- **Risks and assumptions:**
  - The duplicate read sends the Target in a query string. AD-15 keeps query strings out of the logs, and a p1 test checks it. A POST would keep it out of proxies too, but AD-12 names a GET.
  - The check runs at Save (decided 2026-10-22), so a generated Draft can still cost a model call for a duplicate. The other option (checking before Generate) was declined.
  - Item detail is view-only here. Edit, regenerate and delete, and the duplicate check on a Target change in Item detail (FR-23), are epic-maintain-items'.
  - `get_item` searches both Category note types of the Language (two `findNotes`). That's fine for a personal collection. Story 4.4's acceptance run can time it next to the `read_leftovers` cost.
  - The live server's fake keeps Items across E2E tests. The Item E2E files stub the duplicate read, so the result doesn't depend on test order.
- **Next workflow:** `bmad-build` for story 4.3.

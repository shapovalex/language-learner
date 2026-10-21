---
runScope: 'story'
runKey: 'story-2-11'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.11'
storyKey: '2-11'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 11)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-11.md'
generatedTestFiles:
  - 'tests/integration/test_anki_setup_repairs.py'
  - 'tests/api/test_setup_repairs.py'
  - 'tests/e2e/test_setup_repairs.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md (Notes: opt-in repairs decision of 2026-10-14)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-3 Unrecognized content, AD-4, AD-7)'
  - '_bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md (opt-in repair items)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md (Capture card suspended)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Change row, Nothing to change)'
  - '_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md (getMediaFilesNames, storeMediaFile case Surprise)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-9.md (format, conventions)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{guard,store,setup_diff,setup_apply,setup_gate,manifest,codec}.py, domain/setup.py, ports/anki_store.py, features/setup/{routes,service}.py'
  - 'src/language_lab/static/screens/setup.js, static/api.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_state,anki_connect,network,aio,clock}.py'
  - 'tests/integration/{test_anki_migrations,test_anki_prefix_guard}.py, tests/api/test_setup_migrations.py, tests/e2e/test_setup_full_sync.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'An AD-7 media file that no managed note''s Audio field references, read through the codec, previews as an orphanMedia opt-in repair row; a referenced one and another Prefix''s do not' }
  - { id: 'AC-2', idSource: 'generated', text: 'A managed card in a deck other than card_deck(note type, ord) previews as a misplacedCard opt-in repair row named by its card id' }
  - { id: 'AC-3', idSource: 'generated', text: 'An unsuspended Capture card previews as an unsuspendedCard opt-in repair row; a suspended one and an Exercise card do not' }
  - { id: 'AC-4', idSource: 'generated', text: 'GET /api/setup/plan lists every offered row under repairs with its key, unchecked, and planHash is the required items'' alone' }
  - { id: 'AC-5', idSource: 'generated', text: 'Setup shows each opt-in repair row with an unchecked checkbox, apart from the read-only Not managed rows' }
  - { id: 'AC-6', idSource: 'generated', text: 'Unchecked rows stay out of the plan, its hash and the SetupState: leftovers alone leave the state ready' }
  - { id: 'AC-7', idSource: 'generated', text: 'GET /api/setup/plan?repair=<key> answers with that row checked and planHash over the required items plus that row' }
  - { id: 'AC-8', idSource: 'generated', text: 'Non-managed notes and decks stay read-only: no repair row, and an apply with every row checked never touches them' }
  - { id: 'AC-9', idSource: 'generated', text: 'Applying without checking a row sends no write and every leftover stays' }
  - { id: 'AC-10', idSource: 'generated', text: 'Checking one row and applying changes exactly that resource (deleteMediaFile, changeDeck or suspend), and the other leftovers stay offered' }
  - { id: 'AC-11', idSource: 'generated', text: 'A checked row must be confirmed by the hash that includes it: under the unchecked plan''s hash the apply is refused with plan_changed before any write' }
  - { id: 'AC-12', idSource: 'generated', text: 'Checking a box re-reads the plan with ?repair=<key>, and Apply setup posts that plan''s hash with the checked keys as repairs' }
  - { id: 'AC-13', idSource: 'generated', text: 'POST /api/setup/apply hands the checked repairs to the store, which hashes the required items plus those rows' }
---

# ATDD Checklist: Story 2.11, Opt-in repairs for leftovers

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 11 (`risk = "medium"`). There is no story file, so this checklist holds the criteria. AC-1 to AC-13 follow the ticket's description and verify clause in source order:
  - "orphan media (an AD-7 name no note's Audio field references, read through the codec)" is AC-1.
  - "managed cards in the wrong deck for their ord" is AC-2.
  - "unsuspended Capture cards" is AC-3.
  - "to the plan as repair rows each with an unchecked checkbox" is AC-4 (wire) and AC-5 (screen).
  - "only checked rows entering the plan and its hash" is AC-6 and AC-7.
  - "while non-managed notes and decks stay read-only" is AC-8.
  - Verify: "apply without checking changes nothing" is AC-9; "checking one changes exactly that resource" is AC-10; "and changes the hash" is AC-7 and AC-11; "a non-managed note is never touched" is AC-8.
  - AC-12 and AC-13 come from the decisions below.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in stories 2.1 to 2.9 (dev-only, NFR-11).
- **Test design:** none for epic 2. Priorities follow the ticket's risk (medium), raised to P0 where a repair writes to Anki (NFR-1, AD-4).
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - Changed: `domain/setup.py` (three `ResourceKind`s, `PlanItem.key`, `SetupPreview.repairs`), `adapters/anki/{setup_gate,setup_diff,setup_apply,store}.py` (read cards and media, offer rows, run checked ones), `ports/anki_store.py` (`setup_apply(plan_hash, repairs=)`), `features/setup/{service,routes}.py` (`?repair=`, `repairs` in the plan and the apply body), `static/screens/setup.js`, `static/api.js`, `static/css/studio.css`, `tests/fakes/anki_store.py`.
  - Tests (done in this run): `tests/support/anki_state.py` holds cards (`add_card()`, `Card`) and media (`collection.media`), answers `findCards` on an exact `note:` query, `cardsInfo` and `getMediaFilesNames` (case-sensitive `pattern`), and with `writes=True` answers `changeDeck`, `suspend` and `deleteMediaFile` (`REPAIR_WRITE_ACTIONS`). With no cards or media it answers as before.

### Decisions taken with the user (2026-10-21)

| Question | Decision |
| --- | --- |
| How does the screen get the hash for the rows it checked? | **The server re-plans.** GET /api/setup/plan?repair=<key>&repair=<key> answers with those rows checked and `planHash` over the required items plus the checked rows. The screen re-reads the plan on each toggle. Apply sends `{planHash, repairs: [keys]}`; the server re-diffs, re-hashes, and refuses a mismatch with `plan_changed`. |
| How much does one row cover? | **One row per resource.** Orphan media: one row per file, named by its file name. Misplaced card: one row per card, named by its card id. Unsuspended Capture card: one row per card. |

### Defaults taken without a question

- **Domain:**
  - `ResourceKind.ORPHAN_MEDIA = "orphanMedia"`, `MISPLACED_CARD = "misplacedCard"`, `UNSUSPENDED_CARD = "unsuspendedCard"`, all with `PlanAction.REPAIR`.
  - `PlanItem.key` is `f"{kind}:{name}"`.
  - A card row carries display detail that is excluded from equality and the hash (say `detail: Mapping[str, str] = field(default_factory=dict, compare=False, hash=False)`): `noteType`, `card` (template name), `deck` (where it is), plus `expectedDeck` for a misplaced card.
  - `SetupPreview.repairs: tuple[PlanItem, ...] = ()` lists every offered row. `items` stays the required rows only.
- **Detection** (in the preview's reads, still reads only):
  - **Orphan media:** `getMediaFilesNames` with `pattern` `<Prefix>_*`. A name counts only if it fully matches the guard's AD-7 pattern; it's an orphan unless some manifest note's `Audio` field, decoded through the codec, holds `[sound:<name>]`. The notes come from the `notesInfo` read the SchemaVersion already does.
  - **Misplaced card:** `findCards` with each manifest note type's exact `note:` query, then one `cardsInfo`. A card is misplaced when its `deckName` isn't `manifest.card_deck(modelName, ord)`, including a card the user moved out of the Prefix.
  - **Unsuspended Capture card:** a Capture card whose `queue` isn't -1.
- **The hash and state:** `plan_hash((*items, *checked))`. A requested key the fresh preview no longer offers is left out, so the hash differs and the apply is refused as `plan_changed`. The SetupState is computed from `items` only, so leftovers never gate feature writes (AD-19).
- **Apply:** `setup_apply(plan_hash, repairs: Collection[str] = ())`. Under the same lock hold, after the refusals and the Create/Repair/Migrate work, each checked row runs one write through the guarded, ungated path: `deleteMediaFile`, `changeDeck` to the expected deck, or `suspend`. A failed write doesn't end the run. Verify is the fresh diff: `verified` is `not items` plus "no checked key still offered". Each checked key still offered is a discrepancy; unchecked rows aren't.
- **Wire:**
  - The plan gains `"repairs": [{key, action, kind, name, checked, ...detail}]`.
  - GET /api/setup/plan takes repeated `repair` query parameters.
  - The apply body gains optional `"repairs": [key]` (default `[]`).
  - `items`, `requiresFullSync` and `fullSyncRequired` are unchanged.
- **Screen:**
  - An "Optional repairs" card goes below the change list or the "Nothing to change" callout, with the note "Nothing here changes unless you check it.". Its list is labelled by its heading, as the other Setup cards' lists are.
  - Each row is a checkbox labelled by its text:
    - media: the file name with "Not used by any note.";
    - misplaced: "`<noteType>` · `<card>`" with "In `<deck>`; belongs in `<expectedDeck>`.";
    - unsuspended: "`<noteType>` card" with "Not suspended."
  - Toggling a box re-reads the plan with the checked keys. Apply setup shows when the plan has an item or a box is checked, and posts the re-read plan's `planHash` and the checked keys.
  - All of this copy is default copy, not from the UX docs.

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and the screen state is stubbed at the network. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 2.9).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | Media: an orphan, one referenced in editor markup, one referenced plainly, a `LanguageLabDev` one, two non-AD-7 names | the offered keys are the orphan's only |
| AC-2 | Integration | P0 | Vocabulary cards: ord 0 in place, ord 1 in Understand, ord 3 in Produce, one moved to `Default` | the offered keys are the three misplaced cards |
| AC-3 | Integration | P0 | Capture cards unsuspended and suspended, Exercise cards unsuspended | the offered key is the unsuspended Capture card's |
| AC-4 | API | P0 | Fake preview: one Create deck item, one row of each kind | `repairs` keys with `checked` false |
| AC-5 | E2E | P0 | Stubbed plan of three repairs and one unmanaged deck | three unchecked checkboxes in the "Optional repairs" list |
| AC-6 | Integration | P0 | A set-up Anki with one leftover of each kind | `items` is empty |
| AC-7 | API | P0 | `?repair=<media key>&repair=<gone key>` | `planHash` is `plan_hash(required + media row)` |
| AC-8 | Integration | P0 | A Basic note's cards in Captures (unsuspended) and in an unmanaged `<Prefix>::Old` deck | no row names those cards |
| AC-9 | Integration | P0 | Apply the unchecked plan's hash with no repairs | no write sent |
| AC-10 | Integration | P0 | Check one row of each kind in turn (3 cases) | the only write sent is that kind's |
| AC-11 | Integration | P0 | Check the orphan under the unchecked plan's hash | `AppError(PLAN_CHANGED)` |
| AC-12 | E2E | P0 | Check the first box, click Apply setup | the POST body is `{planHash: <re-read hash>, repairs: [key]}` |
| AC-13 | API | P0 | POST the checked hash with `repairs: [card key]` | status 200 |

### Secondary branches for green-phase automation

- AC-1: an `Audio` field holding two `[sound:]` tags; a name that matches AD-7 under another case (spike 2.2: `storeMediaFile` may lowercase) is not listed, since the guard couldn't delete it.
- AC-2: a misplaced Capture card (expected `<Prefix>::Captures`); a card in a deck that doesn't exist any more; the row's `expectedDeck` detail on the wire.
- AC-3: a Capture card that is both misplaced and unsuspended gives two rows, one of each kind.
- AC-4: `items`, `planHash` and `state` are unchanged with no leftovers, and `repairs` is `[]`. `tests/api/test_setup_plan.py` compares whole bodies, so it gains `"repairs": []` in green phase.
- AC-6: `PlanItem.key` and the detail field don't change `plan_hash` (unit).
- AC-7: a key the preview doesn't offer is ignored (covered by the `gone` key in AC-7); a repeated key counts once.
- AC-10: a write that fails (e.g. `suspend` answering an error) doesn't end the run, and the row comes back as a discrepancy; `changeDeck` and `suspend` go through the guard's `cardsInfo` check, `deleteMediaFile` through its AD-7 check.
- AC-11: a checked resource that vanished between the plan and the apply (the orphan deleted in Anki Desktop) is refused as `plan_changed`.
- AC-12: unchecking re-reads the plan without the key; Apply setup is hidden while there are no items and nothing is checked; a `plan_changed` refusal re-reads the plan and keeps the boxes the user checked that are still offered.
- AC-13: the fake's hash covers the required items plus the checked rows (kept in step with the store); `apply_status()` results carry the same shape.

## TDD red phase (current)

Red-phase scaffolds are generated, each marked `pytest.mark.skip` through a module-level `RED_PHASE` marker:

- Integration: 8 tests (10 cases) in `tests/integration/test_anki_setup_repairs.py`.
- API: 3 tests in `tests/api/test_setup_repairs.py`.
- E2E: 2 tests in `tests/e2e/test_setup_repairs.py`.

Names that don't exist yet (`ResourceKind("orphanMedia")`, `SetupPreview(repairs=)`, `setup_apply(..., repairs=)`) are reached inside the tests, so collection passes while they are skipped.

**Red check (2026-10-21):** each file was run with `RED_PHASE` removed. All 15 cases failed for the expected reasons:

- `'SetupPreview' object has no attribute 'repairs'` (8).
- `setup_apply() got an unexpected keyword argument 'repairs'` (2: AC-9, AC-11).
- `'orphanMedia' is not a valid ResourceKind` (3: the API tests).
- The "Optional repairs" checkboxes weren't found (2: AC-5, and AC-12's `check()` timed out).

The rest of the suite still passes with the extended `anki_state.py` (`make test-fast`: 472 passed, 13 skipped).

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `test_anki_setup_repairs.py::test_orphan_media_previews_as_an_opt_in_repair_row` |
| AC-2 | `test_anki_setup_repairs.py::test_a_managed_card_in_the_wrong_deck_previews_as_an_opt_in_repair_row` |
| AC-3 | `test_anki_setup_repairs.py::test_an_unsuspended_capture_card_previews_as_an_opt_in_repair_row` |
| AC-4 | `api/test_setup_repairs.py::test_the_plan_lists_each_opt_in_repair_unchecked` |
| AC-5 | `e2e/test_setup_repairs.py::test_each_opt_in_repair_shows_with_an_unchecked_checkbox` |
| AC-6 | `test_anki_setup_repairs.py::test_opt_in_rows_stay_out_of_the_plan_its_hash_and_the_setup_state` |
| AC-7 | `api/test_setup_repairs.py::test_checking_a_repair_enters_it_in_the_plan_hash` |
| AC-8 | `test_anki_setup_repairs.py::test_non_managed_notes_and_decks_stay_read_only` |
| AC-9 | `test_anki_setup_repairs.py::test_applying_without_checking_a_repair_changes_nothing` |
| AC-10 | `test_anki_setup_repairs.py::test_checking_one_repair_changes_exactly_that_resource` |
| AC-11 | `test_anki_setup_repairs.py::test_a_checked_repair_must_be_confirmed_by_the_hash_that_includes_it` |
| AC-12 | `e2e/test_setup_repairs.py::test_checking_a_repair_replans_and_apply_posts_it_with_the_new_hash` |
| AC-13 | `api/test_setup_repairs.py::test_apply_hands_the_checked_repairs_to_the_store` |

## Next steps (task-by-task activation)

1. **Domain:** add the three `ResourceKind`s, `PlanItem.key` and its detail, and `SetupPreview.repairs`.
2. **Adapter:**
   - Read media and cards in `read_preview`.
   - Offer the rows from `diff`, leaving the SetupState to `items`.
   - Add `setup_apply(plan_hash, repairs=)`: hash the required items plus the checked rows, run each checked repair after the plan, and count checked rows still offered as discrepancies.
   - Update the port and the fake together.
   - Un-skip AC-1 to AC-3, AC-6 and AC-8 to AC-11.
3. **Service and routes:**
   - Add `plan(repairs=)` and `apply(plan_hash, repairs)`.
   - Add `?repair=` on GET /api/setup/plan and `repairs` in the apply body.
   - Add `repairs` to the plan's wire shape.
   - Un-skip AC-4, AC-7 and AC-13, and update `test_setup_plan.py` for `"repairs": []`.
4. **Screen:** add the Optional repairs card, the re-plan on toggle, and `applySetup(planHash, repairs)` in `api.js`. Un-skip AC-5 and AC-12.
5. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoints:**
  - GET /api/setup/plan adds `?repair=` (repeatable) and `"repairs"` to the body.
  - POST /api/setup/apply takes `"repairs"`.
- **UI:** the "Optional repairs" card with one checkbox per row, its re-plan on toggle, and Apply's visibility.
- **Guard:** `deleteMediaFile`, `changeDeck` and `suspend` are already in `guard.py`; no new write kinds.
- **Wiring to check in review:** the service passes the checked keys through to `AnkiStore.setup_apply`. API tests use the fake store and don't prove the adapter hashes the same rows; AC-11 does.

## Validation (step 5)

- Prerequisites: the criteria come from entry 11; the framework is pytest and pytest-playwright; the dev environment runs.
- Every leaf test's docstring names exactly one declared AC, and each AC has exactly one leaf. AC-10's three parametrized cases are cases of that leaf.
- Each leaf's first assertion is the criterion-defining one. Setup calls (preview, plan reads) stay unasserted before it.
- One exception: AC-12 checks a box and clicks Apply setup before its assertion, because the transition needs both; in red phase the `check()` is what times out.
- AC-9, AC-10 and AC-11 run their transitions (preview then apply), and AC-8 applies with every row checked before its follow-up assertions.
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were removed.

## Completion

- **Risks and assumptions:**
  - The spike recorded no `cardsInfo`, `findCards`, `changeDeck`, `suspend` or `deleteMediaFile`. The simulator follows AnkiConnect's documented shapes (`queue` -1 for suspended). Device acceptance (entry 13) is where a real Anki confirms them.
  - Spike 2.2 saw `storeMediaFile` lowercase a name, and `getMediaFilesNames` match case-sensitively. A lowercased managed file doesn't match AD-7, so it is neither offered nor deletable here. Epic-reference-audio should store lowercase-safe names, or AD-7 should be amended.
  - The server re-plans on each toggle, which is one Anki read (one lock hold) per click. That's fine for one user; the screen should drop a stale answer when toggles overlap.
  - All screen copy for this card is default copy, not from the UX docs.
- **Next workflow:** `bmad-build` for story 2.11.

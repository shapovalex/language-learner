---
runScope: 'story'
runKey: 'story-2-6'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.6'
storyKey: '2-6'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 6)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-6.md'
generatedTestFiles:
  - 'tests/integration/test_anki_prefix_guard.py'
  - 'tests/unit/test_anki_query.py'
  - 'tests/unit/test_anki_store_port.py (one leaf added)'
  - 'tests/integration/test_anki_setup_preview.py'
  - 'tests/unit/test_setup_plan.py'
  - 'tests/api/test_setup_plan.py'
  - 'tests/e2e/test_setup_preview.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-1, AD-2, AD-3, AD-4, AD-5, AD-7, AD-19, Consistency Conventions)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Setup key strings, Setup components, State Patterns, J5)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md (Change row, Info callout)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Setup.dc.html'
  - '_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md (Q5, Q6, reply shapes, Surprises)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-4.md, atdd-checklist-2-1.md (format and conventions)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{client,store,manifest}.py, ports/anki_store.py, features/setup/{routes,service}.py, app.py, domain/errors.py, settings.py'
  - 'src/language_lab/static/screens/setup.js, static/api.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_connect,aio,network,ports}.py'
  - 'tests/api/test_setup_readiness.py, tests/e2e/test_setup_readiness.py, tests/integration/test_anki_adapter.py, tests/unit/test_anki_store_port.py'
  - 'tests/fixtures/anki/: modelNames, deckNames, getDeckConfig, createModel, modelTemplates, modelStyling, notesInfo'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'The AD-4 guard inside adapters/anki rejects, before any request is sent, any write, delete, move, preset or media action whose target is not a manifest resource, the <Prefix> preset or an AD-7 media name, including LanguageLabDev targets from a LanguageLab Prefix; unknown actions are rejected and multi is checked action by action' }
  - { id: 'AC-2', idSource: 'generated', text: 'A write that targets notes, cards or a preset by id is sent only after the guard looks it up and finds every note of a manifest note type (or the preset a managed deck uses); otherwise only the lookup is sent' }
  - { id: 'AC-3', idSource: 'generated', text: 'One query builder emits only exact deck:"<Prefix>::<path>" / deck:"<Prefix>" and note:"<type>" scopes for manifest names, with no user text' }
  - { id: 'AC-4', idSource: 'generated', text: 'The AnkiStore port gains a read of the managed state, setup_preview() -> SetupPreview, kept in step by the fake and the adapter' }
  - { id: 'AC-5', idSource: 'generated', text: 'The adapter reads note types, fields, templates, CSS, decks, preset assignment and bury flags with reads only: no write action is sent during preview, and every query is exact-scope' }
  - { id: 'AC-6', idSource: 'generated', text: 'diff(manifest, Anki) yields Create, Repair and Migrate plan items: an empty Prefix previews 28 decks, 5 note types, their templates and CSS, and the preset; a set-up Prefix previews nothing; a changed template previews one Repair' }
  - { id: 'AC-7', idSource: 'generated', text: 'The plan has a hash that is independent of order and changes with any item' }
  - { id: 'AC-8', idSource: 'generated', text: 'Unrecognized content under the Prefix is listed as read-only "Not managed by LanguageLab" entries, outside the plan and its hash' }
  - { id: 'AC-9', idSource: 'generated', text: 'GET /api/setup/plan returns the Prefix, the plan hash, the items and the unmanaged entries' }
  - { id: 'AC-10', idSource: 'generated', text: 'The Setup screen shows the change list headed "What will change in Anki" with "Nothing changes until you apply."' }
  - { id: 'AC-11', idSource: 'generated', text: 'An empty plan shows the "Nothing to change" callout instead of the change list' }
  - { id: 'AC-12', idSource: 'generated', text: 'The Setup screen lists unrecognized content as read-only "Not managed by LanguageLab" rows' }
  - { id: 'AC-13', idSource: 'generated', text: 'The Setup screen keeps the EXPERIENCE.md subtitle and shows the study-not-the-root footer' }
---

# ATDD Checklist: Story 2.6, Prefix guard and Setup preview without touching Anki

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 6 (`risk = "high"`, `refine = true`). There is no story file, so this checklist holds the refined criteria. AC-1 to AC-13 follow the ticket's description in source order, with the verify clauses folded in:
  - "rejected before any request is sent (including LanguageLabDev targets from a LanguageLab Prefix)" is in AC-1.
  - "every built query in exact-scope form" is in AC-3 and AC-5.
  - The three preview outcomes are in AC-6.
  - "the adapter issues no write action during preview" is in AC-5.
  - AC-2 splits the id-targeted half of the guard out of AC-1, so each gets one leaf.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in stories 2.1 and 1.x (dev-only, NFR-11).
- **Test design:** none for epic 2. Priorities follow the ticket's risk (high), NFR-1 (the Prefix boundary), FR-6 (preview before apply), FR-8 (user deck options are left alone) and AD-3 (the plan hash apply relies on).
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - New: `domain/setup.py`, `adapters/anki/guard.py`, `adapters/anki/query.py`, a diff module in `adapters/anki/` (any name).
  - Changed: `adapters/anki/client.py` (takes the guard), `adapters/anki/store.py` (`manifest=` and `setup_preview()`), `ports/anki_store.py`, `tests/fakes/anki_store.py`, `features/setup/{routes,service}.py`, `app.py` (builds the manifest and guard from `ANKI_PREFIX`), `static/api.js`, `static/screens/setup.js`, `static/css/studio.css`.
  - Tests: `tests/support/anki_state.py` (new) and `stub_api_json()` in `tests/support/network.py`.

### Decisions taken with the user (2026-10-21)

| Question | Decision |
| --- | --- |
| How far does the guard reach for writes that target notes or cards by id? | **Look up the ids now.** The guard reads `notesInfo`/`cardsInfo` before the write and rejects it unless every note is of a manifest note type. Only the lookup is sent. A preset saved by id must be the config a managed deck already uses. |
| Which unrecognized content is listed as "Not managed by LanguageLab"? | **Decks and note types.** Decks under `<Prefix>` and note types named `<Prefix> …` that the manifest doesn't declare. Non-managed notes stay with entry 11 (UX OQ-6 is open). |
| How does the change list show plan items? | **Grouped, as in the mockup.** One row per resource kind and action (Decks, Note types, Card templates and CSS, Deck options), with a chip like "Create 28" or "Repair 1" and the resource names as muted detail. |
| What is an existing note type whose fields differ? | **Migrate.** Field changes are schema changes (AD-3). Entry 9 makes them runnable and flags full sync. Template or CSS drift is Repair. |

### Defaults taken without a question

- **Domain types** (`domain/setup.py`):
  - `PlanAction` (StrEnum): `create`, `repair`, `migrate`.
  - `ResourceKind` (StrEnum): `deck`, `noteType`, `templates`, `preset`.
  - `PlanItem(action, kind, name)` and `Unmanaged(kind, name)`. `name` is the full Anki name: the deck path, the note type, or the preset (the Prefix).
  - `SetupPreview(items, unmanaged)`.
  - `plan_hash(items) -> str`: 64 lowercase hex characters (sha256 is expected, not pinned), computed over the items as a set.
- **Port:** `AnkiStore.setup_preview() -> SetupPreview`. The adapter reads Anki and diffs it against the manifest under one lock hold, so features never see Anki names except as display strings (AD-1, AD-5).
- **Plan items for an empty Prefix:** 28 deck Creates, 5 note-type Creates, 5 templates Creates (one per note type, its card templates and CSS together) and 1 preset Create, 39 in all.
- **Repair** covers:
  - a note type's card templates or CSS that differ from the files (a changed, missing or extra card template, or changed CSS);
  - the preset with any of the three bury flags on;
  - a Study or Pronunciation deck that doesn't use the preset.

  If no managed deck uses the preset, it is a preset Create. Other deck options never appear in the plan (FR-8).
- **"Under the Prefix"** means a deck equal to `<Prefix>` or starting with `<Prefix>::`, and a note type starting with `<Prefix> ` (with the space). So `LanguageLabDev…` and `LanguageLabArchive` are never under `LanguageLab`.
- **The guard is part of the client.** `AnkiConnectClient(url, *, transport=None, guard=None)` checks every v6 `invoke` through `PrefixGuard(manifest)`. Without a guard, it sends reads only, so a preview client can't write. A rejection raises `PrefixViolation`, a programming error: it reaches the request log as a 500 `internal_error` and carries no target name. v1 Sync is not a resource write and stays unguarded.
- **Name-targeted writes the guard checks:**
  - `createDeck`, `deleteDecks`, `setDeckConfigId` (`decks`): every deck is in the manifest.
  - `createModel`, `modelField*`: `modelName` is a manifest note type.
  - `updateModelTemplates`, `updateModelStyling`: `model.name` is a manifest note type.
  - `cloneDeckConfigId`: `name` is the Prefix.
  - `addNote`: a manifest note type into a manifest deck.
  - `storeMediaFile`, `deleteMediaFile`: the name matches AD-7, `<Prefix>_<uuid4>_<12 hex>.mp3`, case-sensitively.
  - `multi`: each inner action.
  - Anything else: rejected.
- **Id-targeted writes:**
  - `updateNoteFields` and `deleteNotes` look up with `notesInfo`.
  - `changeDeck` (whose deck must also be in the manifest) and `suspend` look up with `cardsInfo`.
  - `saveDeckConfig` must carry the Prefix as its name and the id of the config `getDeckConfig` returns for a managed preset deck.
- **API body:** `{"prefix", "planHash", "items": [{"action", "kind", "name"}], "unmanaged": [{"kind", "name"}]}`, items in the store's order.
- **Screen:**
  - The change list follows the readiness card.
  - Rows go in kind order (Decks, Note types, Card templates and CSS, Deck options), then action order within a kind (create, repair, migrate).
  - Unmanaged rows sit in their own list under the heading "Not managed by LanguageLab".
  - The footer is the mockup's two lines, with the Prefix from the plan.
  - There is no Apply button yet (entry 7).

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and the screen part is plain list rendering stubbed at the network. Execution is **sequential**, in this session, with no subagents.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | 19 out-of-Prefix writes, then 13 allowed ones, through a guarded client over the replay | each rejected call raises `PrefixViolation`, then no rejected call sent anything |
| AC-2 | Integration | P0 | 13 id-targeted writes, against notes and cards of a managed and a `Basic` note type | which writes were sent equals the expected allowed set |
| AC-3 | Unit | P0 | Build a query for every manifest deck and note type, then for refused names | `deck_query` for each manifest deck is exactly `deck:"<deck>"` |
| AC-4 | Unit | P1 | Compare port, fake and adapter signatures | the port's methods are `reachable`, `sync` and `setup_preview` |
| AC-5 | Integration | P0 | Preview a set-up Prefix with one changed template and an extra deck | no action outside `READ_ACTIONS` was sent (`multi` unpacked) |
| AC-6 | Integration | P0 | 15-row table of collections: empty, set-up, and one change each | the preview's items equal the expected set |
| AC-7 | Unit | P0 | Hash four items in two orders, then six variants | the reversed items hash the same |
| AC-8 | Integration | P1 | A set-up Prefix plus unknown decks and note types, `LanguageLabArchive`, a user preset and a full `LanguageLabDev` | the unmanaged set equals the three entries under the Prefix |
| AC-9 | API | P0 | `FakeAnkiStore(preview=...)` with four items and one unmanaged entry | status 200 |
| AC-10 | E2E | P0 | Stubbed empty-Prefix plan (39 items, kinds shuffled) | the change list has 4 rows |
| AC-11 | E2E | P1 | Stubbed empty plan | "Nothing to change." is visible |
| AC-12 | E2E | P1 | Stubbed plan with one Repair and two unmanaged entries | the "Not managed by LanguageLab" list has 2 rows |
| AC-13 | E2E | P2 | Stubbed empty-Prefix plan | the study-not-the-root footer is visible with the stub's Prefix |

- **One leaf per criterion.** AC-6 is one parametrized leaf (15 cases). AC-1 and AC-2 are table-driven inside one leaf each.
- **Red-phase imports.** Missing modules are imported in each leaf's body, so collection stays green. Hoist them when green.
- **No duplicate coverage.** The diff runs at Integration only, through the store, against the in-memory collection that answers with the recorded reply shapes. The route test (AC-9) uses the fake and checks shape only. The E2E tests stub the network and check rendering only.
- **Negative paths at high risk.**
  - AC-1: LanguageLabDev from LanguageLab, `<Prefix>X`, an unmanaged deck under the Prefix, a bad item inside `multi`, an unknown write action, and media names that aren't AD-7.
  - AC-2: unknown note ids, and a mixed managed and `Basic` batch.
  - AC-3: wildcards and quote injection.
  - AC-6: user-set deck options (must preview nothing), and a fully set-up `LanguageLabDev` beside an empty `LanguageLab`.

## TDD Red Phase (Current)

Scaffolds generated: **13 leaves, 27 cases, all skipped with a `RED_PHASE` reason.**

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/integration/test_anki_prefix_guard.py` | Integration | 2 (2): AC-1, AC-2 |
| `tests/unit/test_anki_query.py` | Unit | 1 (1): AC-3 |
| `tests/unit/test_anki_store_port.py` | Unit | 1 (1) added: AC-4 |
| `tests/integration/test_anki_setup_preview.py` | Integration | 3 (17): AC-5 (1), AC-6 (15), AC-8 (1) |
| `tests/unit/test_setup_plan.py` | Unit | 1 (1): AC-7 |
| `tests/api/test_setup_plan.py` | API | 1 (1): AC-9 |
| `tests/e2e/test_setup_preview.py` | E2E | 4 (4): AC-10 to AC-13 |

Observed with the skip markers stripped (a scratchpad plugin, not committed): **27 failed.**

| Count | Failure | Leaves |
| --- | --- | --- |
| 16 | `TypeError: AnkiConnectStore.__init__() got an unexpected keyword argument 'manifest'` | AC-5, AC-6 |
| 4 | `ModuleNotFoundError: language_lab.domain.setup` | AC-4, AC-7, AC-8, AC-9 |
| 2 | `ModuleNotFoundError: language_lab.adapters.anki.guard` | AC-1, AC-2 |
| 1 | `ModuleNotFoundError: language_lab.adapters.anki.query` | AC-3 |
| 4 | the first `expect` (row count 4, callout visible, 2 not-managed rows, footer visible) | AC-10 to AC-13 |

**Green feasibility, checked and removed.** Throwaway stand-ins turned all **27 of 27** cases green, and the rest of the suite stayed green: all 113 E2E tests and 350 non-E2E tests passed. The one exception was the expected failure listed below. The stand-ins were:

- `domain/setup.py`, `adapters/anki/query.py` and `adapters/anki/guard.py`
- the client taking `guard=`, `AnkiConnectStore(manifest=).setup_preview()`, the port method and the fake's `preview=`
- `GET /api/setup/plan`
- a grouped change list in `setup.js`

The one expected failure is the story 2.1 port test's exact-set assertion `{"reachable", "sync"}`. The AC-4 leaf supersedes it, so drop that assertion when AC-4 goes green.

Each mutation below was caught, except where the table says otherwise:

| Mutation | Caught by |
| --- | --- |
| Guard matches decks by `startswith(prefix)` | AC-1 |
| Guard lets an unknown action through | AC-1 |
| Guard skips the `notesInfo` lookup | AC-2 |
| Guard doesn't check the saved preset's name | AC-2 |
| The diff ignores CSS | AC-6 `changed-css` |
| Field drift reported as Repair | AC-6 `field-removed`, `field-added` |
| Preset assignment not checked | AC-6 `deck-on-default-preset` |
| A preview sends `createDeck` | AC-5, AC-6 (all 15), AC-8 |
| "Under the Prefix" without `::` for decks | AC-8 |
| "Under the Prefix" without the space for note types | AC-8 |
| Hash depends on order | AC-7 |
| Hash ignores the action | AC-7 |
| Query builder accepts anything starting with the Prefix | AC-3 |
| `planHash` includes unmanaged entries | AC-9 |
| Chip without the count | AC-10, AC-12 |
| Empty plan still shows the list | AC-11 |
| Footer hard-codes `LanguageLab` | AC-13 |
| A checkbox on a not-managed row | AC-12 |
| **Rows ordered by action before kind** | **Not caught.** The AC-10 plan has only Creates (see the backlog) |

The stand-ins were removed: the three new modules were deleted and `src/` and `tests/fakes/` were restored from git. With the scaffolds skipped, the suite stays green (**437 passed, 27 skipped**), and `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P0 | `test_guard_rejects_writes_outside_the_prefix_before_sending_anything` | each REJECTED call raises `PrefixViolation`; then none sent anything; each ALLOWED call succeeds and sends exactly its own action (no lookup); a dev-Prefix guard allows `LanguageLabDev::Study` and rejects the release deck |
| AC-2 | P0 | `test_guard_looks_up_id_targets_and_sends_the_write_only_for_managed_notes` | the map of write sent per case equals the expected allowed set; then allowed cases succeed with only lookups before the write; rejected ones raise `PrefixViolation` having sent only lookups |
| AC-3 | P0 | `test_query_builder_emits_only_exact_scopes_for_manifest_names` | each manifest deck's query is `deck:"<deck>"`; then each note type's is `note:"<type>"`; all match the exact-scope pattern; eight deck and six note-type inputs raise `ValueError`; a dev manifest refuses release names |
| AC-4 | P1 | `test_anki_store_port_adds_the_setup_preview_read_and_the_fake_matches` | port methods are `{reachable, sync, setup_preview}`; then `setup_preview` is async and returns `SetupPreview`; fake and adapter signatures match |
| AC-5 | P0 | `test_preview_sends_only_reads_and_exact_scope_queries` | no sent action outside `READ_ACTIONS`; then the preview is the one templates Repair; every sent `query` is built from exact manifest scopes |
| AC-6 | P0 | `test_preview_diffs_the_manifest_into_create_repair_and_migrate_items` [empty-prefix, empty-prefix-beside-dev, set-up, changed-template, changed-css, missing-card-template, missing-deck, missing-note-type, bury-flag-on, deck-on-default-preset, no-preset, field-removed, field-added, user-deck-options, dev-prefix-beside] | items as `(action, kind, name)` equal the expected set; then no duplicates |
| AC-7 | P0 | `test_plan_hash_is_stable_across_order_and_changes_with_any_item` | reversed items hash the same; then 64 hex characters; six variants (action, kind, name, dropped, added, empty) each differ from the original and from each other; enum values |
| AC-8 | P1 | `test_unrecognized_content_under_the_prefix_is_listed_read_only` | unmanaged equals the two decks and one note type under the Prefix; then no plan items; same hash as a clean set-up Prefix; reads only |
| AC-9 | P0 | `test_plan_route_returns_items_unmanaged_rows_and_the_plan_hash` | status 200; then the exact camelCase body with `planHash == plan_hash(items)` |
| AC-10 | P0 | `test_setup_lists_what_will_change_grouped_by_kind_and_action` | 4 rows in the list named "What will change in Anki"; then kind labels in order; chips "Create 28/5/5/1"; heading and "Nothing changes until you apply."; the Note types row names a note type; no checkbox or button |
| AC-11 | P1 | `test_setup_shows_nothing_to_change_when_the_plan_is_empty` | "Nothing to change." visible; then its detail line; no change heading or note; no alert; no Apply setup |
| AC-12 | P1 | `test_setup_lists_unrecognized_content_as_not_managed` | 2 rows in the list named "Not managed by LanguageLab"; then their names; no checkbox or button; the change list has the one "Card templates and CSS" row with "Repair 1" |
| AC-13 | P2 | `test_setup_footer_says_to_study_the_study_deck_not_the_root` | `In Anki, study “LanguageLabDev::Study”, not the root deck` visible; then the Pronounce line; the subtitle names the Prefix |

## Implementation contract the tests encode

- **`domain/setup.py`:** `PlanAction`, `ResourceKind`, `PlanItem(action, kind, name)`, `Unmanaged(kind, name)`, `SetupPreview(items: tuple, unmanaged: tuple)` (keyword-constructible) and `plan_hash(items) -> str`, as under the defaults above.
- **`adapters/anki/guard.py`:**
  - `PrefixGuard(manifest: Manifest)` and `PrefixViolation(Exception)`.
  - `AnkiConnectClient(url, *, transport=None, guard=None)` runs the guard inside `invoke` before posting, and makes any lookups through the unguarded post.
  - An allowed name-targeted write sends exactly one request (AC-1 pins no lookup for `setDeckConfigId`, `cloneDeckConfigId` or `addNote`).
- **`adapters/anki/query.py`:** `deck_query(manifest, deck) -> str` and `note_query(manifest, note_type) -> str`. Each raises `ValueError` for a name not in the manifest.
- **`AnkiConnectStore(client, lock, *, manifest=...)`:** `setup_preview()` runs under one lock hold and sends reads only. It may use any action in `tests/support/anki_state.READ_ACTIONS`: `deckNames`, `modelNames`, `modelFieldNames`, `modelTemplates`, `modelStyling`, `findModelsByName`, `getDeckConfig` (`false` for a missing deck), `multi` and others. Field order matters: a reorder is a Migrate. Template comparison is exact text, front and back by card name, plus CSS.
- **`FakeAnkiStore(preview: SetupPreview | None = None)`:** `setup_preview()` returns it (an empty preview by default) and raises `anki_busy` when `busy`.
- **`GET /api/setup/plan`:** see the API body above. `anki_busy` and `anki_unavailable` go through the existing AppError handler (503).
- **`app.py`:** builds `build_manifest(settings.anki_prefix)` once, gives the store `manifest=` and the client `guard=PrefixGuard(manifest)`.
- **Screen:**
  - `getPlan()` in `api.js`.
  - In `setup.js`: the "What will change in Anki" `h2` labels a `ul` of change rows (`aria-labelledby`), followed by the "Nothing changes until you apply." line.
  - Chip text is `<Action> <count>`, with the action word capitalized.
  - An empty plan shows the info callout's two lines, and no change heading.
  - The "Not managed by LanguageLab" heading labels its own `ul`.
  - The footer has two `p`s.
  - Styles: the `change-row`, `chip-accent` and `info-callout` components (DESIGN.md).

## Fixture and support changes (made in this run)

- `tests/support/anki_state.py` (new): an in-memory Anki collection answered as AnkiConnect, using the recorded reply shapes.
  - Collections: `stock_collection()` (the recorded stock note types, the Default deck and preset), `managed_collection(manifest)`, `apply_manifest()`.
  - Presets: `preset_config()` (the recorded `getDeckConfig` with dotted overrides) and `set_path()`.
  - Replay: `collection_replies()` for `AnkiConnectReplay`, and `READ_ACTIONS`.
  - Inspection: `sent_actions()` and `sent_queries()`, with `multi` unpacked.
- `tests/support/network.py`: `stub_api_json(page, path, body)`.
- `tests/README.md`: both helpers.

## Next Steps (Task-by-Task Activation)

1. Pick a task and remove its `@RED_PHASE` (or `@SETUP_RED_PHASE`) line.
2. Run it, e.g. `uv run pytest tests/unit/test_setup_plan.py`.
3. Watch it fail for the reason above, implement, and watch it pass. Then hoist its in-body imports.
4. If a test fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes:
   - No story 2.6 `RED_PHASE` markers remain.
   - The story 2.1 exact-set port assertion is gone.
   - `make test` and `make lint` pass.

Suggested order:

1. `domain/setup.py` (AC-7).
2. `query.py` (AC-3).
3. The guard in the client (AC-1, AC-2).
4. The port, fake and `setup_preview` with the diff (AC-4, AC-5, AC-6, AC-8).
5. The route and `app.py` wiring (AC-9).
6. The screen (AC-10 to AC-13).

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-10 | A mixed plan (Create and Repair of one kind, and a Migrate) renders the rows in kind-then-action order. The order mutation above survived | P1 |
| AC-9 | `anki_busy` and `anki_unavailable` from `setup_preview()` give the 503 envelope | P1 |
| AC-10 | A plan error (503 envelope) shows an inline alert in place of the change list, and readiness still renders | P2 |
| AC-5 | The preview holds the Anki lock once: a concurrent `reachable()` waits, and a 15 s wait is `anki_busy` | P2 |
| AC-1 | `app.py` wires the guard: the composed app's client rejects an out-of-Prefix write (a probe through `create_app`) | P1 |
| AC-1 | A `PrefixViolation` reaches the client as a 500 `internal_error`, and the log line carries no deck or note type name | P2 |
| AC-6 | A field reorder previews Migrate, and an extra card template previews Repair | P2 |
| AC-6 | Several changes at once (missing deck, changed CSS, bury flag on) preview all three, and nothing else | P2 |
| AC-10 | Phone width (390): the rows wrap, and the chips stay on the row | P3 |
| AC-8 | Non-managed notes in Prefix decks (entry 11 / OQ-6) | P3 |

## Open items

- **`setDeckConfigId` checks only the decks.** The guard can't map a config id to a name before the preset exists, so the `configId` is unchecked. The write stays inside managed decks. Entry 7 should set the id that `cloneDeckConfigId` returned.
- **Media names and case.** Spike 2.2 saw `storeMediaFile` lowercase a name. The AD-7 pattern carries the Prefix's case. The guard checks the requested name case-sensitively. Whether stored names should be lowercase is for the Items epic, and may amend AD-7.
- **Preset existence is inferred from deck assignment.** AnkiConnect has no action that lists presets. If a `<Prefix>` preset exists but no managed deck uses it, the preview says Create, and apply (entry 7) must reuse it, not clone a second one.
- **Template text is compared exactly.** If Anki normalizes saved templates or CSS (whitespace, line endings), a freshly applied Prefix would preview Repairs forever. Entry 13's Mac Mini run (apply, then a second preview) shows whether it does.
- **`saveDeckConfig` returns `false`** (spike Q5). This entry only reads the flags. Entry 7 must prove a working save.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (the ticket description and verify, AD-3/AD-4/AD-7, EXPERIENCE.md Setup strings, the mockup, the spike's reply shapes, and four decisions recorded with the user), pytest and pytest-playwright are configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-13), with no collisions
- [x] Every leaf's docstring carries exactly one `AC-n`, and each criterion has exactly one red-phase leaf (13 leaves)
- [x] Every scaffold is skipped with a reason naming what re-enables it, and none has placeholder assertions
- [x] The first assertion is the criterion-defining one. The stand-in run showed each leaf reaching it, and the mutation table shows each failing on its own branch
- [x] No unimplemented setup result is parsed before the criterion assertion. AC-1 and AC-2 collect outcomes through `settle` and assert after. AC-9's fake construction raises in red, and nothing is derived from it
- [x] The preview isn't a state transition; AC-6's table drives each change from a set-up or empty collection
- [x] Existing tests are unchanged in behavior and pass (437 passed, 27 skipped). `ruff check` and `ruff format --check` are clean
- [x] Story handoff: there's no story file, so this checklist is the handoff for `bmad-build` on entry 6
- [x] No browser sessions were opened outside pytest. The unskip plugin and stand-in backups are in the session scratchpad, and the stand-ins were removed from the tree

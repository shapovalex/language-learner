---
runScope: 'story'
runKey: 'story-5-1'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-23'
storyId: '5.1'
storyKey: '5-1'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-maintain-items/tickets.toml (entry 1)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-5-1.md'
generatedTestFiles:
  - 'tests/api/test_items_search.py'
  - 'tests/e2e/test_items_search.py'
  - 'tests/e2e/test_item_edit.py'
inputDocuments:
  - '_bmad/config.toml (resolved core and modules.tea)'
  - 'AGENTS.md'
  - '_bmad-output/initiative-languagelab-v1/epic-maintain-items/tickets.toml (entry 1)'
  - '_bmad-output/initiative-languagelab-v1/epic-maintain-items/epic-maintain-items.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-4, AD-6, AD-9, AD-11, AD-12, AD-13)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-22, FR-23, AC11, AC12)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Items, detail, search and state patterns)'
  - 'pyproject.toml; tests/conftest.py; tests/e2e/conftest.py; tests/README.md'
  - 'src/language_lab/features/items/{routes,service}.py; domain/items.py; ports/anki_store.py; adapters/anki/store.py'
  - 'src/language_lab/static/screens/{items,item-detail,make-item}.js; static/{api,router}.js'
  - 'tests/support/{items,duplicates,items_screen,network,unsaved,viewports,anki_state,captures,hosts}.py; tests/fakes/anki_store.py'
  - 'tests/api/{test_items_read,test_items_save}.py; tests/integration/{test_anki_item_reads,test_anki_item_save}.py; tests/e2e/test_item_detail.py'
  - '.agents/skills/bmod-tea/knowledge/data-factories.md'
  - '.agents/skills/bmod-tea/knowledge/component-tdd.md'
  - '.agents/skills/bmod-tea/knowledge/test-quality.md'
  - '.agents/skills/bmod-tea/knowledge/test-healing-patterns.md'
  - '.agents/skills/bmod-tea/knowledge/test-levels-framework.md'
  - '.agents/skills/bmod-tea/knowledge/test-priorities-matrix.md'
  - '.agents/skills/bmod-tea/knowledge/ci-burn-in.md'
acceptanceCriteria:
  - {"id": "AC-1", "idSource": "generated", "text": "Search matches normalized Target substrings using AD-12 NFC, casefold, surrounding Unicode punctuation, collapsed whitespace and apostrophe mapping; diacritics stay significant."}
  - {"id": "AC-2", "idSource": "generated", "text": "Search matches normalized Russian meaning substrings."}
  - {"id": "AC-3", "idSource": "generated", "text": "Search matches normalized RussianAlternatives substrings."}
  - {"id": "AC-4", "idSource": "generated", "text": "Search spans both Categories of only the requested Language; an empty query lists all its Items."}
  - {"id": "AC-5", "idSource": "generated", "text": "Search reads only exact Prefix-scoped note types, sends no user text in Anki queries, writes nothing and propagates Anki failures."}
  - {"id": "AC-6", "idSource": "generated", "text": "Item list rows expose read-only hasAudio metadata derived from the stored Audio field, without altering ItemContent or audio."}
  - {"id": "AC-7", "idSource": "generated", "text": "Phone and desktop Items show full-row links with Target, Russian meaning, Category and an audio indicator only for rows with Reference audio; a result opens detail."}
  - {"id": "AC-8", "idSource": "generated", "text": "Language-scoped live search is debounced and a late earlier response cannot replace the newest query results."}
  - {"id": "AC-9", "idSource": "generated", "text": "The Items list shows a loading skeleton while its read is pending and then shows the results."}
  - {"id": "AC-10", "idSource": "generated", "text": "An empty collection hides search and shows No English Items yet / Items are made from Captures.; searching a populated list with no matches shows No English Items match followed by the query."}
  - {"id": "AC-11", "idSource": "generated", "text": "A failed list read shows an inline alert with Try again; retry reads again and replaces the error with results."}
  - {"id": "AC-12", "idSource": "generated", "text": "Item detail edits Category fields and Save changes posts the existing ItemId and audio=keep through existing Save; only explicit Save commits, then dirty state clears. The adapter updates the existing note preserving Card identities, scheduling, review histories and audio."}
  - {"id": "AC-13", "idSource": "generated", "text": "Opening an Item again re-reads current Anki values including direct edits, rather than using the list or a prior editor buffer."}
  - {"id": "AC-14", "idSource": "generated", "text": "Changing Target rechecks duplicates before Save with the existing ItemId excluded; Cancel preserves edits and a changed Target is rechecked; Create anyway updates the edited Item under its original identity."}
  - {"id": "AC-15", "idSource": "generated", "text": "Duplicate Open existing uses the router unsaved-changes alert; Keep editing preserves the buffer and Discard opens the matched Item without saving the edited Item."}
  - {"id": "AC-16", "idSource": "generated", "text": "Failed Save preserves local edits and dirty state with prior Anki values and audio unchanged; retry saves the same ItemId, and leaving unsaved edits uses the router Keep editing / Discard guard."}
---

# ATDD Checklist: Story 5.1 — Search, open, and edit existing Items

## Preflight and story context

Approved ticket entry 1 (high risk, after 4.1 and 4.3). There is no leaf story file; the published ticket description and verify clause, epic boundaries, and linked requirements supply the criteria above. All ids are generated in source order: search, list states, open/edit, duplicate recheck and failure/dirty-state handling. PRD AC11/AC12 retain their original spelling and are references rather than supplied AC-<n> ids.

Stack detection: backend (Python manifest, pytest configuration, no Node manifest), with a static browser UI exercised by the existing Python Playwright suite. E2E applies to that real UI even though manifest detection says backend; no JavaScript runner or new framework is installed. Environment: existing .venv and local browser dependencies. No epic-5 or system test design was found in test-design/ or the legacy test-artifacts/ root. Priorities derive from the approved high-risk ticket and AD-4/AD-6/AD-12/AD-13.

Playwright-utils and Pact flags are true, but their package/runner/relevance gates are closed: this is Python pytest-playwright with no Node packages or Pact artifacts. No TypeScript imports, Pact broker probing or new dependencies apply. Existing data factories, codec/collection replay and network helpers are reused.

Affected components: Items service/routes and list reads, read-only audio-presence metadata, API client, Items and Item detail screens, existing duplicate sheet and router dirty-state integration. Save already updates by ItemId. Regeneration, delete, audio controls and stale-audio warnings belong to later stories.

Proposed minimum wire contract: GET /api/items/<lang>?q=<query> returns 200 {items: [{itemId, ...ItemContent, hasAudio: boolean}]}; absent/empty q lists all. hasAudio is list metadata, derived from stored Audio without retrieving media or extending editable ItemContent. Existing detail, duplicate and multipart Save contracts stay authoritative. Search errors use the existing AD-15 envelope. Stable ordering follows Category enumeration and candidate order; no new sort requirement.

Existing adapter save/read and duplicate-exclusion tests provide regression coverage for implemented prerequisites. Real Anki review histories cannot be proven by an in-memory replay: the independent released-wheel acceptance in story 5.3 remains required. Failed update replay will also be checked as a regression guard during this run.

## Generation mode

AI generation from approved requirements and source, with no recording needed for the unimplemented screens. Browser behavior uses Python Playwright and documented accessible names.

## Test strategy

Exactly one skipped primary scaffold per declared AC; secondary cases are deferred to green-phase automation. Primary level: E2E for user transitions, API for matching and scoped reads.

| AC | Priority | Level | Criterion-defining outcome |
| --- | --- | --- | --- |
| AC-1 | P0 | API | Search matches normalized Target substrings using AD-12 NFC, casefold, surrounding Unicode punctuation, collapsed whitespace and apostrophe mapping; diacritics stay significant. |
| AC-2 | P0 | API | Search matches normalized Russian meaning substrings. |
| AC-3 | P0 | API | Search matches normalized RussianAlternatives substrings. |
| AC-4 | P0 | API | Search spans both Categories of only the requested Language; an empty query lists all its Items. |
| AC-5 | P0 | API | Search reads only exact Prefix-scoped note types, sends no user text in Anki queries, writes nothing and propagates Anki failures. |
| AC-6 | P1 | API | Item list rows expose read-only hasAudio metadata derived from the stored Audio field, without altering ItemContent or audio. |
| AC-7 | P0 | E2E | Phone and desktop Items show full-row links with Target, Russian meaning, Category and an audio indicator only for rows with Reference audio; a result opens detail. |
| AC-8 | P1 | E2E | Language-scoped live search is debounced and a late earlier response cannot replace the newest query results. |
| AC-9 | P1 | E2E | The Items list shows a loading skeleton while its read is pending and then shows the results. |
| AC-10 | P1 | E2E | An empty collection hides search and shows No English Items yet / Items are made from Captures.; searching a populated list with no matches shows No English Items match followed by the query. |
| AC-11 | P1 | E2E | A failed list read shows an inline alert with Try again; retry reads again and replaces the error with results. |
| AC-12 | P0 | E2E | Item detail edits Category fields and Save changes posts the existing ItemId and audio=keep through existing Save; only explicit Save commits, then dirty state clears. The adapter updates the existing note preserving Card identities, scheduling, review histories and audio. |
| AC-13 | P0 | E2E | Opening an Item again re-reads current Anki values including direct edits, rather than using the list or a prior editor buffer. |
| AC-14 | P0 | E2E | Changing Target rechecks duplicates before Save with the existing ItemId excluded; Cancel preserves edits and a changed Target is rechecked; Create anyway updates the edited Item under its original identity. |
| AC-15 | P0 | E2E | Duplicate Open existing uses the router unsaved-changes alert; Keep editing preserves the buffer and Discard opens the matched Item without saving the edited Item. |
| AC-16 | P0 | E2E | Failed Save preserves local edits and dirty state with prior Anki values and audio unchanged; retry saves the same ItemId, and leaving unsaved edits uses the router Keep editing / Discard guard. |

## Generation and aggregation

Capability probe: subagent orchestration is available; no dedicated agent-team runtime was used. Requested mode auto resolved to subagent with parallel API and E2E workers, as required by step 4. Both workers returned success and the exact persisted registry. Elapsed generation was not benchmarked; no numerical speedup is claimed.

All 16 leaves are intentionally skipped via module-level pytest.mark.skip (the Python equivalent of test.skip). Each docstring begins with exactly one [P#] AC-n title. No production files or dependencies changed. Python runner adaptation: native action/wait failures remain visible; a missing search/editor prerequisite can stop a transition before its final criterion assertion. Such failures demonstrate a missing dependency, not independent proof of later duplicate or retry behavior. The handoff explicitly requires rechecking those transitions after the editor/list exists.

| Criterion | Primary scaffold | Priority |
| --- | --- | --- |
| AC-1 | `tests/api/test_items_search.py::test_search_normalizes_target_substrings` | [P0] |
| AC-2 | `tests/api/test_items_search.py::test_search_matches_the_russian_meaning` | [P0] |
| AC-3 | `tests/api/test_items_search.py::test_search_matches_a_russian_alternative` | [P0] |
| AC-4 | `tests/api/test_items_search.py::test_search_includes_both_categories_only_in_the_requested_language` | [P0] |
| AC-5 | `tests/api/test_items_search.py::test_search_uses_read_only_exact_prefix_scopes` | [P0] |
| AC-6 | `tests/api/test_items_search.py::test_item_list_reports_stored_audio_presence_without_writing` | [P1] |
| AC-7 | `tests/e2e/test_items_search.py::test_item_rows_open_detail_on_phone_and_desktop` | [P0] |
| AC-8 | `tests/e2e/test_items_search.py::test_live_search_debounces_and_ignores_a_late_old_response` | [P1] |
| AC-9 | `tests/e2e/test_items_search.py::test_pending_list_shows_loading_then_results` | [P1] |
| AC-10 | `tests/e2e/test_items_search.py::test_search_no_matches_is_distinct_from_an_empty_collection` | [P1] |
| AC-11 | `tests/e2e/test_items_search.py::test_failed_list_retry_replaces_the_error_with_items` | [P1] |
| AC-12 | `tests/e2e/test_item_edit.py::test_save_changes_commits_existing_identity_and_clears_dirty_state` | [P0] |
| AC-13 | `tests/e2e/test_item_edit.py::test_reopening_reads_the_current_item_instead_of_the_prior_buffer` | [P0] |
| AC-14 | `tests/e2e/test_item_edit.py::test_changed_target_rechecks_and_create_anyway_keeps_the_edited_item_id` | [P0] |
| AC-15 | `tests/e2e/test_item_edit.py::test_open_existing_guards_the_unsaved_edit_before_opening_the_match` | [P0] |
| AC-16 | `tests/e2e/test_item_edit.py::test_failed_save_keeps_edits_and_leave_guard_then_retries_the_same_item` | [P0] |

## Factories, fixtures and mock requirements

Reused factories: vocabulary(), sentence(), store_with_items(), stored_fields(), managed_collection(), item_note(), wired(). New browser support is tests/support/maintain_items_screen.py (per-test stored_item factory, accessible locators, list/detail stubs and EditableItemApi). Unique UUIDs and fresh fake/replay collections isolate tests. Browser page routes and data disappear at fixture teardown; no real Anki, external LLM, or media service is called.

Mock contracts: (1) list GET with q, returning items and hasAudio; (2) detail GET with the existing flat Item; (3) duplicate GET with matches and current itemId exclusion; (4) multipart Save POST with itemId and audio=keep; (5) existing AD-15 error envelopes. HeldRoute and the Playwright virtual clock control loading/debounce and delayed response ordering. EditableItemApi checks client request behavior only; its successful write is a mock and cannot prove real Anki persistence.

Accessible names: Search English Items / Search French Items, Save changes, Reference audio (list icon), existing Category field labels, whole-row links with Targets, alert + Try again, and the existing duplicate/unsaved dialog names. No new data-testid is required. The Reference audio accessible name is a scaffold default; retain equivalent accessible semantics if implementation changes the exact name.

## Implementation checklist and green-phase follow-up

- [ ] AC-1..AC-4: add service matching through normalize_text for each Target, Russian and each RussianAlternative, across both Category scopes of the requested Language; wire list GET before dynamic Item routes. Implement absent and empty q; retain diacritics. Add blank-whitespace/punctuation-only and apostrophe-variant cases, French search, unknown Language validation and query-log privacy checks during green.
- [ ] AC-5: retain PrefixGuard and exact note_query scopes; filter in the service. Add busy/unavailable and gated read cases, a note deleted between findNotes and notesInfo, and verify user query text never enters Anki queries or request logs.
- [ ] AC-6: carry stored Audio presence through the read-only result path and return hasAudio only as list metadata. Add reverse Category audio cases; empty Audio must be false. Keep audio controls, media downloads and stale-audio warnings in epic 6.
- [ ] AC-7..AC-11: implement responsive Items rows, debounced live search with stale-response protection, skeleton, collection-empty/search-empty states and error retry through the shared API client. Add French labels, keyboard row activation, clearing a query, and rapid Language navigation. The debounce test uses an upper budget of 1000 ms without requiring an exact production delay.
- [ ] AC-12: replace view-only detail with editable Category fields, shared content validation and explicit Save changes through the existing multipart Save. Keep ItemId and audio=keep; disable duplicate submits and clear router dirty state only after success. Add Sentence edits (including Note), optional clearing, alternatives, invalid inputs, unchanged-Target saves, and unchanged-field preservation. Retire only the obsolete no-textbox assertion in tests/e2e/test_item_detail.py; preserve its read/error/back-link coverage.
- [ ] AC-13: every mount reads detail again; no prior list/editor buffer supplies authoritative values. Add real adapter-backed open/reopen after a direct Anki field edit and decode markup/alternatives.
- [ ] AC-14..AC-15: reuse duplicate check excluding current ItemId on Target changes; Cancel keeps the local buffer, Create anyway updates the original Item, and Open existing uses router.confirmLeave(). Add same-Target self-exclusion, multiple matches, changed Target after a failed check, and server-error recovery.
- [ ] AC-16: retain buffer and dirty state after failed Save, retry with the same ItemId, and use router-managed Keep editing/Discard on back/nav/browser navigation. Add unchanged Target, return-to-original dirty clearing and failure on duplicate read. Add a persistent automated adapter update-failure regression for both Categories; the validation probe in this run is supplementary evidence.
- [ ] Keep existing tests/integration/test_anki_item_save.py update-in-place checks and tests/api/test_items_read.py self-exclusion/read contracts green. In 5.3, verify note/Card identity plus actual review histories and scheduling with reviewed Cards on the released wheel; the collection fixture has no history/scheduling model.

Effort: high risk per approved ticket; a delivery estimate belongs in the subsequent build plan. The nine tasks above are the implementation/verification handoff, not completed feature work.

## Activation and manual handoff

No writable leaf story exists: pass story 5.1 (epic-maintain-items/tickets.toml entry 1), this checklist and generatedTestFiles to bmad-build. The ticket store remains the approved source; this checklist holds the ATDD registry. No other story checklist was changed.

For each build task, remove only its skip marker (or move the module skip to the remaining functions), confirm RED, implement, verify GREEN, then refactor with regression tests. Do not unskip every scenario before its prerequisites exist. In particular rerun AC-8 and AC-10..AC-16 after the relevant list/editor controls are implemented so their complete transitions execute.

Commands from the repository root (the existing .venv is already populated):

```sh
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest tests/api/test_items_search.py tests/e2e/test_items_search.py tests/e2e/test_item_edit.py -q
.venv/bin/pytest tests/api/test_items_read.py tests/api/test_items_save.py tests/integration/test_anki_item_reads.py tests/integration/test_anki_item_save.py tests/e2e/test_item_detail.py tests/e2e/test_duplicate_warning.py -q
```

Use uv run in the normal project environment if desired. Red-activation tooling and logs are temporary diagnostics; the committed evidence file records their outcomes. No browser recording sessions were opened.

## Validation and completion (2026-10-23)

- Criterion registry/AST validation: exactly 16 primary leaves, one per AC; 11 P0 and 5 P1. Both worker outputs carry the exact ordered registry. Three test modules plus one browser support module; no new dependencies.
- Normal run: **16 skipped**, no errors. These skip markers remain committed.
- Temporary runtime activation: **6 API failures**, no errors. Five cases return 404 on the absent list route; AC-5 sees no scoped Anki queries. Subsequent matching/audio assertions remain to be exercised during green.
- Temporary Chromium activation: **10 browser failures**, no errors. AC-7/AC-9 fail at missing rows/loading; AC-8, AC-10..AC-16 stop at missing search, alert or editable fields. Deeper transitions are not claimed as independently verified. Phone/desktop, debounce and duplicate/failure branches must execute fully during implementation.
- Existing Item read, Save, adapter and duplicate/detail regressions: **89 passed**.
- Additional Save probe: **4 passed** (Vocabulary/Sentence × successful/rejected update), checking note/Card identity, preserved Audio/media and unchanged collection on rejection. The collection cannot measure scheduling or review history.
- Repository-wide Ruff lint/format: **passed** (294 Python files). Diff whitespace check passed. No browser recording sessions or test servers remain.

Durable evidence: `_bmad-output/test-artifacts/atdd/atdd-validation-5-1.json` carries the criterion/test map, counts, failure signatures and limitations. Raw temporary worker JSON and JUnit logs are diagnostic inputs rather than duplicate source artifacts. Validation used a temporary pytest collection plugin, so no source skip markers needed removal/restoration.

ATDD scaffolding is complete; feature implementation remains pending. Next workflow: `bmad-build` for epic 5 story 1, using this checklist and the published ticket entry. Real Anki history/scheduling checks remain assigned to 5.3.

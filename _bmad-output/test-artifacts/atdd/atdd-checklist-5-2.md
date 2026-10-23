---
runScope: 'story'
runKey: 'story-5-2'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-23'
storyId: '5.2'
storyKey: '5-2'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-maintain-items/tickets.toml (entry 2)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-5-2.md'
generatedTestFiles:
  - 'tests/api/test_drafts_regenerate.py'
  - 'tests/e2e/test_item_regenerate.py'
inputDocuments:
  - '_bmad/config.toml (resolved core and modules.tea)'
  - 'AGENTS.md'
  - '_bmad-output/initiative-languagelab-v1/epic-maintain-items/tickets.toml (entry 2)'
  - '_bmad-output/initiative-languagelab-v1/epic-maintain-items/epic-maintain-items.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-11, AD-13, AD-15)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-24, NFR-3, NFR-4)'
  - '_bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md (CAP-8 assumptions: Sentence Note regenerate)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Item detail key strings, compare pair, J4, responsive compare pair)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md (compare pair)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-ItemDetail.dc.html'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-5-1.md (prior story patterns)'
  - 'pyproject.toml; tests/conftest.py; tests/e2e/conftest.py'
  - 'src/language_lab/features/drafts/{routes,service}.py; features/items/routes.py; ports/llm.py; domain/items.py'
  - 'src/language_lab/static/screens/{item-detail,make-item,captures}.js; static/{api,dom}.js'
  - 'tests/support/{drafts,duplicates,items,items_screen,maintain_items_screen,network,captures_screen}.py; tests/fakes/{llm,anki_store}.py'
  - 'tests/api/test_drafts_generate.py; tests/e2e/{test_generate_draft,test_item_edit}.py'
  - '.agents/skills/bmod-tea/knowledge/data-factories.md'
  - '.agents/skills/bmod-tea/knowledge/component-tdd.md'
  - '.agents/skills/bmod-tea/knowledge/test-quality.md'
  - '.agents/skills/bmod-tea/knowledge/test-healing-patterns.md'
  - '.agents/skills/bmod-tea/knowledge/test-levels-framework.md'
  - '.agents/skills/bmod-tea/knowledge/test-priorities-matrix.md'
  - '.agents/skills/bmod-tea/knowledge/ci-burn-in.md'
acceptanceCriteria:
  - {"id": "AC-1", "idSource": "generated", "text": "Regeneration returns the full validated Category generation model from 4.2 (AD-11) for the given Language, Category and Target, without allocating or returning an ItemId and without touching Anki."}
  - {"id": "AC-2", "idSource": "generated", "text": "Regeneration keeps the existing generation retry and error behavior: the model's llm_failed and llm_invalid_output (after its one retry) are 502 in the AD-15 envelope."}
  - {"id": "AC-3", "idSource": "generated", "text": "Regenerate Russian meaning shows Current vs Preview (Preview · not saved) of the Russian meaning and alternatives, sends the edit buffer's Target without an ItemId, and changes neither the buffer nor Anki."}
  - {"id": "AC-4", "idSource": "generated", "text": "Use preview on a Vocabulary example moves only the example and its Russian translation into the edit buffer; unrelated unsaved edits, other fields and the ItemId are retained and nothing is written to Anki."}
  - {"id": "AC-5", "idSource": "generated", "text": "A Sentence Item regenerates its Note with the same Current vs Preview, and Use preview changes only the Note in the edit buffer."}
  - {"id": "AC-6", "idSource": "generated", "text": "Keep current discards the Preview, leaving the edit buffer (including unrelated unsaved edits) unchanged and making no Anki write."}
  - {"id": "AC-7", "idSource": "generated", "text": "A failed regeneration shows its alert with Try again and preserves the current edit buffer; Try again asks again and then shows the Preview."}
  - {"id": "AC-8", "idSource": "generated", "text": "Only Save changes commits accepted Preview fields, together with unrelated edits, to the existing note under the same ItemId with audio=keep."}
---

# ATDD Checklist: Story 5.2 — Regenerate content with Current vs Preview

## Preflight and story context

Approved ticket entry 2 (medium risk, after 5.1 and 4.2). There is no leaf story file; the published ticket description and verify clause, the epic's Done-when 3, FR-24/NFR-4, AD-11 and the UX compare pair supply the criteria above. All ids are generated in source order: server contract, client compare/choose flows, failure, then Save. Story 5.1 is merged to main (PR #49), so Item detail is already editable.

Stack detection: backend (Python manifest, pytest configuration, no Node manifest), with a static browser UI exercised by the existing Python Playwright suite. E2E applies to that real UI; no JavaScript runner or new framework is installed. No epic-5 or system test design exists in test-design/ or the legacy test-artifacts/ root; priorities derive from the approved medium-risk ticket, NFR-4 (Preview-and-Save) and AD-11.

Playwright-utils and Pact flags are true, but their package/runner/relevance gates are closed: this is Python pytest-playwright with no Node packages or Pact artifacts. Knowledge loaded: core plus backend fragments (listed in inputDocuments).

Affected components: drafts routes/service (a regeneration entry point that shares `Llm.generate` and `GeneratedFields.to_content`), API client, Item detail screen (regenerate buttons, compare pair, generation alert) and the dirty-state count. Items Save, reads and duplicate checks are unchanged. Audio Preview, Voice and the stale-audio warning belong to epic 6.

Proposed minimum wire contract (scaffold default; the build may rename it if the tests move with it): `POST /api/drafts/regenerate` with JSON `{language, category, target}` (optional `generationContext`, default empty) answers **200** with the flat ItemContent of the Category's full generated model: the Target as given, nulls as empty, empty mnemonic for Vocabulary, and **no `itemId`**. Invalid input is 422 `validation_failed`; the model's `llm_failed` / `llm_invalid_output` are 502 in the AD-15 envelope, exactly like `/api/drafts/generate`. It lives in `features/drafts` because AD-11 says regeneration "calls the drafts generation for the Item's Category". The client sends the edit buffer's current Target and takes only the requested field group:

| Group | Button | Compare pair | Fields taken |
| --- | --- | --- | --- |
| Russian meaning | Regenerate Russian meaning | Russian meaning · compare | russian, russianAlternatives |
| Example (Vocabulary) | Regenerate example | Example · compare | example, exampleRussian |
| Note (Sentence) | Regenerate Note | Note · compare | note |

"Regenerate Russian meaning", "Example · compare", "Current", "Preview · not saved", "Keep current" and "Use preview" are EXPERIENCE.md/mockup copy. "Regenerate example", "Regenerate Note", "Russian meaning · compare" and "Note · compare" follow the same pattern and are scaffold defaults (OQ-14 left the Note unmocked).

## Generation mode

AI generation from approved requirements and source; no recording is needed for unimplemented controls. Browser behavior uses Python Playwright and accessible names.

## Test strategy

Exactly one skipped primary scaffold per declared AC; secondary cases are deferred to green-phase automation. API for the server contract, E2E for buffer transitions.

| AC | Priority | Level | Criterion-defining outcome |
| --- | --- | --- | --- |
| AC-1 | P0 | API | 200 from the regeneration route, then full generated ItemContent without itemId, one model call, Anki unreachable and unneeded |
| AC-2 | P1 | API | 502 with `llm_invalid_output` in the AD-15 envelope, no itemId |
| AC-3 | P0 | E2E | Russian meaning compare pair shows the Preview value beside Current; buffer and Anki unchanged; request carries buffer Target, no itemId |
| AC-4 | P0 | E2E | After Use preview the Example field holds the Preview; only example/exampleRussian changed; unrelated unsaved Mnemonic edit kept; no Save |
| AC-5 | P1 | E2E | After Use preview the Sentence Note holds the Preview; Russian meaning and Hint unchanged |
| AC-6 | P0 | E2E | After Keep current the Example keeps its current value and the pair is gone; unrelated unsaved edit kept; no Save |
| AC-7 | P1 | E2E | A failed regeneration shows an alert with Try again; buffer kept; Try again asks again and shows the Preview |
| AC-8 | P0 | E2E | The single Save payload carries the accepted Preview Russian meaning under the original ItemId with audio=keep, plus the unrelated edit |

Red phase: AC-1/AC-2 fail first on the absent route (404/405 instead of 200/502). E2E leaves first fail on the missing Regenerate button (Python runner adaptation, as in 5.1: an action failure precedes the criterion assertion; the transitions must be rechecked once the controls exist).

## Generation and aggregation

Execution mode: config `auto` would resolve to subagents, but this session spawns subagents only on the user's explicit request, so generation ran **sequentially** inline (API, then E2E). This changes orchestration only; the red-phase contract is the same.

All 8 leaves are skipped through a module-level `pytest.mark.skip`, the Python equivalent of `test.skip`. Each docstring starts with exactly one `[P#] AC-n`. No production files or dependencies changed.

| Criterion | Primary scaffold | Priority |
| --- | --- | --- |
| AC-1 | `tests/api/test_drafts_regenerate.py::test_regenerate_returns_the_full_generated_model_without_an_item_id` | [P0] |
| AC-2 | `tests/api/test_drafts_regenerate.py::test_a_failed_regeneration_is_502_with_the_generation_error_code` | [P1] |
| AC-3 | `tests/e2e/test_item_regenerate.py::test_regenerate_russian_meaning_shows_current_beside_the_preview` | [P0] |
| AC-4 | `tests/e2e/test_item_regenerate.py::test_use_preview_moves_only_the_example_into_the_edit_buffer` | [P0] |
| AC-5 | `tests/e2e/test_item_regenerate.py::test_a_sentence_regenerates_its_note_with_the_same_compare_pair` | [P1] |
| AC-6 | `tests/e2e/test_item_regenerate.py::test_keep_current_discards_the_preview_and_leaves_the_buffer` | [P0] |
| AC-7 | `tests/e2e/test_item_regenerate.py::test_a_failed_regeneration_keeps_the_buffer_and_try_again_shows_the_preview` | [P1] |
| AC-8 | `tests/e2e/test_item_regenerate.py::test_save_changes_alone_commits_the_accepted_preview_under_the_same_item_id` | [P0] |

## Factories, fixtures and mock requirements

The scaffolds reuse `fake_llm`, `drafts_client`, `drafted`, `GENERATED` and `VOCABULARY_TARGET` (tests/support/drafts.py), `FakeAnkiStore(available=False)`, and `stored_item`, `EditableItemApi`, `edit_field` and `save_changes` from 5.1. The new browser support is `tests/support/regenerate_screen.py`. It holds `REGENERATE_API`, the Preview replies (which differ in every field, so a group taking the wrong field shows up), `stored_sentence`, the locators and the `RegenerateApi` double, which records JSON bodies and switches between 200 and a 502 envelope. Each test registers its own page routes, and no real Anki or LLM is called.

Accessible names: Regenerate Russian meaning / Regenerate example / Regenerate Note (buttons). Each compare pair is a `group` named "<group> · compare" containing "Current", "Preview · not saved", Keep current and Use preview. The failure is a `role=alert` with Try again. The unsaved chip reads "N unsaved change(s)". No data-testid is needed.

## Implementation checklist and green-phase follow-up

- [ ] AC-1: add `DraftService.regenerate(language, category, target, generation_context="")`, which returns `fields.to_content(target)` and issues no ItemId, plus the `POST /api/drafts/regenerate` route that reuses `GenerateRequest` and answers 200. Green-phase additions: a French Sentence case, 422 for blank/unknown inputs before the model is asked, and the Target/Generation context kept out of logs (AD-15).
- [ ] AC-2: propagate `AppError` unchanged. Add an `llm_failed` case. The adapter's one retry is already covered by tests/integration/test_openrouter_llm.py; regeneration must call the same `Llm.generate`.
- [ ] AC-3: add `regenerateContent(body)` to api.js. On Item detail, add Regenerate Russian meaning, a loading state on the button or pair, and the compare pair with Current over Preview on phone (side by side when it is at least 2×300px wide; EXPERIENCE.md responsive table). Send the buffer's Target, not the loaded one. Add the phone layout and a check that the buffer's edited Target is the one sent.
- [ ] AC-4: Use preview copies only the group's fields into `values` and re-renders the inputs, so the unsaved count includes them. Add Use preview on the Russian meaning, where the alternatives arrive one per line. A Preview identical to Current should leave the Item clean.
- [ ] AC-5: add Regenerate Note for Sentence only, with no example button. Add the Vocabulary/Sentence button matrix.
- [ ] AC-6: Keep current drops the Preview. Decide (UX "Unsaved … Preview") whether an open, unaccepted Preview alone counts as unsaved for the router leave guard, then test leaving with an open Preview.
- [ ] AC-7: a failed regeneration shows the same copy as Draft generation (`generationFailure` in captures.js; consider moving it into make-item.js for sharing), adapted so the body says the Item is unchanged. Add llm_invalid_output copy, a network failure, and a regeneration in flight when the user leaves (a late reply opens nothing).
- [ ] AC-8: Save stays the existing Save, and an unaccepted Preview is never sent. Add a test where Save runs while a Preview is still open, and an example accepted then Saved. NFR-3 (a failed Save keeps the accepted Preview in the buffer) is already shown by 5.1 AC-16. Real-Anki note/Card identity on Save is covered by 5.1's adapter tests and 5.3's released-wheel acceptance.
- [ ] Keep tests/api/test_drafts_generate.py, tests/e2e/test_generate_draft.py and tests/e2e/test_item_edit.py green: regeneration must not change Draft generation or the 5.1 editor.

## Activation and manual handoff

There is no writable leaf story. Pass story 5.2 (epic-maintain-items/tickets.toml entry 2), this checklist and generatedTestFiles to `bmad-build`. For each task, remove the module skip, or move it onto the remaining functions. Confirm RED, implement, confirm GREEN, then refactor.

```sh
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest tests/api/test_drafts_regenerate.py tests/e2e/test_item_regenerate.py -q
.venv/bin/pytest tests/api/test_drafts_generate.py tests/api/test_items_save.py tests/api/test_items_read.py tests/e2e/test_item_edit.py tests/e2e/test_generate_draft.py tests/e2e/test_item_detail.py -q
```

## Validation and completion (2026-10-23)

- Registry: 8 ACs, all generated ids. Exactly 8 primary leaves, one per AC (5 P0, 3 P1), across two test modules and one support module. No new dependencies.
- Normal run: **8 skipped**, no errors.
- Temporary activation (a pytest collection plugin in the session scratchpad strips skip markers; no source was edited): **8 failed**, 0 errors. AC-1 and AC-2 return `405 != 200/502` because the route is absent. All six E2E leaves load the editor (setup passes), then time out at the missing Regenerate button. That is an action failure before the criterion assertion, the same Python runner adaptation as 5.1, so the compare/choose/failure transitions must be re-observed once the controls exist.
- Neighbouring regressions (drafts generate, Items save/read, Item edit/detail, Generate Draft): **79 passed**.
- Ruff lint and format: passed (299 files). `git diff --check` is clean. No browser recording sessions or servers remain.

Next workflow: `bmad-build` for epic 5 story 2.

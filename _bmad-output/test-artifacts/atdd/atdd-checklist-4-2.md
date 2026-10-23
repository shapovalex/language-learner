---
runScope: 'story'
runKey: 'story-4-2'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-22'
storyId: '4.2'
storyKey: '4-2'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/tickets.toml (entry 2)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-4-2.md'
generatedTestFiles:
  - 'tests/unit/test_draft_generation_domain.py'
  - 'tests/unit/test_llm_port.py'
  - 'tests/unit/test_docs_model_evaluation.py'
  - 'tests/integration/test_openrouter_llm.py'
  - 'tests/api/test_drafts_generate.py'
  - 'tests/e2e/test_generate_draft.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/tickets.toml (entry 2)'
  - '_bmad-output/initiative-languagelab-v1/epic-capture-to-item/epic-capture-to-item.md (Done when 2 and 5; Notes 2026-10-08, 2026-10-22)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-1, AD-8, AD-11, AD-13, AD-15, AD-18, Deferred: adapter timeouts)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-4, FR-14 to FR-18, NFR-8, §5.2); addendum.md (A2, A3 fields, A4 OpenRouter)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Key strings: Capture detail, Draft; Text-source choice; Buttons; Loading — generation; Model unreachable; Generation failed)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-4-1.md (format, conventions, decisions)'
  - 'No test design for epic 4: test-design/test-design-epic-4.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/{app,settings,env.example}.py, domain/{items,catalog,errors}.py, features/drafts/{routes,service}.py, features/items/routes.py, ports/{anki_store,sync_requester}.py'
  - 'src/language_lab/static/{api,router}.js, static/screens/{captures,make-item}.js'
  - 'tests/README.md, tests/fakes/{anki_store,sync_requester}.py, tests/support/{items,items_screen,captures,captures_screen,network,aio,hosts,anki_connect,live_server}.py, tests/support/fixtures/{logs,live_server}.py'
  - 'tests/api/test_drafts_blank.py, tests/e2e/test_make_an_item.py, tests/integration/test_anki_item_save.py, tests/unit/{test_anki_store_port,test_docs_consistency}.py'
  - 'docs/configuration.md'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'Per Category, the generated-fields model is ItemContent less target, category and mnemonic, and for Sentence less example: strict_json_schema(category) has exactly the properties russian, russianAlternatives, hint, partOfSpeech, grammar, example, exampleRussian (Vocabulary) or russian, russianAlternatives, hint, note (Sentence) (AD-11; Target is input)' }
  - { id: 'AC-2', idSource: 'generated', text: 'strict_json_schema() sets additionalProperties false, makes every property required, renders optional fields as nullable, and emits no defaults (AD-11)' }
  - { id: 'AC-3', idSource: 'generated', text: 'The generated model refuses a reply with an extra key (mnemonic, target, a Sentence example), a missing key, a null required field, a blank Russian meaning, or a comma alternative' }
  - { id: 'AC-4', idSource: 'generated', text: 'A valid generated reply becomes the Draft''s ItemContent through to_content(target): the given Target and the Category, null optional fields empty, and an empty mnemonic' }
  - { id: 'AC-5', idSource: 'generated', text: 'The OpenRouter adapter POSTs chat completions with OPENROUTER_MODELS in configured order as models, a strict json_schema response_format holding the Category''s strict_json_schema, provider {require_parameters: true} and no other routing or privacy keys (A4, NFR-8, FR-17), the Target, Language, Category and Generation context in the messages, and the key as a Bearer token' }
  - { id: 'AC-6', idSource: 'generated', text: 'A valid reply returns the generated model after one request' }
  - { id: 'AC-7', idSource: 'generated', text: 'An invalid reply is retried once, and a second invalid reply is llm_invalid_output after exactly two requests (FR-16)' }
  - { id: 'AC-8', idSource: 'generated', text: 'A failed request (refused, timed out, an HTTP error status, a non-JSON body) is llm_failed after one request, with no retry' }
  - { id: 'AC-9', idSource: 'generated', text: 'The Llm port, its fake and the OpenRouter adapter declare the same async generate(language, category, target, generation_context) (AD-1)' }
  - { id: 'AC-10', idSource: 'generated', text: 'POST /api/drafts/generate with {language, category, target, generationContext} is 201 with a fresh lowercase UUIDv4 itemId and the generated ItemContent, flat, with the given Target, touching no Anki (AD-8, AD-11)' }
  - { id: 'AC-11', idSource: 'generated', text: 'A blank or missing Target, an unknown Language or Category, a non-string Generation context or a non-JSON body is 422 validation_failed, and the model is not called' }
  - { id: 'AC-12', idSource: 'generated', text: 'llm_failed and llm_invalid_output from the model are 502 with their code in the AD-15 envelope' }
  - { id: 'AC-13', idSource: 'generated', text: 'The Generation context reaches the model but never the response, the Save that follows, Anki, or the logs (FR-16, AD-15)' }
  - { id: 'AC-14', idSource: 'generated', text: 'The Make an Item pane has the Generation context field ("Generation context · optional · used once, never saved") and the Primary "Generate Draft" beside "Write it myself", disabled with the same reasons until a Language, a Category and, for Custom value, its text are given' }
  - { id: 'AC-15', idSource: 'generated', text: 'Generate Draft sends the chosen text, Language, Category and Generation context, shows "Writing your Draft…", and fills the Draft editor at /captures/<captureId>/new with the generated fields, Target as chosen and Mnemonic empty' }
  - { id: 'AC-16', idSource: 'generated', text: 'A Vocabulary Draft''s example has Clear, which empties Example and Example in Russian, and Save then sends both empty under the generated ItemId and returns to the Capture with the success banner' }
  - { id: 'AC-17', idSource: 'generated', text: 'A failed generation shows the EXPERIENCE.md inline alert for its code ("Couldn''t reach the model" or "Couldn''t generate a Draft", with "Your Capture is unchanged.") and Try again, which asks again and fills the editor' }
  - { id: 'AC-18', idSource: 'generated', text: 'docs/configuration.md has an "Evaluating a model" section: evaluate a model against its fixture set (English and French, Vocabulary and Sentence, Russian meanings) before adding it to or reordering OPENROUTER_MODELS (FR-4)' }
---

# ATDD Checklist: Story 4.2, OpenRouter Draft generation

## Run context

- **Story source:** epic-capture-to-item `tickets.toml`, entry 2 (`risk = "high"`, after entry 1, merged in PR #41). There is no story file, so this checklist holds the criteria. AC-1 to AC-18 follow the ticket's description in source order, with the verify clauses folded in:
  - "the schema assertion" is AC-2.
  - "a valid Draft returned" is AC-6 (adapter) and AC-10 (API).
  - "an invalid reply retried once then llm_invalid_output" is AC-7.
  - "a reordered OPENROUTER_MODELS changing the model called" is AC-5.
  - "Generation context absent from Anki writes and logs" is AC-13.
  - "Generate filling the editor, the example removed before Save, and the error state" are AC-15, AC-16 and AC-17.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in epics 1 to 4 (dev-only, NFR-11).
- **Test design:** none for epic 4. Priorities follow the ticket's risk (high), epic Done when 2 and 5, and AD-11. AC-9 (port shape) is P1 like the AnkiStore port tests, and AC-18 (docs) is P2 like the other docs tests. Every other criterion is P0.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - New: `ports/llm.py` (`Llm`), `adapters/openrouter/` (`OpenRouterLlm`), `tests/fakes/llm.py` (`FakeLlm`).
  - Changed: `domain/items.py` (the generated-fields models, `generated_model()`, `strict_json_schema()`, `to_content()`), `features/drafts/{routes,service}.py` (the generated Draft), `app.py` (`create_app(..., llm=)`, the 502 mapping), `tests/support/live_server.py` (inject `FakeLlm()`), `static/api.js` (`generateDraft`), `static/screens/{captures,make-item}.js` (the context field, Generate Draft, loading, errors, Clear), `docs/configuration.md`.
  - Tests (done in this run):
    - `tests/support/drafts.py`: generated replies on the wire, `generated()`, `fake_llm()`, `drafts_client()`.
    - `tests/support/openrouter.py`: `completion()`, `OpenRouterReplay` (an httpx transport answering in order and recording what was sent), the failure kinds.
    - `tests/support/items_screen.py`: the Generate Draft copy and locators.
    - The tests README lists them.

### Decision taken with the user (2026-10-22)

| Question | Decision |
| --- | --- |
| Can the model change the Target text? | **No.** Target is input. The generated models leave out `target` (and `category`), and the Draft's Target is exactly the chosen text. The user edits it in the editor if needed. |

### Defaults taken without a question

- **Domain (`domain/items.py`):**
  - `generated_model(category)` returns the generated-fields model: Vocabulary `russian`, `russianAlternatives`, `hint`, `partOfSpeech`, `grammar`, `example`, `exampleRussian`; Sentence `russian`, `russianAlternatives`, `hint`, `note`. `extra="forbid"`, camelCase aliases.
  - Never null: `russian`, `russianAlternatives` (may be empty), and for Vocabulary `example` and `exampleRussian` (FR-14: one example by default). Every other field is `str | None` with no default, so it is required and nullable.
  - The `russian` and alternative rules are `ItemContent`'s (non-blank, no comma).
  - `strict_json_schema(category) -> dict` is the schema sent to OpenRouter. It has no `default` anywhere.
  - `to_content(target) -> ItemContent` on a generated model: nulls become `""`, and `mnemonic` is `""`.
- **Port:** `Llm.generate(language: Language, category: Category, target: str, generation_context: str) -> <generated model>`. Raises `AppError(LLM_FAILED | LLM_INVALID_OUTPUT)`.
- **Adapter:** `OpenRouterLlm(api_key: str, models: Sequence[str], *, transport: httpx.AsyncBaseTransport | None = None)`, exported from `language_lab.adapters.openrouter`.
  - POST `https://openrouter.ai/api/v1/chat/completions`, `Authorization: Bearer <key>`.
  - Body: `models` (the configured list, in order), `messages` (a system prompt, and a user message naming the Language, the Category, the Target and the Generation context), `response_format: {type: "json_schema", json_schema: {name, strict: true, schema}}`, `provider: {require_parameters: true}`. Nothing else in `provider`, and no `data_collection`, `zdr`, `order`, `only` or `ignore` (NFR-8).
  - The reply's `choices[0].message.content` is validated with the generated model. Invalid means: content not JSON, failing the model, `null` content (a refusal), or no choices. One retry, then `llm_invalid_output`.
  - A transport error, a timeout, a non-2xx status or a non-JSON body is `llm_failed` at once, with no retry (architecture Deferred: only generation's invalid output retries).
  - It logs nothing with the prompt, the Target, the context or the reply (AD-15).
- **Fake:** `FakeLlm(reply: dict | None = None, *, error: ErrorCode | None = None)`. `generate()` records `(language, category, target, generation_context)` in `requests`, then raises `AppError(error)` or returns `reply` (generated fields on the wire) validated with `generated_model(category)`. With no `reply` it returns a fixed valid reply for the Category.
- **Wiring:** `create_app(settings, *, anki_store=None, llm=None, clock=None)` builds `OpenRouterLlm(settings.openrouter_api_key, settings.openrouter_models)` unless `llm` is given. `run_live_server` injects `FakeLlm()`, so no E2E test can reach OpenRouter with the placeholder key.
- **Route:** POST /api/drafts/generate, JSON `{language: "en"|"fr", category, target, generationContext}` (`generationContext` may be empty or left out).
  - **201** `{itemId, ...ItemContent}`, flat like the Save's `item` part. The ItemId is issued like the blank Draft's.
  - Invalid input is 422 `validation_failed`.
  - `llm_failed` and `llm_invalid_output` are **502**: both are upstream failures, and neither is the server's fault.
- **Screen, Make an Item pane:**
  - A textbox labelled "Generation context · optional · used once, never saved", under the pickers.
  - The Primary button "Generate Draft", with "Write it myself" kept beside it as the link-styled button. Both are disabled for the same reasons ("Choose a Language and Category." / "Enter the custom value.").
- **Screen, Draft editor:**
  - Generate Draft opens /captures/<captureId>/new at once, with a skeleton and "Writing your Draft…" (`role="status"`), then fills the editor from the reply. Target is the chosen text. Mnemonic is empty and editable (FR-18).
  - The Generation context lives in the screen's memory only (AD-13). It is not shown in the editor and not sent at Save.
  - A Vocabulary Draft's Example has a "Clear" button that empties Example and Example in Russian.
  - A failed generation shows a `role="alert"` in place of the form:
    - `llm_failed`: "Couldn't reach the model" / "Your Capture is unchanged."
    - `llm_invalid_output`: "Couldn't generate a Draft" / "The model's answer failed the checks twice. Your Capture is unchanged."
    - Any other code: "Couldn't generate a Draft" with the envelope's message.

    "Try again" sends the same request again. No Draft exists until a reply arrives, so the screen isn't dirty while loading or after a failure.
- **Docs:** `## Evaluating a model` in `docs/configuration.md`, after the keys table. It holds a fixture table (Language, Category, Target, Generation context, what a good Draft has) with English and French rows of both Categories, and says to run it before adding a model to, or reordering, `OPENROUTER_MODELS`.

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and the generated Draft is stubbed at the network for the screen tests. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 4.1).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Unit | P0 | Each Category's schema | its `properties` keys equal the generated fields |
| AC-2 | Unit | P0 | Each Category's schema, walked | every object's `additionalProperties` is false |
| AC-3 | Unit | P0 | 9 cases: extra `mnemonic`, `target` or Sentence `example`; a missing key; a null `russian` or `example`; a blank `russian`; a comma alternative | `ValidationError` raised |
| AC-4 | Unit | P0 | A Vocabulary and a Sentence reply with null optionals | `to_content(target)` dumped by alias equals the expected ItemContent |
| AC-5 | Integration | P0 | Two model orders from `OPENROUTER_MODELS` | the sent `models` equal the configured order |
| AC-6 | Integration | P0 | A valid Vocabulary and Sentence reply | the result dumped equals the reply |
| AC-7 | Integration | P0 | 5 invalid kinds, twice | the outcome's code is `llm_invalid_output` |
| AC-8 | Integration | P0 | Refused, timed out, 401, 429, 500, not JSON | the outcome's code is `llm_failed` |
| AC-9 | Unit | P1 | Port, fake and adapter | the fake's and adapter's `generate` signature equals the port's |
| AC-10 | API | P0 | en Vocabulary and fr Sentence over an unavailable Anki fake | status 201 |
| AC-11 | API | P0 | 7 cases: blank, missing Target; unknown Language, Category; context not a string; not JSON; JSON array | status 422 |
| AC-12 | API | P0 | The fake raising each code | status 502 |
| AC-13 | API | P0 | Generate with a context, then Save the reply | the model got the context |
| AC-14 | E2E | P0 | Capture detail at phone and desktop widths | Generate Draft is disabled |
| AC-15 | E2E | P0 | English Vocabulary with a context, the reply held | "Writing your Draft…" is visible |
| AC-16 | E2E | P0 | Generate, Clear the example, Save | Example is empty after Clear |
| AC-17 | E2E | P0 | Each code, then Try again | the alert has the code's title |
| AC-18 | Unit | P2 | docs/configuration.md | the "Evaluating a model" heading exists |

### Secondary branches for green-phase automation

- AC-3: a reply whose `russianAlternatives` holds a blank entry (ItemContent refuses it, so the generated model does too).
- AC-5:
  - `messages` has a system prompt that asks for one contextual primary meaning and no dictionary dump (FR-14). Not asserted: prompt wording is the user's quality gate at Save.
  - A timeout is set on the client (adapter-local, architecture Deferred).
- AC-7 (p1, written): an invalid reply followed by a valid one returns the valid one.
- AC-10 (p1, written): a left-out Generation context reaches the model as `""`.
- AC-10: `create_app(settings)` with no injected `llm` builds `OpenRouterLlm` from `settings.openrouter_models`, which proves the wiring.
- AC-11 (p1, written): a text body instead of JSON is 422.
- AC-13 (p1, written):
  - The adapter logs no Target, context, key or reply, answered, invalid or failed.
  - On screen, the context is in neither the URL, `history.state`, storage, nor the Save's `item` part.
- AC-15 (p1, written):
  - A Sentence Draft has no Example and no Clear, and its null Note is empty.
  - Generating and editing a Draft sends no Save (FR-18).
- AC-15: the success banner clears when the next Draft is generated (EXPERIENCE.md Success banner).
- AC-15: leaving the screen while "Writing your Draft…" shows no unsaved alert, and a late reply doesn't open the editor.
- AC-17:
  - Another code (e.g. `validation_failed`) shows "Couldn't generate a Draft" with the envelope's message.
  - Generate Draft and Try again are disabled while a request is in flight.
- Widths: the loading and error states at `viewports.ALL`, with no horizontal overflow.

## TDD red phase (current)

Red-phase scaffolds are generated, each file skipped by a module-level `pytestmark = pytest.mark.skip(reason=...)`:

- Unit:
  - 4 tests (15 cases) in `tests/unit/test_draft_generation_domain.py`.
  - 1 test in `tests/unit/test_llm_port.py`.
  - 1 test in `tests/unit/test_docs_model_evaluation.py`.
- Integration: 6 tests (19 cases) in `tests/integration/test_openrouter_llm.py`.
- API: 6 tests (13 cases) in `tests/api/test_drafts_generate.py`.
- E2E: 7 tests (9 cases) in `tests/e2e/test_generate_draft.py`.

The generation models, the port, the adapter and `FakeLlm` don't exist yet. They are imported inside the tests and in `tests/support/drafts.py`, so collection passes while they are skipped.

**Red check (2026-10-22):** each file was run as a copy with its skip marker removed. All 58 cases failed for the expected reasons:

- `ModuleNotFoundError: language_lab.adapters.openrouter` (20).
- `ModuleNotFoundError: tests.fakes.llm` (13).
- `ImportError: generated_model` / `strict_json_schema` from `language_lab.domain.items` (15).
- The pane's Generation context field and Generate Draft not found (9).
- The docs section absent (1).

Afterwards `make test-fast` passed (630 passed, 49 skipped), and so did `tests/e2e/test_make_an_item.py` (12 passed).

### Other changes in this run

- `choose()` moved from `tests/e2e/test_make_an_item.py` into `tests/support/items_screen.py`, so both E2E files share it.
- `pyproject.toml` declares `known-first-party = ["language_lab", "tests"]` for ruff's isort. Before, an import of a module that doesn't exist yet sorted as third-party, and story 4.1 needed a fix-up commit once `domain/items.py` existed.

## Acceptance criteria coverage

| AC | Test |
| --- | --- |
| AC-1 | `unit/test_draft_generation_domain.py::test_each_category_generates_its_item_fields_less_target_and_mnemonic` |
| AC-2 | `unit/test_draft_generation_domain.py::test_strict_json_schema_follows_the_strict_rules` |
| AC-3 | `unit/test_draft_generation_domain.py::test_the_generated_model_refuses_a_reply_outside_the_schema` |
| AC-4 | `unit/test_draft_generation_domain.py::test_a_valid_reply_becomes_the_drafts_item_content` |
| AC-5 | `integration/test_openrouter_llm.py::test_generate_asks_openrouter_with_the_configured_models_and_a_strict_schema` |
| AC-6 | `integration/test_openrouter_llm.py::test_a_valid_reply_is_the_generated_draft` |
| AC-7 | `integration/test_openrouter_llm.py::test_an_invalid_reply_is_retried_once_then_llm_invalid_output` |
| AC-8 | `integration/test_openrouter_llm.py::test_a_failed_request_is_llm_failed_with_no_retry` |
| AC-9 | `unit/test_llm_port.py::test_the_llm_port_the_fake_and_the_openrouter_adapter_declare_generate` |
| AC-10 | `api/test_drafts_generate.py::test_generate_returns_a_draft_with_a_fresh_item_id_and_the_given_target` |
| AC-11 | `api/test_drafts_generate.py::test_an_invalid_request_is_validation_failed_and_the_model_is_not_asked` |
| AC-12 | `api/test_drafts_generate.py::test_a_failed_generation_is_502_with_its_code` |
| AC-13 | `api/test_drafts_generate.py::test_the_generation_context_reaches_the_model_and_nothing_else` |
| AC-14 | `e2e/test_generate_draft.py::test_generate_draft_waits_for_a_language_a_category_and_a_custom_value` |
| AC-15 | `e2e/test_generate_draft.py::test_generate_draft_shows_the_loading_state_then_fills_the_draft_editor` |
| AC-16 | `e2e/test_generate_draft.py::test_clear_removes_the_example_before_save` |
| AC-17 | `e2e/test_generate_draft.py::test_a_failed_generation_shows_its_alert_and_try_again_asks_again` |
| AC-18 | `unit/test_docs_model_evaluation.py::test_configuration_docs_say_how_to_evaluate_a_model_against_fixtures` |

The P1 tests named in the secondary branches each name one of these ACs in their docstring. The test in the table is that AC's primary scaffold.

## Next steps (task-by-task activation)

1. **Domain:**
   - Add the generated-fields models, `generated_model()`, `strict_json_schema()` and `to_content()` to `domain/items.py`.
   - Un-skip `tests/unit/test_draft_generation_domain.py` (AC-1 to AC-4).
2. **Port, adapter and fake:**
   - Add `ports/llm.py`, `adapters/openrouter/` (`OpenRouterLlm`) and `tests/fakes/llm.py` (`FakeLlm`).
   - Un-skip `tests/unit/test_llm_port.py` (AC-9) and the integration file (AC-5 to AC-8).
3. **Feature and wiring:**
   - Add `DraftService.generate()` and POST /api/drafts/generate.
   - Add `create_app(..., llm=)`, and map `llm_failed` and `llm_invalid_output` to 502 in `_APP_ERROR_STATUS`.
   - **Inject `FakeLlm()` in `run_live_server`** before any E2E run, so the placeholder key never reaches OpenRouter.
   - Un-skip the API file (AC-10 to AC-13).
4. **Screen:**
   - Add `generateDraft` to `api.js`.
   - Add the context field, Generate Draft, loading, error alert, Try again and Clear to `make-item.js` / `captures.js`.
   - Un-skip the E2E file (AC-14 to AC-17).
5. **Docs:** add "Evaluating a model" to `docs/configuration.md`, and un-skip the docs test (AC-18).
6. For each step: un-skip, run `uv run pytest <file>`, see it fail, implement, see it pass. Then run `make test` and `uv run ruff check`.

## Implementation guidance

- **Endpoint:** POST /api/drafts/generate, JSON `{language, category, target, generationContext?}`:
  - 201 `{itemId, ...ItemContent}`.
  - 422 `validation_failed`.
  - 502 `llm_failed` or `llm_invalid_output`.
- **Adapter:** POST https://openrouter.ai/api/v1/chat/completions with these keys:
  - `models`
  - `messages`
  - `response_format` (strict `json_schema`)
  - `provider: {require_parameters: true}`

  It retries once on invalid output only.
- **UI:**
  - The pane: "Generation context · optional · used once, never saved", the Primary "Generate Draft", and "Write it myself" kept.
  - The editor:
    - "Writing your Draft…" in a `role="status"` skeleton.
    - The filled fields, with Clear on a Vocabulary Example.
    - The error alert per code, with Try again.
- **Wiring to check in review:**
  - `create_app` builds `OpenRouterLlm` from settings only when no `llm` is injected.
  - The live server injects `FakeLlm()`.
  - The Generation context isn't in the request log, the response or the Save.

## Validation (step 5)

- Prerequisites: the criteria come from entry 2; the framework is pytest and pytest-playwright; the dev environment runs.
- Every test's docstring names exactly one declared AC. Each AC has exactly one primary leaf, and parametrized cases are cases of that leaf.
- Each primary leaf's first assertion is the criterion-defining one. Setup stays unasserted before it, and the unimplemented generate response in AC-13 is not parsed until after the first assertion.
- AC-7, AC-15, AC-16 and AC-17 run their transitions:
  - AC-7: an invalid reply, then a retry.
  - AC-15: a held request, then its reply.
  - AC-16: Clear, then Save.
  - AC-17: a failure, then Try again.
- Story metadata and handoff paths are in the frontmatter. No browser CLI sessions were opened. The red-check copies were removed.

## Completion

- **Risks and assumptions:**
  - The OpenRouter reply shape is hand-built from its docs. Story 4.4's acceptance run should record a real reply and compare.
  - OpenRouter's strict mode may reject some JSON Schema forms Pydantic emits (`anyOf` with null, `$defs`, `title`). The AC-2 test allows both `type: [..., "null"]` and `anyOf`, so the implementer can post-process the schema. Model evaluation (AC-18) is where a real model proves it.
  - 502 for both `llm_*` codes is a default.
  - The Draft keeps no Generation context after the reply, so a later per-field regenerate (epic-maintain-items) can't reuse it. That matches "used once".
  - Generate Draft opens the editor route at once with the loading state, per EXPERIENCE.md "Loading — generation" on the Draft screen.
- **Next workflow:** `bmad-build` for story 4.2.

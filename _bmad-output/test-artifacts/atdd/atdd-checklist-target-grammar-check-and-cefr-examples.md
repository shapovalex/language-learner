---
runScope: 'story'
runKey: 'story-target-grammar-check-and-cefr-examples'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-27'
storyId: 'target-grammar-check-and-cefr-examples'
storyKey: 'target-grammar-check-and-cefr-examples'
storyFile: '_bmad-output/initiative-languagelab-v1/plan-target-grammar-check-and-cefr-examples.md'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-target-grammar-check-and-cefr-examples.md'
generatedTestFiles:
  - tests/unit/test_helpers_domain.py
  - tests/integration/test_openrouter_helpers.py
  - tests/api/test_helpers_grammar.py
  - tests/api/test_helpers_examples.py
  - tests/e2e/test_grammar_check.py
  - tests/e2e/test_example_sentences.py
  - tests/support/helpers.py
  - tests/support/grammar_screen.py
  - tests/support/examples_screen.py
  - tests/fakes/llm.py
inputDocuments:
  - _bmad-output/initiative-languagelab-v1/plan-target-grammar-check-and-cefr-examples.md
  - .claude/skills/bmod-tea/knowledge/data-factories.md
  - .claude/skills/bmod-tea/knowledge/component-tdd.md
  - .claude/skills/bmod-tea/knowledge/test-quality.md
  - .claude/skills/bmod-tea/knowledge/test-healing-patterns.md
  - .claude/skills/bmod-tea/knowledge/test-levels-framework.md
  - .claude/skills/bmod-tea/knowledge/test-priorities-matrix.md
  - .claude/skills/bmod-tea/knowledge/ci-burn-in.md
  - pyproject.toml
  - tests/conftest.py
acceptanceCriteria:
  - id: AC-1
    idSource: generated
    text: 'Given a Draft or an Item in edit with a non-blank Target, when the user presses Check grammar, then the verdict shows under Target; when wrong, the corrected text and a Russian explanation, and Use correction replaces the Target (and the Draft title). Nothing changes otherwise.'
  - id: AC-2
    idSource: generated
    text: 'Given a blank Target or compose box, Check grammar or Example sentences is disabled.'
  - id: AC-3
    idSource: generated
    text: 'Given compose text "jump to conclusions", when the user opens Example sentences, picks English and generates, then six groups A1–C2 show with 5 sentences each and their Russian.'
  - id: AC-4
    idSource: generated
    text: 'Given a shown sentence, when the user presses its Make an Item, then the Make an Item pane opens at /captures/make with that sentence as the text and English chosen; no Capture is created.'
  - id: AC-5
    idSource: generated
    text: 'Given either helper fails, an alert with Try again shows and the Target or compose text is unchanged.'
---

# ATDD Checklist: Target grammar check and CEFR example sentences

## TDD Red Phase (Current)

The red-phase scaffolds are generated and every module is skipped with `pytestmark = pytest.mark.skip(reason="Target helpers RED scaffold: activate when implementing the plan")`. Execution mode: subagent (API + E2E in parallel).

- Backend: 27 tests, 55 cases after parametrize, across unit, integration and API. With the skip removed, every case fails for the expected reason:
  - unit: `ModuleNotFoundError: language_lab.domain.helpers`
  - integration: `AttributeError: OpenRouterLlm.check_grammar/examples`
  - API: HTTP 405 (route missing)
- E2E: 5 tests, one per AC. With the skip removed, all 5 fail on a locator timeout for "Check grammar" or "Example sentences". No test failed on a fixture or syntax error.

## Acceptance Criteria Coverage

| Criterion | Priority | Primary leaf |
|-----------|----------|--------------|
| AC-1 | P0 | tests/e2e/test_grammar_check.py::test_check_grammar_shows_the_correction_and_use_correction_replaces_the_target |
| AC-2 | P1 | tests/e2e/test_grammar_check.py::test_check_grammar_and_example_sentences_are_disabled_while_blank |
| AC-3 | P0 | tests/e2e/test_example_sentences.py::test_generate_shows_six_cefr_groups_of_five_sentences_with_russian |
| AC-4 | P0 | tests/e2e/test_example_sentences.py::test_a_sentences_make_an_item_opens_the_pane_with_it_and_no_capture |
| AC-5 | P1 | tests/e2e/test_example_sentences.py::test_a_failed_generation_shows_try_again_and_keeps_the_compose_text |

I/O matrix rows (backend contract):
- **M-1 and M-2** (grammar 200 shapes): tests/api/test_helpers_grammar.py.
- **M-3** (examples 6×5): tests/api/test_helpers_examples.py.
- **M-4** (malformed set → retry → `llm_invalid_output`): tests/unit/test_helpers_domain.py and tests/integration/test_openrouter_helpers.py.
- **M-5** (422, model not asked) and **M-6** (502 `llm_failed` / `llm_invalid_output`): both API files.
- **Same LLM and models:** the integration tests assert the same URL, key, `models` and `provider.require_parameters`, and a strict closed schema.

Deviation from the TS title guard: backend leaves carry M-ids (matrix rows), not AC-ids, in their `[P0]/[P1]` docstrings. The AC registry's one-leaf-per-criterion rule holds across the E2E leaves.

Green-phase follow-ups, not scaffolded:
- Grammar check in Item edit
- The correct-verdict UI
- The grammar-helper failure branch of AC-5
- The `/captures/examples` fresh-mount redirect
- The examples context never kept

## Next Steps (Task-by-Task Activation)

1. When you start a task, remove the module's `pytestmark` skip.
2. Run it (`uv run pytest <file> -q`) and confirm it fails first.
3. Implement until it passes.
4. Fix the implementation for a feature bug, or the test only for a genuine test bug. Never weaken a matrix expectation.
5. Finish with `make lint` and `make test`.

## Implementation Guidance

Endpoints:
- `POST /api/helpers/grammar` takes `{language, category, target}` and returns 200 `{correct, corrected, explanation}`.
- `POST /api/helpers/examples` takes `{language, target, context?}` and returns 200 `{levels:[{level, sentences:[{sentence, russian}×5]}×6]}`.

Port and fake:
- `Llm.check_grammar(language, category, target)` and `Llm.examples(language, target, context)`.
- `tests/fakes/llm.py` already implements both. `generate` is unchanged.
- **Update `tests/unit/test_llm_port.py`**, which asserts the port is only `{"generate"}`.

Contract choices the tests fix:
- The request key is `context`. A missing context reaches the model as `""`.
- `ExampleSet` rejects a blank sentence. `GrammarCheck` rejects extra fields.
- The grammar system prompt mentions "Russian". The examples prompt leaves out a blank context.

UI (E2E locators):
- **Draft form:** "Check grammar" and "Use correction" buttons. Use correction updates the Target input and the h1.
- **Compose card:** an "Example sentences" button.
- **Examples pane:** a region named "Example sentences", reached at `/captures/examples`. Inside it, the English/French picker (`aria-pressed`), a field labelled "Context…" and an exact "Generate" button.
- **Results:** each level is a `role=group` named "A1".."C2", with one listitem per sentence and the Russian translation and a "Make an Item" button inside each item.
- **Failure:** the alert uses the existing llm_failed title "Couldn't reach the model", with Try again.
- **Sentence → Make an Item:** the compose box gets the sentence, then navigation to `/captures/make` with Use as is and English pressed. No Capture is POSTed.

## Validation (Step 5)

- Prerequisites are met: an approved plan with ACs, and a pytest/pytest-playwright framework.
- Every new module is skipped through `pytestmark`. There are no placeholder assertions.
- Each of AC-1..AC-5 has exactly one E2E leaf. Backend leaves map to M-1..M-6.
- The first assertions isolate the promised value. API calls to unimplemented routes stay unparsed before them.
- `make lint` is clean. 1521 tests collected. `make test-fast` gave 965 passed and 55 skipped. The related E2E suites (generate draft, make an item directly, item regenerate) gave 55 passed, so the fake extension broke nothing.
- No Playwright CLI sessions were opened. Worker summaries are in the session scratchpad.
- Next: implementation through bmad-build (the plan is ready-for-dev), then `bmad-testarch-automate` for the green-phase follow-ups listed above.

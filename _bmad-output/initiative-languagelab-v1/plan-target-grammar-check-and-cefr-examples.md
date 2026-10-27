---
title: 'Target grammar check and CEFR example sentences'
type: 'feature'
ticket: ''
created: '2026-10-27'
status: 'built'
baseline_revision: 'ca6c26b326d62480bd686e17008d7bc1e307c821'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** While shaping a Target, the learner can't tell whether it's grammatically correct. They also have no quick way to see how a word or phrase is used at different CEFR levels and turn a sentence they like into a card.

**Approach:** Two LLM helpers, both on the existing OpenRouter adapter with the same `OPENROUTER_MODELS`:
1. **Check grammar**: a button under the Target field of the shared editor (the Draft editor and Item edit). It shows a verdict, a corrected form when the Target is wrong, and a short explanation in Russian. **Use correction** replaces the Target.
2. **Example sentences**: a standalone tool on the Captures screen. An "Example sentences" button sits beside Save Capture and Make an Item and opens a pane for the compose text (the word or phrase). There the user picks a Language, optionally adds context, and presses Generate. The result is 5 sentences for each CEFR level A1, A2, B1, B2, C1 and C2, each with a Russian translation. Each sentence has **Make an Item**, which opens the existing Make an Item pane (no Capture) with that sentence as the text.

User decisions (2026-10-27): keep both helpers in one plan. Grammar check goes in the Draft editor and Item edit, with the explanation in Russian. Examples are independent of the Draft flow and live on the Captures screen: 5 sentences per level, all six levels, with Russian. Creating a card goes through the existing Make an Item pane.

## Boundaries & Constraints

**Always:**
- Same LLM and models: the same `OpenRouterLlm` instance (same key, the `models` list, `provider.require_parameters`, a strict JSON-schema response format, one retry on invalid output only). `llm_failed`/`llm_invalid_output` → 502 in the error envelope.
- Requests are validated like `/api/drafts/*`: a non-blank target and a known language (and category for grammar). Invalid input → 422 `validation_failed` before the model is called. An examples answer without exactly 6 levels in A1→C2 order with 5 sentences each is invalid output.
- Neither helper touches Anki or changes a field unless the user acts. The examples context is used once and never kept.
- No content is logged: the Target, the context, sentences or explanations (AD-15, NFR-7).
- Examples routes are `/captures/examples`, listed before the CaptureId routes like `/captures/make`. The results live in screen memory only (AD-13). A fresh mount at that route redirects to `/captures`. Its buttons are disabled while the compose box is blank, like Make an Item.
- Make an Item on a sentence puts the sentence into the compose box and navigates to `/captures/make`, with the pane's Language preselected to the examples Language. After that, the existing make-without-Capture flow runs unchanged.
- `tests/fakes/llm.py` stays in step with the port. E2E keeps `FakeLlm` (no OpenRouter).

**Never:** No new provider, model setting or env key. No automatic grammar check while typing. No change to Draft generation's prompt, schema or behavior, or to the Capture-based flow. Helper results are never stored.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Correct Target | `POST /api/helpers/grammar` {language:en, category:vocabulary, target:"jump to conclusions"} | 200 `{correct:true, corrected:null, explanation}` | — |
| Incorrect Target | {en, sentence, "He go to school."} | 200 `{correct:false, corrected:"He goes to school.", explanation}` (Russian) | — |
| Examples | `POST /api/helpers/examples` {language:fr, target:"tirer des conclusions", context?} | 200 `{levels:[{level:"A1", sentences:[{sentence, russian}×5]} … C2]}` | — |
| Malformed examples answer | 4 sentences for B1, or levels missing or out of order | retried once, then 502 `llm_invalid_output` | envelope |
| Blank / unknown input | target "   ", language "xx", category "phrase" | 422 `validation_failed`, model not called | envelope |
| Model down | adapter fails | 502 `llm_failed` | UI shows the message with Try again; fields and compose text unchanged |

</frozen-after-approval>

## Code Map

- `src/language_lab/ports/llm.py` -- `Llm` Protocol. Add `check_grammar(language, category, target) -> GrammarCheck` and `examples(language, target, context) -> ExampleSet`, with the same error contract as `generate`.
- `src/language_lab/adapters/openrouter/__init__.py` -- reuse `_post` and the 2-attempt loop. Generalize the body builder and `_validate` so they take (system prompt, user prompt, schema name, schema, model). Add one system prompt per helper. `_SYSTEM_PROMPT` and `generate` stay byte-identical in behavior (`tests/integration/test_openrouter_llm.py` must still pass).
- `src/language_lab/domain/items.py` -- the `strict_json_schema`/camelCase model pattern to follow. The new models go in `src/language_lab/domain/helpers.py` (`GrammarCheck`, `ExampleSentence`, `LevelExamples`, `ExampleSet`, `CefrLevel` A1–C2).
- `src/language_lab/features/drafts/{routes,service}.py` -- the pattern to copy for `features/helpers/{__init__,routes,service}.py` (`helpers_router(HelperService(llm))`, prefix `/api/helpers`, POST → 200). Wire it in `src/language_lab/app.py` beside `drafts_router` (~line 400).
- `src/language_lab/static/api.js` -- add `checkGrammar(body)` and `exampleSentences(body)` beside `regenerateContent`.
- `src/language_lab/static/screens/make-item.js` `editorFields(category, values, {busy, onChange})` -- shared with `screens/item-detail.js:492`. Add a `language` option and the grammar row under Target (`button-link`, a result panel, `skeleton`/`alertBox`/`tryAgain` from `dom.js`). Use correction sets `values.target` and the input, then calls `onChange("target")`. `makeItemPane` gains a preselected-Language input.
- `src/language_lab/static/router.js` ROUTES (line ~28) -- add `/captures/examples` → captures `{examples: true}` before the CaptureId patterns, and widen the `(?!make…)` lookaheads to exclude `examples` too.
- `src/language_lab/static/screens/captures.js` -- the compose card (`save`, `make` buttons, ~line 222), `MAKE_PATH`, `show(id, makeItem)`, `unmount.update`. Add the "Example sentences" button, the examples pane in `detailPane` (a Language picker reusing `make-item.js`'s `picker` pattern, a context textarea, Generate, and results grouped by level), and the per-sentence Make an Item.
- `src/language_lab/static/css/studio.css` -- helper panel and level-group styles, using the existing tokens.
- Tests to copy: `tests/api/test_drafts_regenerate.py`, `tests/integration/test_openrouter_llm.py` + `tests/support/openrouter.py`, `tests/unit/test_llm_port.py`, `tests/e2e/test_make_an_item_directly.py`, `tests/e2e/test_generate_draft.py`, `tests/support/drafts.py`, `tests/fakes/llm.py`.

## Tasks & Acceptance

**Execution:**
- [x] ATDD first: run `bmad-testarch-atdd` to write the red tests (unit domain models, integration adapter bodies/retry, api `tests/api/test_helpers_grammar.py` + `test_helpers_examples.py`, e2e `tests/e2e/test_grammar_check.py` + `test_example_sentences.py`), then push them to main (AGENTS.md).
- [x] `src/language_lab/domain/helpers.py` -- the wire models, `CefrLevel`, the strict schemas and the 6×5 validation.
- [x] `src/language_lab/ports/llm.py`, `tests/fakes/llm.py` -- the two port methods, with fake replies and recorded requests.
- [x] `src/language_lab/adapters/openrouter/__init__.py` -- the two methods on the shared request path.
- [x] `src/language_lab/features/helpers/*`, `src/language_lab/app.py` -- the service, routes and wiring.
- [x] `src/language_lab/static/api.js`, `screens/make-item.js`, `screens/item-detail.js` -- the grammar check UI.
- [x] `src/language_lab/static/router.js`, `screens/captures.js`, `css/studio.css` -- the examples tool.

**Acceptance Criteria:**
- Given a Draft or an Item in edit with a non-blank Target, when the user presses Check grammar, then the verdict appears under Target. When the Target is wrong, it also shows the corrected text and a Russian explanation, and Use correction replaces the Target (and the Draft title). Nothing changes unless the user presses it.
- Given a blank Target or compose box, then Check grammar or Example sentences is disabled.
- Given compose text "jump to conclusions", when the user opens Example sentences, picks English and generates, then six groups A1–C2 appear with 5 sentences each and their Russian.
- Given a shown sentence, when the user presses its Make an Item, then the Make an Item pane opens at `/captures/make` with that sentence as the text and English chosen. No Capture is created.
- Given either helper fails, then an alert with Try again shows, and the Target and compose text are unchanged.

## Implementation Notes

- ATDD red tests exist (2026-10-27). Follow the activation steps and the locator/contract guidance in `../test-artifacts/atdd/atdd-checklist-target-grammar-check-and-cefr-examples.md`. Remove each module's `pytestmark` skip as you implement it. `tests/fakes/llm.py` already has `check_grammar`/`examples`. `tests/unit/test_llm_port.py` must be updated for the two new port methods.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick): high 0 / medium 2 / low 1 / false 0 / maybe-false 0

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1 | `make-item.js` `grammarRow.render`: `{correct:false, corrected:null or ""}` renders "Looks correct" | medium | patch | Confirmed: `if (result.correct \|\| !result.corrected)` takes the correct branch. `GrammarCheck` has no cross-field rule, so that answer validates and isn't retried. Patch: `GrammarCheck` rejects `correct:false` without a non-blank `corrected` (invalid output → retry), with a unit test. |
| 2 | No test for AC-1 in Item edit, or for AC-5 on the grammar helper | medium | patch | Confirmed: AC-1 names "a Draft or an Item in edit" and AC-5 says "either helper". `tests/e2e/test_grammar_check.py` covers only the Draft editor and has no failure case. Patch: E2E tests for Check grammar + Use correction in Item edit (h1 updates) and for the grammar 502 alert with Try again (Target unchanged). |
| 3 | `captures.js` `makeFromSentence` ignores clicks while a Capture save is busy, but the sentence buttons look enabled | low | reject | Real but unlikely in everyday use: it needs a sentence click during a Save Capture round-trip. The fix needs a detail-pane re-render on every busy change, which is more than a direct correction. |

## Design Notes

The helpers go on the shared Llm port instead of a second adapter, so "same LLM and model" holds by construction. Examples get a fixed shape: the strict schema can't count array items, so pydantic enforces 6 levels in order × 5 sentences, and a mismatch takes the existing invalid-output retry path.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test` -- expected: all green, including the new ATDD tests

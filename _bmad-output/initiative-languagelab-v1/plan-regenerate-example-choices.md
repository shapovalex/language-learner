---
title: 'Regenerate example: pick one of 10 new examples, guided by a fresh generation context'
type: 'feature'
ticket: ''
created: '2026-11-23'
status: 'built'
baseline_revision: 'db2902c46c4f8516fbafc3d129b4ba35d66d0d5f'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** On a Vocabulary Item's detail screen, "Regenerate example" re-runs the whole generation and offers a single replacement, with no way to steer it. The user wants 10 candidate examples (each with its Russian translation) to choose from, and a generation context of their own for this regeneration, separate from the one used when the Item was made.

**Approach:** Replace the example group's flow on the item detail screen. "Regenerate example" now opens an inline panel with an optional context textarea and a Generate button. A new helper endpoint asks the model for exactly 10 `{sentence, russian}` pairs using the Item's Target, Language and the given context. Picking one puts `example` and `exampleRussian` into the edit buffer. The existing Save then writes the change and regenerates the example audio.

## Boundaries & Constraints

**Always:**
- The context is optional. Like every other context in the app, it is used once and never stored, returned or logged.
- Picking a candidate changes only the edit buffer. Nothing reaches Anki until Save changes, and the existing `exampleVoice` path regenerates the example audio and the Example card.
- The model's answer is valid only with exactly 10 non-blank pairs. Invalid output is retried once (the existing `_complete` behaviour) and then surfaced as the existing invalid-twice error.
- Errors reuse the existing regenerate failure alert, with a Try again that keeps the typed context.

**Never:**
- No change to the other regenerate groups (Russian meaning, Note, audio), to Captures' Example sentences, or to the Item create flow.
- The original generation context is not stored or shown. It isn't kept anywhere.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Target "chat", context "at the vet" | 10 sentence/Russian pairs listed. Choosing one fills Example and ExampleRussian in the buffer and closes the panel | — |
| Empty context | Context blank | Same as above; the prompt omits the context line | — |
| Model unreachable | LLM_FAILED | Existing "Couldn't reach the model" alert, Try again, typed context kept | Buffer unchanged |
| Bad output twice | 9 or 11 pairs, or a blank field | Invalid-twice alert | Buffer unchanged |
| Dismiss | Panel open | "Keep current" closes the panel with the buffer untouched | — |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/helpers.py` -- `ExampleSentence` (l.52), `ExampleSet` and `examples_json_schema` (l.68 and l.91). Add an `ExampleChoices {sentences: list[ExampleSentence]}` with a validator requiring exactly 10, plus `example_choices_json_schema()`.
- `src/language_lab/ports/llm.py` -- the `Llm` protocol. Add `example_choices(language, target, context, meaning) -> ExampleChoices`.
- `src/language_lab/adapters/openrouter/__init__.py` -- copy the pattern of `_EXAMPLES_PROMPT` (l.70), `_examples_prompt` (l.108) and the `examples` method, using `_complete` (l.178) with a strict schema.
- `src/language_lab/features/helpers/service.py` and `routes.py` -- add `example_choices` and `POST /api/helpers/example-choices` (`{language, target, context="", meaning=""}`), following `/examples`; `meaning` is the Item's current Russian meaning.
- `src/language_lab/static/api.js` -- add `exampleChoices()` next to `exampleSentences` (l.167).
- `src/language_lab/static/screens/item-detail.js` -- `GROUPS` example entry (l.88). `regenerateSlot` (l.738), `regenerate` (l.798) and `usePreview` (l.825) stay as they are for the other groups. Branch the example group into a choices panel. The Save path (`exampleVoice`, l.888) is reused unchanged.
- `src/language_lab/static/screens/captures.js` l.549-660 -- the existing context textarea plus sentence list UI. Copy its markup and classes; don't import from it.
- `tests/fakes/llm.py` -- `FakeLlm`. Add a `choices_reply` and a recorded `choice_requests`.
- Tests to mirror: `tests/api/test_helpers_examples.py` (including its no-logging test), `tests/integration/test_openrouter_llm.py`, `tests/e2e/test_item_regenerate.py`, `tests/support/regenerate_screen.py`.
- Do not touch: `adapters/anki/store.py` example handling or `features/items/service.py` `_example_changed`. They already handle the audio and card change on Save.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/helpers.py` -- add `ExampleChoices` (exactly 10) and its schema function -- validation drives the retry.
- [x] `src/language_lab/ports/llm.py`, `adapters/openrouter/__init__.py` -- add the port method, prompt and adapter. The prompt asks for 10 varied, natural sentences using the Target, each with a Russian translation, and adds `Context: …` only when the context is non-blank.
- [x] `src/language_lab/features/helpers/service.py`, `routes.py` -- add the service method and the endpoint.
- [x] `tests/fakes/llm.py` -- extend the fake.
- [x] `src/language_lab/static/api.js`, `static/screens/item-detail.js` -- add the client call and the example group's choices panel (context textarea, Generate button, skeleton while loading, a list of 10 rows with a "Use this example" button each, a Keep current button, the failure alert with Try again). Style it with existing CSS classes; add to `static/*.css` only if needed.
- [x] Tests:
  - unit: the `ExampleChoices` count validator.
  - integration: the OpenRouter `example_choices` request carries the context and parses the reply.
  - api: 200 shape, the LLM error mapping, and the context is not logged.
  - e2e: update `test_item_regenerate.py` for the example group (generate with a context, choose the 4th example, buffer updated, Save sends `exampleVoice`), plus Keep current, and a failure followed by Try again.

**Acceptance Criteria:**
- Given an Item's detail screen, when I type a context and press Generate, then 10 examples with their Russian translations are listed and the model was asked with that context.
- Given the list, when I choose one and press Save changes, then the Item's Example and ExampleRussian are that pair and its example audio is regenerated.
- Given the list, when I leave the screen without saving, then the Item in Anki is unchanged.

## Implementation Notes

- The OpenRouter tests went into `tests/integration/test_openrouter_helpers.py`, where the other helper methods are tested, not `test_openrouter_llm.py`.
- The prompt adds `Russian meaning: …` when the buffer's Russian meaning is non-blank, and `Context: …` when the context is non-blank (Design Notes).
- Panel: `Example · choose` group, with the current Example pane, the `Context · optional · used once, never saved` textarea, Generate, the skeleton / alert / list of 10 (each row has "Use this example"), and Keep current. It uses only existing CSS classes. A listed answer counts as one unsaved change, like an open Preview. The context stays in the box while the panel is open, and is never stored. Try again builds a fresh request from the box's current context and the buffer's Target and Russian meaning.
- The existing e2e tests that used the example group's compare pair now use the Russian meaning group (unsaved/leave guard, unreachable copy, reply after leaving, pair disabled during Save). The example group has its own new tests.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick lens) — high 0 · medium 1 · low 2 · false 0 · maybe-false 0

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Try again resends the stale `choices.request`, ignoring a context edited after the failure | medium | patch | `tryAgain(() => runChoices(choices.request))` confirmed; the textarea stays editable and updates `choices.context`. Patched: Try again rebuilds the request from the current context and buffer, plus an e2e assertion |
| Context typed during an in-flight Generate is wiped on success | low | patch | `choices.context = ""` in the `runChoices` success path confirmed. Fix is a deletion, so the context now stays while the panel is open |
| Another group's regeneration landing steals focus from the context box | low | patch | `context && focus === null` confirmed: `regenerate` renders with a heading focus target. Patched so the kept context focus wins, as `keepField` does |

## Design Notes

The other groups keep their compare pair (one preview compared against the current value). Only the example group gets the list. The list shows the current Example above it for reference, so the compare pair isn't needed here. The prompt includes the Item's current Russian meaning, when there is one, so the examples use the same sense of the word.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test-fast` -- expected: all pass
- `make test-e2e` -- expected: all pass

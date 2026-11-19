---
title: 'Make an Item from an example sentence with its known Russian and Language'
type: 'feature'
ticket: ''
created: '2026-11-18'
status: 'built'
baseline_revision: '75bf25187b0d59fdad0314d1567c53e9453e68f9'
route: 'oneshot'
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

**Problem:** A generated example sentence's "Make an Item" only copies the sentence into the compose box and opens the generic Make an Item pane, so the user must pick a Category and then either regenerate the Draft with the model (re-translating a sentence whose Russian is already on screen) or type the Russian themselves.

**Approach:** A sentence's "Make an Item" opens the Draft editor directly (blank Draft ItemId from `POST /api/drafts/blank`, no model call) as a Sentence Item in the examples' Language, with Target = the sentence and Russian meaning = its shown Russian. The sentence still becomes the compose text, so the Draft's back link / Discard return to the Make an Item pane for it as before, and Save follows the existing Draft lifecycle. If the blank-Draft request fails, the user lands on the Make an Item pane (examples Language preselected) with the error shown, as today.

</frozen-after-approval>

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/static/screens/captures.js` -- `makeFromSentence(sentence, russian)`: set compose text as today, then `blankDraft()` → `draft = newDraft({captureId: null, text}, {language: examples.language, category: "sentence"}, {itemId, values})` with `values.target`/`values.russian` filled, and `navigate(MAKE_DRAFT_PATH)`; on failure preset the Language and open `MAKE_PATH` with `choice.error`. Update header comment.
- [x] `tests/e2e/test_example_sentences.py` -- AC-4 test now expects /captures/make/draft with Target, Russian meaning, English Sentence meta, no generate request and no Capture saved.

**Acceptance Criteria:**
- Given generated English examples, when a sentence's Make an Item is pressed, then the Draft editor opens at /captures/make/draft as "English Sentence" with Target = sentence and Russian meaning = its Russian, and no `/api/drafts/generate` or `/api/captures` request is sent.

## Implementation Notes

Oneshot: ~40 changed lines across one screen module and one e2e test. Category is fixed to Sentence because every generated example is a full sentence.

## Verification

**Commands:**
- `uv run pytest tests/e2e/test_example_sentences.py tests/e2e/test_make_an_item_directly.py -q` -- expected: pass

## Review Triage Log

Quick review: 2 medium, 1 low patched, 1 test gap patched, 1 low rejected, 1 low (plan checkboxes) fixed.

- medium (patch): Draft took the picker's current Language instead of the one the sentences were generated in → now `examples.request.language`; covered by the new failure-path test (picker switched to French, pane shows English).
- medium (patch): a late `POST /api/drafts/blank` reply navigated to the Draft/pane after the user had left the examples pane → guard on `exploring && !editing` plus the compose text.
- low (patch): refused navigation left `draft`/`presetLanguage` set → cleared after `navigate`, as `onGenerate()` does.
- low (rejected): no busy state on Make an Item while the ItemId request runs; it's a fast local call and repeat clicks are already ignored.
- test gap (patch): added `test_a_failed_draft_request_opens_the_pane_with_its_language_and_the_error`.
- low (patch): Execution checkboxes ticked.

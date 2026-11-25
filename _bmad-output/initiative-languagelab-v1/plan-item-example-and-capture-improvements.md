---
title: 'Example improvements: regenerate in the Draft, example audio on Item detail, return to the copied Capture, clean Example sentences'
type: 'feature'
ticket: ''
created: '2026-11-25'
status: 'built'
baseline_revision: 'e55f1f90d6f91aebb051baf822ffc4d565101d0d'
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

**Problem:** Four rough edges around examples. (1) "Regenerate example" (10 choices) exists only on Item detail, not in the Draft editor while creating an Item. (2) Item detail can't play an Item's example audio or regenerate it. (3) After "Copy to compose box" → Example sentences → a sentence's Make an Item → Save, the app lands on /captures, so the user must hunt for the Capture to delete it. (4) Opening Example sentences again still shows the previous generation's results.

**Approach:** (1) Move the choices panel into a shared module and use it in the Vocabulary Draft editor as well as Item detail. (2) Add an "Example audio" card to Vocabulary Item detail: it plays the saved clip, previews a new one in the Reference audio card's Voice, and lets the user keep or use it. A used clip is uploaded with Save changes. (3) Remember which Capture the compose text was copied from. A compose-text Draft saved from it returns to that Capture with the "Make another Item from this Capture, or delete it." flash. (4) Pressing "Example sentences" opens an empty pane.

## Boundaries & Constraints

**Always:**
- Nothing reaches Anki before Save. Chosen examples and accepted clips live only in screen memory and count as unsaved changes.
- Choices contexts are used once and never stored or logged, as now.
- An uploaded example clip is valid only for a Vocabulary Item whose Example and ExampleRussian are both non-blank. Otherwise the request fails with `VALIDATION_FAILED` before anything is written. It is stored through the existing `example_audio_bytes` path in `save_item`.
- An accepted example clip is sent only when its text equals the buffer's Example at Save. Otherwise the existing `exampleVoice` path decides, as today.
- Item detail's existing choices-panel behaviour and tests keep working, apart from moving to the shared module.

**Never:**
- No change to Reference (Target) audio behaviour, the regenerate compare pair for the Russian meaning or Note, or the Capture list.
- No regenerate example for Sentence Drafts. They have no Example field.
- No new LLM endpoint. Reuse `/api/helpers/example-choices` and `/api/audio/preview`.

**Decisions (2026-11-25):**
- Return to Capture applies to any Draft made from compose text copied from a Capture: an Example sentence's Make an Item and the compose box's Make an Item pane (Generate Draft or Write it myself).
- Every press of "Example sentences" clears the results, error and context. The chosen Language stays.
- Example audio regeneration works like the Reference audio card: preview the clip, then Keep current or Use new. A used clip is uploaded with Save changes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Draft regenerate | Vocabulary Draft, press Regenerate example, Generate | 10 pairs listed; Use this example fills Example/ExampleRussian and closes the panel | Model failure: alert with Try again, values unchanged |
| Example audio play | Vocabulary Item with ExampleAudio | Player for /api/media/<exampleAudio> | Load error: "Couldn't load the saved example audio." |
| Example audio regenerate | Press Regenerate example audio, then Use new | Preview of the buffer's Example in the Voice, counted as unsaved; Save uploads it; card then shows it as current | TTS failure: alert with Try again, current unchanged |
| No example | Example blank | Card shows "Add an example to make its audio."; button disabled | — |
| Return to Capture | Copy to compose box from Capture C → examples → Make an Item → Save | Lands on /captures/C with the Capture flash; compose box cleared | Save failure: stays in the editor as now |
| Origin dropped | After copying, user saves the compose text as a Capture, or copies another | The origin becomes the new copy, or none | — |
| Clean examples | Results shown, user presses Example sentences again | Pane with no results, no error, empty context; an in-flight reply is dropped | — |

</frozen-after-approval>

## Code Map

- `static/screens/item-detail.js` -- choices panel `choicesPanel`/`openChoices`/`generateChoices`/`runChoices`/`chooseExample`/`closeChoices` (l.930-1075): extract the DOM builder into the shared module and keep the state and focus wiring here. `itemAudioCard` (l.172-445): parameterize it for an example variant (no voice picker, voice from the reference card, no Remove, text = `values().example`, heading "Example audio"), or write a sibling `exampleAudioCard`. `syncDirty` (l.510) adds its `pending()`. `saveChanges` (l.1159) sends the example blob, and `load` (l.1121) reads `read.exampleAudio`.
- `static/example-choices.js` (new) -- the shared panel builder: context textarea, Generate, skeleton, alert with Try again, a list of 10 with "Use this example", and Keep current. The caller owns state, and the panel takes callbacks.
- `static/screens/make-item.js` -- `draftEditor` (l.534): for `vocabulary`, add a "Regenerate example" button-link and the panel after the `exampleRussian` field. State goes in `draft.choices` and survives re-renders. The request is `{language: draft.language, target, context, meaning: values.russian}`. One request at a time, and a late reply for a closed panel or a discarded Draft is dropped (token check).
- `static/screens/captures.js` -- `copyToBox` (l.534) sets `copiedFrom = captureId`. `submit` (a Capture save that cleared the box) and an emptied box clear it. `makeFromSentence` (l.682) and `onWrite`/`onGenerate` with `captureId === null` stamp `draft.returnTo = copiedFrom`. `saveDraft` (l.934): when `returnTo` is set, clear the box and `navigate(capturePath(returnTo), {flash: savedFlash(target, returnTo, failed)})`. `examplesButton` click (l.1251): reset `examples` (token++, request/result/error null, context "") before navigating.
- `static/api.js` -- `saveItem(lang, item, audioBlob, exampleBlob = null)` appends `exampleAudioFile`. Update the `getItem` doc for `exampleAudio`.
- `features/items/routes.py` -- `save`: an optional `example_audio_file` (alias `exampleAudioFile`), read with the `MAX_AUDIO_BYTES` cap like `audioFile`. `get_item`: add `"exampleAudio": item.example_audio`.
- `features/items/service.py` -- `save(..., example_audio_bytes=None)`: when given, require `_wants_example(content)` (else `VALIDATION_FAILED`), skip synthesis, and pass the bytes through. `adapters/anki/store.py` already validates the MP3 and places the card. Do not touch it.
- Tests to mirror: `tests/e2e/test_item_regenerate.py`, `tests/support/regenerate_screen.py`, `tests/e2e/test_item_audio.py`, `tests/support/item_audio_screen.py`, `tests/e2e/test_capture_copy.py`, `tests/e2e/test_example_sentences.py`, `tests/support/examples_screen.py`, `tests/api/` items save tests, and `tests/fakes/`.

## Tasks & Acceptance

**Execution:**
- [x] `features/items/routes.py`, `service.py` -- accept `exampleAudioFile`; return `exampleAudio` from GET -- backend for item 2.
- [x] `static/api.js` -- `saveItem` example blob.
- [x] `static/example-choices.js`, `static/screens/item-detail.js` -- extract the panel; Item detail uses it unchanged in behaviour.
- [x] `static/screens/make-item.js` -- Draft regenerate example (item 1).
- [x] `static/screens/item-detail.js` -- Example audio card, unsaved count, Save upload, saved → current (item 2).
- [x] `static/screens/captures.js` -- `copiedFrom`/`returnTo` (item 3); reset examples on the button (item 4). Update the header comments.
- [x] Tests: api (exampleAudioFile stored; rejected for Sentence/blank example; GET exampleAudio); e2e Draft regenerate (choose the 3rd, Save carries it); e2e Item example audio (play URL, regenerate → Use new → Save uploads `exampleAudioFile`; Keep current; TTS failure); e2e copy → examples → Make an Item → Save lands on the Capture; e2e second Example sentences press shows no old results.

**Acceptance Criteria:**
- Given a Vocabulary Draft, when I pick a regenerated example and save, then the Item in Anki has that Example and ExampleRussian, and its example audio was made.
- Given a Vocabulary Item with example audio, when I open it, then I can play that clip; when I regenerate, use the new clip and save, then Anki's ExampleAudio holds the new clip.
- Given a Draft made from text copied from Capture C, when Save succeeds, then I'm on Capture C's detail and can delete it.
- Given earlier Example sentences results, when I press Example sentences, then the pane shows no results.

## Implementation Notes

- Item detail's Example audio card is `itemAudioCard` with `example: true` (no Voice picker, no Remove, "Regenerate example audio" / "Preview example audio", "Use new"). Its Voice is `audioCard.voice()`; the Reference card's `onVoices` refreshes it once Voices load.
- After a Save that changed the Example without uploading a clip, Item detail re-reads the Item (best effort) so the card plays the remade clip instead of a stale /api/media name.
- The route validates `exampleAudioFile` with `validate_mp3` (size cap and MP3 frames) before the service runs; the service then requires `_wants_example` (`VALIDATION_FAILED`).
- The Draft's choices panel re-renders only its own slot, so typing in other fields keeps focus; `disposeDraftAudio` also drops `draft.choices`, so a late reply for a discarded Draft is ignored.
- `copiedFrom` survives edits that leave text in the box (e.g. a sentence's Make an Item replacing it); only a Capture save, an emptied box or another copy changes it.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick lens) — high 0 · medium 2 · low 2 · false 0 · maybe-false 0

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A withheld accepted example clip survives a successful Save: the unsaved chip stays and the card shows "New audio" | medium | patch | Confirmed: `saved()` runs only with `exampleBlob`, and `reset()` touches only `current`, so `pending()` still counts `accepted`. Patch: clear the accepted clip after a Save with no blob, and assert the chip is hidden in the test |
| The card isn't re-read when a Save made example audio for an unchanged Example that had none | low | patch | Confirmed: `_example_changed` returns True when there is no example audio, while the client re-reads only when `example` changed. Patch: also re-read when the card had no clip |
| Deleting the copied Capture leaves `copiedFrom` set, so a later Save goes to a deleted Capture | medium | patch | Confirmed: `onDelete` calls `forget(id)` and never touches `copiedFrom`. On desktop the box keeps its text. Patch: clear it on delete, plus an e2e test |
| The example upload is not read or closed when `audio_upload` raises first | low | patch | Confirmed by the order of calls in `save`. Patch: read both uploads first, then validate |

## Design Notes

The example card takes its Voice from the Reference audio card (`audioCard.voice()`), so the screen keeps a single Voice picker. The panel is extracted as a builder, not a stateful component, because Item detail's focus-keeping (`keepContext`, `focusTargets`) depends on owning the re-render.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test-fast` -- expected: all pass
- `make test-e2e` or the e2e subset via `make test` -- expected: all pass

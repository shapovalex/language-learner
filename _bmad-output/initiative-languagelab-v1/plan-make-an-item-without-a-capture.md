---
title: 'Make an Item without a Capture'
type: 'feature'
ticket: ''
created: '2026-10-25'
status: 'built'
baseline_revision: 'd2c582d8b3f731b6221147fd536c81dfec4f9111'
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

**Problem:** An Item can only be made from a Capture (Captures → open a Capture → Make an Item). Making one directly means saving a throwaway Capture first and deleting it afterwards.

**Approach:** User decision (2026-10-25): the starting point is on the Captures screen. A "Make an Item" button beside Save Capture opens the Make an Item pane for the typed compose text, without saving a Capture. The text is "Use as is" (or a Custom value). The user picks Language and Category, optionally adds Generation context, and chooses Generate Draft or Write it myself. Everything after that is the same as from a Capture: the Draft editor, automatic Reference audio, the duplicate check and Save to Anki. No Capture is created, read or deleted.

## Boundaries & Constraints

**Always:**
- It is the same Draft flow, not a copy. Reuse `captures.js`'s existing lifecycle (generate, retry, editor, dirty state, `saveDraft`, duplicate sheet, Open existing, dispose), with a source that has no Capture: no captureId, and the compose text as its text. The Capture-based flow's behavior, copy and routes are unchanged.
- Routes: the pane is at `/captures/make` and the Draft at `/captures/make/draft`, both listed before `/captures/<id>` so that `make` is never read as a CaptureId. The Draft lives at its route (AD-13). Leaving it asks "This Draft isn't saved." like the Capture Draft.
- "Make an Item" is disabled while the compose box is blank, like Save Capture. The pane's actions stay disabled with the existing reason until the text, Language and Category are set.
- A successful Save returns to `/captures` with the flash "Saved “<Target>” to Anki." (no Capture sentence) and clears the compose box. Leave or Cancel keeps the compose text.
- No backend or API changes: `blankDraft`, `generateDraft`, `findDuplicates` and `saveItem` are reused as they are.
- User decision (2026-10-25): acceptance is simple and UI only. No AnkiConnect or `/api` requests.

**Never:** Creating, changing or deleting a Capture in this flow. No Capture text or "from Capture" copy in the Draft. No changes to the Capture-based flow's behavior.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Write | Target, en or fr, Vocabulary or Sentence, Write it myself | Draft editor with the Target filled; automatic audio; Save stores one Item with four Cards | Existing Save errors keep the Draft |
| Generate | Same, Generate Draft, optional context | Generating screen, then the Draft; Save as above | Existing Generation failure + Try again |
| Missing input | Blank Target, or no Category | Both actions disabled with the reason | — |
| Duplicate | Target matches an existing Item | Existing sheet: Open existing / Cancel / Create anyway | — |
| Leave | Back/nav with an unsaved Draft | "This Draft isn't saved." alert; Stay keeps it, Leave discards it and its audio | — |
| Blank compose | Empty compose box | "Make an Item" disabled | — |
| Captures untouched | Any of the above | The Captures list is unchanged before and after; the compose box is cleared only after a successful Save | — |

</frozen-after-approval>

## Code Map

- `src/language_lab/static/screens/captures.js`: today it owns the whole Draft lifecycle: `onWrite`/`onGenerate` (L345–400), `generate` (L402), `syncDirty`, `renderEditor`, `openEditor`/`closeEditor`, `saveDraft` (L489, including the automatic audio wait), `openSheet`/`closeSheet`/`openExisting`, and route handling (`params.draft`, L748). `newDraft` (L99) and `savedFlash` (L80) are Capture-specific. Reuse it with a capture-less source (`captureId: null`, `text` = compose text). Its return path is `/captures`, and its flash has no Capture sentence. The compose card (`save`, `box`, L195–205) gets the "Make an Item" button, which follows Save Capture's enabled rule.
- `src/language_lab/static/screens/make-item.js`: `makeItemPane` (L172) and `chosenText` work as they are, with the compose text in place of the Capture text. On desktop, show the pane in the detail pane; on the phone, full screen as for an open Capture. `draftEditor`, `generatingScreen`, `duplicateSheet`, `itemPart`, `saveFailure`, `disposeDraftAudio`, `blankValues` and `generatedValues` are reused as they are. Check `generatingScreen` and `draftEditor` for Capture-text copy and omit it when there is no Capture.
- `src/language_lab/static/router.js`: `ROUTES` (L23) and the Draft dirty rule at L384, where `kind "draft"` asks on any path change. Add `/captures/make` and `/captures/make/draft` to the `captures` screen, before the `/captures/<id>` patterns. Also check `staysOnScreen` and the compose dirty state. `static/css/studio.css`: reuse existing classes.
- Tests: `tests/e2e/test_make_an_item.py`, `test_generate_draft.py`, `test_duplicate_warning.py`, `test_unsaved_alert.py` and `test_draft_audio.py` must stay green unchanged, apart from imports. Helpers: `tests/support/items_screen.py`, `captures_screen.py`, `audio_screen.py`.

## Tasks & Acceptance

**Execution:**
- [x] `captures.js`: the "Make an Item" button, the capture-less source through the existing lifecycle, the `/captures/make` routes and the Save return. `make-item.js` only if Capture-text copy must be hidden. `router.js` routes.
- [x] `tests/e2e/test_make_an_item_directly.py` (new): one test per Matrix row, for en and fr at phone and desktop widths. Includes a UI-only live-server journey: type text → Make an Item → Write it myself → Save to Anki → open the Item from search (its player holds the automatic clip) → the Captures list is unchanged.

**Acceptance Criteria:**
- Given no Capture, when the user makes an Item through the new start, then it is saved with automatic audio and four Cards, and the Captures list is unchanged.
- Given the existing Capture-based e2e suites, when they run unchanged, then they pass in Chromium and WebKit.

## Review Triage Log

Pass 1 (quick, 2026-10-25): high 0, medium 1, low 5, false 1, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| Save Capture at `/captures/make` (desktop) leaves a dead pane | medium | patch | `submit()` clears the box without re-rendering the pane or leaving the route. Leave the make route after a Capture save; add a desktop check. |
| Compose text lost on Open existing / nav Discard | low | reject | Open existing means the text matched an existing Item. Nav Discard is an explicit leave after the "This Draft isn't saved." alert. Keeping the text across unmount needs new state. |
| New copy "Type the text in New Capture." and `blank` option | low | reject | No existing reason covers blank text, so the actions would otherwise be disabled with no reason. The copy has been surfaced to the user. |
| `draftTarget` `!target` changes the Capture flow for empty Capture text | false | reject | A Capture's text is never blank: Save Capture and the API reject blank text. |
| Four Cards not checked | low | patch | The Item delete confirmation lists the Cards; assert it. |
| Untested Matrix cells: Save error, Leave stores nothing, failure snapshot | low | patch | Add them with the existing helpers. |
| `expect_no_capture_copy` back-link check is timing-dependent | low | patch | Make it deterministic. |

After the patches, verification on my side: `make test` 1288 passed; `make test-webkit` 837 passed; `make lint` and `git diff --check` clean. Nothing deferred.

## Verification

**Commands:**
- `make test`, `make test-webkit`, `make lint`, `git diff --check`: expected clean.

**Manual checks (UI only, on the next release):**
- On the phone, type a word in New Capture, tap Make an Item (not Save Capture), pick French and Vocabulary, Write it myself, Save to Anki. The Saved flash appears, and in Anki Desktop the card shows the word and plays its audio. Captures shows no new Capture.
- Do the same with Generate Draft in English.

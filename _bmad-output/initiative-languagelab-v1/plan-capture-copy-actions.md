---
title: 'Capture copy actions and a prefilled Custom value'
type: 'feature'
ticket: ''
created: '2026-11-15'
status: 'built'
baseline_revision: '1d3d6151bea81ef82a5ff1b7fc329300e1656364'
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

**Problem:** An existing Capture's text can't be reused. To run Example sentences on it, or to put it anywhere else, the user retypes it. In Make an Item, choosing "Custom value" opens an empty field, so a small change to the text means retyping all of it.

**Approach:** Capture detail gets two buttons. "Copy to compose box" puts the Capture's text into the New Capture box and returns to the list, so the existing Save / Make an Item / Example sentences / Capture and translate buttons work on it. "Copy" writes the Capture's text to the system clipboard. In the Make an Item pane, choosing Custom value while its field is empty fills the field with the text that Use as is would take.

**Decisions (2026-11-15):**
- Scope stays as one plan with all three improvements (user chose "Keep all").
- For an existing Capture, Example sentences is reached through "Copy to compose box" only. There is no direct Example sentences button on Capture detail.
- Copy to compose box replaces any text already in the box, without asking (same as an example sentence's Make an Item).

## Boundaries & Constraints

**Always:** Text is copied verbatim (`capture.text`). "Copy to compose box" starts a new composition the same way `makeFromSentence` does: new CaptureId, `clearTranslation()`, `state.error = null`, `syncDirty()`. It then goes to `/captures` and focuses the box. Clipboard copy uses `navigator.clipboard.writeText` and falls back to a hidden textarea with `document.execCommand("copy")` when the async API is missing or rejects (the app can be opened over plain http on the LAN, which is not a secure context). The button's label shows "Copied" for about 2 seconds, or "Couldn't copy" on failure. The Custom value field is prefilled only when it is empty, so the user's edits survive switching between the radios. Nothing about the text is logged (AD-15).

**Never:** No backend or API changes. No changes to Save Capture, Capture and translate, or Example sentences behaviour. No copy buttons on list rows. Example sentences must not auto-run.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| COPY_TO_BOX | Capture "jump to conclusions" open, box empty | Route `/captures`, box holds the text and has focus, screen dirty | No error expected |
| COPY_TO_BOX_BUSY | a Save is in flight | Button disabled (same as `makeFromSentence`'s `state.busy` guard) | Ignored |
| CLIPBOARD_OK | press Copy | Clipboard holds the text; button reads "Copied" then reverts | No error expected |
| CLIPBOARD_FAILS | async API and execCommand both fail | Button reads "Couldn't copy" then reverts | No alert, no throw |
| CUSTOM_PREFILL | Use as is → Custom value, field empty | Field = Capture text (or compose text at /captures/make), Generate/Write enabled once Language+Category are chosen | No error expected |
| CUSTOM_KEPT | custom edited, switch to Use as is and back | Field keeps the edit | No error expected |

</frozen-after-approval>

## Code Map

- `src/language_lab/static/screens/captures.js`:
  - `renderDetail()` (~L460-485) builds the shown-Capture article (`.capture-detail-content`, actions row, `deleteButton(layout)`). Add a `.capture-detail-copy` row with the two buttons under the time, only when `open.status === "shown"`, and in both layouts.
  - `makeFromSentence()` (~L621) is the pattern for starting a new composition.
  - `makeItemPane(...)` calls at L446 and L484 now pass `text` (`box.value.trim()` / `open.capture.text`) instead of `blank`.
  - Add constants beside the others (~L83-120).
- `src/language_lab/static/screens/make-item.js`: `makeItemPane(choice, {onGenerate, onWrite, blank})` (L187). Replace `blank` with `text`, and keep `blank = !text` internally. In the `custom` radio's `change` handler (~L215), set `choice.custom = custom.value = text` when `choice.custom` is empty, before `refresh()`. `chosenText` stays as is.
- `src/language_lab/static/dom.js`: add an exported `copyText(text) -> Promise<boolean>` (async API, then execCommand fallback).
- `src/language_lab/static/css/studio.css`: next to `.capture-detail-time` (~L624), add `.capture-detail-copy` (flex, gap `--space-3`, `margin-top: var(--space-4)`) using the existing `.button.button-secondary`.
- Tests:
  - `tests/e2e/test_make_an_item.py::test_write_it_myself_waits_for_a_language_a_category_and_a_custom_value` (L98) expects "Enter the custom value." right after checking Custom value. Change it to clear the field first, and assert the prefill.
  - Reuse `open_capture` (L76) and `tests/support/captures_screen.py` (`compose_box`, `detail`).
  - Chromium e2e reads the clipboard via `context.grant_permissions(["clipboard-read", "clipboard-write"])` plus `navigator.clipboard.readText()`.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/static/dom.js` -- add `copyText` -- shared clipboard helper with fallback.
- [x] `src/language_lab/static/screens/make-item.js` -- `text` option and Custom value prefill -- improvement 2.
- [x] `src/language_lab/static/screens/captures.js` -- Copy and Copy to compose box buttons, `copyToBox()`, pass `text` to `makeItemPane`, update the header comment -- improvements 1 and 3.
- [x] `src/language_lab/static/css/studio.css` -- `.capture-detail-copy` row -- layout.
- [x] `tests/e2e/test_capture_copy.py` (new) -- COPY_TO_BOX at phone and desktop widths, CLIPBOARD_OK (chromium), CUSTOM_PREFILL and CUSTOM_KEPT -- cover the matrix; adjust the existing custom-value test in `tests/e2e/test_make_an_item.py`.

**Acceptance Criteria:**
- Given an open Capture on a phone-width screen, when the user presses "Copy to compose box", then the list screen shows with the text in New Capture, and "Example sentences" opens the pane for that text.
- Given an open Capture, when the user presses "Copy" and then pastes elsewhere, then the pasted text equals the Capture's text.
- Given the Make an Item pane at /captures/make, when the user chooses Custom value, then the field holds the compose text.

## Implementation Notes

- The prefill also changed two more existing tests that expected an empty Custom value right after checking it: `tests/e2e/test_make_an_item_directly.py::test_the_pane_waits_for_the_text_a_language_and_a_category` and `tests/e2e/test_generate_draft.py::test_generate_draft_waits_for_a_language_a_category_and_a_custom_value`. Both now clear the field before asserting the reason.
- In `makeItemPane` the option is destructured as `text: asIs`, since the function already has a local `text` (the fieldset).
- `renderButtons()` also updates the "Copy to compose box" buttons' disabled state, so a Save that starts or ends while a Capture is open updates them (COPY_TO_BOX_BUSY).
- Added a CLIPBOARD_FAILS e2e test (both copy paths stubbed to fail).

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0 · medium 1 · low 4 · false 0 · maybe-false 0

| # | Finding | Verdict | Route | Evidence |
|---|---------|---------|-------|----------|
| 1 | dom.js `copyText` fallback selects nothing on iOS Safari over plain http | medium | patch | iOS ignores `select()` on textareas without `setSelectionRange`; the phone-over-LAN case is exactly when the fallback runs. Fix: add `setSelectionRange` and a 16px font. |
| 2 | Fallback path never tested succeeding | low | patch | Both copy tests skip it (granted API / both stubbed to fail). Added a Chromium test with `writeText` rejecting. |
| 3 | COPY_TO_BOX "screen dirty" not asserted | low | patch | Save enabled only proves text in box; added unsaved-alert assertion. |
| 4 | `copyToBox` mutates the box before a navigate the router may refuse (confirm busy) | low | reject | Only reachable while a delete confirmation is in flight over the detail; rare, and a fix adds a branch around navigate. |
| 5 | Copy label reset timer not cleared on unmount | low | reject | Writes to a detached button only; harmless, fix adds unmount plumbing. |

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test-fast` -- expected: all pass
- `uv run pytest -m e2e tests/e2e/test_capture_copy.py tests/e2e/test_make_an_item.py tests/e2e/test_make_an_item_directly.py tests/e2e/test_captures_list.py` -- expected: all pass

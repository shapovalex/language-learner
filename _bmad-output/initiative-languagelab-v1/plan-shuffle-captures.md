---
title: 'Shuffle the Captures list'
type: 'feature'
ticket: ''
created: '2026-11-27'
status: 'built'
baseline_revision: '881e35cda6a670b69e414a0aeafdd5b8cee875bb'
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

**Problem:** The Captures list is always newest first, so the user keeps working on the same recent Captures and older ones sit untouched; they want to pick several random ones to work on.

**Approach:** A "Shuffle" button in the Captures list header puts the loaded list in a random order, only in the browser (nothing is written to Anki or sent to the server). While shuffled the header reads "Shuffled" / "N Captures · shuffled", pressing Shuffle again reshuffles, and a "Newest first" button puts the list back in date order. The order is kept while the Captures screen stays mounted (opening a Capture, making an Item, deleting a Capture and going back keep it); a fresh visit to Captures starts newest first. A Capture saved while shuffled appears at the top, as today.

</frozen-after-approval>

## Implementation Notes

Oneshot: one screen module, a few CSS lines and one E2E test file; no server or Anki change.

- `captures.js`: module-level `shuffled` (Fisher–Yates) and `newestFirst` (sort by `createdAt`, the server's fixed UTC ISO format, so text order is date order). `list.shuffled` flips the narrow header to "Shuffled" and the wide one to "N Captures · shuffled"; `loadList` resets it (a Try again reload is newest first).
- The restore button reads "Sort newest first", not "Newest first": the phone header span already says "Newest first", and the same text on a hidden button would make the existing `get_by_text("Newest first")` checks ambiguous.
- `studio.css`: `.captures-list-header` is now a wrapping flex row; `.captures-order-actions` holds the two link buttons.
- Test: `tests/e2e/test_captures_shuffle.py` pins `Math.random` to 0 for a known order, checks no `/api/` request is sent, and the order survives opening a Capture.

## Review Triage Log

Pass 1 (quick): high 0, medium 1, low 3, false 0, maybe-false 0.

- medium, patch: `onSaved` rebuilt the list with `withSaved`, putting every Capture saved this mount back on top, so a save while shuffled undid the shuffle for earlier saves. Now only the new Capture goes on top and the rest keep their order; E2E test added.
- low, patch: Shuffle on a one-Capture list marked it "shuffled" with no change. Shuffle is hidden below two Captures; E2E test added.
- low, kept for the human: the restore button reads "Sort newest first" where the frozen intent says "Newest first" (reason in Implementation Notes). Raised with the user, frozen block left unchanged.
- low, reject: no tests for keeping the order after Make an Item / delete, a fresh visit, Try again, or reshuffling. All of these use the same mount-memory path that the open-a-Capture and save tests already cover. The extra tests would be costly stubbing for little signal.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test` -- expected: all pass

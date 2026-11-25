---
title: 'Lock Produce, Write and Example cards until the Understand card is answered'
type: 'feature'
ticket: ''
created: '2026-11-25'
status: 'built'
baseline_revision: '7156a438300776dfd5559d027957d1bf5dce0230'
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

**Problem:** A new Item's Study cards (Understand, Produce, Write, and Vocabulary Example) all become new cards at once, in any order, so the user can be asked to produce or write a word before ever seeing it in Understand.

**Approach:** A newly created Item's Produce (ord 1), Write (ord 2) and Example (ord 4) cards start suspended and the note carries a lock tag. Before each Sync, the app finds locked notes whose Understand card (ord 0) has been answered at least once, unsuspends their locked cards and removes the tag.

**Decisions (2026-11-25):**
- "Reviewed" means the first answer to the Understand card, whatever the rating (the card is no longer new).
- Only Items created from now on are locked; existing Items are never touched (no reconciliation).
- Pronounce (ord 3) is never locked.

## Boundaries & Constraints

**Always:** The lock is recorded only in Anki (a note tag, AD-13 style); every write goes through the Prefix guard; an unlock failure never fails or blocks the Sync; the Example card is unlocked only when the note's `ExampleAudio` holds something (otherwise it stays suspended as today).

**Never:** Touch notes without the lock tag; change Pronounce exclusion; add UI; migrate or reconcile existing notes; widen any search beyond exact manifest scopes plus fixed literals.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New Item | Save of an unknown ItemId | Note added with lock tag; ords 1, 2 (and 4 if made) suspended; ords 0, 3 not | Failure mid-way: tag already on the note, so a later unlock still resolves it |
| Not yet answered | Locked note, Understand card new | Unlock pass leaves it alone | — |
| Answered | Locked note, Understand card not new | Ords 1, 2 unsuspended; ord 4 unsuspended if `ExampleAudio` non-empty; tag removed | — |
| Example audio arrives while locked | Save/backfill stores example audio on a locked note | Example card moved to its Study deck, stays suspended | — |
| Existing Item updated | Save of a known ItemId (no tag) | No lock; behaves as today | — |
| User-suspended card on unlocked note | No lock tag | Never unsuspended | — |
| Anki down / Setup not ready at unlock | Before Sync | Unlock logged and skipped; Sync still runs | Swallow `AppError`, log one line |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/manifest.py` -- `Manifest`: add a `lock_tag` (`<Prefix>::Locked`) and `LOCKED_ORDS = (1, 2, EXAMPLE_ORD)`; the one source of Anki names.
- `src/language_lab/adapters/anki/query.py` -- add `unlockable_notes_query(manifest, note_type)` → `note:"<type>" tag:<lock_tag> card:1 -is:new` (fixed literals only).
- `src/language_lab/adapters/anki/guard.py` -- `addNote`: `tags` absent or exactly `[lock_tag]`; new id-targeted `removeTags` with `notes` of manifest note types and `tags == lock_tag`. Unknown stays fail-closed.
- `src/language_lab/adapters/anki/store.py` -- `save_item` add path (~line 566): pass `tags: [lock_tag]` in `addNote`, then after the `changeDeck` loop `suspend` the `LOCKED_ORDS` cards present. `_place_example_card` (~line 638): skip the unsuspend when the note carries the lock tag (read `tags` from the `notesInfo` `_note_cards` already sends). New `unlock_answered_items()`: under one lock hold, per Item note type (`manifest.item_note_type` for each Language × Category) `findNotes` the unlockable query, `notesInfo` + `cardsInfo`, `unsuspend` suspended ords 1/2 (and 4 when `ExampleAudio` non-empty), then one `removeTags`. Returns count unlocked.
- `src/language_lab/ports/anki_store.py` -- add `unlock_answered_items() -> int` to the protocol, documented.
- `tests/fakes/anki_store.py` -- `FakeAnkiStore.unlock_answered_items` (counts calls, `unlock_error` to raise); keep docstring in step.
- `src/language_lab/features/sync/service.py` -- `_sync_once`: call `self._anki.unlock_answered_items()` first; catch `AppError`/`Exception`, log a warning, continue to `sync()`. Docstring note: unlocks ride the same Sync up.
- `tests/support/anki_state.py` -- simulator: note `tags`, card `reviewed` flag (`type`/`queue` non-new), `addNote` `tags`, `removeTags` write, `findNotes` for the unlockable query; `item_note(..., tags=, reviewed_ords=)` helpers.
- Reuse: `_present_entries`, `_note_cards`, `_SUSPENDED_QUEUE`, `is_int`, `sent_writes`/`sent_queries` helpers. Don't change: setup diff/repairs, Pronunciation code, Capture code.
- `docs/anki.md` -- one short paragraph on the lock tag and when cards unlock.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/adapters/anki/manifest.py` -- add `lock_tag`, `LOCKED_ORDS` -- single source of names
- [x] `src/language_lab/adapters/anki/query.py` + `tests/unit/test_anki_query.py` -- unlockable query and its test
- [x] `src/language_lab/adapters/anki/guard.py` + `tests/integration/test_anki_prefix_guard.py` -- allow tagged addNote and lock-tag `removeTags`; refuse other tags / unmanaged notes
- [x] `tests/support/anki_state.py` -- simulator support for tags, reviewed cards, `removeTags`, unlockable query
- [x] `src/language_lab/adapters/anki/store.py` -- lock on create, lock-aware `_place_example_card`, `unlock_answered_items`
- [x] `src/language_lab/ports/anki_store.py`, `tests/fakes/anki_store.py` -- port method and fake
- [x] `src/language_lab/features/sync/service.py` -- unlock before each Sync, failures logged and ignored
- [x] `tests/integration/test_anki_study_lock.py` -- matrix rows against the simulator
- [x] `tests/unit/test_sync_service.py` -- unlock runs before sync; an unlock failure still syncs
- [x] `docs/anki.md` -- document the lock

**Acceptance Criteria:**
- Given a running app with Sync enabled, when a new Item is saved and its Understand card is then answered once in Anki, then after the next Sync its Produce and Write cards (and Example card if it has audio) are unsuspended and the note no longer has the lock tag.
- Given Sync disabled (dev mode), when an Item is saved, then it is still locked, and nothing unlocks it (documented).

## Implementation Notes

- `_place_example_card` on a locked note does more than skip the unsuspend: Anki makes a newly rendering Example card unsuspended, so the card is actively suspended (after the deck move) to keep it locked, as the matrix row "stays suspended" requires.
- The unlock re-checks in Python that each found note carries the tag (case-insensitive) and that its ord 0 card's `type` is not new, then sends one `unsuspend` and one `removeTags` per note type, unsuspend first so a failure leaves the tag for the next pass.
- Review change: the unlock now runs after a Sync that ends OK (not before), and when it unlocked any Item one more Sync sends the unsuspends up, its outcome the recorded status; so an Understand answer from the phone unlocks within one Sync, as AC-1 and docs/anki.md say. An unlock failure keeps the first Sync's status.
- Review change: Save's lock `suspend` is sent right after `addNote`'s cards are read, before the `changeDeck` moves, so a failed move never leaves Produce/Write open on a tagged note.
- The guard's `removeTags` requires exactly `{notes, tags}` params with `tags` equal to the lock tag string (AnkiConnect takes a space-separated string).
- Two existing example-audio tests now answer Understand and run the unlock before exercising re-enable paths; write-sequence assertions on new-Item saves gained the trailing `suspend`.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 1, low 3, false 0, maybe-false 0.

| Verdict | Route | Finding | Evidence / action |
|---|---|---|---|
| medium | patch | Unlock runs before `sync()`, so a phone review unlocks one Sync late (AC-1, docs) | Confirmed in `_sync_once`; patched: sync, then unlock on OK, then one more sync when anything unlocked |
| low | patch | Partial Save failure leaves a tagged note with Produce/Write unsuspended; retry never suspends | Confirmed: `suspend` was after the `changeDeck` loop; patched: suspend right after `_cards_by_ord` |
| low | patch | `save_item` docstring stale (Example "unsuspended", no lock) | Confirmed; docstring corrected |
| low | reject | Guard allows lock tag on Capture/Reading Rule notes | Only manifest notes, never sent by the app; tightening adds an Item-type set to the guard for a case no caller reaches |

## Design Notes

The unlock runs after each Sync that ends OK, and one more Sync runs when it unlocked anything: a review made on the phone is pulled in and its unlocks go up in the same cycle (changed in review pass 1 from "before the Sync"). A tag (not a field) avoids a schema migration and lets the user unlock by hand in Anki (remove tag, unsuspend).

## Verification

**Commands:**
- `make test-fast` -- expected: all pass
- `uv run ruff check . && uv run ruff format --check .` -- expected: clean

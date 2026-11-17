---
title: 'Exclude Items from Pronunciation practice'
type: 'feature'
ticket: ''
created: '2026-11-16'
status: 'built'
baseline_revision: 'de352574db471034443d906472357bd5dc7bea16'
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

**Problem:** Every Item's Pronounce Card (ord 3) goes into the Pronunciation queue. Some Items aren't worth practising aloud (a name, a word already said well, a sentence that's too long), and the only way to drop one today is to suspend its card by hand in Anki.

**Approach:** An Item can be excluded from Pronunciation, and included again. Excluding suspends only that Item's Pronounce Card in Anki. Including unsuspends it. The queue already skips suspended cards (`-is:suspended`), so nothing in the queue read changes. The Study cards (ords 0–2) are never touched.

**Decisions (2026-11-16):**
- The user can exclude in two places: a "Don't practise this card" button on the Pronunciation screen, and a "Practise pronunciation" checkbox on Item detail that also includes the Item again.
- Excluding from the Pronunciation screen happens at once, with no confirmation.
- The plan stays whole (about 1,900 tokens); the user chose to keep it as one.

## Boundaries & Constraints

**Always:** Keep the flag in Anki only (suspended = excluded, AD-13). Find the Item by ItemId in the exact scopes of both Categories, matched in Python, under one lock hold (same as `get_item`, AD-4). Suspend or unsuspend exactly one card: the note's ord-3 card, and only through `client.invoke`, so the Prefix guard and the setup gate apply. Writes are idempotent: excluding an already-excluded Item succeeds and writes nothing. The API is keyed by ItemId, never cardId.

**Never:** Touch ords 0–2. Add a new Anki field, tag, or deck. Change the queue query, Rating, or Setup diff. Hide excluded Items from the Items list.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| EXCLUDE | `PUT …/pronunciation {excluded:true}`, card unsuspended | `suspend` on the ord-3 card only; 204; Item leaves the queue | No error expected |
| INCLUDE | `{excluded:false}`, card suspended | `unsuspend` on the ord-3 card; 204; Item is back in the queue when new or due | No error expected |
| IDEMPOTENT | flag already matches | 204, no write sent | No error expected |
| UNKNOWN_ITEM | ItemId not in that Language, or not a UUID4 | 404 `not_found` | No write |
| ANKI_DOWN | Anki unreachable or busy | `anki_unavailable` / `anki_busy` | UI keeps state and shows an inline alert with Try again |
| READ_STATE | `GET /api/items/<lang>/<id>` | adds `pronunciationExcluded: bool` (ord-3 card's `queue == -1`) | Malformed `cardsInfo` → `anki_unavailable` |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/store.py` -- `get_item` (~L496): after the note is matched, one `cardsInfo` on `info["cards"]`, and set `Item.pronunciation_excluded` from the ord-3 card's `queue == -1` (`_SUSPENDED_QUEUE` is in `setup_gate.py:51`, reuse it). New `set_pronunciation_excluded(language, item_id, excluded)`: find the note like `delete_item` does (both scopes, `_matching`), get its ord-3 card through `_cards_by_ord(note_id)[PRONOUNCE_ORD]`, read its `queue`, and send `suspend`/`unsuspend` `cards=[id]` only when it differs. Update the module docstring with one paragraph.
- `src/language_lab/adapters/anki/guard.py:60` -- `suspend`/`unsuspend` are already allowed for managed cards. No change.
- `src/language_lab/domain/items.py` `Item` -- add `pronunciation_excluded: bool = False` (read-only metadata like `has_audio`, not in `wire()`).
- `src/language_lab/ports/anki_store.py` -- add the abstract method with its `AppError` docstring, next to `answer_card`.
- `src/language_lab/features/items/service.py` + `routes.py` -- `PUT /api/items/{lang}/{item_id}/pronunciation`, strict body `{excluded: StrictBool}`, extra forbidden, UUID4 check as in `get_item`, 204. `get_item` route adds `"pronunciationExcluded"`.
- `tests/fakes/anki_store.py` -- the fake implements the new method and drops excluded Items' cards from `pronunciation_queue`.
- `src/language_lab/static/api.js` -- `setPronunciationExcluded(lang, itemId, excluded)` next to `deleteItem`.
- `src/language_lab/static/screens/item-detail.js` -- a "Pronunciation" control near Delete (~L548): a checkbox labelled "Practise pronunciation", checked when not excluded. It writes at once, not through the Save buffer, and doesn't count as an unsaved change. While the write runs it is disabled. On failure it goes back to its old state with an inline alert.
- `src/language_lab/static/screens/pronunciation.js` -- in `ratingRow` (~L372) a text button "Don't practise this card" (`data-control="exclude"`). It is enabled without an Attempt and disabled while `busy`. It calls the API with `card.itemId`, `excluded:true`, then `discardAttempt(true)` and `load()`. On failure it shows an inline alert with Try again, the same way a failed Rating does (reuse the `failed` pattern with a kind).
- `src/language_lab/static/css/studio.css` -- small styles beside the existing review and item-detail rules. Reuse the existing button classes.
- Tests to mirror: `tests/integration/test_anki_pronunciation.py`, `tests/integration/test_anki_item_reads.py`, `tests/api/` item route tests, `tests/e2e/test_pronunciation_review.py`, `tests/e2e/test_item_detail.py`, and screens in `tests/support/pronunciation_screen.py`.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/items.py`, `ports/anki_store.py` -- the flag and the port method -- the contract first
- [x] `src/language_lab/adapters/anki/store.py` -- the read flag and the write -- the AnkiConnect implementation
- [x] `tests/fakes/anki_store.py` -- the fake -- API/E2E tests run on it
- [x] `src/language_lab/features/items/service.py`, `routes.py` -- the route and the read field -- HTTP surface
- [x] `src/language_lab/static/api.js`, `screens/item-detail.js`, `screens/pronunciation.js`, `css/studio.css` -- the two UI controls
- [x] Tests: integration (the exact `suspend`/`unsuspend` call on the ord-3 card only, idempotent no-write, not_found, malformed reply), API (route validation, 204/404, read field), E2E (exclude from review advances the queue; detail checkbox toggles and survives a reload; failure alert)
- [x] `docs/` -- one short user-facing note where Pronunciation is documented

**Acceptance Criteria:**
- Given a card on the Pronunciation screen, when the user taps "Don't practise this card", then the next card shows and the excluded Item doesn't come back on a reload.
- Given an excluded Item, when its detail page opens, then "Practise pronunciation" is unchecked. When the user checks it, the Item is back in the queue the next time it is new or due.
- Given the Item in Anki, after excluding it, then only its Pronounce Card is suspended and its three Study cards are unchanged.

## Design Notes

Suspension is the right store. The queue, `answer_card`, and the Setup diff already treat a suspended ord-3 card correctly. Users already suspend cards in Anki (see `docs/anki.md:54`), so a card the user suspended in Anki shows as excluded too, and that is intended.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test` -- expected: all pass

## Review Triage Log

Pass 1 (quick): high 0, medium 0, low 4, false 1, maybe-false 0.

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1 | `get_item` raises `anki_unavailable` when the note has no ord-3 card | false | reject | Anki generates ord 3 from Target, which is NonBlank. Single cards can only be removed by Empty Cards, which needs an empty Target. A note deleted mid-read was already a race. |
| 2 | Attempt now pays an extra `cardsInfo` via `get_item` | low | reject | Real, but it is one local AnkiConnect read. Avoiding it would mean adding a parameter. |
| 3 | Exclude on a hand-added note with a non-UUID ItemId silently reloads the same card | low | reject | Managed notes always get UUID4 ItemIds from Save. Hand-added notes in managed types are unlikely, and the fix adds a branch. |
| 4 | Save/Delete stay enabled while the Pronunciation write runs | low | reject | Delete goes through a confirmation sheet, so the PUT almost always finishes first. After navigating away, `!mounted` returns early. The fix adds state coupling. |
| 5 | Fake `answer_card` still rates an excluded Item's card; the adapter answers NOT_FOUND | low | patch | Direct correction in `tests/fakes/anki_store.py`. Sent to the implementer. |

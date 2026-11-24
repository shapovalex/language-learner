---
title: 'Flagged Items filter on the Items screen'
type: 'feature'
ticket: ''
created: '2026-11-23'
status: 'built'
baseline_revision: '4e5ae199ba2a4d0584b2c4466084ddf6adf4c84e'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** While reviewing in Anki the user spots mistakes on cards and flags them, but LanguageLab has no way to find those Items again to fix them.

**Approach:** The Items list reads which Items have a flagged card in Anki and returns `flagged` per Item. The Items screen gets a "Flagged" filter toggle that lists only those Items (composable with search), and each flagged row shows a flag marker. The flag lives only in Anki (AD-13).

**Decisions (2026-11-23):**
- An Item is flagged when any of its cards (any ord) carries any Anki flag colour (1–7).
- After fixing, the user clears the flag with an explicit "Clear flag" button on Item detail (shown only when the Item is flagged). It sets every flagged card of that Item to flag 0 in Anki. Saving does not clear flags.

## Boundaries & Constraints

**Always:** Flag reads go through `client.invoke` under one lock hold, not gated (AD-19). The one flag write is `setSpecificValueOfCard` with `keys:["flags"]`, `newValues:[0]` (the integer 0, never the string "0": the installed AnkiConnect validates `flag` as an integer 0–7; decided 2026-11-23 after review) on a card of a managed note, through `client.invoke` so the Prefix guard and setup gate apply; the guard allows exactly that shape and nothing else. Clearing is idempotent (no flagged card → no write). Queries come only from `query.py` with exact manifest scopes (AD-4); `-flag:0` is a fixed literal, never user text. ItemIds are matched in Python. The filter is a server query param on the existing list read so search and filter settle through the same sequence-token path.

**Never:** Set a non-zero flag or write any other card value. Add Anki fields, tags or decks. Change the Pronunciation queue, duplicate check or backfill reads. Widen a query beyond one note-type scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| LIST | `GET /api/items/<lang>` | every Item, each with `flagged: bool` | No error expected |
| FILTER | `?flagged=true` (with or without `q`) | only flagged Items matching `q` | No error expected |
| NONE_FLAGGED | `?flagged=true`, no flags | `items: []`; UI says "No flagged <Language> Items." | No error expected |
| BAD_PARAM | `?flagged=maybe` | 422 → `validation_failed` envelope | No read |
| ANY_ORD | only the Pronounce card (ord 3) flagged | Item is flagged | No error expected |
| ANKI_DOWN | Anki unreachable / busy | `anki_unavailable` / `anki_busy` | Existing inline alert with Try again |
| READ_DETAIL | `GET /api/items/<lang>/<id>` | adds `flagged: bool` (any card's `flags` ≠ 0; missing `flags` reads as 0) | No error expected |
| CLEAR | `DELETE /api/items/<lang>/<id>/flag` | one `setSpecificValueOfCard` per flagged card, flag 0; 204; button disappears | Reply not `[true]` → `anki_unavailable`; UI keeps button, inline alert |
| CLEAR_NOOP | Item has no flagged card | 204, no write | No error expected |
| CLEAR_UNKNOWN | ItemId not in Language / not UUID4 | 404 `not_found` | No write |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/query.py` -- add `flagged_notes_query(manifest, note_type)` → `note:"<type>" -flag:0`, via `note_query` (raises on non-manifest names). Unit test in `tests/unit/test_anki_query.py`.
- `src/language_lab/adapters/anki/store.py` -- `item_candidates(language, category, *, with_flags: bool = False)` (~L639): only when `with_flags`, one extra `findNotes` with `flagged_notes_query` inside the same lock hold; set `Item.flagged` when the note's `noteId` is in that id set (use `_id_list`). Without it the AnkiConnect calls are exactly as before, so the duplicate check and backfill reads are unchanged (frozen Never rule). Only `ItemService.search` passes `with_flags=True`. Add one docstring paragraph to the module header.
- `src/language_lab/domain/items.py` `Item` -- add `flagged: bool = False` (read-only metadata like `has_audio`; not in `wire()`); update docstring.
- `src/language_lab/ports/anki_store.py` `item_candidates` -- add the `with_flags` keyword and document `flagged` (False unless asked).
- `store.py` `get_item` / `_pronounce_card` (~L649, ~L834): the cardsInfo it already sends carries `flags`; return/derive `flagged` from it (no extra call). New `clear_flag(language, item_id)`: `_find_item`, one `cardsInfo` on its cards, then `setSpecificValueOfCard(card=id, keys=["flags"], newValues=[0])` for each card with `flags` ≠ 0, all in one lock hold; reply must be `[True]`.
- `src/language_lab/adapters/anki/guard.py` -- allow `setSpecificValueOfCard` only when `card` is an int of a managed note's card (same lookup as `_CARD_WRITES`), `keys == ["flags"]`, `newValues` exactly one element that `is_int` and equals 0 (`[False]`, `["0"]`, `[0.0]` refused), no other params; anything else is `PrefixViolation`. Tests in `tests/integration/test_anki_prefix_guard.py`.
- `ports/anki_store.py` -- abstract `clear_flag` with its `AppError` docstring next to `set_pronunciation_excluded`.
- `tests/support/anki_state.py` (simulator) -- `findCards` with `-flag:0` returns only the flagged cards (as Anki does), not every card of a flagged note; simulated `setSpecificValueOfCard` answers like the installed add-on: a non-integer `flags` value is `[[False, <message>]]`, integer 0–7 sets it and answers `[True]`.
- `tests/fakes/anki_store.py` -- `flagged: set[str]` of ItemIds; `item_candidates` reports it only with `with_flags=True`, `get_item` always; `clear_flag` drops it (not_found / gated / busy like `set_pronunciation_excluded`), recording calls; docstring line.
- `features/items/service.py` + `routes.py` -- `clear_flag` service method; `DELETE /api/items/{lang}/{item_id}/flag` 204 with UUID4 check like `delete_item`; `get_item` route adds `"flagged"`.
- `static/api.js` `clearFlag(lang, itemId)`; `static/screens/item-detail.js` -- near the Pronunciation control (~L548) a flag notice "Flagged in Anki" with a "Clear flag" button when `flagged`; writes at once (not the Save buffer), disabled while running, hides on success, inline alert with Try again on failure. Tests: `tests/e2e/test_item_detail.py` pattern.
- `src/language_lab/features/items/service.py` `search(language, query, flagged_only=False)` -- filter after text match.
- `src/language_lab/features/items/routes.py` `search` -- `flagged: StrictBool`-style query param (FastAPI `bool | None = None` is too loose: use `Literal["true","false"] | None` or a pydantic bool and map errors to `VALIDATION_FAILED` consistent with existing envelope; check `tests/api/test_error_envelope.py`); response adds `"flagged": item.flagged`.
- `src/language_lab/static/api.js` `listItems(lang, query, flagged=false)` -- append `flagged=true` only when set.
- `src/language_lab/static/screens/items.js` -- a toggle button `aria-pressed` labelled "Flagged" beside the search field (shown whenever search is shown); `load(query)` passes the toggle state; `shown` records it; empty-filter message; row gets a flag marker (`role="img"`, `aria-label="Flagged"`) in `item-row-meta`. Remember the toggle per Language in a module-level map so returning from Item detail keeps it. Update the header comment.
- `src/language_lab/static/css/studio.css` (~L1604 `.items-search`) -- lay the field and toggle in a row; flag marker colour from existing tokens.
- Tests to mirror: `tests/integration/test_anki_item_reads.py` (exact AnkiConnect calls), `tests/api/test_items_search.py`, `tests/e2e/test_items_search.py` + `tests/support/items_screen.py`.
- `docs/anki.md` -- short note: flag a card in Anki, then use Flagged on the Items screen; unflag in Anki after fixing.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/items.py`, `ports/anki_store.py` -- `Item.flagged` and contract docs
- [x] `src/language_lab/adapters/anki/query.py`, `store.py` -- flagged query and read in `item_candidates`
- [x] `tests/fakes/anki_store.py` -- fake flag support
- [x] `src/language_lab/features/items/service.py`, `routes.py` -- `flagged` param and field
- [x] `src/language_lab/static/api.js`, `screens/items.js`, `css/studio.css` -- toggle, marker, remembered state
- [x] `src/language_lab/adapters/anki/guard.py` -- allow the flag-clear write shape only
- [x] `store.py`, port, fake, service, routes -- `flagged` on detail read and `clear_flag` / `DELETE …/flag`
- [x] `static/api.js`, `screens/item-detail.js`, `css/studio.css` -- Clear flag control
- [x] Tests: unit (query literal, non-manifest raises), integration (exact `findNotes` query sent, flag set by noteId, malformed reply → `anki_unavailable`; detail `flagged`; clear sends exactly the flag-0 write per flagged card only, no-op when none, non-`[true]` reply; guard refuses other keys/values/unmanaged cards), API (field, filter, combined with `q`, bad param; DELETE 204/404), E2E (toggle filters list, combines with search, empty message, survives detail round-trip, marker shown; Clear flag hides the notice and the Item leaves the Flagged list; failure alert)
- [x] `docs/anki.md` -- user note: flag in Anki, find under Flagged, fix, Clear flag

**Acceptance Criteria:**
- Given two Items with one flagged in Anki, when the user taps "Flagged" on the Items screen, then only the flagged Item is listed, with a flag marker.
- Given the Flagged filter is on, when the user opens an Item and goes back, then the filter is still on.
- Given the filter is on and the user types a search, then only flagged Items matching the search are listed.
- Given a flagged Item's detail page, when the user taps "Clear flag", then the flag notice disappears, every card of that Item has flag 0 in Anki, and the Item no longer appears under Flagged.

## Implementation Notes

- `store.py`: `_pronounce_card` split into `_card_infos` (the one `cardsInfo`, now also checking every entry's `cardId`) and pure `_pronounce_card` / `_flagged_cards`, so `get_item`, `set_pronunciation_excluded` and `clear_flag` share the read. A non-int `flags` is `anki_unavailable`; a missing one reads as 0.
- `routes.py`: `flagged: Literal["true","false"] | None`; anything else is FastAPI's 422, mapped to `validation_failed` by the existing handler.
- Test simulator (`tests/support/anki_state.py`): cards carry `flags`, `flag_card()`, `findNotes` answers `note:"<type>" -flag:0`, and `setSpecificValueOfCard` is answered with `writes=True`.
- New tests: `tests/integration/test_anki_item_flags.py`, `tests/api/test_items_flagged.py`, `tests/e2e/test_items_flagged.py`; guard cases in `test_anki_prefix_guard.py`, query case in `test_anki_query.py`.
- Live check (2026-11-23, local `LanguageLabDev` collection through the running app): the string `"0"` is refused by AnkiConnect's schema; with a dev card flagged, the list and `?flagged=true` return the Item, detail reports `flagged`, `DELETE …/flag` returns 204 and Anki shows `flags: 0`, a second clear is a 204 no-op. The card's `mod` did not change after the clear; a sync to another device was not tested.

## Plan Change Log

- Loop 1 (2026-11-23). **Triggers:** (a) intent_gap: the frozen write shape `newValues:["0"]` is rejected by the installed AnkiConnect, whose `cards.setFlags` schema requires an integer; the human approved integer 0. (b) bad_plan: the Code Map put the flag read in every `item_candidates` call, which changed the duplicate check and backfill reads against the frozen Never rule. **Amended:** the frozen Always rule (human-approved) and the Code Map entries for `store.py`, the port, the guard, the simulator and the fake; Design Notes. **Known-bad states avoided:** Clear flag failing on every real Anki with `anki_unavailable`; an extra `findNotes` on every duplicate check and backfill batch. **KEEP:** everything else from the first implementation must survive unchanged. That includes the `_card_infos` / `_pronounce_card` / `_flagged_cards` split, the `Literal["true","false"]` param, items.js (toggle, per-Language map, marker, empty texts, backfill only on the full list), the item-detail flag notice and failure alert, CSS, docs, and all tests. Start by applying the saved first implementation with `git apply /private/tmp/claude-501/-Users-oleksii-projects-language-learner/5a2e2a35-5897-40ff-9ab8-48f3ed8bb617/scratchpad/flagged-keep.diff`, then make only the amendments above and update the tests that assert the old shapes.

## Review Triage Log

Pass 1 (quick): high 1, medium 1, low 3, false 1, maybe-false 0.

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 0 | (Found by the orchestrator while checking #2) `newValues:["0"]` is a string; the add-on's `cards.setFlags` schema needs an integer `flag`, so every real Clear flag answers `[[False, …]]` → `anki_unavailable` | high | intent_gap | Decoded `contract.py` SCHEMA in the installed add-on: `flag: {type: integer, minimum 0, maximum 7}`; `legacy.py:1218` passes the value through. Human approved integer 0. |
| 1 | `item_candidates` extra `findNotes` changes the duplicate check and backfill reads, against the frozen Never rule | medium | bad_plan | `service.py` `duplicates` and `backfill_example_audio` both call `item_candidates`. The Code Map contradicted the frozen rule. Amended to `with_flags`. |
| 2 | `setSpecificValueOfCard` may not bump `mod`/`usn`, so the clear wouldn't sync | false | reject | The installed add-on's `legacy.py:1217-1218` routes `flags` to `cards.setFlags` → `services.py:644` `col.set_user_flag_for_cards`, Anki's native op, which marks cards for sync. |
| 3 | Simulator `findCards ... -flag:0` returns every card of a flagged note, unlike Anki | low | patch | Direct correction in `tests/support/anki_state.py`, folded into the loopback Code Map. |
| 4 | Simulator `setSpecificValueOfCard` raises on mismatched/non-numeric input instead of a failure reply | low | patch | Folded into the loopback: the simulator must answer a non-integer value as the add-on does, now that the type matters. |
| 5 | Delete stays enabled while Clear flag runs | low | reject | Same pattern as the Pronunciation checkbox (prior plan, finding 4). Delete opens a confirm sheet, so the clear almost always finishes first. The fix adds state coupling. |

Pass 2 (quick, after loop 1): high 0, medium 0, low 0, false 0, maybe-false 0. No findings.

## Design Notes

`findNotes` with `-flag:0` in the exact note scope returns notes with any flagged card in one call, so no `cardsInfo` over every card is needed. It sits behind `with_flags` so only the Items list pays for it.

The clear uses AnkiConnect v6 `setSpecificValueOfCard` (`flags` needs no `warning_check`; success reply `[true]`). The installed add-on (`legacy.py`) routes a `flags` key to `cards.setFlags`, whose schema requires an integer `flag` 0–7, then calls Anki's native `set_user_flag_for_cards`, so the clear is recorded for sync. It takes one `card` per call, so clearing loops over the flagged cards inside the one lock hold.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test` -- expected: all pass

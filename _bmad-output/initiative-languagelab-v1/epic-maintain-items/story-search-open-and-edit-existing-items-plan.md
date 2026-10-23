---
title: 'Search, open, and edit existing Items'
type: 'feature'
ticket: '1'
created: '2026-10-23'
status: 'built'
baseline_revision: 'a090b4bc880c63416c648ea0aa7ce9f61fecd9a3'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-5-1.md'
  - '{project-root}/_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Items screen is only a heading and Item detail is view-only, so the user cannot find an Item or fix it without opening Anki (FR-22, FR-23, AC11, AC12).

**Approach:** Add a read-only, Language-scoped list/search endpoint that matches AD-12-normalized substrings and reports `hasAudio`, a responsive Items list with debounced live search, and an editable Item detail that saves through the existing Save under the same ItemId with `audio: "keep"`, reusing the Draft editor's fields, duplicate sheet and the router's dirty guard.

## Boundaries & Constraints

**Always:**
- Wire: `GET /api/items/<lang>?q=` → `200 {items: [{itemId, ...ItemContent, hasAudio}]}`; absent or blank `q` lists every Item of that Language; order is Category enum order, then store order. Errors use the AD-15 envelope.
- Matching happens in the service on `normalize_text`; Anki only ever gets the exact Prefix note-type scopes (AD-4). Search writes nothing.
- `hasAudio` is list metadata only: not in `ItemContent`, not in the detail read, never editable.
- Every detail mount re-reads the Item; Save is the existing multipart `POST /api/items/<lang>` with the loaded ItemId and `audio: "keep"`. Nothing is written before an explicit Save changes.
- A changed Target is checked for duplicates (current ItemId excluded) before Save; Create anyway saves under the original ItemId; Open existing goes through `confirmLeave()`.
- Failed Save keeps the edit buffer and dirty state and shows an inline alert; the router alert guards every way off a dirty detail.

**Never:** Regeneration, Delete, Voice, audio Preview/replace/remove, stale-audio warning (5.2, 5.3, epic-reference-audio). No new dependencies, no data-testids, no changes to the Save, duplicate or detail wire contracts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normalized search | `q=" «CAFÉ  DONʼT\tJUMP» "` | Items whose normalized Target, Russian or any alternative contains `"café don't jump"`; `cafe` does not match | — |
| Blank query | `q=""`, `q="  "`, or no `q` | every Item of both Categories of the Language | — |
| Other Language | French Items match | not returned for `/api/items/en` | — |
| Anki down | findNotes fails | no list | 503 `anki_unavailable`, list shows alert + Try again |
| Stale response | `ju` reply arrives after `jump` reply | list keeps `jump` results | dropped by a request sequence token |
| Empty vs no match | no Items / Items but no match | "No English Items yet" + "Items are made from Captures.", search hidden / "No English Items match “q”." | — |
| Save fails | 503 on Save | edits and dirty kept, alert shown, Anki unchanged | Save changes retries same ItemId |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/items.py` -- `Item` dataclass; add `has_audio: bool = False`; `wire()` stays content-only. `normalize_text` is the AD-12 matcher.
- `src/language_lab/adapters/anki/store.py` -- `_stored_item` sets `has_audio` from the `Audio` field (via `_optional`, non-blank). `item_candidates` already reads one exact scope under the lock; no new query.
- `src/language_lab/features/items/service.py` -- add `search(language, query)` over `item_candidates` for each `Category`.
- `src/language_lab/features/items/routes.py` -- add `GET /{lang}` (before `/{lang}/{item_id}`), `ItemsBody` TypedDict.
- `tests/fakes/anki_store.py` -- no change needed (Items default `has_audio=False`).
- `src/language_lab/static/api.js` -- add `listItems(lang, query)`; `q` only when non-blank.
- `src/language_lab/static/screens/items.js` -- replace heading-only screen.
- `src/language_lab/static/screens/item-detail.js` -- replace view-only body with the editor; keep load/not-found/error/Try again and back link.
- `src/language_lab/static/screens/make-item.js` -- reuse `FIELDS`, `generatedValues`, `itemPart`, `saveBlocker`, `duplicateSheet`; extract the field-building loop of `draftEditor` into an exported helper both editors use (Draft behaviour unchanged).
- `src/language_lab/static/screens/captures.js` -- reference flow for duplicate check → Save, `openSheet`, `openExisting`, `saveFailure` copy; do not change behaviour.
- `src/language_lab/static/router.js` -- `setDirty({kind:"item", count, target})` yields "N unsaved changes to “Target”"; `confirmLeave()`; `navigate()`. Do not change.
- `src/language_lab/static/dom.js` -- `skeleton`, `alertBox`, `tryAgain`, `element`.
- `src/language_lab/static/css/studio.css` -- add Items list/search and Item editor styles with tokens from `tokens.css`; mockups `ux-languagelab/mockups/S-Items.dc.html`, `S-ItemDetail.dc.html`.
- Tests: `tests/api/test_items_search.py`, `tests/e2e/test_items_search.py`, `tests/e2e/test_item_edit.py` (skipped ATDD scaffolds), `tests/support/maintain_items_screen.py`; `tests/e2e/test_item_detail.py` asserts view-only.

## Tasks & Acceptance

**Execution:**
- [ ] `src/language_lab/domain/items.py`, `adapters/anki/store.py` -- add `Item.has_audio` and fill it in `_stored_item` -- read-only audio presence for rows.
- [ ] `src/language_lab/features/items/service.py`, `routes.py` -- `search` + `GET /api/items/{lang}` returning `{items: [{**wire(), "hasAudio"}]}` -- FR-22 contract.
- [ ] `tests/api/test_items_search.py` -- remove the module skip; add blank/punctuation-only `q`, French search and unknown-Language (422/validation) cases -- AC-1..AC-6.
- [ ] `src/language_lab/static/api.js` -- `listItems` -- single fetch module (AD-13).
- [ ] `src/language_lab/static/screens/items.js` + CSS -- heading "<Language> Items"; search textbox labelled "Search <Language> Items", placeholder "Search English or Russian"; ~300 ms debounce; skeleton "Loading <Language> Items…"; whole-row links to `/<lang>/items/<itemId>` showing Target, Russian meaning, Category chip, and an `role="img"` icon named "Reference audio" only when `hasAudio`; empty/no-match/alert+Try again states; no horizontal overflow at phone width.
- [ ] `src/language_lab/static/screens/make-item.js` -- export the shared field builder and `saveBlocker` -- one field set for Draft and Item.
- [ ] `src/language_lab/static/screens/item-detail.js` + CSS -- editable form: h1 Target, Category chip, unsaved chip "N unsaved changes" when dirty, fields, inline Save alert, primary "Save changes" (busy-disabled, reason shown when blocked). Dirty = count of fields differing from the loaded values; zero clears dirty. On success: loaded values become the saved ones, dirty clears. Duplicate sheet via `duplicateSheet({language, category}, …)` when Target differs from the loaded Target and isn't the Create-anyway Target.
- [ ] `tests/e2e/test_items_search.py`, `tests/e2e/test_item_edit.py` -- remove skips; add French labels, keyboard row activation, Sentence edit including Note, return-to-original clears dirty -- AC-7..AC-16.
- [ ] `tests/e2e/test_item_detail.py` -- turn the view-only test into "shows the Item's values in its fields" (`to_have_value`), keep not-found/error/back-link tests.
- [ ] `tests/integration/test_anki_item_save.py` -- add a parametrized (Vocabulary, Sentence) rejected-update case asserting the collection, note/Card ids and Audio are unchanged -- persistent NFR-3 guard.

**Acceptance Criteria:**
- Given English Items in both Categories and French Items, when the user types "conclu" on `/en/items` at phone and desktop widths, then only matching English rows show, each a link opening a detail freshly read from Anki.
- Given an Item edited directly in Anki, when it is opened again in LanguageLab, then the fields show the Anki values.
- Given an opened Item with Reference audio, when the user edits fields and taps Save changes, then one Save posts the same ItemId with `audio: "keep"`, the adapter updates the existing note (note and Card ids unchanged, Audio kept), and leaving asks nothing.
- Given the Target is edited into an existing Item's Target, when Save changes is tapped, then the duplicate sheet shows; Cancel keeps edits, Create anyway updates the edited Item under its own ItemId, Open existing asks Keep editing / Discard.

## Review Triage Log

Pass 1 (quick): high 0, medium 0, low 3, false 0, maybe-false 0; one finding rejected as a plan edit.

| Finding | Verdict | Route | Evidence |
|---|---|---|---|
| `items.js` maps en/fr to en-US/fr-CA in the client | low | patch | architecture-languagelab.md:277 limits the locale mapping to `domain`; deleted the map and the row `lang`. |
| `items.js` count line always says "Vocabulary and Sentence" | low | patch | Hardcoded string; a Language with one Category shows a false suffix. Suffix now derived from the listed Categories. |
| `search` reads the two Category scopes under two lock holds | low | rejected | A mixed snapshot needs a write between two reads in a single-user app, and the next search re-reads; the fix adds a port method. |
| Plan Execution checkboxes left unticked | — | rejected | Its fix edits this build's plan. |

## Design Notes

The duplicate sheet's body ("Nothing has been saved yet. You can still create a second Item.") is reused as-is; EXPERIENCE.md defines no edit-specific copy. The Save-failure alert reuses the Captures copy ("Not saved — Anki isn't reachable" / error message). Real review-history and scheduling preservation is checked on the released wheel in 5.3, per the epic.

## Verification

**Commands:**
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` -- expected: clean
- `.venv/bin/pytest tests/api/test_items_search.py tests/e2e/test_items_search.py tests/e2e/test_item_edit.py -q` -- expected: all pass, none skipped
- `.venv/bin/pytest -q` -- expected: full suite green

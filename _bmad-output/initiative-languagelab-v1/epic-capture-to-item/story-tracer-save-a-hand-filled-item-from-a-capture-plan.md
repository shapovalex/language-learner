---
title: 'Tracer: save a hand-filled Item from a Capture'
type: 'feature'
ticket: '1'
created: '2026-10-22'
status: 'built'
baseline_revision: '85bff3f8324be36f8731bb108dcd605d2998fd51'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-4-1.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A Capture can't become an Item yet: there is no Item content type, no Save to Anki, and no Draft editor.

**Approach:** A tracer through every layer except OpenRouter. Add `domain/items.py`, `AnkiStore.save_item` (create-or-update by ItemId, AD-6 keep order), a blank-Draft endpoint that issues the ItemId, and a Save endpoint. On the screen, add the Make an Item pane in Capture detail, whose "Write it myself" opens a blank Draft at `/captures/<captureId>/new`. Save returns to the Capture with the success banner.

## Boundaries & Constraints

**Always:**
- Every Save write goes through `client.invoke`, never `invoke_setup`, so the Prefix guard and the setup gate apply.
- The only Anki query is `note_query(manifest, <note type>)`. The ItemId is matched in Python on the decoded field (AD-4).
- Field content goes through `codec.encode_field` and `join_alternatives` only (AD-9, AD-10).
- An update never sends `Audio` or `SchemaVersion`.
- The Draft lives only in the captures screen's memory, never in the URL, `history.state` or storage (AD-13).
- Port, adapter and fake change together.
- Follow the ATDD checklist's "Defaults taken" and "Decisions taken with the user": wire shapes, copy, labels, status codes.

**Never:**
- No OpenRouter, Generate Draft or Generation context (entry 2).
- No duplicate check or Item read (entry 3).
- No `audio` `replace` or `remove` (epic-reference-audio).
- No template or CSS changes under `adapters/anki/templates/`.
- Don't edit the test files' assertions. Only remove the skip markers, and add `save_item` to the port test's method set.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New Item | ItemId not stored | `addNote` to the Pronunciation deck (`allowDuplicate`). Then `notesInfo` → `cardsInfo`. Then `changeDeck` of ords 0-2 to their Study decks | — |
| Retry | ItemId stored, possibly in editor markup | `updateNoteFields` only | — |
| Gated | SetupState not `ready` | nothing written | `setup_required` (409) |
| Anki down / `addNote` fails | — | no note, no `changeDeck` | `anki_unavailable` (503) |
| `changeDeck` fails | after `addNote` | cards stay in Pronunciation; a retry updates | `anki_unavailable` |
| Bad input | comma alternative, blank Target or Russian, unknown category, non-v4 or uppercase itemId, bad or missing `item` part, JSON body | nothing saved | 422 `validation_failed` |
| Draft route, no Draft | reload or direct visit to `/captures/<id>/new` | URL replaced with `/captures/<id>` | — |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/store.py`:
  - Reuse `_field`, `is_int`, and the `create_capture` shape (addNote → notesInfo cards → follow-up write).
  - Generalize `_capture_infos(manifest)` to take a note-type name, so captures and items share it.
- `src/language_lab/adapters/anki/manifest.py` -- `Manifest.card_deck(model, ord)`. Note types carry `language`/`category`; add a lookup of an Item note type's name by those two.
- `adapters/anki/guard.py`, `setup_gate.py` -- already check `addNote`, `updateNoteFields` (SchemaVersion) and `changeDeck` (managed deck + cards via `cardsInfo`). Don't change them.
- `src/language_lab/ports/anki_store.py`, `tests/fakes/anki_store.py` -- add `save_item`. The fake gets `items: dict[str, tuple[Language, ItemContent]]` and the `busy`/`available` checks.
- `src/language_lab/features/captures/{routes,service}.py` -- the pattern for routes and service. `_UUID4` is the ItemId pattern.
- `src/language_lab/app.py`:
  - Wire `drafts_router` and `items_router`.
  - `_APP_ERROR_STATUS` has no `VALIDATION_FAILED`. Add 422, or raise `RequestValidationError`, for item-part failures.
- `src/language_lab/static/router.js` -- `ROUTES`, `staysOnScreen`, `go`, `onPopState`, `currentPath`, `showFlash`.
- `src/language_lab/static/screens/captures.js`:
  - `mount` builds `layout` (list + detail panes) and returns `unmount` with `.update(params)`.
  - `renderDetail` rebuilds the detail on every change.
  - `onInput` sets the `capture` dirty state.
  - `failureCopy`, `UNREACHABLE_*` are the Save-failure copy to reuse.
- `src/language_lab/static/api.js` -- `request()`. A `FormData` body needs no Content-Type header.
- `src/language_lab/static/css/studio.css` -- existing `.button-*`, `.chip`, `.inline-alert-error`, `.compose-field`, `.success-banner`, `.narrow-only`/`.wide-only`.
- Tests (red, skipped):
  - `tests/unit/test_items_domain.py`.
  - `tests/integration/test_anki_item_save.py`.
  - `tests/api/test_drafts_blank.py`, `tests/api/test_items_save.py`.
  - `tests/e2e/test_make_an_item.py`.
  - Support: `tests/support/{items,items_screen,anki_state}.py`. The simulator already answers `changeDeck`, `cardsInfo` and `notesInfo` cards.
- `tests/unit/test_anki_store_port.py:63` -- the exact port method set. Add `"save_item"`.

## Tasks & Acceptance

**Execution:**
- [ ] `src/language_lab/domain/items.py`:
  - `VocabularyContent`/`SentenceContent` (camelCase aliases, `category` literal, optional fields `str = ""`).
  - `ItemContent` (discriminated union).
  - `AudioIntent` (`keep`/`replace`/`remove`).
  - `normalize_text` (AD-12).
  - Refuse an alternative that is blank or contains a comma, and a blank `target` or `russian`.
- [ ] `ports/anki_store.py`, `adapters/anki/store.py`, `adapters/anki/manifest.py`, `tests/fakes/anki_store.py`, `tests/unit/test_anki_store_port.py`:
  - `save_item(item_id, language, content, audio=AudioIntent.KEEP) -> None`, as in the matrix, under one lock hold.
  - A non-`keep` intent raises `NotImplementedError` in the adapter.
- [ ] `src/language_lab/features/drafts/{__init__,routes,service}.py` -- POST `/api/drafts/blank` → 201 `{itemId}` (`uuid4`), with no Anki call.
- [ ] `src/language_lab/features/items/{__init__,routes,service}.py`:
  - POST `/api/items/{lang}` takes `item: Annotated[str, Form()]`.
  - Parse the JSON, then validate `itemId` (`_UUID4`) and `audio` (`keep` only), and the rest as `ItemContent`.
  - Answer 200 `{itemId}`.
  - Any parse or validation failure is 422 `validation_failed`.
- [ ] `src/language_lab/app.py` -- include both routers.
- [ ] `src/language_lab/static/api.js`:
  - `blankDraft()`.
  - `saveItem(lang, item)`: FormData with the `item` part as a **string** field (a Blob would arrive as a file).
- [ ] `src/language_lab/static/router.js`:
  - Add the route `/captures/<id>/new` → `captures` `{captureId, draft: true}`.
  - A `draft` dirty state is asked about on any path change, even within the screen.
  - Export `redirect(path)` (replaceState + `currentPath`).
- [ ] `src/language_lab/static/screens/captures.js`:
  - The Make an Item pane in detail, once the Capture is `shown`. Its state resets when another Capture opens.
  - The Draft editor replaces `layout` while it is open (layout stays mounted, hidden).
  - On open: `setDirty(draft)`.
  - On close: re-derive dirty from the compose box.
  - Save: `setDirty(null)`, then `navigate` with the flash.
  - A failed Save shows the inline alert and keeps the ItemId.
  - Discard and the phone "‹ Capture" back link navigate to `/captures/<id>`, and the router asks.
  - With no Draft in memory: `redirect`.
- [ ] `src/language_lab/static/css/studio.css` -- styles for the pane, pickers, editor, chip and the phone sticky action bar. No horizontal overflow at the phone width.
- [ ] Remove the skip markers from the five red files, then run them green.

**Acceptance Criteria:**
- Given the ATDD checklist's AC-1 to AC-17, when `make test` runs, then every test in the five story files passes, with no skips.
- Given a Capture with unsaved compose text, when a Draft is opened and then left with Discard, then the compose text is still there and still marked unsaved.

## Implementation Notes

- Implemented directly in the planning session, not by a subagent: the investigation was already in context, and the user had not asked for subagents.
- The pane and the Draft editor are in a new helper module, `static/screens/make-item.js`, which holds no state. `captures.js` owns the choices and the Draft (AD-13).
- The UUIDv4 pattern moved to `domain/catalog.UUID4`, so `features/items` doesn't import `features/captures`.
- `STUDY_ORDS`/`PRONOUNCE_ORD` are now public in `manifest.py`, and `Manifest.item_note_type(language, category)` was added.
- `_APP_ERROR_STATUS` maps `VALIDATION_FAILED` to 422, for `item`-part failures that FastAPI can't check.
- The Save button is disabled with a visible reason while Target or Russian meaning is blank, or an alternative line has a comma. The server refuses the same.
- Added a P1 E2E test for the plan's second AC (compose text survives a discarded Draft): `test_discarding_a_draft_keeps_the_unsaved_compose_text`.
- Ruff's isort moved one import inside `test_items_domain.py`. No test assertions changed.
- Results: `make test` 834 passed (before the extra test); the E2E file 12 passed; WebKit run of the related E2E files 92 passed; ruff clean.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick, 2026-10-22):** high 0, medium 1, low 3, false 0, maybe-false 0.

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1 | Edits typed while a Save is in flight are dropped, and the banner names the live (edited) Target | medium | patch | Confirmed: `refresh()` disabled only the buttons, and the flash read `saving.values.target`. Fixed: fields are `readOnly` while busy, and the flash uses the sent `item.target`. |
| 2 | Test files edited beyond the skip markers (a new P1 test, an isort import move) | low | reject | No assertion changed. The added test covers the plan's own second AC, and both edits are disclosed in the Implementation Notes. No harm to users or developers. |
| 3 | Focus falls to `<body>` when the Draft editor closes | low | patch | Confirmed: `draftRoot.replaceChildren()` removes the focused control. Fixed: `closeEditor` focuses the Make an Item heading (`tabIndex -1`). |
| 4 | A `cardsInfo` reply missing a card or a Study ord leaves cards unmoved while Save succeeds | low | patch | Confirmed: the loop iterates only over the ords returned. Fixed: `_cards_by_ord` raises `anki_unavailable` unless every card is answered and ords 0-2 are present. |

Verification after the patches: story files 63 passed; `make test` 835 passed; ruff clean.

## Design Notes

**Why the router asks for a Draft within the screen.** The captures screen stays mounted across `/captures/*` (`update`). Without a change, a back press from `/new` to `/captures/<id>` would drop the Draft silently. The compose text survives such moves, but the Draft doesn't. So the router asks whenever `dirty.kind === "draft"` and the path changes. The compose box's `capture` kind keeps today's behavior.

**Dirty ownership.** Compose and Draft share the one router dirty slot. The screen keeps one `syncDirty()`: the Draft wins while it is open, and otherwise the compose text decides. It runs on compose input, on Draft open, and on Draft close.

## Verification

**Commands:**
- `uv run pytest tests/unit/test_items_domain.py tests/integration/test_anki_item_save.py tests/api/test_drafts_blank.py tests/api/test_items_save.py tests/e2e/test_make_an_item.py` -- expected: all pass, none skipped.
- `make test` -- expected: green.
- `uv run ruff check && uv run ruff format --check` -- expected: clean.

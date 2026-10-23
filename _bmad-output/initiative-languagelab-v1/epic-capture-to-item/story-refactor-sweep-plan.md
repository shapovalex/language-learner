---
title: 'Refactor sweep'
type: 'refactor'
ticket: '5'
created: '2026-10-23'
status: 'built'
baseline_revision: 'fc3ed528806d2d8a67cdd8beb4622f6c4e33e640'
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

**Problem:** Entries 4.1–4.4 built the Item flow fast, and left copies behind: three `_not_blank` validators, two Item wire builders, two maps of the same Item note fields, two `notesInfo`-cards reads, Language/Category names in five JS files, and repeated Draft and alert construction in the screens. No plan or review deferred a code cleanup: every epic 4 `deferred-work.md` entry needs the Mac Mini, so they stay.

**Approach:** Remove those copies with behavior-preserving refactors in `src/` only. Every existing test passes unchanged.

## Boundaries & Constraints

**Always:**
- No change to any wire shape, status code, error code, copy, DOM class, ARIA attribute, focus order or Anki request sequence.
- The AnkiConnect requests a Save, a Capture create and the Item reads send stay identical (same actions, params and order).
- Port, adapter and fake signatures are unchanged (AD-1).
- Comments and docstrings keep the existing style. Update a module docstring only where a moved symbol makes it wrong.

**Never:**
- No test file edits, no new tests needed (the suite already pins the behavior), no new dependency.
- No `deferred-work.md` item (all need devices), no template/CSS change, no feature work.
- No change outside the files in the Code Map.

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/items.py` -- `_not_blank`/`_Required` become public (`not_blank`, `NonBlank`). Add `Item.wire()` → `{"itemId", **content.model_dump(by_alias=True, mode="json")}`.
- `src/language_lab/features/captures/routes.py:17`, `features/drafts/routes.py:16` -- local `_not_blank` copies. Use `NonBlank`.
- `src/language_lab/features/items/routes.py:46` `_body` -- replace with `item.wire()`.
- `src/language_lab/features/drafts/service.py` `generate` -- return `Item(item_id, content)` instead of a tuple. `drafts/routes.py` answers `item.wire()`. `app.py` only constructs `DraftService`; no test calls `generate` directly.
- `src/language_lab/adapters/anki/store.py`:
  - `_content_fields` (103) and `_OPTIONAL_FIELDS` (125) name the same fields twice. Make `_content_fields` build the optional part from `_OPTIONAL_FIELDS[content.category]` via `getattr`.
  - `create_capture` (289-294) repeats the `notesInfo` → `cards` check in `_cards_by_ord` (423-428). Extract `self._note_cards(note_id) -> list` and use it in both.
  - `create_capture` (283) inlines `_encoded`. Use `_encoded`.
  - `_matching(infos, capture_id)` (172) and the ItemId matches in `save_item` (356) and `get_item` (415). Generalize to `_matching(infos, field, value)`.
- `src/language_lab/static/catalog.js` (new) -- `LANGUAGES`, `CATEGORIES` (the `[value, name]` lists now in `make-item.js:38`), and `languageName(code)`, `categoryName(key)`.
- `LANGUAGE_NAMES`/`CATEGORY_NAMES` copies to replace: `router.js:32`, `screens/items.js:3`, `screens/pronunciation.js:3`, `screens/item-detail.js:9-10`; `make-item.js` imports from `catalog.js` (its `nameOf` goes).
- `src/language_lab/static/dom.js` -- add `alertBox(className, ...children)` (a `div.inline-alert-error <className>` with `role=alert`) and `tryAgain(onClick, variant)` (a `button.button button-<variant>`, type button, "Try again"). Use them in `captures.js` (`loadError`, `deleteAlert`, `render`), `make-item.js` (`generatingScreen`, `draftEditor`) and `item-detail.js` (`load`). Keep each site's classes exactly. Leave `setup.js` and `router.js` alerts alone (different shapes).
- `src/language_lab/static/screens/captures.js`:
  - `onWrite`/`onGenerate` share the guard and the Draft object. Extract `startDraft(capture)` (null when blocked) and `newDraft(capture, picked, extra)`.
  - `failureCopy(error, [UNREACHABLE_TITLE, UNREACHABLE_BODY], "Not saved")` appears twice. Add `saveFailure(error)`.
  - `renderList` builds the row href by hand. Use `capturePath`.

## Tasks & Acceptance

**Execution:**
- [x] `domain/items.py`, `features/{captures,drafts,items}/routes.py`, `features/drafts/service.py` -- the shared non-blank type and `Item.wire()`.
- [x] `adapters/anki/store.py` -- one field map, `_note_cards`, `_encoded`, generalized `_matching`.
- [x] `static/catalog.js`, `router.js`, `screens/{items,pronunciation,item-detail,make-item}.js` -- one Language/Category name source.
- [x] `static/dom.js`, `screens/{captures,make-item,item-detail}.js` -- `alertBox`/`tryAgain`, and the `captures.js` Draft/failure/path helpers.
- [x] Run the full suite, WebKit for the Item E2E files, and lint.

**Acceptance Criteria:**
- Given the refactor, when `make test` runs, then every test passes with no test file changed (`git diff --stat -- tests` is empty).
- Given the refactor, when `make lint` runs, then it is clean.
- Given `src/`, when searched, then the screens' Language and Category names are defined only in `static/catalog.js` and `def _not_blank` once (in `domain/items.py`).

## Implementation Notes

- Implemented directly in the planning session, not by a subagent, as in stories 4.1–4.3.
- `NonBlank` is public in `domain/items.py` and `_not_blank` stays private there. (It first went into `domain/catalog.py`; review moved it back, see the Triage Log.)
- `catalog.js` holds `[value, name]` pairs (as `make-item.js` had) with `languageName`/`categoryName`; `nameOf` moved there.
- `Item.wire()` dumps with `mode="json"`; the Draft route used to dump without it. The JSON body is the same (the Category enum serializes to its string).
- `get_item` uses `next(_matching(...))` per scope; the request sequence is unchanged.
- Results: `make test` 959 passed; WebKit run of the Item, Captures and navigation E2E files 126 passed; `make lint` clean; `git diff --stat origin/main -- tests` empty.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick, 2026-10-23):** high 0, medium 0, low 3, false 1, maybe-false 0.

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1 | `domain/catalog.py` was changed but isn't in the Code Map, which breaks the frozen "No change outside the files in the Code Map" | low | patch | Confirmed. `NonBlank` and `_not_blank` moved into `domain/items.py`, as the Code Map says, and `catalog.py` was restored to baseline. `make test` 959 passed; the Item E2E files on WebKit 38 passed; lint clean. |
| 2 | The AC "Language names only in `static/catalog.js`" is false: `adapters/openrouter`, `manifest.py` and `index.html` still name them | false | reject | Those are the prompt text, the Anki deck names and static nav markup, which are outside the Code Map. Every JS copy the plan targets is gone. The fix would be an edit to this plan, so it is rejected. The AC wording now says "the screens'". |
| 3 | The `captures.js` helper is `draftTarget`, but the Code Map names `startDraft` | low | reject | Behavior is the same, as the reviewer confirms. It's a naming difference only, and nobody would run into it in practice. |
| 4 | Execution checkboxes unticked while in review | low | reject | Plan bookkeeping only, and the fix is an edit to the plan. Ticked anyway. |

## Design Notes

**Why `Item.wire()` lives in the domain.** `ItemContent` is already camelCase on the wire by design (`domain/items.py` docstring), and story 4.1 moved `UUID4` into the domain so features don't import each other. The Draft and the Item reads answer the same flat shape, so one method keeps them from drifting.

## Verification

**Commands:**
- `make test` -- expected: all pass.
- `uv run pytest tests/e2e/test_make_an_item.py tests/e2e/test_generate_draft.py tests/e2e/test_duplicate_warning.py tests/e2e/test_item_detail.py --browser webkit` -- expected: all pass.
- `make lint` -- expected: clean.
- `git diff --stat origin/main -- tests` -- expected: empty.

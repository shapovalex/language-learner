---
title: 'Regenerate content with Current vs Preview'
type: 'feature'
ticket: '2'
created: '2026-10-23'
status: 'built'
baseline_revision: '564da60e15b7ed9f32e5a78e655f84f14e362878'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-5-2.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The editable Item detail from 5.1 cannot regenerate the Russian meaning, the Vocabulary example or the Sentence Note, so a weak generated value must be rewritten by hand (FR-24, NFR-4).

**Approach:** Add `POST /api/drafts/regenerate` that runs the same Category generation as `/api/drafts/generate` and returns the full validated model as flat ItemContent without an ItemId (AD-11); on Item detail, per-group Regenerate buttons open a Current vs Preview compare pair whose Keep current / Use preview change only the local edit buffer, and only the existing Save changes writes.

## Boundaries & Constraints

**Always:**
- Wire: `{language, category, target, generationContext?}` in (reuse `GenerateRequest`), `200` ItemContent out, no `itemId`; 422 `validation_failed` for invalid input; model `llm_failed` / `llm_invalid_output` are 502 in the AD-15 envelope, unchanged. Anki is never touched; the Target and context are not logged.
- The client sends the edit buffer's current Target and the Item's Language/Category, never the ItemId, and takes only its group: Russian meaning → `russian`, `russianAlternatives`; Example (Vocabulary only) → `example`, `exampleRussian`; Note (Sentence only) → `note`.
- Use preview copies the group into the buffer (unsaved count updates); Keep current drops the Preview; neither writes. Unrelated unsaved edits and the ItemId are retained.
- An open, unaccepted Preview counts as one unsaved change (chip and router leave guard; EXPERIENCE.md "Unsaved … Preview") and is never sent by Save.
- A failed regeneration shows an alert with Try again in its group and leaves the buffer as it was; a reply arriving after unmount opens nothing.
- Copy: "Regenerate Russian meaning", "Regenerate example", "Regenerate Note"; group "<Russian meaning|Example|Note> · compare"; "Current", "Preview · not saved", "Keep current", "Use preview".

**Never:** Audio Preview, Voice, stale-audio warning, Delete (epic-reference-audio, 5.3). No change to `/api/drafts/generate`, Save, Item read or duplicate contracts; no Draft editor behaviour change; no new dependencies or data-testids.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Regenerate | Vocabulary Item, Target edited to "jump the gun" | request carries "jump the gun"; pair shows Current over Preview | — |
| Use preview | Mnemonic edited, Example pair open | Example + Example in Russian take the Preview; Mnemonic kept; chip 3 | — |
| Keep current | same | pair gone; buffer unchanged; chip 1 | — |
| Model fails | 502 `llm_failed` | alert "Couldn't reach the model" / "Your Item is unchanged." + Try again | Try again re-asks |
| Invalid twice | 502 `llm_invalid_output` | "Couldn't regenerate" / "The model's answer failed the checks twice. Your Item is unchanged." | — |
| Save with open Preview | Russian pair open, unaccepted | Save sends Current values only | — |

</frozen-after-approval>

## Code Map

- `src/language_lab/features/drafts/service.py` -- add `regenerate(language, category, target, generation_context)` returning `fields.to_content(target)` via the same `self._llm.generate`; no `blank()` call.
- `src/language_lab/features/drafts/routes.py` -- add `@router.post("/regenerate")` (200) reusing `GenerateRequest`; return `content.model_dump(by_alias=True, mode="json")`.
- `src/language_lab/static/api.js` -- add `regenerateContent(body)` beside `generateDraft` (JSON POST).
- `src/language_lab/static/screens/item-detail.js` -- state: `previews` per group, `regenerating` group, `regenError {group, error}`. After `editorFields(...)` returns `{fields, inputs}`, insert each group's slot after its anchor field's wrap (`inputs.alternatives` / `inputs.exampleRussian` / `inputs.note` `.parentElement`): the Regenerate button (`button-link`, disabled while `busy`, any regeneration in flight, or Target blank), then the alert or the compare pair (`section role="group"` labelled by its `h2`). `unsavedCount` adds the open-Preview count; `syncDirty` uses it. Focus returns to the group's Regenerate button after Keep/Use. Check `mounted` after every await.
- `src/language_lab/static/screens/make-item.js` -- reuse `generatedValues` (turns `russianAlternatives` into the newline `alternatives` value) to map a Preview into buffer keys; no behaviour change.
- `src/language_lab/static/screens/captures.js` -- `generationFailure` copy is the reference; don't change it; Item copy lives in item-detail.js.
- `src/language_lab/static/css/studio.css` -- compare pair styles from DESIGN.md `compare-current` / `compare-preview` (2px `border` / `accent-tint` + 2px `accent`, `rounded.inner`, panes `flex: 1 1 300px` wrap, overline labels, actions right-aligned: Keep current secondary, Use preview soft); tokens from `tokens.css`. Mockup `ux-languagelab/mockups/S-ItemDetail.dc.html`.
- Tests: `tests/api/test_drafts_regenerate.py`, `tests/e2e/test_item_regenerate.py` (skipped scaffolds), `tests/support/regenerate_screen.py`, `tests/support/maintain_items_screen.py` (`EditableItemApi`, `edit_field`, `save_changes`), `tests/support/drafts.py`.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/features/drafts/service.py`, `routes.py` -- `regenerate` + route -- AD-11 shared generation, no ItemId.
- [x] `tests/api/test_drafts_regenerate.py` -- remove module skip; add French Sentence, `llm_failed` 502, blank-Target 422 with no model call.
- [x] `src/language_lab/static/api.js` -- `regenerateContent`.
- [x] `src/language_lab/static/screens/item-detail.js` + `css/studio.css` -- Regenerate buttons, loading (button busy + skeleton "Writing a Preview…" in the slot), compare pair, Keep current / Use preview, group alert with Try again, open-Preview dirty count; update the header comment.
- [x] `tests/e2e/test_item_regenerate.py` -- remove skip; add: edited Target is the one sent; open Preview shows chip "1 unsaved change" and leaving asks Discard/Keep editing; Save with an unaccepted Preview sends Current values; Vocabulary shows no Regenerate Note.

**Acceptance Criteria:**
- Given the ATDD scaffolds AC-1..AC-8, when activated, then all pass unchanged in intent.
- Given an Item with a Preview open, when the user leaves via the back link, then the unsaved alert shows and Keep editing keeps the Preview.
- Given story 5.1 and Draft generation suites, when run, then they stay green.

## Implementation Notes

- The slot's skeleton is the shared `skeleton()` (role=status "Writing a Preview…"); the Regenerate button carries `aria-busy` and is disabled while any regeneration runs, while saving, or with a blank Target.
- After a reply, focus moves to the pair's `h2` (tabIndex -1); after a failure, to Try again; after Keep/Use, to the group's Regenerate button. A re-render without a focus target keeps the focused field and its selection, so typing during a regeneration is not interrupted.
- A failed regeneration drops that group's earlier open Preview (the alert takes its slot). Copy for other errors: "Couldn't regenerate" + the envelope message.
- Added `.button-soft` (accent-soft) for Use preview; compare styles are new `compare-*` / `regenerate-*` classes in studio.css.
- Extra tests beyond the plan list: Target/context not logged, unknown Category/Language 422, blank Target disables Regenerate, Russian meaning Use preview (alternatives one per line), llm_failed copy, and a late reply after leaving opens nothing.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 2, low 4, false 1, maybe-false 0.

| Finding | Verdict | Route | Evidence |
|---|---|---|---|
| Use preview / Keep current enabled during an in-flight Save; Save success resets `values` and drops the accepted Preview | medium | patch | `regenerateSlot` pair buttons had no `busy` guard while fields are read-only; disabled while `busy`. |
| A regeneration reply moves focus off the field being typed in | medium | patch | `keepField` was computed only when `focus === null`; the reply paths pass a group focus. Field focus now wins. |
| Clicking Regenerate drops keyboard focus to body | low | patch | The clicked button is re-rendered `disabled`; the in-flight button is now `aria-disabled` and keeps focus. |
| Try again never disabled, silently no-ops while blocked | low | patch | `regenerate()` returns early under the Regenerate buttons' disabled condition; same condition applied. |
| Reply while the duplicate sheet is open re-renders behind the modal | low | rejected | Needs Save with a changed Target that matches a duplicate during an in-flight regeneration; rare, and the fix adds a guard. |
| Leave-guard test could pass after a navigate-and-return | false | rejected | The test asserts the pair (in-memory state) is still visible after Keep editing, which a remount would not show. |
| `regenerationFailure` duplicates `generationFailure` branching | low | rejected | Plan's Code Map keeps Item copy in item-detail.js; consolidating moves code across screens for a three-line branch. |

## Design Notes

Regeneration lives in `features/drafts` because AD-11 says it "calls the drafts generation for the Item's Category"; it returns 200 (nothing is created) unlike generate's 201. Only one regeneration runs at a time, which keeps one `regenerating` slot and avoids interleaved replies. After a successful Save, open Previews stay open and compare against the new Current.

## Verification

**Commands:**
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` -- expected: clean
- `.venv/bin/pytest tests/api/test_drafts_regenerate.py tests/e2e/test_item_regenerate.py -q` -- expected: all pass, none skipped
- `.venv/bin/pytest -q` -- expected: full suite green

---
title: 'Regenerate, keep, and remove audio on existing Items'
type: 'feature'
ticket: '2'
created: '2026-10-24'
status: 'built'
baseline_revision: '655d7d034b71a7ba41ae78656e648a8baa8847bf'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-6-2.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Item detail cannot play, regenerate, keep or remove an Item's Reference audio, and Save rejects `audio=remove`.

**Approach:** Add a Reference audio card to editable Item detail on 6.1's Voice/Preview/multipart contracts, with pending replace/remove committed only by Save changes, and complete AD-6 removal in Save.

## Boundaries & Constraints

**Always:** Every mount re-reads the Item; current clip plays from `/api/media/<audio>`, never autoplays. Only explicit Regenerate audio synthesizes; Voice changes only write `voice-pref.js`. Offered, accepted and removal states stay in screen memory and each counts as one unsaved change (chip + router alert). Save keeps the global lock, Setup gate, Prefix guard and AD-6 order; failures stop without compensation; the previous note/audio survives until the note write succeeds; leftovers are repaired through Setup. Only `api.js` fetches. Blob URLs are revoked on replace/discard/departure.

**Never:** Schema/template/Setup changes; new endpoints; inline rollback; Preview writes; re-synthesis on Target edits; blocking Save on stale audio. Released-wheel/device/real-Azure evidence (6.4) and the Draft card refactor (6.3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Open | Detail `audio: name|null` | Card "Reference audio" with Voice; player only when audio exists | Media 404/failure: card without playable clip; edits unaffected |
| Regenerate | Explicit click, buffer Target, chosen Voice | Compare: "Current" / "Preview · not saved"; Keep current / Use preview | TTS failure: "Couldn't make the audio. Current audio is unchanged."; current and accepted clips kept |
| Use preview | Offered clip | Pending `replace` with exact Blob; nothing written | Save failure retains Blob; retry resends same bytes and ItemId |
| Remove | Item with audio | Pending removal, undoable; Save sends `audio=remove`, no file | Remove + `audioFile`: 422, zero writes |
| Stale | Buffer Target ≠ the clip's Target | "Audio no longer matches the text." beside Regenerate audio | Save still sends `audio=keep` |
| Save remove | Stored Item with managed clip | `updateNoteFields` (Audio empty) → `deleteMediaFile` old clip; one lock | Note failure: no delete. Cleanup failure: `anki_unavailable`, note stands; retry rewrites note only; Setup offers `orphanMedia` |
| Save remove | Item without audio, or new ItemId | Note written with empty Audio; no media deletion | Setup gate/Prefix refusals unchanged |
| Saved | Successful Save | Replace: accepted clip becomes Current; remove: no player; chip clean | Late replies after leaving open nothing |

</frozen-after-approval>

## Code Map

- `features/items/routes.py::_SaveIntent,save` — accept `REMOVE`; `remove`/`keep` with a file stays 422.
- `adapters/anki/store.py::save_item` (~L339) — `remove`: skip media store, set `fields[_AUDIO] = ""`, after the note write (and card placement) delete `old_name` when present. `_audio_name` yields only managed names. Reuse existing lock/guard/client; don't touch `delete_item`/`get_media`.
- `ports/anki_store.py::save_item` docstring; `tests/fakes/anki_store.py::save_item` (~L174) — mirror remove (pop `audio[item_id]`, drop media).
- `static/screens/item-detail.js` — add card after fields; extend `unsavedCount`/`syncDirty` with audio state; `saveChanges` passes intent + Blob to `saveItem(lang, part, blob)` and on success adopts the clip; dispose URLs in the unmount return. Existing groups/duplicate/Delete flows unchanged.
- `static/screens/make-item.js::itemPart` (L107) — `audio` is computed from `draft.audio.accepted`; Item detail overrides `part.audio` instead of changing Draft behavior. `referenceAudio`/`disposeDraftAudio` (L503–655): pattern to follow (sequence guard, players set, voice fallback, locale map). Reuse by extraction only if Draft behavior is untouched; duplication is acceptable (6.3 sweeps).
- `static/api.js::getVoices,previewAudio,saveItem,getItem` — reuse; update comments only.
- `static/css/studio.css` — reuse `.reference-audio*`, `.compare-*`; add minimal rules for the stale/removal rows.
- `tests/support/item_audio_screen.py` — set `CURRENT_LABEL`/`PREVIEW_LABEL` to source text "Current"/"Preview · not saved" (CSS uppercases; matches `regenerate_screen.py`).

## Tasks & Acceptance

**Execution:**
- [x] `features/items/routes.py`, `adapters/anki/store.py`, `ports/anki_store.py`, `tests/fakes/anki_store.py` — implement `remove` per matrix; activate `tests/api/test_item_audio_lifecycle.py` and `tests/integration/test_anki_audio_lifecycle.py`, observe RED then GREEN.
- [x] `static/screens/item-detail.js`, `static/css/studio.css`, `static/api.js` — implement the card, pending intents, stale warning, Save integration and disposal; update header comment.
- [x] `tests/e2e/test_item_audio.py`, `tests/support/item_audio_screen.py` — activate 8 scaffolds (RED then GREEN); add matrix expansions: tablet width + WebKit run, undo removal, Voice-list failure/Try again, replace-intent cleanup failure + retry, remove on Item without audio, remove+file 422 zero writes, Setup gate refusing remove, `hasAudio` after replace/remove, URL revocation on leave.
- [x] `tests/unit/test_anki_store_port.py` and existing Item edit/regenerate/delete tests — keep port/fake/adapter parity and regressions green.

**Acceptance Criteria:**
- Given an Item with audio, when the user regenerates, uses the Preview and saves, then playback returns the exact previewed MP3, the old clip is gone and the Item keeps its ItemId and four Cards.
- Given the 11 ATDD criteria and matrix rows, when automated checks run, then all active story tests pass with no scaffold skips and failures preserve promised local and stored state without leaking content.

## Implementation Notes

- Adapter: `remove` sets `Audio` to empty and deletes the old managed clip after the note write and card placement; a retry after a cleanup failure rewrites the note only (the field no longer names the clip), so the leftover becomes Setup's `orphanMedia`.
- `tests/api/test_reference_audio.py::test_inconsistent_audio_parts_are_rejected` (6.1) asserted `remove` without a file is 422; that case is now valid, so its parameter became `remove` *with* a file (still 422, zero writes).
- AC-1 scaffold raced the card render; it now waits for the player before probing bytes.
- The current clip's `<audio>` uses `preload="metadata"` so a 404/failed clip is detected and the card shows "Couldn't load the saved audio." without a player. Players are cached per URL so re-renders don't stop playback.
- Matrix expansions: API (no-audio remove, new-ItemId remove, remove+file 422, Setup gate, `hasAudio` after replace/remove), integration (replace cleanup failure + retry + orphan), unit (fake parity), e2e (tablet undo removal, Voice-list Try again, no-audio Preview/discard, saved replace→Current then saved remove, Blob URL revocation on discard/leave, media failure).
- Root audit: added `test_a_preview_reply_after_leaving_opens_nothing` (matrix row "Saved": late replies); mutation-checked by removing the disposed guard (RED) and restoring it (GREEN). Root verification: `make test` 1168 passed; `tests/e2e -k "item or audio" --browser webkit` 107 passed; `make lint`, `git diff --check` clean. Every matrix row now has a passing covering test.

## Plan Change Log

## Review Triage Log

Pass 1 (quick, 2026-10-24): high 0, medium 1, low 6, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| Audio actions drop keyboard focus | medium | patch | `changed()` → `renderEditor()` without focus; `audioCard.render()` replaces the pressed button, focus falls to body. Focus the matching card control after each action. |
| In-flight Regenerate audio button disabled | low | patch | Card `refresh()` sets `disabled` while previewing, contrary to the editor's "stays focusable, aria-disabled" pattern; keep it enabled with aria-busy/aria-disabled. |
| Save not gated while an audio Preview is in flight | low | reject | Real but harmless: the offered clip stays pending and compares after the Save (matches the text groups' "Previews stay open across a Save"); gating adds a new accessor/guard. |
| Unbounded poll loop in late-reply test | low | patch | `while not held` has no bound; bound it and assert. |
| Voice-enabled assertion can never fail | low | patch | The card never disables the select; delete the assertion. |
| New-ItemId remove test docstring overclaims card placement | low | patch | Only `addNote` and no media writes are asserted; assert placement or narrow the docstring. |
| Remove audio with no saved clip discards an accepted Preview without undo | low | reject | Follows Design Notes ("Remove clears accepted"); rare path, fix adds branches/copy. |

After patches, root verification: story files 26 passed (no skips); `make test` 1168 passed; `tests/e2e -k "item or audio" --browser webkit` 107 passed; `make lint`, `git diff --check` clean. Nothing deferred.

## Design Notes

Card state: `current` (`{url, target}` from `/api/media` with the loaded Target, or null), `offered`, `accepted` (`{blob, url, target}`), `removing` (bool). Accept clears `removing`; Remove clears `accepted`. Intent: `accepted` → `replace`, `removing` → `remove`, else `keep`. Stale compares buffer Target with the clip that will remain (accepted, else current). One "Regenerate audio" button only (strict locators); with no audio it reads "Preview". Removal copy (epic-delegated): "Remove audio" → note "Audio will be removed when you save." + "Keep audio" to undo. Compare heading "Reference audio · compare" and hint "The old audio is removed only after Save succeeds." per S-ItemDetail.

## Verification

**Commands:**
- `.venv/bin/pytest tests/api/test_item_audio_lifecycle.py tests/integration/test_anki_audio_lifecycle.py tests/e2e/test_item_audio.py -q` — all pass, none skipped.
- `.venv/bin/pytest tests/e2e/test_item_audio.py tests/e2e -k "item or audio" --browser webkit -q` — pass.
- `make test`, `make lint`, `git diff --check` — clean.

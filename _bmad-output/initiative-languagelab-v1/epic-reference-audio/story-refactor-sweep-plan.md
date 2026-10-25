---
title: 'Refactor sweep: Reference audio'
type: 'refactor'
ticket: '3'
created: '2026-10-24'
status: 'built'
baseline_revision: '393bda3db36fe3952680ffc048154140b069a2e7'
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

**Problem:** Stories 6.1 and 6.2 left the same Reference audio logic in two places: the Voice picker, voice-list fallback, sequenced Preview and clip release in the Draft card and the Item detail card, and the audio intent/upload checks and managed media name in the Save route, the Anki adapter and the fake. 6.2 deferred the Draft-card refactor to this story.

**Approach:** Extract the shared logic into one client module and one domain helper, used by every site. Do this without changing any behavior, copy, wire contract or test expectation. Record in this plan how each review finding from 6.1 and 6.2 was settled.

## Boundaries & Constraints

**Always:** Behavior-preserving. Every existing test passes unchanged except imports and helper consolidation. Draft and Item cards keep their own rendering (the Draft's inline accepted/offered players, the Item's compare pair, removal row and focus handling). Only `api.js` fetches. Only `voice-pref.js` touches localStorage. The AD-6 write order, lock, guard and gate stay as they are in `save_item`. The store still validates intent/bytes itself, because the port contract holds without the route.

**Never:** New capability, copy, endpoints, wire fields or CSS changes. No new deferred-work entries for CAP-9 scope. The two rejected 6.2 findings (Save not gated during an in-flight Preview; Remove with no saved clip discarding an accepted Preview) stay rejected, as the 6.2 triage decided.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Voices | Either card, `en`/`fr` | Same `en-US`/`fr-CA` request, stored-or-first fallback and `voice-pref.js` writes as before | Voice-list failure: same alert and Try again |
| Preview | Explicit Preview/Regenerate | Same sequenced request; a late or superseded reply is ignored after dispose | Same TTS alert; clips kept |
| Save parts | `replace`+file, `keep`/`remove` with or without file | One helper decides; same 200/422/413 at route, adapter and fake | Zero Anki writes on refusal, as before |
| Media name | Replace bytes | `<Prefix>_<ItemId>_<sha256[:12]>.mp3` from one function | — |

</frozen-after-approval>

## Code Map

- `static/screens/make-item.js::referenceAudio,disposeDraftAudio` (L503–656) and `static/screens/item-detail.js::itemAudioCard` (L105–440) — duplicated pieces: the `fr`→`fr-CA` locale mapping (L523/L130, same as `domain/catalog.py::LOCALES`), Voice `<select>` building and change → `writeVoice`, `loadVoices` (preferred ?? `readVoice`, else first), the loading/error/empty hints, the `preview()` sequence/disposed guard, and clip release (pause, drop src, load, revoke blob URL). Keep `draft.audio` state on the Draft (it outlives rerenders, captures.js calls `disposeDraftAudio`). Keep `players` as a Set in the Draft card and a Map by URL in the Item card.
- `static/api.js::getVoices,previewAudio` — reuse as they are.
- `features/items/routes.py::save` (L72–91), `adapters/anki/store.py::save_item` (L355–360, name L370–371), `tests/fakes/anki_store.py::save_item` (~L185–203) — the same intent/bytes rule and name format in three places. `domain/audio.py` is the home (it owns `validate_mp3`, `MAX_AUDIO_BYTES`). Keep the route's bounded `read(MAX_AUDIO_BYTES + 1)`.
- `tests/support/{audio,audio_screen,item_audio_screen,regenerate_screen}.py` — `VOICES_API`/`PREVIEW_API` are defined twice, and `unsaved_chip`, `KEEP_CURRENT`/`USE_PREVIEW`/`CURRENT` labels are repeated. `item_audio_screen.CURRENT_LABEL`/`PREVIEW_LABEL` equal `regenerate_screen.CURRENT`/`PREVIEW_NOT_SAVED`.
- Review findings to settle: 6.1 has one patched finding (reserved MPEG emphasis), 6.2 has five patched and two rejected. No `deferred-work.md` entry names epic-reference-audio.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/static/reference-audio.js` (new) — export `audioLocale(language)`, a Voice-picker builder (select + loading/error/empty hints, with a Try again callback), `chooseVoice(voices, current, locale)`, a sequenced `requestPreview(state, body)` (returns the Blob or null when it was superseded or disposed, and throws on failure) and `releasePlayer(audio)`. This is the one shared home for the logic both cards use.
- [x] `src/language_lab/static/screens/make-item.js` — rebuild `referenceAudio`/`disposeDraftAudio` on the module, with the same DOM, states and labels.
- [x] `src/language_lab/static/screens/item-detail.js` — rebuild `itemAudioCard` on the module, with the same DOM, focus targets, pending/intent/saved/dispose API and header comment.
- [x] `src/language_lab/domain/audio.py` — add `audio_upload(intent, data) -> bytes | None` (the intent/file rule plus `validate_mp3`) and `media_name(prefix, item_id, data)`. Use them in `features/items/routes.py`, `adapters/anki/store.py` and `tests/fakes/anki_store.py`. Unit-test both in `tests/unit/` (every intent × file/no-file, the 413 and 422 paths, and the name format).
- [x] `tests/support/{audio_screen,item_audio_screen}.py` — import the repeated constants and `unsaved_chip` from `audio.py`/`regenerate_screen.py` instead of redefining them.
- [x] This plan's Implementation Notes — a findings ledger: each 6.1/6.2 finding with its resolution, and why nothing remains outside this epic.

**Acceptance Criteria:**
- Given the refactor, when the focused audio, Item Save/Delete, managed-media and browser suites run in Chromium and WebKit, then all pass with no test assertions edited.
- Given the two card files, when searched, then neither contains the locale mapping, voice fallback, Preview sequencing or player-release code any more, only calls into `reference-audio.js`.

## Implementation Notes

- `static/reference-audio.js` exports `audioLocale`, `chooseVoice`, `voicePicker(state, locale, retry, disabled)`, `requestPreview(state, body)`, `releasePlayer(audio)` and, beyond the listed set, `loadVoices(state, locale, render)` (the getVoices + `chooseVoice` + disposed-guard sequence both cards repeated). Requests stay in `api.js`, storage in `voice-pref.js`.
- Draft card: the select keeps its `disabled` rule (passed in); `loadVoices` renders through `state.render` so a rerendered card receives the reply, as before. Item card: the select is never disabled (default `false`); focus targets, `settle`, aria-busy/aria-disabled and the `pending/intent/blob/saved/dispose` API are untouched.
- `requestPreview` owns the sequence bump and the superseded/disposed check for both success and failure. The `state.sequence += 1` in both disposes was dropped: `disposed = true` already makes every pending request return null.
- `domain/audio.py`: `audio_upload(intent, data)` and `media_name(prefix, item_id, data)`. The route still reads `MAX_AUDIO_BYTES + 1` and calls `audio_upload` before the service. The adapter calls it before the manifest/lock (same place as the old inline check) and names media with `media_name`. The fake calls it after its busy/available/setup checks (same order as before). Unit tests: `tests/unit/test_audio_domain.py`.
- Test support: `audio_screen.py` takes `VOICES_API`/`PREVIEW_API` from `audio.py` and `USE_PREVIEW` from `regenerate_screen.py`. `item_audio_screen.py` drops `CURRENT_LABEL`, `PREVIEW_LABEL` and `unsaved_chip`. `regenerate_screen.unsaved_chip` became `exact=True` (the Item audio version), which is stricter and still matches the chip, whose text is exactly the label. `tests/e2e/test_item_audio.py` and `test_draft_audio.py` changed imports only (aliases keep `CURRENT_LABEL`/`PREVIEW_LABEL` in the test bodies).

### Findings ledger

| Story | Finding | Resolution | Still holds after this sweep |
|---|---|---|---|
| 6.1 | MP3 validator accepts reserved MPEG emphasis | Patched in `validate_mp3`, with the `reserved-emphasis` regression in `tests/api/test_reference_audio.py` | Yes. `audio_upload` calls the same `validate_mp3` |
| 6.2 | Audio actions drop keyboard focus | Patched (`settle(key)` focuses the card control) | Yes. `settle`/`nodes` unchanged |
| 6.2 | In-flight Regenerate audio button disabled | Patched (enabled, aria-busy + aria-disabled) | Yes. `refresh()` unchanged |
| 6.2 | Unbounded poll loop in late-reply test | Patched (bounded and asserted) | Yes. Test untouched |
| 6.2 | Voice-enabled assertion can never fail | Patched (assertion deleted) | Yes. Item select is still never disabled |
| 6.2 | New-ItemId remove test docstring overclaims | Patched | Yes. Test untouched |
| 6.2 | Save not gated during an in-flight Preview | Rejected (6.2 triage) | Still rejected, unchanged behavior |
| 6.2 | Remove with no saved clip discards an accepted Preview | Rejected (6.2 triage) | Still rejected, unchanged behavior |

Nothing remains outside this epic: `deferred-work.md` has no epic-reference-audio entry, both triages ended with nothing deferred, and the 6.2 Draft-card refactor deferral is closed here. Real Azure/Anki and device evidence was already assigned to story 6.4 by 6.1's Design Notes. That is in-epic work, not a deferral.

## Plan Change Log

## Review Triage Log

Pass 1 (quick, 2026-10-24): high 0, medium 0, low 2, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| Item card `dispose()` gained `audio.load()` via `releasePlayer` (frozen intent: behavior-preserving) | low | patch | Real but invisible: the clip-error listener returns once disposed. Restored the original pause + remove-src loop in `dispose()`; `release(clip)` keeps its existing `load()`. `tests/e2e/test_item_audio.py` 30 passed (Chromium + WebKit). |
| Shared `unsaved_chip` became `exact=True`, changing what `test_item_regenerate.py`'s 7 visibility checks match | low | reject | Strictly stronger match; the chip text is exactly `unsavedLabel(count)`, so every check passes. Either choice changes one suite, and keeping two helpers reintroduces the duplication this sweep removes; no assertion line was edited. |

## Verification

Run 2026-10-24: focused api/integration/unit set 79 passed (with the new unit file). `tests/e2e -k "item or audio or draft"` in Chromium and WebKit: 246 passed. `make test` 1179 passed. `make test-webkit` 633 passed. `make lint` and `git diff --check` clean.

**Commands:**
- `.venv/bin/pytest tests/api/test_reference_audio.py tests/api/test_item_audio_lifecycle.py tests/integration/test_anki_audio_save.py tests/integration/test_anki_audio_lifecycle.py tests/integration/test_azure_speech.py tests/unit/test_anki_store_port.py -q` — pass
- `.venv/bin/pytest tests/e2e/test_draft_audio.py tests/e2e/test_item_audio.py tests/e2e -k "item or audio or draft" --browser webkit -q` — pass
- `make test`, `make lint`, `git diff --check` — clean

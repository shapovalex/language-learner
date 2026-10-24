---
title: 'Preview and save Reference audio from a Draft'
type: 'feature'
ticket: '1'
created: '2026-10-24'
status: 'built'
baseline_revision: '28310f007ab1c57d654534782e6e66db23e01be1'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-6-1.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Drafts cannot preview or save Reference audio.

**Approach:** Add Speech/Azure, explicit Draft Preview and comparison, then multipart Save and guarded playback through Anki media. Expose the saved audio filename for story 6.2.

## Boundaries & Constraints

**Always:** Backend credentials; escaped SSML; current exact-locale neural catalog; unchanged MP3 bytes. Preview is memory-only, outside the Anki lock. Save uses the global lock, Prefix guard, Setup gate, codec, ItemId retries and AD-6 ordering. Failures stop without compensation; prior note/audio survive until note-write success. Only `api.js` fetches; only `voice-pref.js` accesses localStorage. Drafts/Blobs stay in screen memory.

**Never:** Automatic synthesis/playback; preview sessions or application database; browser provider calls; schema/template changes. Existing-Item audio UI, remove intent and lifecycle completion belong to 6.2; released-wheel/device acceptance belongs to 6.4.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Voices | `GET /api/audio/voices?locale=en-US|fr-CA` | `{voices:[{name,locale,displayName}]}` from current catalog | Inline retry retains edits; safe envelope |
| Preference | Missing/unavailable stored Voice | First available locale Voice; persist explicit selections independently | Empty catalog disables Preview; denied storage tolerated |
| Preview | `POST /api/audio/preview` JSON `{language,voice,target}` | `audio/mpeg`, no-store; no Anki writes | Bad locale/Voice/blank text: 422; provider failure: 502 `tts_failed` |
| Compare | New offered clip; optional accepted clip | Keep current discards offer; Use preview replaces accepted clip | TTS failure retains both edits and prior clip |
| Stale | Target differs from clip's synthesis text | “Audio no longer matches the text.”; explicit Preview available | Save remains available; Voice changes never synthesize |
| Save | Multipart `item` JSON, `audio=replace`, `audioFile` | Exact bytes; backend `<Prefix>_<ItemId>_<sha256[:12]>.mp3`; exact sound reference | Reject invalid combinations/empty or malformed MP3; uploads over 5 MB: 413 |
| Writes | New or retried ItemId | Store media → add/update note → move new ords 0–2 → delete differing superseded managed media | Stop at failure; orphan media/partial writes repaired through Setup |
| Read | `GET /api/media/{name}`; Item detail | Managed bytes; detail adds `audio: filename|null` | Foreign/non-managed/missing: 404; reads remain ungated |
| Save error | Accepted Blob and local edits | Retry retains ItemId, edits and exact Blob; ordinary `audio=keep` still works | Existing content-free envelope/logs |

</frozen-after-approval>

## Code Map

- `app.py::create_app`: composition/lifespan; OpenRouter supplies the safe adapter pattern.
- `adapters/anki/store.py::save_item`: existing scoped queries, codec and card placement. `guard.py::media_pattern` supplies filename validation.
- `static/screens/captures.js`: Draft lifetime. `make-item.js::draftEditor,itemPart`: controls/shared keep-default payload; preserve duplicate and unsaved flows.
- `static/api.js`: envelope parser assumes JSON. `studio.css`: responsive Draft/sticky actions.
- `tests/support/{audio,azure,audio_screen}.py`: replay/Blob probes; remove temporary interface compatibility detection.

## Tasks & Acceptance

**Execution:**
- [x] `domain/audio.py`, `domain/catalog.py`, `ports/speech.py`, `adapters/azure/__init__.py`, `tests/fakes/speech.py` — implement Voice/Speech, locale mapping, current catalog and escaped REST synthesis with bounded HTTP requests.
- [x] `features/audio/{__init__,routes,service}.py`, `app.py` — wire voices/Preview and safe status mapping/lifespan.
- [x] `features/items/{routes,service}.py`, `ports/anki_store.py`, `adapters/anki/{store,client,guard}.py`, `tests/fakes/anki_store.py` — validate bounded MP3 uploads, extend Save ordering and add locked guarded media retrieval with strict base64 decoding.
- [x] `domain/items.py`, `features/items/routes.py`, `adapters/anki/store.py` — expose managed saved filename separately from content, preserving existing responses elsewhere.
- [x] `static/voice-pref.js`, `static/api.js` — implement independent preferences, binary requests and exact-Blob multipart Save.
- [x] `static/screens/{captures,make-item}.js`, `static/css/studio.css` — add audio card, compare/retry/stale states; guard late responses and revoke URLs on discard/replacement/departure, retaining accepted audio across rerenders.
- [x] `tests/{api/test_reference_audio.py,integration/test_azure_speech.py,integration/test_anki_audio_save.py,e2e/test_draft_audio.py}` and supporting audio helpers — activate 17 scaffolds, prove RED then GREEN; cover matrix failures, gate/Prefix refusal, fallback, URL cleanup, late replies, no autoplay and both Categories/locales at phone/tablet/desktop widths.
- [x] `tests/unit/test_anki_store_port.py`, related domain/adapter tests — verify port/fake/adapter parity and existing keep/read/Delete regressions.

**Acceptance Criteria:**
- Given a Draft in either language, when the user explicitly previews, accepts and saves audio, then playback returns byte-identical MP3 and the Item has four Cards in the correct decks.
- Given the story's 17 ATDD criteria and matrix scenarios, when automated checks run, then all active story tests pass and recoverable failures preserve the promised local and stored state without leaking content or credentials.

## Implementation Notes

- Implemented Speech/Azure, memory-only Preview, byte-preserving Save/media playback and Draft comparison. Detail alone gains `audio`; existing list/duplicate shapes and keep Saves remain compatible.
- Observed RED before implementation; activated all 17 scaffolds. Expanded failure, locale/Category, responsive and lifecycle checks. WebKit interception omits uploaded file bytes: failure journeys observe browser FormData, while separate un-intercepted app journeys prove actual HTTP upload/playback in Chromium and WebKit.
- Verification on final implementation: `make test`: 1,140 passed; audio WebKit: 29 passed; un-intercepted Chromium/WebKit journeys: 4 passed; `make lint` and whitespace checks clean. Root independently reran four story files plus port tests: 84 passed, none skipped (JUnit retained locally at `/tmp/story-6-1-audit.xml`). Existing upstream TestClient deprecation warning remains.
- Matrix audit: every row has passing focused coverage. Voices: catalog freshness and recoverable voice-list error tests. Preference: independent locale/browser, unavailable fallback, denied storage and empty catalog tests. Preview: memory-only, invalid input, safe TTS/provider failure tests. Compare: Keep current and failed Preview retention tests. Stale: Target warning and Voice-change tests. Save: exact bytes/name, invalid/empty/truncated/oversized upload and intent-part tests. Writes: one-lock/decks, store/note failure, successful cleanup and same-hash retry tests. Read: guarded playback, saved reference, missing/malformed media and ungated reads tests. Save error: failed binary retry plus ordinary keep tests.
- No real provider recording or device/wheel acceptance claimed; those evidence tasks remain for 6.4.

- After review patch, root verification: `make test` **1,141 passed**; relevant audio/Draft/duplicate/API-client WebKit **65 passed**; `make lint` and `git diff --check` clean. The malformed-MP3 regression is included in the full run. All matrix coverage remains passing.

## Plan Change Log

## Review Triage Log

Pass 1 (quick, 2026-10-24): high 0, medium 1, low 0, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| MP3 validator accepts reserved MPEG emphasis | medium | patch | Independently reproduced the exact 417-byte malformed clip: Save returned 200 and stored media. Reject reserved header values in the existing validator and add a no-write regression; no public API change. Fixed the reserved-emphasis check; regression observed RED then passed with 422 and zero Anki requests. |

## Design Notes

Keep accepted/offered clips separate, each with Blob, URL and synthesis Target. Guard async completion by Draft identity and request sequence. The epic delegates fallback choice. REST contract: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech.

Synthetic fixtures retain their provenance; real Azure/Anki comparison and device/wheel evidence remain for 6.4.

## Verification

- `uv run pytest tests/api/test_reference_audio.py tests/integration/test_azure_speech.py tests/integration/test_anki_audio_save.py tests/e2e/test_draft_audio.py -q` — all story tests pass, no scaffold skips.
- `make test` and relevant audio/Draft E2E with `--browser webkit` — regressions pass.
- `make lint` and `git diff --check` — clean.
- Complete workflow review, then push the implementation branch and create a PR per AGENTS.md.

---
title: 'Record Attempts and show Azure feedback per locale'
type: 'feature'
ticket: '2'
created: '2026-10-25'
status: 'built'
baseline_revision: '7ad0c867c4ea9a24a05711048297d25424815a16'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-7-2.md'
  - '{project-root}/_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The review loop has no recording or Assessment; learners cannot compare their pronunciation with the Target before choosing a Rating.

**Approach:** Add native browser recording, one backend Attempt request, Azure assessment shaped per locale, and ephemeral feedback with unlimited retries. Enable Ratings after a usable Assessment on the current Card.

## Boundaries & Constraints

**Always:** Read Target through the scoped AnkiStore by itemId. Bound uploads to 5 MiB and decoded audio to 30 seconds; auto-stop recording at 30 seconds. Process entirely in memory using PyAV, mono 16 kHz PCM WAV, without numpy. English keeps Azure IPA/prosody; French exposes overall, word and position scores, never sound names. Keep session Sync and scheduler behavior from 7.1. Drop recordings/results after successful Rating or leaving; clean microphone resources and ignore stale replies. Ratings remain neutral and eligible after the first usable result, including during later Attempts.

**Never:** Attempt-driven Anki writes, client-supplied reference text, audio/content/score logging, disk spooling, browser persistence, history, Reference autoplay, suggested Ratings, new providers or scheduling changes. Real-device/released-wheel acceptance belongs to 7.4.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Attempt | multipart itemId + recording | 200 `{assessment,nothingHeard:false}` | Unknown Item → 404 |
| Silence | every word Omission | 200 `{assessment:null,nothingHeard:true}`; warning + Record again; no new eligibility | Card unanswered |
| Invalid recording | >5 MiB / decoded >30 s / corrupt | Reject before Azure | 413 payload_too_large / 422 validation_failed |
| Provider failure | HTTP, timeout, malformed/empty reply | Fixed error; Record again / Exit | 503 assessment_failed; Card current |
| Microphone unavailable | denied/unsupported capture | Warning; Reference playable | No answer or new eligibility |

</frozen-after-approval>

## Code Map

- `src/language_lab/features/pronunciation/{routes,service}.py`: extend existing router/service; reuse `AnkiStore.get_item`, releasing its lock before conversion/provider calls. `app.py` injects Speech and maps assessment_failed to 503.
- `src/language_lab/adapters/azure/__init__.py`: existing bounded httpx client and injected transport; add regional STT without breaking TTS. Probe replies have flat NBest scores, not SDK nesting.
- `src/language_lab/static/screens/pronunciation.js`: reuse queue, session, Rating retry and Reference lifecycle; separate per-Card eligibility from latest result. Existing re-render focus assumes enabled Ratings and needs adaptation.
- `tests/support/{assessment,attempt_screen}.py`, `fake_microphone.js`: existing real Anki replay, native recording doubles and lifecycle observers; fixtures under `tests/fixtures/azure-assessment/` retain provenance.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/pronunciation.py` — add validated Assessment, word, phoneme and position types with `.wire()`; centralize locale shaping. French buckets use `min(2,floor(3*i/n))`, minimum per bucket; empty buckets are null.
- [x] `src/language_lab/ports/speech.py`, `adapters/azure/__init__.py`, `tests/fakes/speech.py` — add `assess(locale,target,wav) -> Assessment | None`; encode assessment header, request English IPA/prosody, parse probe fixtures, redact failures.
- [x] `src/language_lab/features/pronunciation/audio.py` — bounded in-memory decoding/resampling with flush and sample-count duration limit; run conversion off the event loop.
- [x] `src/language_lab/features/pronunciation/{routes,service}.py`, `app.py` — validate bounded multipart without temporary files, trusted Item/locale lookup, conversion, Speech call and fixed error envelopes; close resources on failure/cancellation.
- [x] `src/language_lab/static/{api.js,attempt-recorder.js}` — multipart helper and abort support; capture native MP4/WebM, analyser meter, timer/size limits and complete disposal.
- [x] `src/language_lab/static/screens/pronunciation.js`, `static/css/studio.css` — recording/retry/error states, score ring, selectable word details and locale feedback per EXPERIENCE.md. Stop Reference on Record; disable it while recording. Use fixed ring color, 60/80 feedback thresholds with non-color cues, polite announcements, responsive columns and useful focus after transitions.
- [x] `tests/api/test_pronunciation_attempt.py`, `tests/integration/{test_attempt_audio,test_azure_assessment}.py`, `tests/e2e/test_pronunciation_attempt.py` — activate scaffolds RED then GREEN; test matrix errors, exact limits, short French words, lower phoneme scores, provider redaction and no disk writes. Expand stale permission/assessment replies and eligibility after later failure/silence.
- [x] `tests/e2e/test_pronunciation_review.py` — establish usable Attempts before Ratings; preserve scheduling/retry assertions and verify the next Card resets eligibility.

**Acceptance Criteria:**
- Given real probe fixtures, when backend tests run, then both native codecs decode without numpy, locale feedback matches fixtures, and Attempts produce no Anki writes or private logs.
- Given fake microphones on Chromium/WebKit, when users record, retry, rate or leave, then all 7.2 journeys pass, feedback never selects a Rating, and resources/results are released.
- Given existing functionality, when the full suite and lint run, then regressions pass and activated 7.2 tests have no implementation skips.

## Implementation Notes

- Added validated Assessment/word/phoneme/position models and centralized locale policy. The real REST flat NBest fixtures retain English IPA/prosody; French strips sound names and uses the approved minimum-per-third buckets, including null empty buckets for short words.
- Added Azure regional STT assessment through the existing bounded/injected httpx client. HTTP errors, timeout, malformed replies and invalid scores return fixed assessment failures; all-Omission is an explicit successful nothing-heard response.
- The Attempt endpoint uses a strict streaming multipart parser instead of UploadFile, avoiding temporary-file spooling entirely. Only itemId and recording are accepted. Trusted Target lookup finishes before off-thread PyAV decoding and provider work. Audio conversion closes in-memory resources, flushes resampling, and bounds both decoded duration and output sample count.
- Browser capture uses native MP4/WebM, an analyser meter, a 30-second timer and 5 MiB guard. AudioContext activation starts synchronously in the tap for Safari. Disposal clears handlers/chunks, stops tracks, disconnects nodes, closes contexts and invalidates pending permission/assessment callbacks. The Blob callback parameter is explicitly cleared after the API helper takes the upload body; screen state never stores Blob/FormData or object URLs.
- Added current-Card Assessment eligibility independent of the latest result; retries, silence, errors and pending assessments preserve earlier eligibility. Successful Rating/card change/exit clears results and eligibility, aborts pending assessment and disposes capture. Reference stops on Record, remains disabled during recording and never autoplays. Added fixed-color ring, locale details, non-color threshold cues, polite announcement and responsive columns.
- Activated every 7.2 scaffold and adapted 7.1 Rating journeys to earn eligibility with a usable Attempt. Expanded backend/browser boundaries, errors, privacy, exact limits, short French words, lower phoneme scores, stale permission/replies and disposal checks.
- WebKit required two test-boundary corrections: its native MediaDevices/track wrappers can be recreated, so the microphone double now uses a stable prototype override and retains its returned track wrappers; Playwright issue #14624 omits intercepted file bytes, so the Attempt helper follows the existing audio helper pattern to observe unchanged FormData before fetch and cross-check bytes when interception supplies them. Separate un-intercepted MP4 and WebM uploads verify the real app receives and decodes native bytes in both browser engines.
- No real-device or released-wheel acceptance was added; those remain story 7.4 as required.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — 2026-10-25: high 0, medium 1, low 0, false 0, maybe-false 0

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Phone places Ratings before Assessment | medium | patch | Confirmed render nests Rating in the first column before the scores sibling, and mobile flex stacks that order; reviewer measured Rating y=366 and feedback y=522 at 390px. Fixed by moving Rating after feedback in DOM and placing it in the tablet grid; new phone/tablet DOM and bounding-box assertions pass on both browser engines. |

## Verification

Implementation evidence (2026-10-25):

- Initial activated backend RED: 9 failed at absent route/converter/assess. Initial browser RED: missing Record control.
- Expanded backend modules: **41 passed** with `uv run pytest tests/api/test_pronunciation_attempt.py tests/integration/test_attempt_audio.py tests/integration/test_azure_assessment.py -q`.
- Chromium pronunciation modules: **40 passed** before adding the two real-upload cases; the final full-suite run below includes those cases.
- WebKit pronunciation modules: **42 passed** with `uv run pytest tests/e2e/test_pronunciation_attempt.py tests/e2e/test_pronunciation_review.py --browser webkit -q`, including un-intercepted MP4/AAC and WebM/Opus uploads through the real app.
- Earlier full `make test`: **1,448 passed**. Final `make test` after Safari lifecycle/test-boundary fixes and two additional real uploads: **1,450 passed** (54.74 seconds).
- `make lint` and `git diff --check`: passed. No implementation skips remain in the four activated modules.
- Inspected recorder and screen closure cleanup in addition to visible track/URL/UI checks; released-device heap acceptance remains outside this story.

- Run the four activated 7.2 test modules and existing pronunciation review tests; repeat both browser modules with `--browser webkit`.
- Run `make test` and `make lint`; inspect closure cleanup because visible state and track counts cannot prove Blob reachability.
- After implementation/review, commit to a feature branch, push and create a PR per AGENTS.md.

Matrix audit: every row ran and passed in the 41 backend / 42 browser checks: trusted Attempt + unknown Item (API trusted-target and locale tests), silence (provider all-Omission, API success mapping, browser warning/gate), invalid recordings (oversize/overlong/corrupt API tests), provider failures (HTTP/malformed/timeout integration and browser recovery), microphone unavailable (denied browser warning with playable Reference). The final 1,450-test suite includes all covering cases without implementation skips.

Final parent verification after review patch: `make test` **1,452 passed** (56.68s); WebKit pronunciation modules **44 passed** (37.17s); `make lint` and `git diff --check` passed. Quick review found one medium presentation issue, patched and verified; nothing deferred from this build. Real-device/released-wheel acceptance remains story 7.4.

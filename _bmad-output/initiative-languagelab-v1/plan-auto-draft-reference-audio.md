---
title: 'Generate Reference audio automatically for new Drafts'
type: 'feature'
ticket: ''
created: '2026-10-25'
status: 'built'
baseline_revision: '98153a450e6559813c633c23c547ae7fa86f9151'
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

**Problem:** A new Draft has no Reference audio until the user picks a Voice, presses Preview and then Use preview. Most Items are saved without audio as a result.

**Approach:** When a Draft opens, from Generate Draft or Write it myself, synthesize audio for its Target with the remembered Voice for its locale. Make that clip the Draft's accepted audio, so Save to Anki stores it with no extra click.

## Boundaries & Constraints

**Always:**
- User decision (2026-10-25): applies to both generated Drafts and Drafts written by hand, because the Target is the same in both. This reverses story 6.1's "Never: automatic synthesis" for Drafts only. Item detail stays explicit (Regenerate audio).
- Automatic synthesis runs once per Draft, after its Voice list loads. It needs a Voice and a non-blank Target. It uses the existing Preview request (`requestPreview`), so nothing is written to Anki, and it never autoplays.
- The clip becomes `accepted`, so Save sends `audio=replace` with its exact bytes. The existing player, the Preview/compare flow and Keep current / Use preview still work for later explicit Previews.
- A failure never blocks the Draft or Save: an inline notice with Try again, and Save stores the Draft without audio.
- After the automatic clip, Target edits show the existing "Audio no longer matches the text." warning, and Voice changes only store the preference. Neither resynthesizes.
- User decision (2026-10-25): a Save pressed while the automatic audio is in flight waits for it (busy "Making audio…"), then saves with the clip, or without audio if it fails.
- User decision (2026-10-25): acceptance is simple and UI only. No AnkiConnect or `/api` requests.

**Never:** Automatic synthesis on Item detail, on Target or Voice edits, or on rerenders. No new endpoints, backend changes or Anki writes before Save. No autoplay.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Generated Draft | Generate Draft succeeds, en or fr | One Preview request with the remembered or first Voice; a player shows the clip; Save stores it | — |
| Written Draft | Write it myself with the Capture text as Target | Same as Generated Draft | — |
| Blank Target / no Voices | Empty Target, or empty catalog | No request; Draft saves without audio | Voice-list failure: existing Try again; synthesis follows a successful retry |
| Failure | Preview request fails | Notice "Couldn't make the audio. The Draft will save without audio." with Try again | Save works without audio; a retry success becomes accepted |
| In flight | Save pressed while audio is being made | Save to Anki shows "Making audio…", stays busy, then saves with the clip | On failure it saves without audio |
| Edits | Target or Voice changed after the clip | Stale warning on a Target change; no new request | — |
| Explicit Preview | Preview after the automatic clip | Existing compare: Keep current / Use preview | Existing |
| Leave | Draft discarded or left during synthesis | Late reply ignored; Blob URLs revoked | — |

</frozen-after-approval>

## Code Map

- `src/language_lab/static/screens/make-item.js::referenceAudio` (L523–622): Draft card state (`accepted`, `offered`, `previewing`, `previewError`, `sequence`, `disposed`), `preview()` and `loadVoices()` (L595). `first` (L525) marks the first mount per Draft. Hook the one-time automatic synthesis there, after `loadVoices` resolves. The card is created at L397, and `itemPart` (L115) already sends `replace` when `draft.audio.accepted` is set.
- `src/language_lab/static/reference-audio.js`: `loadVoices`, `requestPreview` (sequence and dispose guard), `chooseVoice`. Reuse; don't change the Item card's behavior.
- `src/language_lab/static/screens/captures.js`: Draft lifetime and `disposeDraftAudio`; Save busy handling is in `make-item.js`.
- Tests asserting "no automatic synthesis" or a Draft Save with `audio=keep`, which the user decision reverses: `tests/e2e/test_draft_audio.py` (fallback without synthesis, empty catalog, Voice change, keep-intent Save), `test_make_an_item.py`, `test_generate_draft.py`, `test_reference_audio_journey.py`. Update their expectations to the new behavior; do not delete their other checks. Doubles: `tests/support/audio_screen.py`, `tests/fakes/speech.py`.
- `architecture-languagelab/architecture-languagelab.md` AD-14 Preview: add that a new Draft requests one Preview automatically.

## Tasks & Acceptance

**Execution:**
- [x] `static/screens/make-item.js` — one automatic synthesis per Draft into `accepted`, the failure notice with Try again, and the in-flight Save wait. Keep the explicit Preview flow.
- [x] `tests/e2e/test_draft_audio.py` (and the files listed above) — a test per Matrix row, at phone and desktop widths, for en and fr. Update the reversed expectations. A UI-only live-server case: Generate Draft → Save to Anki with no audio clicks → reopen the Item from search → the player holds the Draft's clip.
- [x] `architecture-languagelab.md` AD-14 — record the automatic Draft Preview.

**Acceptance Criteria:**
- Given a new Draft from either path, when the user only presses Save to Anki, then the Item has the automatically made audio.
- Given the full suite, when it runs, then it passes in Chromium and WebKit with no skips.

## Review Triage Log

Pass 1 (quick, 2026-10-25): high 0, medium 1, low 3, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| Save during Voice loading doesn't wait, so it saves without audio | medium | patch | `autoPending` is set only after `loadVoiceList` resolves, so `saveDraft` sees null and sends `keep`. Make `autoPending` cover the Voice load plus synthesis, and add a held-Voices Save test. |
| Failure Try again can synthesize a blank Target or with no Voice | low | patch | Unlike `preview()`, neither the button nor `synthesize()` checks them. Add the same guard. |
| `first_held` loop is unbounded | low | patch | It can hang instead of failing. Bound it and assert. |
| Failure and In-flight rows tested only on Write it myself | low | patch | Parametrize them over the Generate path too. |

After the patches, verification on my side: `make test` 1261 passed; `make test-webkit` 783 passed; `make lint` and `git diff --check` clean. Nothing deferred.

## Verification

**Commands:**
- `make test`, `make test-webkit`, `make lint`, `git diff --check`: expected clean.

**Manual checks (UI only, on the next release):**
- On the phone, from a Capture, Generate Draft and then Save to Anki without touching audio. In Anki Desktop the card plays the Target in your remembered Voice.
- Repeat with Write it myself, in French.
- Change the Voice after the clip appears: no new audio is made until you press Preview. Edit the Target: the stale warning appears.
- The failure notice is covered by the automated tests: it can't be caused from the UI without breaking the connection to LanguageLab itself.

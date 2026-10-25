---
title: 'French Reference audio Voices from fr-CA and fr-FR'
type: 'feature'
ticket: ''
created: '2026-10-25'
status: 'built'
baseline_revision: 'd2c582d8b3f731b6221147fd536c81dfec4f9111'
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

**Problem:** French Reference audio can only use `fr-CA` Voices. The user also wants France French (`fr-FR`) Voices.

**Approach:** User decision (2026-10-25): show one French Voice list that has both locales, grouped as "Canada" and "France". Audio is made in the chosen Voice's own locale. Each browser remembers one French Voice, whichever locale it is from. English stays `en-US` only.

## Boundaries & Constraints

**Always:**
- A Language has an ordered tuple of Voice locales: `en` → (`en-US`), `fr` → (`fr-CA`, `fr-FR`). That is the one source, in `domain/catalog.py`, and the client mirrors it in `reference-audio.js`.
- `GET /api/audio/voices?language=en|fr` replaces `?locale=`. It returns `{voices:[{name, locale, displayName}]}` for all of that Language's locales, in locale order, from a single provider catalog read. An unknown Language gets a 422.
- Preview (`POST /api/audio/preview {language, voice, target}`) validates that the Voice is in that Language's catalog, then synthesizes with that Voice's own locale (SSML `xml:lang`).
- Both cards (the Draft, including the automatic Draft audio, and Item detail) share the picker in `reference-audio.js`. For French, the `<select>` uses `<optgroup label="Canada">` and `<optgroup label="France">`. English has no groups.
- Preference: one key per Language: `languagelab.voice.en-US` (unchanged) and `languagelab.voice.fr`. When `fr` is unset, the stored `languagelab.voice.fr-CA` value is read as a fallback, so an existing choice survives. Only `voice-pref.js` touches localStorage. Fallback when nothing valid is stored: the first Voice listed (Canada first).
- User decision (2026-10-25): acceptance is simple and UI only. No AnkiConnect or `/api` requests.

**Never:** `fr-FR` for English, or any third locale. No changes to Save, media, or Anki; no pronunciation work.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| French list | French Draft or Item | One picker, "Canada" then "France" groups | Voice-list failure: existing Try again |
| fr-FR Voice | Pick a France Voice, Preview (or automatic Draft audio) | Synthesized with `fr-FR`; Save stores it as usual | Existing TTS failure |
| Preference | Pick a France Voice, open a new French Draft | That Voice preselected; English unaffected | Denied storage tolerated |
| Old preference | Only `languagelab.voice.fr-CA` stored | That Voice preselected | Unavailable Voice → first listed |
| English | English Draft or Item | `en-US` only, no groups | — |
| Validation | Preview with a Voice not in the Language's catalog (e.g. an English Voice for `fr`) | 422 | No synthesis |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/catalog.py` L28 `LOCALES = {EN: "en-US", FR: "fr-CA"}` → Voice locales per Language as tuples. It is used only by `features/audio/service.py` (L4, L14, L21).
- `src/language_lab/features/audio/{routes,service}.py`: `voices(locale)` → `voices(language)`; `preview` looks up the Voice in the Language's catalog and uses its `locale`. `ports/speech.py` and `adapters/azure/__init__.py::voices` (L40, one `voices/list` GET, filtered on `Locale ==`) → filter on a set of locales, keeping locale order. `synthesize(locale, …)` is unchanged.
- `src/language_lab/static/api.js::getVoices` → takes the Language. `static/reference-audio.js`:
  - `audioLocale` (L11): replace with the Language's preference key.
  - `chooseVoice`, `voicePicker` (optgroups from each Voice's `locale`).
  - `loadVoices`.
- `static/voice-pref.js`: the `fr` key, with the `fr-CA` read fallback. `static/screens/make-item.js` L528 and `item-detail.js` L134 call `audioLocale`. Update both call sites; the cards are otherwise unchanged.
- Tests and fixtures: `tests/fakes/speech.py` (add a `fr-FR` Voice), `tests/support/audio.py` (`EN_VOICE`, `FR_VOICE`, `VOICES_API`), `audio_screen.py`, `tests/fixtures/azure/catalog-example.json`, `tests/integration/test_azure_speech.py`, `tests/api/test_reference_audio.py`, `tests/e2e/test_draft_audio.py`, `test_item_audio.py`, `test_reference_audio_journey.py`. Update the `?locale=` expectations to `?language=`.
- `architecture-languagelab.md` AD-13 (Voice preference) and the PRD AC14 wording (`fr-CA`): record the French list and the single French preference.

## Tasks & Acceptance

**Execution:**
- [x] Backend: catalog tuples, the `voices(language)` route, service, port, Azure adapter and fake; Preview in the Voice's locale.
- [x] Client: `api.js`, `reference-audio.js` (optgroups, preference key), `voice-pref.js` fallback, and both call sites.
- [x] Tests per Matrix row: unit/API/integration for the backend; e2e for the Draft and Item cards at phone and desktop widths. Add a UI-only live-server case: a French Draft with a France Voice saves, and the reopened Item plays it.
- [x] Docs: AD-13 and AC14 wording.

**Acceptance Criteria:**
- Given a French Draft or Item, when the Voice picker opens, then it lists the Canada and France Voices in two groups, and audio is made in the chosen Voice's locale.
- Given the full suite, when it runs, then it passes in Chromium and WebKit with no skips.

## Review Triage Log

Pass 1 (quick, 2026-10-25): high 0, medium 0, low 5, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| Arch JSON-conventions row says the locale mapping lives "only in `domain`" | low | patch | `reference-audio.js` mirrors it, as the plan requires. Name it as the one client mirror. |
| PRD Glossary/scope and FR-26 heading still say French = `fr-CA` | low | patch | They contradict the updated FR-26/AC14. Clarify that Reference audio uses `fr-CA` and `fr-FR`, and pronunciation stays `fr-CA`. |
| Client drops Voices whose locale isn't mirrored, while `chooseVoice` can still pick one | low | reject | Not reachable: the server returns only the Language's mirrored locales. Guarding the drift would add a branch for a state the code can't produce. |
| Old-preference, denied-storage and Item unavailable-Voice cases run at phone width only, or are missing | low | patch | Parametrize over phone and desktop; add the Item unavailable-Voice case. |
| Fake speech comment overstates what its order proves | low | patch | Reword it; the adapter ordering is covered by the integration test. |

After the patches, verification on my side: `make test` 1297 passed; `make test-webkit` 841 passed; `make lint` and `git diff --check` clean. Nothing deferred.

## Verification

**Commands:**
- `make test`, `make test-webkit`, `make lint`, `git diff --check`: expected clean.

**Manual checks (UI only, on the next release, with real Azure):**
- Open a French Draft. The Voice list shows Canada and France groups. Pick a France Voice, and the automatic or explicit Preview sounds France French. Save to Anki, and the card plays it in Anki.
- Open a new French Draft: the France Voice is preselected. An English Draft still lists only US Voices.

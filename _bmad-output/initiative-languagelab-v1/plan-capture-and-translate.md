---
title: 'Capture and translate on the Captures screen'
type: 'feature'
ticket: ''
created: '2026-11-14'
status: 'built'
baseline_revision: '8cb9940cb2a5f56c1168869d7a72920897b2043d'
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

**Problem:** On the Captures screen the user can save a Capture but cannot see what it means without leaving the app. They want one action that saves the Capture and shows its translation.

**Approach:** Add a "Capture and translate" button to the compose card. It saves the Capture exactly like Save Capture, then asks a new LLM helper `POST /api/helpers/translate` for the Russian translation of the text and shows it inline in the compose card. A Language picker (English | French) at the top of the Captures screen says which language the captured text is in; it defaults to English and remembers its choice in localStorage.

**Decisions (2026-11-14):**
- The translation is always into Russian. The picker chooses the text's Language, only English or French (the existing `Language` enum / `LANGUAGES`).
- The translation shows inline in the compose card ("original → Russian"); the screen stays on the list.
- Show only: the translation lives in screen memory (AD-13), is not stored in Anki, and is gone when another Capture and translate runs, the text is edited, or the screen remounts.
- The picker sits at the top of the Captures screen beside the "Captures" heading, not in the app-wide header.

## Boundaries & Constraints

**Always:** Save first, using the same CaptureId/retry rules as Save Capture (AD-8, AD-20). Translate only after the save succeeds. The translation request goes through the existing `Llm` port and OpenRouter `_complete` path with a strict schema (AD-11). Nothing about the text is logged (AD-15). localStorage access is wrapped in try/catch like `voice-pref.js`; a missing or unknown stored value falls back to English. The button follows Save Capture's enabled rule (disabled while busy or blank).

**Never:** No new Anki fields or note-type changes. Do not change Save Capture, Make an Item or Example sentences behaviour. No translation of existing Captures from the list (out of scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | "jump to conclusions", picker = English (default) | Capture saved; compose box cleared; card shows "jump to conclusions → делать поспешные выводы" | No error expected |
| PICKER_CHANGED | picker set to French, page reloaded | Picker shows French; next request sends `language: "fr"` | No error expected |
| SAVE_FAILS | Anki unreachable | Same alert as Save Capture; no translate request; text kept | Try again retries save then translate |
| TRANSLATE_FAILS | save OK, model unreachable/invalid twice (502) | Capture stays saved and listed; card shows "Couldn't translate" alert | Try again re-asks only the translation |
| BAD_INPUT | blank text or unknown language to API | 422 `validation_failed`, model not asked | Error envelope |
| STORAGE_BLOCKED | localStorage throws | Picker shows English; choice works for the session | Silently ignored |

</frozen-after-approval>

## Code Map

- `src/language_lab/static/screens/captures.js` -- compose card (`mount`, ~L244-262), `submit()` (~L981), `renderButtons()`, `renderDetail()`; reuse `submit`'s save path, `saveFailure`, `alertBox`, `tryAgain`, `navigate(capturePath(id))`.
- `src/language_lab/static/voice-pref.js` -- the sole localStorage owner; add translation-language read/write here (key `languagelab.captureLanguage`, values `en`|`fr`).
- `src/language_lab/static/api.js` -- add `translateText(body)` mirroring `exampleSentences` (L167).
- `src/language_lab/static/css/studio.css` -- `.compose-card` (L375) and `main h1` styles; add a small header row for heading + picker and a translation block style.
- `src/language_lab/features/helpers/routes.py` / `service.py` -- add `TranslateRequest` and `POST /api/helpers/translate`, `HelperService.translate`.
- `src/language_lab/domain/helpers.py` -- add `Translation` answer model (`russian: NonBlank`) and `translation_json_schema()`; reuse `Language` from `domain/catalog.py`.
- `src/language_lab/ports/llm.py` -- add `translate(language, text) -> Translation` to the protocol.
- `src/language_lab/adapters/openrouter/__init__.py` -- add `_TRANSLATE_PROMPT` and `translate()` via `_complete`.
- `tests/fakes/llm.py` -- add `translate` with recorded requests and an overridable reply/failure.
- Tests to mirror: `tests/api/test_helpers_examples.py`, `tests/support/helpers.py`, `tests/e2e/test_example_sentences.py`, `tests/support/examples_screen.py`, `tests/unit/test_helpers_domain.py`, `tests/integration/test_openrouter_helpers.py`.

## Tasks & Acceptance

**Execution:**
- [ ] `src/language_lab/domain/helpers.py` -- add `Translation` model (`russian: NonBlank`) and `translation_json_schema()` -- wire + strict schema.
- [ ] `src/language_lab/ports/llm.py`, `adapters/openrouter/__init__.py`, `tests/fakes/llm.py` -- add `translate` -- new LLM capability.
- [ ] `src/language_lab/features/helpers/{routes,service}.py` -- `POST /api/helpers/translate` `{language, target}` → `{russian}` -- endpoint.
- [ ] `src/language_lab/static/voice-pref.js`, `static/api.js` -- pref read/write and `translateText` -- client plumbing.
- [ ] `src/language_lab/static/screens/captures.js`, `static/css/studio.css` -- picker beside the heading, "Capture and translate" button, inline translation block in the compose card, failure + Try again -- UI.
- [ ] `tests/api/test_helpers_translate.py`, `tests/unit/test_helpers_domain.py`, `tests/integration/test_openrouter_helpers.py`, `tests/e2e/test_capture_and_translate.py` (+ support module) -- cover the I/O matrix.

**Acceptance Criteria:**
- Given a fresh browser, when the Captures screen opens, then the translation-language picker shows English.
- Given text in the compose box, when the user presses "Capture and translate", then the Capture appears in the list and its Russian translation shows in the compose card.
- Given the user picks another language, when they reload, then the picker still shows that language.
- Given the translation fails after a successful save, when the user presses Try again, then only the translation is re-requested and no second Capture is made.

## Design Notes

The translation service is a sibling of `examples`: same `_complete`, own system prompt ("translate the Target from its Language into natural Russian, keeping register; one translation, not a dictionary list"). The translation lives in screen memory only (AD-13), like example results.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test-fast` -- expected: all pass
- `uv run pytest -m e2e tests/e2e/test_capture_and_translate.py tests/e2e/test_captures_compose.py tests/e2e/test_example_sentences.py` -- expected: all pass

## Implementation Notes

- No navigation after Capture and translate (the decision says the screen stays on the list); `navigate(capturePath(id))` in the Code Map was not used.
- Plain Save Capture and a picker change leave an on-screen translation in place; an edit clears it.
- E2E texts carry a unique suffix because Captures persist across tests on the live server.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0 · medium 0 · low 5 · false 0 · maybe-false 0

| # | Finding | Verdict | Route | Evidence |
|---|---------|---------|-------|----------|
| 1 | captures.js `submit()`: translation shown beside text edited during the save | low | patch | `clearTranslation()` nulls `translation.request` before the save, so `onInput` skips clearing; `runTranslation` then fires though the box kept new text. Fix: translate only when `box.value === text`. |
| 2 | Translation Try again not disabled while a Save is busy | low | reject | Token guard keeps state consistent; rarely met; fix adds a branch to `renderButtons`. |
| 3 | `tests/fakes/llm.py` `translate_error` unused | low | patch | No caller passes it; deletion. |
| 4 | No e2e for clearing on a second run or remount | low | reject | Remount clearing is inherent (module memory); second run calls `clearTranslation()` directly; added tests only. |
| 5 | Integration docstring "either helper" stale; adapter log test not extended to translate | low | patch (docstring) / reject (log test) | Docstring is a direct correction; API test `test_the_text_and_translation_are_not_logged` covers AD-15. |

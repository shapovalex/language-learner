---
title: 'Refactor sweep: Pronunciation review'
type: 'refactor'
ticket: '3'
created: '2026-10-25'
status: 'built'
baseline_revision: '4d05d6701bcc2118d1bd2993adcc1a52a1fac929'
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

**Problem:** Stories 7.1 and 7.2 left repeated logic in the pronunciation feature, the Anki queue and answer paths, the Azure assessment and the review screen: an inline Language→assessment-locale mapping, repeated reply-list validation in the adapter, twin multipart header callbacks, repeated capture-state checks, focus calls and result handling in the screen, and a duplicated fixtures path in test support.

**Approach:** Consolidate each repeat into one helper or constant at its natural home, without changing behavior, copy, wire contracts, CSS or test expectations. Record in this plan how every 7.1 and 7.2 review finding was settled.

## Boundaries & Constraints

**Always:** Behavior-preserving. Every existing test passes with no assertion edited (imports and support-helper consolidation only). Only `api.js` fetches. The ease mapping stays in the Anki adapter, locale shaping in `domain/pronunciation.py`. Lock holds, guard, Setup gate and the AD-20 reps check stay as they are. Status codes and error codes are unchanged for every input, including malformed multipart.

**Never:** New capability, copy, endpoints, wire fields or CSS changes. No new deferred-work entries for CAP-10 scope. The two rejected 7.1 findings (1b: one copy for every Rating failure; 3b: a stale queue on show-again) stay rejected, as the 7.1 triage decided. Older non-epic-7 code is touched only where a new shared helper replaces an identical block.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Attempt locale | `en` / `fr` Attempt | Speech gets `en-US` / `fr-CA`, from one mapping | Same 404/413/422/503 |
| Multipart | header >8 KiB, itemId >36 bytes, oversize recording or stream | Same 422 / 413 as before | Zero Azure calls on refusal |
| Queue and Rating replies | malformed list, `{}` entries, wrong length | Same `ANKI_UNAVAILABLE`, same skipped entries | — |
| Review screen | record, retry, fail, silence, rate, leave | Same states, labels, focus targets and announcements | Same alerts |

</frozen-after-approval>

## Code Map

- `src/language_lab/features/pronunciation/service.py:28` -- inline `"en-US" if language == Language.EN else "fr-CA"`. Home: `domain/pronunciation.py` (owns the `Literal["en-US","fr-CA"]` locale policy). Don't reuse `catalog.LOCALES` (that is the Voice list; `fr` there has two locales).
- `src/language_lab/domain/pronunciation.py::Assessment.from_azure` -- `prosody=... if locale == "en-US" else None` repeats what the `locale_feedback` validator already enforces for `fr-CA`.
- `src/language_lab/features/pronunciation/upload.py::read_attempt` -- `header_field`/`header_value_part` share the 8192-byte budget check; magic `8192`, `36` (UUID length), `16384` stream slack and `200` boundary length; an odd parenthesized ternary in `data_part`.
- `src/language_lab/adapters/anki/store.py` -- `_queued_cards` (L197), `_notes_by_id` (L219) and `_note_infos` (L675) each repeat "list of the expected length, `{}` skipped, non-dict → `ANKI_UNAVAILABLE`"; the `findCards`/`findNotes` id-list check repeats at L565 and L681. `answer_card` has three consecutive `NOT_FOUND` scope checks and a misrapped docstring. Keep queue ordering, lock scope and the `{}`-means-unknown-card handling.
- `src/language_lab/static/screens/pronunciation.js` -- `attemptState === "recording" || === "permission"` in `playReference`, `targetCard` and `startRecording`; `body.querySelector('[data-control="record"]')?.focus()` four times; the `then`/`catch` tails of `complete` repeat `attemptRequest = null; attemptState = "result"; render(); focus`; `ratingRow` builds buttons by hand while `action()` exists; the record labels and alert copy tables live inside functions (module constants like `RATINGS`); `scoresCard` re-checks `lang === "fr"` for Prosody (the domain already nulls it); `feedbackClass` and the error-type label are long one-line ternaries. `alert.className = ...` overrides `alertBox`'s class for warnings. Header comment still reads as 7.1.
- `src/language_lab/static/dom.js::alertBox` -- 19 callers; add an optional warning variant only if it keeps every existing call unchanged, else leave the override.
- `src/language_lab/static/api.js::sessionSignal,sessionBeacon` -- both build the session path.
- `src/language_lab/static/attempt-recorder.js:71` -- `30_000` beside exported `MAX_ATTEMPT_BYTES`; export `MAX_ATTEMPT_SECONDS` and use it.
- `tests/support/attempt_screen.py:33` -- `SAMPLES` equals `assessment.FIXTURES`. `attempt_screen.assessment()` and `assessment.assessment_wire()` are intentionally different (hand-built vs real-fixture values); keep both.
- Findings to settle: 7.1 pass 1 (1a, 2, 3a, 4 patched; 1b, 3b rejected); 7.2 pass 1 (one patched). `deferred-work.md` has no epic-pronunciation-review entry.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/pronunciation.py`, `features/pronunciation/service.py` -- add `ASSESSMENT_LOCALE: dict[Language, ...]` and use it in `attempt`; keep the prosody conditional in `from_azure` (it precedes validation) -- one locale policy home.
- [x] `src/language_lab/features/pronunciation/upload.py` -- named limits, one header-budget helper, plain error-code choice -- same outcomes per input.
- [x] `src/language_lab/adapters/anki/store.py` -- shared `_present_entries(reply, expected)` and `_id_list(reply)` helpers used by the queue, `_notes_by_id`, `_note_infos` and both find calls; one scope predicate in `answer_card`; fix its docstring wrap.
- [x] `src/language_lab/static/screens/pronunciation.js` (+ `dom.js` if the variant fits, `api.js`, `attempt-recorder.js`) -- `capturing()`, `focusRecord()`, one result-settle helper, `action()` for Rating buttons, hoisted label/copy tables, readable `feedbackClass`/error label, dropped redundant Prosody check, updated header comment; one session-path helper; `MAX_ATTEMPT_SECONDS`.
- [x] `tests/support/attempt_screen.py` -- read samples via `assessment.FIXTURES`.
- [x] This plan's Implementation Notes -- findings ledger: each 7.1/7.2 finding, its resolution, whether it still holds, and why nothing remains outside this epic.

**Acceptance Criteria:**
- Given the refactor, when the pronunciation, Azure, Anki adapter and review-screen suites run on Chromium and WebKit, then all pass with no assertion edited.
- Given the sweep, when `service.py`, `upload.py`, `store.py` and `pronunciation.js` are searched, then none still contains the inline locale ternary, twin header callbacks, repeated reply-list checks or repeated record-focus query.

## Implementation Notes

**Consolidations made**

- Locale: `ASSESSMENT_LOCALE` (with an `AssessmentLocale` alias used by `Assessment.locale`) in `domain/pronunciation.py`; `PronunciationService.attempt` indexes it. `from_azure` keeps its `en-US`-only prosody read (restored by the parent after implementation): it runs before field validation, so dropping it would let an out-of-range French `ProsodyScore` fail the reply, a behavior change.
- Multipart: `MAX_HEADER_BYTES`, `MAX_BOUNDARY_BYTES`, `UUID_LENGTH`, `STREAM_SLACK_BYTES`; one `header_bytes(target)` factory serves both header callbacks with the shared budget; `data_part` picks its error code with a plain conditional.
- Anki adapter: `_id_list` (both `findCards` and `findNotes`) and `_present_entries` (`_queued_cards`, `_notes_by_id`, `_note_infos`). `answer_card` folds its three `NOT_FOUND` checks into one `in_scope` predicate (short-circuited, so `card_deck` is still only asked for a Language model) and its docstring is rewrapped.
- Screen: `capturing()`, `focusRecord()`, one `settle(update)` for both Attempt outcomes, Rating buttons from `action()`, module tables `RECORD_LABELS`, `ATTEMPT_ALERTS`, `ERROR_LABELS`, an if-chain `feedbackClass`, no `lang === "fr"` Prosody check, a header comment covering 7.2. `api.js` gains `sessionPath`; `attempt-recorder.js` exports `MAX_ATTEMPT_SECONDS`.
- `dom.js::alertBox` left unchanged: its `(className, ...children)` rest signature has no room for an optional variant without touching its 19 callers, so the screen keeps its `className` override for warnings.
- `tests/support/attempt_screen.py` reads probe media from `assessment.FIXTURES`; `SAMPLES` is gone. Both `assessment()` helpers stay.

**Findings ledger**

| Story / finding | Resolution | Still holds | Why |
|---|---|---|---|
| 7.1 #1a: `not_found` on Rating showed the reachability alert | patched | yes | `submit()` re-reads the queue on `not_found` (unchanged by this sweep). |
| 7.1 #1b: `anki_busy`/network share "Anki isn't reachable" | rejected | yes (rejected) | EXPERIENCE.md fixes the copy; a UX decision, not a refactor. Untouched. |
| 7.1 #2: focus lost on re-render | patched | yes | `render()` still restores focus to the same control, else Record. |
| 7.1 #3a: session started while hidden | patched | yes | `load()` still starts only when `visibilityState !== "hidden"`. |
| 7.1 #3b: stale queue on show-again | rejected | yes (rejected) | Harmless (AD-20 `alreadyAnswered`/404 then re-read). Untouched. |
| 7.1 #4: Rating ignored `queue`/deck | patched | yes | Now part of the single `in_scope` predicate in `answer_card`: `queue >= 0` and `deckName == card_deck(model, 3)`. |
| 7.2 #1: phone placed Rating before Assessment | patched | yes | `render()` still appends `scoresCard()` before `ratingRow()`. |

Nothing remains outside this epic: every finding is patched or rejected by its story's triage, and `deferred-work.md` has no epic-pronunciation-review entry; this sweep adds none.

**Risk noted**

- The `from_azure` prosody conditional was first dropped, then restored: without it an `fr-CA` reply with an out-of-range `ProsodyScore` would fail validation (503) instead of being nulled, which breaks the behavior-preserving rule.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — 2026-10-25: high 0, medium 0, low 1, false 0, maybe-false 0

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Ledger task left unchecked though the ledger is written | low | reject | Real but plan-only: the ledger under Implementation Notes matches the 7.1/7.2 triage logs. A fix that edits this build's plan is rejected by rule; the box was ticked as bookkeeping. |

Before review, the parent restored `from_azure`'s `en-US`-only prosody read after the diff read showed that dropping it changed the outcome for an out-of-range French `ProsodyScore` (frozen intent: behavior-preserving).

## Verification

**Commands:**
- `uv run pytest tests/api/test_pronunciation.py tests/api/test_pronunciation_attempt.py tests/integration/test_anki_pronunciation.py tests/integration/test_attempt_audio.py tests/integration/test_azure_assessment.py tests/integration/test_azure_speech.py tests/integration/test_anki_prefix_guard.py tests/unit -q` -- expected: pass
- `uv run pytest tests/e2e/test_pronunciation_review.py tests/e2e/test_pronunciation_attempt.py --browser chromium --browser webkit -q` -- expected: pass
- `make test`, `make lint`, `git diff --check` -- expected: clean

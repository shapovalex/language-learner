---
title: 'Verify Pronunciation review end to end on the released wheel'
type: 'chore'
ticket: '4'
created: '2026-10-25'
status: 'built'
baseline_revision: 'f2d60a4cedc7f2a9070f82144ca7c57a9f2b3d25'
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

**Problem:** Stories 7.1 and 7.2 test the review screen against page-local API doubles. Nothing drives a real review session through the running app (queue → Reference → Attempt → feedback → Rating → next Card → empty state), and the epic has no released-wheel acceptance record.

**Approach:** Add one integrated Playwright journey against a live app, driven and checked only through the UI. Write a short acceptance checklist the user runs on the released wheel using only the LanguageLab UI and the Anki Desktop / AnkiMobile UI.

## Boundaries & Constraints

**Always:**
- User decision (2026-10-25, "keep acceptance small and UI oriented", same as 6.4): no API requests to Anki or the app in checks (`curl`, `page.request`, `/api/...` assertions). This replaces the ticket's `language-lab-record-fixtures anki` subcommand and the sanitized Azure reply comparison. Both are recorded in deferred-work; the hand-built AnkiConnect exchanges stay.
- The journey runs the real app on its own live server with a seeded `FakeAnkiStore` (per Language: one due and one new Pronounce Card; the due one has Reference audio in `media`) and a `FakeSpeech` whose `assessment` is the real Azure fixture parsed by the real adapter. Its only browser double is the existing fake microphone (`install_microphone`). It acts only through roles and labels and observes only the page.
- The manual checklist runs on the Mac Mini with `uvx` and the wheel only, `ANKI_PREFIX=LanguageLabDev`, and real Azure. It uses iPhone Safari, iPad Safari and a desktop browser over Tailscale HTTPS, plus Anki Desktop (Browse, card info) and AnkiMobile. Every result starts as `not run`.
- No production code changes. If the journey finds a bug, record it and stop. Don't fix it here.

**Never:** Raw AnkiConnect or Azure reply capture, `curl` steps, a release cut, edits to ticket files, or invented manual passes. Push the branch and create a PR (AGENTS.md).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Open | `/{lang}/pronunciation` | Chip "1 due, 1 new"; due Card's Target; Ratings disabled | — |
| Reference | Play reference audio | Player source is the seeded clip | — |
| Attempt | Record, stop | Score ring and Word feedback. en: IPA phonemes and prosody. fr: start/middle/end positions, no sound named | — |
| Retry | Try again, stop | New feedback; Card still current; Ratings enabled | — |
| Rate | Good | Next (new) Card's Target; chip "0 due, 1 new"; feedback cleared | — |
| Finish | Record, Easy | Empty state "Nothing to practice in {Language}" | — |

</frozen-after-approval>

## Code Map

- `tests/support/live_server.py::run_live_server` -- hard-codes `FakeAnkiStore()`/`FakeSpeech()`. Add optional `anki_store`/`speech` keyword arguments (defaults unchanged) so the journey can seed them. Update its `tests/README.md` row.
- `tests/support/attempt_screen.py` -- reuse `install_microphone`, `finish_attempt`, `record_button`, `score_ring`, `word_feedback`. Do not use `AttemptApi`/`ReviewApi` (page doubles).
- `tests/support/pronunciation_screen.py` -- reuse `queue_chip`, `target_text`, `rating_button`, `reference_button`, `RATINGS`, `EMPTY_TITLE`, `LANGUAGES`.
- `tests/support/assessment.py` -- `FIXTURES`, `EN_REPLY`, `FR_REPLY`, `assess_wire` (real `AzureSpeech` over the offline replay). Build the seeded `Assessment` from it, as `tests/integration` does, not from the hand-built `assessment()`.
- `tests/fakes/anki_store.py` -- seed `pronounce` with `(Language, is_due, PronounceCard)` and `media`. `answer_card` drops the Card. Setup is READY by default. `src/language_lab/domain/pronunciation.py::PronounceCard`.
- `tests/support/audio.py` -- `MP3`, `managed_name`. `tests/support/item_audio_screen.py::player_bytes` or `audio_screen.rendered_audio_bytes` read what the player holds.
- `tests/e2e/test_reference_audio_journey.py` -- model for module docstring, parametrization and `p0` marker.
- `_bmad-output/test-artifacts/acceptance/reference-audio-acceptance-6-4.md` -- model for the checklist layout (Setup, Done-when table, criterion rows, Recorded run). Install from `docs/install.md`. Latest tag is `v1.0.0`; this epic ships next, so the tag field stays blank.

## Tasks & Acceptance

**Execution:**
- [x] `tests/support/live_server.py` -- add optional `anki_store`/`speech` parameters -- the journey needs a seeded store without changing the shared `live_server`.
- [x] `tests/e2e/test_pronunciation_journey.py` (new) -- a function-scoped seeded server on its own socket, so each case gets a fresh store. One `p0` journey parametrized English/French × phone/desktop runs every Matrix row in order.
- [x] `_bmad-output/test-artifacts/acceptance/pronunciation-review-acceptance-7-4.md` (new) -- frontmatter `status: not-run`. Sections: Setup (install the wheel, LanguageLabDev, two disposable Items per Language with audio, note their Card info "Reviews" counts); one table for Done-when 1–6. Rows: mic permission prompt on each device; mic-blocked after Deny; en-US feedback (IPA, prosody); fr-CA feedback (positions only); retry leaves the Card unchanged in Anki Browse; Rating changes due date/Reviews in Anki Desktop and AnkiMobile after Sync; Anki closed during a Rating keeps the Card current; Sync time in Anki after starting, finishing and closing the tab mid-session; nothing to delete afterwards (Check Media unchanged). Then a Recorded run table. Each row says what to do in which UI and what you should see. Link the automated journey.
- [x] `_bmad-output/initiative-languagelab-v1/deferred-work.md` -- append entries for the fixture recorder subcommand and the Azure reply comparison.

**Acceptance Criteria:**
- Given the new journey, when it runs in Chromium and WebKit, then all four cases pass, with no `page.route`, no `page.request` and no store or `/api` assertions.
- Given the checklist, when it is read, then every check is a tap or click in LanguageLab, Anki Desktop or AnkiMobile, and each of the six Done-when checks has at least one row.

## Implementation Notes

- The Reference player is a detached `<audio>` (never in the DOM), so `player_bytes`/`rendered_audio_bytes` can't see it. The journey's init-script probe records the source each media element is asked to `play()` and fetches it in-page, as those helpers do.
- `assess_wire` runs through `tests.support.aio.run`: Playwright's sync API keeps a loop running, so `asyncio.run` is refused.
- The seeded attempt service reads the Item (`get_item`), so the store holds both Items in `items` too. Due Targets ("I thought so", "Bonjour, Marie") differ from the fixture's word so the word pill and the Target never share exact text.
- Logs (DW5, NFR-7) aren't visible in any UI; the checklist points at the existing API log tests for that part.
- The journey found no bug.

## Plan Change Log

## Review Triage Log

Pass 1 (quick, 2026-10-25): high 0, medium 4, low 2, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| `played_bytes()` fetches `/api/media` from the test and asserts the reply | medium | patch | Breaks the frozen "no /api assertions" rule. Replace it with passive observation of the browser's own media request, and assert that it names the seeded clip. |
| `PLAYED_PROBE` patches `HTMLMediaElement.play` (a second browser double) | medium | patch | The frozen rule allows only the fake microphone. The probe is removed by the same fix. |
| DW1/DW4 can't make E1/F1 current when other Pronounce Cards are queued | medium | patch | `pronunciation.js` has no skip control. Setup now checks that the LanguageLabDev queue holds only the four Cards. |
| DW3 Good/Hard on new Cards puts them back in the queue as learning Cards before DW6 | medium | patch | The queue query is `(is:due OR is:new)` and default learning steps apply. Rate Easy instead. |
| No check that a retried Rating is applied only once (AC17) | low | patch | Add a double-tap check, and point to the 7.1 automated tests for the lost-reply retry. |
| Done-when 6's hidden-tab and failed-Assessment parts have no row | low | patch | Add a hidden-app step to the Sync row, and point to the 7.2 automated test for the failed Assessment. |

After the patches (commit e237739, plus a correction from `card:3` to `card:4`, the 1-based Pronounce template that `store.py` passes as `PRONOUNCE_ORD + 1`): journey 8 passed in Chromium and WebKit; `make test` 1456 passed; `make lint` and `git diff --check` clean. Nothing deferred.

## Design Notes

UI-only ways to see the Anki side: Browse → Card Info shows Reviews, the Due date and the last Rating, so a retry (no change) and one Rating (one review) are both visible. AnkiMobile's deck list counts drop by one per Rating after Sync. Sync on start/end shows as Anki Desktop's sync indicator, and as AnkiMobile picking up the Rating without a manual desktop sync.

## Verification

**Commands:**
- `uv run pytest tests/e2e/test_pronunciation_journey.py --browser chromium --browser webkit -q` -- expected: 8 passed.
- `make test`, `make lint`, `git diff --check` -- expected: clean.

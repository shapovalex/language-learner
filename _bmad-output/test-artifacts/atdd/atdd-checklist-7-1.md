---
runScope: "story"
runKey: "story-7-1"
workflowStatus: "completed"
stepsCompleted: ["step-01-preflight-and-context", "step-02-generation-mode", "step-03-test-strategy", "step-04-generate-tests", "step-04c-aggregate", "step-05-validate-and-complete"]
lastStep: "step-05-validate-and-complete"
lastSaved: "2026-10-25"
storyId: "7.1"
storyKey: "7-1"
storyFile: ""
storySource: "_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/tickets.toml (entry 1)"
atddChecklistPath: "_bmad-output/test-artifacts/atdd/atdd-checklist-7-1.md"
generatedTestFiles:
  - "tests/api/test_pronunciation.py"
  - "tests/integration/test_anki_pronunciation.py"
  - "tests/e2e/test_pronunciation_review.py"
inputDocuments:
  - "AGENTS.md"
  - "_bmad/config.toml"
  - "_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/tickets.toml (entry 1)"
  - "_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/epic-pronunciation-review.md"
  - "_bmad-output/initiative-languagelab-v1/tickets.toml (epic 7 after)"
  - "_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-30 to FR-36, AC16 to AC20)"
  - "_bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md (A5, A6)"
  - "_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-1, AD-2, AD-4 to AD-7, AD-13, AD-14, AD-17, AD-20)"
  - "_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Pronunciation review, states, J3)"
  - "_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Review.dc.html"
  - "_bmad-output/test-artifacts/atdd/atdd-checklist-6-2.md"
  - "pyproject.toml"
  - "tests/README.md"
  - "tests/conftest.py"
  - "tests/support/anki_state.py"
  - "tests/support/item_delete.py"
  - "tests/fakes/anki_store.py"
  - "tests/fakes/sync_requester.py"
  - "src/language_lab/ports/anki_store.py"
  - "src/language_lab/ports/sync_requester.py"
  - "src/language_lab/features/sync/service.py"
  - "src/language_lab/app.py"
  - ".agents/skills/bmod-tea/knowledge/data-factories.md"
  - ".agents/skills/bmod-tea/knowledge/component-tdd.md"
  - ".agents/skills/bmod-tea/knowledge/test-quality.md"
  - ".agents/skills/bmod-tea/knowledge/test-healing-patterns.md"
  - ".agents/skills/bmod-tea/knowledge/test-levels-framework.md"
  - ".agents/skills/bmod-tea/knowledge/test-priorities-matrix.md"
  - ".agents/skills/bmod-tea/knowledge/ci-burn-in.md"
acceptanceCriteria:
  - {"id": "AC-1", "idSource": "generated", "text": "The queue holds only the Language's new and due, unsuspended Pronounce Cards (ord 3) in its Pronunciation decks under the Prefix."}
  - {"id": "AC-2", "idSource": "generated", "text": "The queue is in FR-30 order: due Cards first, oldest due first, then new Cards in creation order."}
  - {"id": "AC-3", "idSource": "generated", "text": "The queue read returns the due and new counts and, per Card, its cardId, itemId, reps, Category, Target text and saved Reference audio name."}
  - {"id": "AC-4", "idSource": "generated", "text": "The Pronunciation screen shows the current Card's Target text and the \"N due · M new\" chip (aria-label \"N due, M new\") on phone and iPad layouts."}
  - {"id": "AC-5", "idSource": "generated", "text": "An empty queue shows \"Nothing to practice in <Language>\" / \"No new or due Pronounce Cards right now.\" and no Rating buttons."}
  - {"id": "AC-6", "idSource": "generated", "text": "The first Card is read and shown before the pre-session Sync is requested, with no Sync UI, and a slow pre-session Sync never delays it."}
  - {"id": "AC-7", "idSource": "generated", "text": "Reference plays the Card's audio from /api/media on tap; a Card without Reference audio shows no Reference control."}
  - {"id": "AC-8", "idSource": "generated", "text": "A Rating is answered through Anki's scheduler for that Card only, with again/hard/good/easy mapped to ease 1-4 in the adapter."}
  - {"id": "AC-9", "idSource": "generated", "text": "Tapping Again, Hard, Good or Easy (always enabled in 7.1) submits that Card's Rating with its reps and, once Anki confirms, loads the next Card and updates the chip."}
  - {"id": "AC-10", "idSource": "generated", "text": "A retried Rating whose reps no longer match Anki's returns success marked alreadyAnswered and sends no second answer (AD-20)."}
  - {"id": "AC-11", "idSource": "generated", "text": "A failed Rating shows \"Rating not saved — Anki isn't reachable.\" with Try again, and the Card stays current and unanswered."}
  - {"id": "AC-12", "idSource": "generated", "text": "Idempotent session start and end endpoints each request one Sync and never wait for it; requests coalesce to at most one running and one pending Sync (AD-17)."}
  - {"id": "AC-13", "idSource": "generated", "text": "The client sends the session end signal when the review screen unmounts (also on hidden, pagehide via sendBeacon, and an empty queue)."}
  - {"id": "AC-14", "idSource": "generated", "text": "In dev mode (LANGUAGE_LAB_DEV=1) session start and end succeed and request no Sync."}
---

# ATDD Checklist: Story 7.1 — Review loop: queue, Reference playback, Rating, and session Sync

## Preflight

Create mode inferred from the explicit story request ("epic 7 story 1"). Approved high-risk
ticket entry 1 in `epic-pronunciation-review/tickets.toml` is the story source; no leaf story
file exists. Its prerequisites are merged on main: 2.8 (SetupState gate), 2.10 (Sync
scheduler/SyncRequester), 4.1 (Pronounce Cards in Pronunciation decks), 6.1 (Azure adapter,
`/api/media`). No pre-existing 7-1 checklist; fresh run on `main` (87f96b9).

Stack detection: backend (pyproject.toml, no package.json), with a static browser client and
Python Playwright (pytest-playwright). No epic-7 or system test design exists in `test-design/`
or the legacy root; priorities derive from the ticket's high risk and AD-17/AD-20. Playwright-
utils and Pact flags are true but their gates are closed (no package.json, no JS runner, no
Pact artifacts); only the seven core/backend fragments in inputDocuments apply. Browser coverage
stays because the story explicitly promises phone and desktop Playwright for the review screen.

Registry: generated ids in source order from the ticket description, then its verify clause,
with copy fixed by EXPERIENCE.md (queue chip, empty state, Rating failure).

Already satisfied on main (no red leaf): the SyncService coalescing itself
(`tests/unit/test_sync_service.py`) and dev-mode Sync suppression at the lifespan
(`tests/api/test_sync_lifespan.py`). AC-12/AC-14 cover only the new session endpoints' use of it.

## Generation mode

AI generation from the ticket, PRD, architecture, UX copy and existing Python tests. No
recording: the backend stack mandates AI generation and the review screen is a placeholder `h1`.

## Test strategy

One primary red-phase leaf per criterion. AC-4 is parametrized over phone (en) and iPad (fr)
because the criterion names both layouts; it is one leaf.

| Criterion | Level | Priority | Primary first-failing assertion |
| --- | --- | --- | --- |
| AC-1 | Integration | P0 | queued card-id set equals the due and new in-scope Pronounce cards |
| AC-2 | Integration | P0 | queued card ids in due-oldest-first, then creation order |
| AC-3 | API | P0 | first queued Card equals `{cardId, itemId, reps, category, target, audio}` |
| AC-4 | E2E | P1 | chip labelled "3 due, 2 new" reads "3 due · 2 new" |
| AC-5 | E2E | P1 | "Nothing to practice in French" visible |
| AC-6 | E2E | P0 | first Card's Target visible while session start is held unanswered |
| AC-7 | E2E | P1 | Reference tap requests `/api/media/<the Card's managed name>` |
| AC-8 | Integration | P0 | `answerCards` received exactly `[{cardId, ease: 2}]` for Hard |
| AC-9 | E2E | P0 | next Card's Target visible after Good |
| AC-10 | API | P0 | retry answers `alreadyAnswered: true` |
| AC-11 | E2E | P0 | Rating alert copy visible after a 503 |
| AC-12 | API | P0 | one Sync requested right after session start, while it is still running |
| AC-13 | E2E | P0 | session end request sent on leaving to Items |
| AC-14 | API | P1 | dev-mode start/end answer 204 (then zero Syncs) |

P0: AC-1/2/3/6/8/9/10/11/12/13 (scheduling integrity, AD-20 idempotence, AD-17 non-blocking).
P1: AC-4/5/7/14.

Red-phase rules: each leaf's first assertion isolates the newly promised value; transition
criteria perform the transition (Rating, failed Rating then Try again, retried Rating, leaving
the screen). AC-10's first Rating is an opaque setup call. Module-level reasoned
`pytest.mark.skip` until task activation.

## Execution mode

Config `auto`, capability probe on. Resolved mode: **sequential** (API → E2E) in the main
session; this harness spawns subagents only on explicit request. Workers' registries are the
one registry above. Node-only playwright-utils/Pact mandates are inapplicable (no package.json,
JS runner or Pact artifacts), so there are no deviations to roll up.

## Generated scaffolds and coverage

15 executable leaves (14 functions; AC-4 runs twice): 4 API, 3 adapter integration, 7 browser
functions. Every file has a reasoned module-level `pytest.mark.skip`. Each leaf's docstring
carries exactly one id.

| Criterion | Primary scaffold |
| --- | --- |
| AC-1 | `tests/integration/test_anki_pronunciation.py::TestPronunciationQueue::test_queue_holds_only_the_languages_new_and_due_unsuspended_pronounce_cards` |
| AC-2 | `tests/integration/test_anki_pronunciation.py::TestPronunciationQueue::test_queue_is_due_first_oldest_due_first_then_new_in_creation_order` |
| AC-3 | `tests/api/test_pronunciation.py::TestQueueRead::test_the_queue_read_carries_counts_and_each_cards_identity_reps_and_audio` |
| AC-4 | `tests/e2e/test_pronunciation_review.py::TestReviewLoop::test_the_screen_shows_the_queue_chip_and_the_current_target` |
| AC-5 | `tests/e2e/test_pronunciation_review.py::TestReviewLoop::test_an_empty_queue_shows_the_empty_state` |
| AC-6 | `tests/e2e/test_pronunciation_review.py::TestReviewLoop::test_the_first_card_shows_before_and_without_waiting_for_the_presession_sync` |
| AC-7 | `tests/e2e/test_pronunciation_review.py::TestReviewLoop::test_reference_plays_from_media_and_is_absent_without_audio` |
| AC-8 | `tests/integration/test_anki_pronunciation.py::TestRating::test_a_rating_answers_only_that_card_through_the_scheduler` |
| AC-9 | `tests/e2e/test_pronunciation_review.py::TestReviewLoop::test_a_rating_submits_that_card_and_loads_the_next` |
| AC-10 | `tests/api/test_pronunciation.py::TestRatingRetry::test_a_retried_rating_with_stale_reps_is_already_answered_without_a_second_answer` |
| AC-11 | `tests/e2e/test_pronunciation_review.py::TestReviewLoop::test_a_failed_rating_keeps_the_card_current_and_try_again_resends_it` |
| AC-12 | `tests/api/test_pronunciation.py::TestSessionSync::test_session_start_and_end_each_request_a_sync_coalesced_and_never_awaited` |
| AC-13 | `tests/e2e/test_pronunciation_review.py::TestReviewLoop::test_leaving_the_review_sends_the_session_end_signal` |
| AC-14 | `tests/api/test_pronunciation.py::TestSessionSync::test_dev_mode_session_signals_succeed_and_request_no_sync` |

Viewports: phone (AC-4 en, AC-5, AC-6, AC-9), iPad (AC-4 fr), desktop (AC-7, AC-11, AC-13).

## Supporting helpers

- `tests/support/pronunciation.py` (new): the hand-built AnkiConnect exchanges the epic asks
  for in 7.1. `ReviewRig` is the real guarded/gated adapter (`wired_delete`, `ObservedLock`)
  over an in-memory collection whose cards carry a `Schedule` (`due()`, `not_due()`, `new()`).
  `findCards` simulates Anki search at token level: `deck:"X"` (with children, OR'd),
  `note:"T"`, `card:N`/`card:Name`, `is:due` (review, due ≤ `TODAY`, not suspended), `is:new`
  (type 0, **suspended included**, as Anki), `-is:suspended`. `cardsInfo` adds `type`, `queue`,
  `due`, `reps`, `interval`; `answerCards` records `.answers`, bumps reps and reschedules.
  `rig.pronounce(language, category, schedule, ...)` adds an Item as Save leaves it, its Study
  cards due so only deck and ord scope exclude them. `queue_of()`/`rate()` call the proposed
  port methods inside `settle`; `card_ids()`/`card_id_set()`/`counts()` pass an exception
  through to the assertion. `asgi_client()` runs requests in the test's loop so a requested
  Sync can be drained. Sanity-checked: a correctly scoped query returns exactly AC-1's two
  cards, and dropping `-is:suspended` leaks the suspended new card.
- `tests/support/pronunciation_screen.py` (new): `ReviewApi` per-page double for the queue,
  Rating (`rating_error` → 503 `anki_unavailable`), session signals (`hold_start` keeps start
  unanswered; `events` keeps arrival order; `wait_for()` uses round trips, no sleeps) and
  `/api/media`; `review_card()` wire factory; locators for chip, Target, Rating buttons,
  Reference and the Rating alert.

## Proposed contracts and UI selectors

- Port (AD-1; adapter and fake together, plus `tests/unit/test_anki_store_port.py`):
  `pronunciation_queue(language) -> PronunciationQueue(due, new, cards)` with
  `PronounceCard(card_id, item_id, reps, category, target, audio)`; `answer_card(language,
  card_id, reps, rating) -> bool` (True = alreadyAnswered, nothing sent). Both under one lock
  hold; reads ungated, the answer Setup-gated (AD-19). `domain/pronunciation.py` holds `Rating`.
- Guard (AD-4): add `answerCards` as a write allowed only for cards of a manifest note type
  (lookup by id, like `suspend`); today the guard fails closed on it.
- HTTP: `GET /api/pronunciation/{lang}/queue` → `{due, new, cards[]}` (camelCase, `audio`
  managed name or null); `POST /api/pronunciation/{lang}/rating` `{cardId, reps, rating}` →
  `{alreadyAnswered}`; `POST .../session/start|end` → 204, only `SyncRequester.request()`.
- Tension recorded: AD-1 says ports never take card ids, while the ticket's Card payload
  carries `cardId`. The ticket (2026-10-25) wins for 7.1; the builder may wrap it in a domain
  id type and should note the amendment.
- UI (scaffold choices): keep the `h1` "<Language> Pronunciation" (navigation tests rely on
  it); chip text "N due · M new" with `aria-label` "N due, M new"; Target as plain text in
  `main`; Reference button named "Play reference audio" or "Reference"; Rating buttons
  "Again"/"Hard"/"Good"/"Easy"; Rating alert `role="alert"` with "Try again". Live-server
  navigation tests will hit the real queue route over `FakeAnkiStore`, so the fake must answer
  an empty queue.

## Implementation checklist

- [ ] AC-1/AC-2: adapter `pronunciation_queue` with exact scopes (`deck:"<Prefix>::Pronunciation::<Lang>"`,
  ord 3, `is:due`/`is:new`, `-is:suspended`), notesInfo for ItemId/Target/Audio (codec-decoded),
  sort due by `due` then new by creation order (card id).
- [ ] AC-3: queue route and wire model; counts from the same read.
- [ ] AC-8: `answer_card` reads `cardsInfo` reps then `answerCards` with ease 1-4, one lock hold; guard entry.
- [ ] AC-10: reps mismatch → no `answerCards`, `alreadyAnswered: true`.
- [ ] AC-12/AC-14: `features/pronunciation` session routes calling the injected SyncRequester.
- [ ] AC-4/AC-5: `static/screens/pronunciation.js`: skeleton, chip, Target, empty state.
- [ ] AC-6: read the queue first, render, then POST session start without awaiting it.
- [ ] AC-7: Reference via `/api/media/<name>`, never autoplay; no control when `audio` is null.
- [ ] AC-9/AC-11: Rating buttons always enabled; post through `api.js`; reload on success;
  inline alert + Try again (same cardId/reps) on failure.
- [ ] AC-13: end signal on unmount, `visibilitychange` hidden, `pagehide` (`sendBeacon`), empty queue.

Green-phase expansions: all four ease mappings (parametrized); learning cards (queue 1/3) and
their order; escaped Target text decoding (AD-9); queue `anki_unavailable`/`anki_busy` envelope
and the screen's queue-read error; Rating Setup gate (`setup_required`, zero `answerCards`);
answering a card of another Language or Prefix refused; `answerCards` false/failed reply →
`anki_unavailable`; end on hidden, pagehide beacon and empty queue (WebKit too); no Reference
autoplay and no media request before tap; skeleton while the queue is held; tablet layout
columns; logs carry no Target text (NFR-7). Real AnkiConnect recordings replace the hand-built
exchanges in 7.4.

## Activation and downstream handoff

There is no leaf story file to update. Pass `epic-pronunciation-review/tickets.toml` entry 1,
this checklist and generatedTestFiles to bmad-build. Remove one module skip at a time for the
current task, confirm RED, implement, confirm GREEN, then refactor.

```sh
uv run pytest tests/api/test_pronunciation.py tests/integration/test_anki_pronunciation.py tests/e2e/test_pronunciation_review.py -q
uv run pytest tests/e2e/test_pronunciation_review.py --browser webkit -q
uv run ruff check src tests && uv run ruff format --check src tests
```

## Validation limits

Python sync Playwright has no outer promise matcher. With skips stripped, AC-4, AC-5, AC-6 and
AC-13 fail at their own first assertion; AC-7, AC-9 and AC-11 stop at the missing Reference or
Rating button, so their later transitions need re-observation once the screen exists. The
search simulator is token-level and hand-built from AnkiConnect's docs, not recorded; story
7.4 replaces it. Browser doubles do not prove real Anki or Azure behaviour.

## Validation and completion — 2026-10-25

- Registry/static check: 14 ids, exactly one leaf function per id, each docstring carries
  exactly one declared id. 10 P0, 4 P1.
- Normal run: **15 skipped**. Related regressions: unit/api/integration **876 passed,
  7 skipped**; navigation, menu sheet and the new E2E file **37 passed, 8 skipped**.
- Temporary activation (scratch plugin stripping skip markers): **15 failed, 0 passed,
  0 errors**. API: AC-3 `None == {...}`, AC-10 `None is True` (405), AC-12 `0 == 1`, AC-14
  `[405]*4 == [204]*4`. Integration: AC-1/AC-2 the AttributeError for `pronunciation_queue`,
  AC-8 `[] == [{cardId, ease: 2}]`. Browser as in Validation limits.
- Aggregation fixes: AC-1 compares a set helper (sorting an exception crashed before the
  assertion); AC-12 finishes only in-flight Syncs (an empty `finish()` raised first); AC-6
  holds start inside the double so arrival order is observable without a race.
- Ruff check/format clean on `src` and `tests`; `git diff --check` clean. Repo-wide ruff
  flags only the untracked Azure probe scripts under `epic-pronunciation-review/`, which are
  not part of this run.
- Machine-readable mapping: `atdd-validation-7-1.json`.

ATDD scaffolding is complete; story 7.1 implementation remains pending. Next: bmad-build with
this checklist and tickets.toml entry 1. Per AGENTS.md this ATDD run is committed to main and pushed.

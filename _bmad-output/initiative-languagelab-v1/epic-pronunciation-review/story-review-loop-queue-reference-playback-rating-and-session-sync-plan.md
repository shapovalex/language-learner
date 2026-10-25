---
title: 'Review loop: queue, Reference playback, Rating, and session Sync'
type: 'feature'
ticket: '1'
created: '2026-10-25'
status: 'built'
baseline_revision: '683db69c5663d900fc7b98c3c108f12ec295d4ce'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-7-1.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Pronunciation screen is a placeholder heading: there is no queue of Pronounce Cards, no Reference playback, no way to rate a Card through Anki's scheduler, and no session Sync (CAP-10, FR-30/31/34/36).

**Approach:** Add `features/pronunciation` (queue read, Rating, session start/end), two AnkiStore port methods (`pronunciation_queue`, `answer_card`) with adapter, guard entry and fake, and build the review screen (chip, Target, Reference, four always-enabled Rating buttons, empty and failure states, end signals). Activate the story 7.1 ATDD scaffolds.

## Boundaries & Constraints

**Always:**
- Queue = the Language's ord-3 cards in `<Prefix>::Pronunciation::<Lang>` decks under exact manifest scopes, `is:due` or `is:new`, not suspended (nor buried); due first by oldest due, then new by creation order (FR-30, AD-6).
- Card payload `{cardId, itemId, reps, category, target, audio}`; `audio` is the managed name or null. Target decoded via the codec (AD-9).
- Rating: one lock hold reads the card's `reps`; if it differs from the request's, return `alreadyAnswered: true` and send nothing; else `answerCards` with again/hard/good/easy → ease 1-4 (mapping only in the adapter). The answer is a guarded (manifest note type, by card id) and Setup-gated write; reads stay ungated (AD-4, AD-19, AD-20).
- Session start/end: idempotent, 204, only `SyncRequester.request()`, never awaited; dev mode syncs nothing (AD-17).
- Client: read the queue and render the first Card (skeleton meanwhile, no Sync UI) before POSTing session start; send end on unmount, `visibilitychange`→hidden, `pagehide` via `sendBeacon`, and an empty queue. Reference never autoplays and fetches `/api/media/<name>` only on tap.
- A failed Rating shows "Rating not saved — Anki isn't reachable." + Try again (same cardId/reps); the Card stays current.

**Never:** Attempts, recording, Azure assessment or a Rating gate (story 7.2); a queue cap; Rating hotkeys; storing anything about a session; Target text or card ids in logs beyond what the request log already records.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Queue read | due + new + out-of-scope cards | `{due, new, cards}` in FR-30 order | Anki down → 503 `anki_unavailable` |
| Empty queue | no due/new cards | empty state copy, no Rating buttons, end signal sent | — |
| Rating | reps match | `answerCards` once, `{alreadyAnswered:false}`, next Card + chip update | `answerCards` not `[true]` → 503 `anki_unavailable` |
| Retried Rating | reps moved on | `{alreadyAnswered:true}`, no write, next Card | — |
| Rating, Setup not ready | state ≠ ready | 409 `setup_required`, no `answerCards` | inline alert |
| Rating for a card not in the Language's Pronounce scope | foreign/unknown cardId | 404 `not_found`, no write | — |
| Session signal | start/end, any number | 204 at once, ≤1 running + 1 pending Sync | Sync failure never fails the request |

</frozen-after-approval>

## Code Map

- `src/language_lab/ports/anki_store.py` -- add `pronunciation_queue(language) -> PronunciationQueue` and `answer_card(language, card_id, reps, rating) -> bool` (True = alreadyAnswered).
- `src/language_lab/domain/pronunciation.py` (new) -- `Rating` StrEnum, frozen dataclasses `PronounceCard(card_id, item_id, reps, category, target, audio)` and `PronunciationQueue(due, new, cards)`.
- `src/language_lab/adapters/anki/store.py` -- reuse `_note_infos`-style validation, `_field`, `_audio_name`, `is_int`, `manifest.card_deck(model, PRONOUNCE_ORD)`, `manifest.item_note_type`; one `self._lock.hold()` per method; writes via `self._client.invoke` (guard + gate apply).
- `src/language_lab/adapters/anki/query.py` -- the only query builder: add a Pronounce-queue builder from manifest deck + note type (raises on non-manifest names).
- `src/language_lab/adapters/anki/guard.py` -- `answerCards` fails closed today; add an id-targeted branch: every `answers[].cardId` an int, looked up via `cardsInfo` → manifest note type (like `_CARD_WRITES`).
- `src/language_lab/features/items/routes.py`, `features/audio/*` -- route/service shape to copy; `/api/media` already serves Reference clips.
- `src/language_lab/features/sync/service.py` -- `SyncService` is the SyncRequester; inject it (as Setup gets `sync=sync`) in `app.py:338-398`.
- `src/language_lab/static/screens/pronunciation.js` -- placeholder to replace; keep the `h1` "<Language> Pronunciation" (navigation tests). Patterns: `screens/items.js` (mounted flag, skeleton, `alertBox`/`tryAgain`), `dom.js`, `api.js` (only module calling fetch; add queue/rating/session functions and a beacon helper there).
- `src/language_lab/static/css/studio.css` -- `.chip` exists; add review layout (phone stacked, Rating 2×2; tablet two columns, Rating 4 across) per `ux-languagelab/mockups/S-Review.dc.html`, `S-iPadReview.dc.html`, `DESIGN.md` tokens.
- `tests/fakes/anki_store.py` -- add both methods (default empty queue; live-server navigation tests hit the real queue route).
- `tests/unit/test_anki_store_port.py:64-78` -- exact port-method set; add the two names (+ a signature-match test).
- Scaffolds (remove module `pytest.mark.skip`): `tests/integration/test_anki_pronunciation.py`, `tests/api/test_pronunciation.py`, `tests/e2e/test_pronunciation_review.py`; helpers `tests/support/pronunciation.py` (`ReviewRig`; its `findCards` simulator is token-level: `deck:"X"` OR'd, `note:"T"` OR'd, `card:N`, `is:due`/`is:new` union, `-is:suspended`), `tests/support/pronunciation_screen.py`.
- `pyproject.toml` `[tool.ruff]` -- CI runs `ruff check .`; the Azure probe scripts committed under `_bmad-output/` fail it. Add `extend-exclude = ["_bmad-output"]`.

## Tasks & Acceptance

**Execution:**
- [x] `pyproject.toml` -- ruff `extend-exclude = ["_bmad-output"]` -- unbreak repo-wide lint.
- [x] `src/language_lab/domain/pronunciation.py` -- Rating, PronounceCard, PronunciationQueue -- domain types the port returns.
- [x] `src/language_lab/ports/anki_store.py` + `tests/fakes/anki_store.py` + `tests/unit/test_anki_store_port.py` -- declare, fake (in-memory queue list; `answer_card` reps check, records answers), keep aligned -- AD-1.
- [x] `src/language_lab/adapters/anki/query.py`, `guard.py`, `store.py` -- queue (per Category `findCards`, then `cardsInfo`, `notesInfo`; drop queue<0; sort) and answer (`cardsInfo` reps + scope check, then `answerCards`) -- with unit tests in `tests/unit/test_anki_query.py` and guard tests beside the existing guard tests.
- [x] `src/language_lab/features/pronunciation/{__init__,service,routes}.py` + `app.py` -- `GET /api/pronunciation/{lang}/queue`, `POST .../rating` (`{cardId:int, reps:int≥0, rating}` validated → 422 `validation_failed`), `POST .../session/start|end` → 204 -- wire `anki_store` and `sync`.
- [x] `src/language_lab/static/api.js`, `screens/pronunciation.js`, `css/studio.css` -- the review screen.
- [x] scaffold files -- remove skips one at a time (integration → api → e2e), RED then GREEN; add the green-phase expansions from the checklist that guard this scope: all four ease mappings, buried/learning cards, codec-decoded Target, Rating Setup gate, foreign-card refusal, `answerCards` false → 503, end on hidden/pagehide/empty queue, no media request before tap.

**Acceptance Criteria:**
- Given the ATDD checklist's AC-1..AC-14, when the three scaffold files run unskipped on Chromium (and the e2e file on WebKit), then all pass.
- Given the full suite, when `make test` and `make lint` run, then both pass.

## Implementation Notes

- **AD-8 amendment (story 7.1):** the Pronounce card id leaves the adapter as an opaque int, on
  `PronounceCard.card_id` and the Rating body's `cardId`, because a Rating must address one Card
  and carry its `reps` (AD-20). No other Anki id reaches features or the client.
- Queue: one `findCards` per Category via `pronounce_queue_query` (deck + note type from the
  manifest, `card:4 (is:due OR is:new) -is:suspended`), then one `cardsInfo` and one `notesInfo`,
  all under one lock hold. `queue < 0` (suspended, buried) is dropped, since Anki's `is:new`
  keeps buried new cards. Due sort key `(queue == 1, due, cardId)`; new by card id.
- Rating: `cardsInfo` scope check (`ord == 3`, `modelName` one of the Language's two Item note
  types; `{}` for an unknown id) → 404; stale `reps` → `alreadyAnswered` with no write; else
  `answerCards` must answer `[true]`. The gate applies on the write only, so a stale-reps retry
  while Setup isn't ready still answers `alreadyAnswered` (nothing is written either way).
- Guard: `answerCards` passes only when every answer is exactly `{cardId: int, ease: 1-4}` and
  every card is of a manifest note type (`cardsInfo` lookup).
- Client: session start is sent after the first non-empty render; end on unmount, hidden page,
  `pagehide` (`sendBeacon`) and an empty queue (also an empty first read); a page shown again
  with Cards left sends a new start. After a confirmed Rating the queue is read again (next
  Card and chip come from Anki). Rating taps are ignored while one is in flight; the buttons
  are never disabled.
- Layout: the chip sits top right of the Target card at every width (the phone mockup puts it in
  the header beside Menu; the shell header is shared, so it stays in the card). From 600px the
  Rating row is 4 across; the second (scores) column arrives with 7.2.
- Support: `ReviewRig` gained intraday (queue 1, `NOW`) and day learning plus buried schedules;
  `ReviewApi` gained `queue_error`, `hold_queue`/`release_queue()`.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — 2026-10-25: high 0, medium 3, low 2, false 0, maybe-false 0

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1a | `pronunciation.js` failed-Rating branch: a 404 `not_found` (card deleted/changed in Anki after the read) shows the reachability copy and Try again resends forever | medium | patch | `submit()` keeps `failed.body`; adapter raises NOT_FOUND on scope mismatch. Fix: on `not_found`, re-read the queue instead of showing the alert. |
| 1b | Same branch: `anki_busy` / network failure also get "Anki isn't reachable" | low | reject | EXPERIENCE.md fixes this exact copy for "Rating submit failed"; changing it needs a UX decision, not a direct correction. |
| 2 | `render()` rebuilds the layout on busy and after the re-read, so focus on the tapped Rating button (or Try again) drops to `<body>` | medium | patch | `body.replaceChildren(layout)` removes the focused node every Rating. Fix: when focus was inside the review body before a re-render, move it to the matching Rating button (or the first one) of the new layout. |
| 3a | `load()` starts a session when the first read resolves while the page is hidden | low | patch | `startSession()` ignores `document.visibilityState`; one-condition direct correction: start only when visible (the `visibilitychange` handler starts it on show). |
| 3b | On show again, a session starts from the stale pre-hide queue without a re-read | low | reject | Harmless: a stale Card's Rating returns `alreadyAnswered`/404 and the re-read moves on; the extra Sync coalesces. Fix would add a re-read path. |
| 4 | `answer_card` scope check ignores `queue` and deck, so a card suspended/buried or moved out of the Pronunciation deck after the read is still answered | medium | patch | `info["queue"]` is read only in the queue path; `cardsInfo` carries `deckName` and `queue`. Fix: also require `queue >= 0` and `deckName == card_deck(modelName, 3)`, else NOT_FOUND (with 1a, the client moves on). |

## Design Notes

- **cardId in the API** contradicts AD-1/AD-8 ("card ids stay in the adapter"). The ticket (approved 2026-10-25) and scaffolds require it: the Rating must address one Card and carry its reps. Record an AD-8 amendment note in Implementation Notes; card ids are opaque ints to features and client.
- **Queue query** (per Category, both names from the manifest): `deck:"<Prefix>::Pronunciation::<Lang>::<Cat>" note:"<Prefix> <Lang> <Cat>" card:4 (is:due OR is:new) -is:suspended`. Category comes from which query found the card.
- **Order**: due = `type != 0`, sorted by `due` (day number; intraday learning `queue 1`, due in epoch seconds, sorts after day-based due cards), ties by card id; new = `type == 0`, by card id (creation time). `due`/`new` counts from the same read.
- **Rating scope check** (in `answer_card`, before reps): `cardsInfo` entry must exist, `ord == 3`, `modelName` one of the Language's two Item note types; else `NOT_FOUND`.

## Verification

**Commands:**
- `uv run pytest tests/api/test_pronunciation.py tests/integration/test_anki_pronunciation.py tests/e2e/test_pronunciation_review.py tests/unit -q` -- expected: all pass, none skipped
- `uv run pytest tests/e2e/test_pronunciation_review.py --browser webkit -q` -- expected: pass
- `make test` and `make lint` -- expected: pass

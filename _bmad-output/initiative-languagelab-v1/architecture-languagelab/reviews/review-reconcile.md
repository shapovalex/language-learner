---
title: Reconcile review — architecture spine vs PRD, addendum, UX
spine: ../architecture-languagelab.md
inputs: [prd-languagelab.md, addendum.md, EXPERIENCE.md, DESIGN.md (skimmed)]
date: 2026-10-08
---

# Reconcile Review — LanguageLab Architecture Spine

## Verdict

**Mostly aligned. Amend before finalizing.** All FR and NFR areas map to an AD. All six PRD open questions are resolved or deferred: Q1 by AD-14 (30 s), Q5 by AD-12, Q6 by AD-3, and Q2, Q3, Q4 in Deferred. The deliberate departures hold: AD-10 amends A3, and Azure goes through REST rather than the SDK.

The gaps are mostly quiet failure and safety semantics that cut across features, and these belong at initiative altitude:

- timeouts under the global lock;
- retry idempotency;
- deck-option presets crossing the Prefix boundary;
- content leaking through framework logs;
- Origin checks behind Tailscale;
- schema-version gating.

There is also one direct contradiction with the inputs: Figtree is loaded from Google Fonts, but AD-13 says "no CDN".

Severity: **H** = will cause a cross-unit defect or NFR breach if left to epics; **M** = should be fixed in the spine to stop units diverging; **L** = nice to pin, or can be left to an epic with a note.

---

## Findings

### F1 (H): Global lock has no timeout policy, which contradicts "Sync never blocks normal work"

- **Inputs:** FR-36 says "Sync failures … never block normal work". §5.2 says Sync is non-blocking. EXPERIENCE says the pre-session Sync "is not awaited: no delay".
- **Spine:** AD-5 runs Sync, Apply Setup and every read under one `asyncio.Lock`. Deferred says "Request timeouts … are local to each adapter."
- **Problem:** A Sync can be slow, or can hang when AnkiWeb asks for a full-sync choice or Anki shows a modal. While it holds the lock, every Capture save, Item open and Rating waits behind it. The pre-session Sync is enqueued straight after the first card read, so the first Rating of every session may wait on it. Graceful-shutdown Sync on Ctrl+C has no bound either. Because the lock is cross-cutting, timeouts can't be "local to each adapter".
- **Fix:** Amend AD-5 and AD-17:
  - every AnkiConnect call has a hard timeout;
  - Sync has its own upper bound;
  - lock acquisition by a request has a bounded wait, and when it runs out the request returns `anki_unavailable` (or a new `anki_busy` code) without hanging;
  - a periodic Sync is skipped, not queued, if one is already pending;
  - shutdown Sync is bounded so Ctrl+C always exits.

  Move "timeouts" out of Deferred for the Anki adapter.

### F2 (M-H): Retrying a commit whose outcome is unknown can apply it twice

- **Inputs:** FR-34 says a failed Rating leaves "the Card current and unanswered" with Try again. UX offers Try again on Save failed, Capture failed and Rating failed. NFR-3 and FR-20 require exactly one note with four Cards.
- **Spine:** AD-8 has the backend generate `ItemId` at the first Save. No AD covers idempotency.
- **Problem:** After a timeout (see F1) or a dropped response over Tailscale, the client can't tell whether the commit happened. Retrying Save creates a second note with a new ItemId. Retrying a Rating answers the card twice, which corrupts the schedule. Retrying Save Capture creates a duplicate Capture.
- **Fix:** Add an AD covering commit idempotency:
  - **Save Item (create):** the client sends an idempotency key, or the backend issues the ItemId on Draft generation and the client echoes it. Create is a no-op if a note with that ItemId already exists.
  - **Rating:** the request carries the card snapshot the client was shown (card id plus `reps`/`mod`/due). Under the lock, the adapter answers only if the card still matches, and otherwise returns a distinct code so the UI reloads the next card.
  - **Capture:** use a client key the same way.

### F3 (M): Deck-option presets can cross the Prefix boundary, and Pronounce answers can bury Study siblings

- **Inputs:** FR-8 says sibling burying is off for Study decks and other options stay the user's. UJ-4 says "Siblings from the same note are not buried, so each exercise progresses on its own schedule." NFR-1 is the Prefix boundary.
- **Spine:** AD-3 says "Study deck options (sibling burying off; nothing else managed)".
- **Problem:** Anki options are shared presets. If Setup edits the preset the Study decks happen to use (often "Default"), it changes decks outside the Prefix, which breaches NFR-1. Separately, Pronounce cards are answered through Anki's scheduler under the Pronunciation decks' preset. If that preset buries siblings, each Pronounce Rating buries that note's Study Cards for the day, which defeats UJ-4. The PRD only names Study decks, so the spine has to decide this.
- **Fix:** Amend AD-3 and AD-4:
  - the manifest declares a dedicated Prefix-named preset, created by cloning, and assigns it to the managed decks;
  - Setup never modifies a preset that a non-Prefix deck also uses;
  - repair touches only the bury flags of the managed preset;
  - decide explicitly whether the Pronunciation decks also get burying off (recommended: yes, same preset or a sibling preset).

### F4 (M): Content can leak through framework logs and error echoes

- **Inputs:** NFR-7 says logs never contain captured text, generated content, payloads or audio. NFR-9 is stdout only.
- **Spine:** AD-15 lists the fields a log line carries, but says nothing about framework defaults.
- **Problem:** uvicorn's access log prints full URLs including query strings, so an Items search `?q=…` (FR-22) would put content in the logs. FastAPI's default 422 body echoes the invalid input. Unhandled-exception tracebacks and Pydantic `ValidationError` reprs include field values, and LLM output is one of them (AD-11's retry path).
- **Fix:** Amend AD-15:
  - disable uvicorn's access log and replace it with the request-id middleware line, which logs the route template and not the raw URL;
  - map `RequestValidationError` and every unhandled exception to the envelope (`validation_failed`, plus a new `internal_error` code) without echoing input;
  - log exceptions by type and location only, never by `repr` of the payload or model output.

  Also send search terms in a POST body, or exclude the query from every log.

### F5 (M): Origin check behind Tailscale Serve, and how the session-end signal gets through

- **Inputs:** UJ-3 says "Leaving the tab triggers a Sync". The Glossary says a session also ends when the queue is empty. FR-2 requires Tailscale HTTPS.
- **Spine:** AD-16 requires `Origin` to match `Host`, and a missing Origin returns 403. AD-17 signals session end on router unmount and on `pagehide` via `sendBeacon`.
- **Problems:**
  - It's unverified whether Tailscale Serve keeps the public `Host` when it proxies to `127.0.0.1:8787`. If Host arrives rewritten, every write from iPhone or iPad gets a 403.
  - Origin is `https://host` while Host has no scheme, so the comparison rule isn't defined.
  - `sendBeacon` may not reliably send `Origin` in Safari. If it doesn't, AD-16 silently drops the session-end Sync.
  - Switching apps or tabs on iOS fires `visibilitychange`, not `pagehide`, so UJ-3's "leaving the tab" is missed.
  - The queue-empty session end has no trigger.
- **Fix:** Amend AD-16:
  - compare host[:port] of `Origin` against `Host` or `X-Forwarded-Host`, or against an allow-list (the local URL plus the discovered or configured tailnet host);
  - verify Tailscale Serve's header behaviour during the stack check.

  Amend AD-17:
  - the session-end signal is idempotent and only enqueues a Sync;
  - send it on `visibilitychange→hidden`, `pagehide` and router unmount;
  - the backend also treats "next card → queue empty" as session end;
  - either exempt the beacon endpoint from the Origin rule or confirm Safari sends Origin.

### F6 (M): Schema-version gating, `setup_required`, and stale plans are undefined

- **Inputs:** FR-7 says every note records its SchemaVersion and migrations never run at startup. FR-6 says nothing changes before confirmation and the user confirms specific changes. UX says that if the user leaves during Apply, the run is not cancelled, and returning shows the verification result.
- **Spine:** AD-15 lists a `setup_required` code but never says when it is returned. AD-3 defines diff → plan → apply → verify.
- **Gaps:**
  1. Nothing says what features do when Anki structure is missing or out of date, or whether reads and writes are gated.
  2. Nothing covers a downgrade: running an older wheel through `uvx --from` against a collection that a newer version already migrated. That older code would write old-schema notes.
  3. The plan the user confirmed may no longer match Anki at apply time (TOCTOU), and applying a different plan breaks "confirmed".
  4. Apply has to finish even if the client disconnects, and the "verification result" shown on return has to come from a fresh diff, because AD-2 forbids server state.
- **Fix:** Amend AD-3:
  - managed writes return `setup_required` when the manifest diff is non-empty or a managed note type is missing;
  - writes are refused (with a distinct code) if Anki holds a SchemaVersion newer than the code's;
  - Apply carries the hash of the previewed plan, re-diffs under the lock, and refuses if the plan has changed;
  - Apply runs shielded from client disconnect;
  - returning to Setup recomputes diff and verify.

### F7 (M): Item search semantics and Anki query escaping are unpinned

- **Inputs:** FR-22 says search matches Target and Russian meaning across both Categories. UX J4 searches for "conclu" (a substring) and uses debounced live search.
- **Spine:** AD-4 says every read query is scoped to the Prefix. AD-12 covers duplicates only. AD-10 split the field into `Russian` and `RussianAlternatives`.
- **Problems:**
  - Nothing says whether `RussianAlternatives` is searched, or whether search is substring, normalized or diacritic-insensitive.
  - If user text is spliced into an Anki search expression (`"`, `)`, `OR`, `deck:`), it can break the Prefix scoping.
  - `ANKI_PREFIX` itself is never validated. A Prefix containing `::`, `*`, `"` or spaces breaks scoping and media naming (AD-7).
- **Fix:** Add to AD-12, or a new AD:
  - search fetches the Language's managed notes through a fixed, scoped query and filters in the service: `normalize_target`-style substring matching over Target, Russian and RussianAlternatives;
  - user text never enters an Anki search string, and any adapter query that does include values escapes them through one helper;
  - `settings.py` validates `ANKI_PREFIX` against a safe charset such as `[A-Za-z0-9_-]+`.

### F8 (M): Per-locale feedback limits are not enforced in the Assessment contract

- **Inputs:** FR-32 and §9 #18 say the UI never claims a named French sound. UX shows en-US phoneme pills with Azure's IPA symbols, and a fr-CA start/middle/end position strip only. A5 lists the per-locale feedback.
- **Spine:** AD-14 covers transport and limits only.
- **Problems:**
  - Azure's REST response includes phoneme labels for fr-CA too. If the API passes them through, any UI bug can break a release-gate criterion.
  - Getting IPA labels requires asking Azure for the IPA phoneme alphabet; the default is SAPI.
  - The rule that turns phoneme offsets into the start/middle/end positions is assigned to no one.
- **Fix:** Amend AD-14, or add a domain rule:
  - `domain.Assessment` is per-locale;
  - the Azure adapter requests the IPA alphabet for en-US;
  - for fr-CA the adapter or service drops phoneme labels and returns only position buckets computed by one domain function;
  - prosody is present only for en-US.

### Lower-severity findings

- **L1 (L, contradiction): Figtree loaded from Google Fonts versus AD-13's "no CDN".** DESIGN.md §Typography says "Figtree (Google Fonts …)". AD-13 vendors all third-party browser code and allows no CDN. Figtree also appears to have no Cyrillic, and Russian is primary content.
  - *Fix:* AD-13 states that fonts are vendored as woff2 files in `static/vendor/fonts` under the OFL. Note that Russian falls back to system-ui, unless a Cyrillic-capable family is picked.
- **L2 (L): Static asset and API caching across upgrades.** AD-13's "no cache" covers data held in JS. It says nothing about HTTP caching. After a wheel upgrade, Safari can keep serving old ES modules against the new API, and bfcache can show stale Anki data.
  - *Fix:* `/api` responses send `Cache-Control: no-store`. Static assets either carry the version in their URL or send `no-cache` with an ETag. Screens re-mount on `pageshow` with `persisted`.
- **L3 (L): FR-4 docs list is incomplete.** The `docs/` line in the Structural Seed is missing the warning that any local process can control a keyless AnkiConnect. It also doesn't say whether the repo ships the English/French/Russian generation fixture set and a way to run it (FR-4, A2, FR-17 note).
  - *Fix:* add both to the docs line. Decide whether the fixtures plus an opt-in pytest marker ship in `tests/`.
- **L4 (L): FR-35 browser-side disposal.** AD-14 covers the server only. FR-35 also requires recordings and Assessments to be gone from the browser.
  - *Fix:* add a line saying the pronunciation screen drops its Blobs and Assessment objects (and revokes object URLs) on Rating success and on unmount.
- **L5 (L): NFR-5 is enforced only by a default.** AD-16 binds to `LANGUAGE_LAB_HOST` with a default of `127.0.0.1`, so a value of `0.0.0.0` would breach NFR-5.
  - *Fix:* `settings.py` rejects any non-loopback host.
- **L6 (L): The error code enum has gaps.** There is no catch-all `internal_error` (see F4), no code for idempotency or stale-card conflicts (F2), no code for lock-busy (F1), and no code for a newer schema (F6).
- **L7 (L): Upload size limits.** The Save MP3 and Attempt uploads have no maximum size.
  - *Fix:* set a size cap and reject larger uploads with `validation_failed`. 30 s of audio is the natural bound for Attempts.
- **L8 (L): Readiness semantics.** FR-5 says "Azure and OpenRouter are configured". UX treats these as pass/fail checks that gate Apply.
  - *Fix:* state whether each check only looks for configuration or makes a cheap live call (for example, listing voices and listing models).
- **L9 (L): Capture suspension gap.** AD-6 tolerates a Capture whose card is unsuspended after a partial failure. FR-9 says the card "never enters study". The risk is limited, because Captures sit outside `<Prefix>::Study`.
  - *Fix:* note this explicitly as accepted, with Setup repairing it.
- **L10 (L): Pronunciation queue query semantics.** FR-30 asks for new and due cards. UX shows a "N due · M new" chip that updates after each Rating. The spine doesn't define:
  - whether "due" includes learning or relearning cards that come due again during the session;
  - that suspended and buried cards are excluded;
  - that the queue is re-read from Anki after every Rating.

  *Fix:* one line in Capability map or AD-5 noting that the server is stateless and re-queries the queue on each next-card request.

---

## Checked and consistent (no action)

- **PRD open questions:** Q1 resolved (AD-14, 30 s), Q2, Q3 and Q4 deferred, Q5 resolved (AD-12), Q6 resolved (AD-3). UX OQ-1, OQ-6 and OQ-10 follow from these. OQ-5 is deferred. OQ-3 (cost UI) goes with Q3.
- **Deliberate amendments:** AD-10 (Russian split) and Azure via REST/httpx are deliberate and logged. At finalize, offer to update addendum A3 upstream so the two documents don't diverge (this is already noted in the memlog).
- **Covered:**
  - A1 packaging (wheel, uvx, console script, stdout logs, no Node or Docker);
  - A2 config path and keys (AD-18);
  - A4 strict schema, `require_parameters` and one retry (AD-11, AD-18);
  - A5 TTS MP3, exact bytes and delete-after-success (AD-6, AD-7, AD-14);
  - A6 answering via the scheduler, and the Sync triggers;
  - NFR-2 (no DB) and NFR-6 (browser never calls providers);
  - FR-29 localStorage voice;
  - FR-12 return to Capture (client routing);
  - FR-23 last-write-wins;
  - FR-25 delete order;
  - NFR-8 default OpenRouter privacy (inherits from A4; consider naming it in AD-18).

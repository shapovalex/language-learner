---
title: Adversarial review — LanguageLab architecture spine
target: ../architecture-languagelab.md
inputs: ../../prd-languagelab/prd-languagelab.md, ../../prd-languagelab/addendum.md, ../../ux-languagelab/EXPERIENCE.md
date: 2026-10-08
method: For each seam, build two units one level down (epics: Runtime/Setup, Captures, Drafts+Items, Audio, Pronunciation, Sync), each obeying every AD to the letter, that still don't fit together. Each such pair is a hole, and each comes with a proposed AD rule to close it.
---

# Adversarial Review: Architecture Spine

## Verdict

**Not ready to slice into epics yet.** The backend boundary decisions hold up well: the ports, the Prefix guard, the lock, the write order, the error envelope, and config. The spine is silent in three places where separately built units must meet:

1. **The client contract between screens.** Where a Draft lives, how dirty state is reported, how a flash message survives navigation, and how a Pronunciation session starts and ends.
2. **Ownership of shared data shapes.** The Item/Draft API and domain types, the SchemaVersion stamp, the Audio field, and the manifest split between Setup and Items.
3. **A few wire-level details that are loose enough to hide real bugs.** Prefix wildcard scoping, codec escaping, superseded-media deletion, retry idempotency, and an error envelope that can't carry duplicate matches.

None of these needs a new paradigm. Each one closes with one or two sentences added to an existing AD, or with a new AD. There are 18 holes below. H1–H8 are must-fix before the epics are written. H9–H18 should be fixed, or recorded as a deliberate deferral with a named owner.

---

## Must-fix

### H1. The Draft has no home: no route, no handoff, and the post-Save banner has no carrier

- **Unit A (Captures epic):** Capture detail at `/captures/<captureId>` calls `POST /api/drafts/...` and navigates to a new route `/captures/<id>/draft`. It passes the Draft in `history.state`, because AD-13 forbids a cross-screen data cache and AD-2 forbids server-side Draft state.
- **Unit B (Drafts+Items epic):** builds the Draft editor as its own screen module. Following AD-13 ("screens re-read from the API on every mount"), it calls generation again on mount, using the language, category, text, and context from query parameters.
- **Result:**
  - Two LLM calls happen per Draft.
  - Back/forward or a reload silently re-generates, and the user's edits are lost without a dirty prompt, because the route mounted fresh.
  - Generation context ends up in the URL, which shows up in history. That is close to "never persisted".
  - After Save, FR-12 and the UX success banner ("Saved “<Target>” to Anki…") need the Target to cross back to Capture detail. Unit A re-reads the Capture, which has no record of the Item. Unit B appends `?saved=<target>`, which puts content in the URL.
- **Why both comply:** AD-13 lists the client paths and has no Draft path. "No cross-screen data cache" is ambiguous between a cache and a handoff.
- **Proposed rule (AD-13):**
  - The Draft editor is a sub-view of the Capture detail screen at `/captures/<captureId>`, not a route. The Draft and Generation context live only in that screen's memory and are lost on unmount or reload; that's intended, and the dirty guard covers it.
  - The router provides one one-shot `navigate(path, {flash})`. Its message is shown once by the destination screen and is the only data that crosses screens.

### H2. The dirty-state contract has no shape

- **Unit A (Runtime epic, `router.js`):** `router.setDirty(bool)`. It shows a generic "Discard unsaved changes?" dialog and owns `beforeunload`.
- **Unit B (Items epic):** the Item detail needs the dialog body "N unsaved changes to “<Target>”" and the chip count. So it reports `setDirty({count, target})`, or it builds its own dialog for its in-screen "Discard" button, which the UX says also goes through the warning.
- **Unit C (Drafts epic):** needs "This Draft isn't saved."
- **Result:**
  - The dialog copy diverges.
  - Two dialogs can stack.
  - In-screen exits (Discard, the duplicate sheet's "Open existing") either skip the guard or duplicate it.
  - After a successful Save, the screen navigates while still dirty and gets its own warning. Each unit clears dirty at a different moment.
- **Why both comply:** AD-13 says only "screens only report dirty state to it".
- **Proposed rule (AD-13):**
  - Screens call `router.setDirty(null | {kind: 'draft' | 'edits', count, target})`. The router alone renders the unsaved alert, owns `beforeunload`, and provides `router.confirmLeave()` for in-screen exits such as Discard and Open existing.
  - A screen calls `setDirty(null)` before navigating after a successful Save.

### H3. Nobody owns the SchemaVersion write

- **Unit A (Captures epic):** a feature can't import `adapters/anki/manifest.py`, by the dependency rule. So it adds `schema_version: int = 1` to `domain.Capture` and writes it through the port. AD-1 says ports take domain types, so this complies.
- **Unit B (Runtime/Setup epic):** bumps `manifest.SCHEMA_VERSION` to 2 and adds a migration.
- **Result:**
  - Every new Capture is stamped 1, so Setup reports a migration forever.
  - Items, built by a third agent, stamps the manifest version through the adapter. That gives two sources of truth.
  - Separately, an Item edit on a v1 note by a v2 adapter either stamps v2 without migrating the fields (lying), or writes a field the old note type lacks (AnkiConnect error, which the user sees as `anki_unavailable`).
- **Why both comply:** AD-3 says only that the manifest declares "the current SchemaVersion". FR-7 says every note records it, but no AD names who writes it.
- **Proposed rule (AD-3):**
  - `SchemaVersion` is never a domain field. The Anki adapter stamps `manifest.SCHEMA_VERSION` on every note add.
  - The adapter refuses any update to a note whose stamp differs from it, with `setup_required`. Only a Setup migration step rewrites the stamp.

### H4. Two mutation paths for the `Audio` field, and the self-delete case

- **Unit A (Audio epic):** owns Reference audio (FR-26–FR-29), so it ships `PUT /api/audio/<itemId>`: store media → update `Audio` → delete the old file. This mirrors AD-6's Save Item steps 1, 2, and 4, so it complies with AD-6's "fixed order".
- **Unit B (Items epic):** `POST /api/items/<itemId>` takes the field edits plus an optional `audio` multipart part, per AD-6 Save Item.
- **Result:**
  - The Item detail "Save changes" with both text and audio edits becomes either two non-atomic requests or two code paths that both delete superseded media.
  - A new Draft has no ItemId before the first Save (AD-8), so Unit A's endpoint can't serve the Draft editor. The Draft editor has to use Unit B's path, and the Item detail might use either.
- **Self-delete bug:** both units implement "keep current audio" by re-uploading the current Blob, since AD-14 says the browser "re-uploads it at Save". AD-7 hashes the bytes, so the new name equals the old name. AD-6 step 4 then deletes the "superseded" file, which is the file just linked. The Item now points to missing media.
- **Proposed rule (AD-6, AD-14):**
  - The `Audio` field and managed media are mutated only by the Items Save and Delete use cases. `features/audio` owns only the Voice list, Preview synthesis, and serving stored audio.
  - The Save request carries `audio: "keep" | "replace" | "remove"`, with bytes only for `replace`. Step 4 deletes the old file only when its name differs from the new name.

### H5. Item domain and API shape: no owner, no single wire form

- **Unit A (Drafts epic):** owns AD-11's per-Category generated model. It puts `VocabularyDraft` and `SentenceDraft` in `domain/` and returns `{category, fields: {...}}` from `/api/drafts`. Since `RussianAlternatives` is a list, its model also defines the split and join.
- **Unit B (Items epic):** defines `domain.Item` flat: `{itemId, language, category, target, russian, russianAlternatives, …, audio}`. Its Item read response is flat.
- **Result:**
  - The Draft editor (Drafts) and Item detail (Items) can't share a form component. The Save request (AD-11 "extends" the generated model) is flat for one unit and nested for the other.
  - "Client-held fields" in AD-11 is undefined. Is `target` in it? `itemId`? `language`? `audio`?
  - Splitting alternatives is done in the service by one unit and in the adapter by the other. An alternative containing a comma ("быть, существовать") doesn't round-trip.
- **Regeneration clash (FR-24):** Items needs to regenerate only the Russian meaning, only the example, or only the Note. Items adds a `RussianMeaningRegen` model under `features/items`, or calls the Drafts feature internals. The first breaks "one schema per Category"; the second breaks the dependency rule.
- **Proposed rule (new AD, or AD-11):**
  - `domain/items.py` is owned by the Items epic and defines `ItemContent`, a union discriminated by `category`: generated fields + `mnemonic` + `target`. It also defines `Item = ItemContent + itemId + language + audio state`.
  - Draft responses, Save requests, and Item reads all use this flat camelCase shape.
  - `russianAlternatives` items may not contain a comma (the validator rejects it). Only the Anki adapter joins and splits them.
  - Regeneration calls the same per-Category generation with the current Item as context, through the drafts endpoint. The client takes the fields it wants.

### H6. The Pronunciation session lifecycle has no owner, no endpoints, and no dedupe

- **Unit A (Pronunciation epic):**
  - `GET /api/pronunciation/fr/next` returns the first new/due card, then calls `sync.request()`, following AD-5 ("reads the first card before it enqueues").
  - It treats an empty queue as the session end (glossary) and enqueues the post-session Sync.
  - It answers with `POST .../answer {itemId, rating}`.
- **Unit B (Sync epic):**
  - Exposes `POST /api/sync/session-end` for the router-unmount and `sendBeacon` signals in AD-17.
  - Enqueues one Sync per call.
- **Result:**
  - Every `next` call looks like a session start, so every card triggers a Sync unless Unit A invents a server-side "session open" flag. AD-2 forbids that, because it limits runtime state to the lock and the scheduler.
  - The session end fires two or three times: queue empty, unmount, and `pagehide`. That's three Syncs.
  - The bfcache restore on iOS (`pageshow`) never re-mounts, so there's no start Sync.
  - To reach the Sync feature, Pronunciation must import `features/sync`, which the dependency rule forbids, or call `AnkiStore.sync()` directly, which AD-17 forbids.
- **Rating idempotency:** a Rating request that times out after Anki applied it gets retried ("Try again", per the UX), and the card is answered twice.
- **Proposed rule (AD-17, AD-5):**
  - `domain` (or `ports`) defines a `SyncRequester` protocol that `app.py` injects. Its `request()` coalesces to at most one pending Sync.
  - Pronunciation owns `POST /api/pronunciation/<lang>/session` (start: returns the first card and the counts, then requests a Sync) and an idempotent `.../session/end`. The queue is recomputed statelessly on each `next`.
  - An answer carries the card's last-review marker, and the adapter treats a stale marker as already answered.

### H7. The Prefix wildcard leaks between the release and dev instances

- **Unit A (Captures epic):** obeys AD-4 literally. Its list query is `deck:"LanguageLab*" note:"LanguageLab Capture"`, or deck-only.
- **Unit B (Setup epic):** scans `deck:"LanguageLab*"` to report "content under the Prefix the manifest doesn't recognize".
- **Result:** the spine itself prescribes dev Prefix `LanguageLabDev` in the same Anki. `deck:"LanguageLab*"` matches `LanguageLabDev::…`. So:
  - The release Setup reports every dev note and deck as "non-managed content under the Prefix", and offers repairs that would touch dev data. AD-4's write guard is checked against the release manifest, whose note-type names differ, so the result depends on which check each unit happened to write.
  - A deck-only Captures query in release lists dev Captures.
- **Proposed rule (AD-4):**
  - Read queries are scoped as `deck:"<Prefix>"` (Anki includes subdecks) or `"deck:<Prefix>::…"` exact paths, plus `note:"<exact manifest note type>"`. A wildcard on the Prefix itself is never used.
  - Settings validates `ANKI_PREFIX` as `[A-Za-z][A-Za-z0-9]*`, and no Prefix may be a prefix of another Prefix in the same collection. Docs name `LanguageLabDev` as an example only if the first part of the rule holds.

### H8. The error envelope can't carry the duplicate or setup outcomes, and Save isn't idempotent

- **Unit A (Drafts+Items, Draft editor):** calls `GET /api/items/<lang>/duplicates?target=…` and then `POST` Save.
- **Unit B (Items, Save route):** runs the check inside Save. It returns `409` with the matches so that FR-19 "Open existing" can link to them. But AD-15's envelope is `{code, message, requestId}` only, and the enum has no `duplicate_found`. So it returns `200 {created:false, matches}`, a non-error 200 that `api.js` treats as success.
- **Result:** the client and server disagree on whether duplicates are a read or an outcome of Save. "Create anyway" needs a flag that only one unit knows.
- **`setup_required`:** the code exists, but no AD says who emits it. Captures maps AnkiConnect's "model not found" to `anki_unavailable` (the copy says "Anki isn't reachable", which is wrong). Items does a full manifest diff before every request. Setup adds middleware.
- **Duplicate notes on retry:** the first Save times out after Anki committed it. The user taps Try again, and the backend mints a second ItemId (AD-8: "at the first Save"). That's a silent duplicate note with four more cards.
- **Proposed rule (AD-15, AD-8, AD-12):**
  - The duplicate check is a separate read endpoint owned by Items. Save never checks.
  - The envelope gains an optional `details` object, and the enum is the only place new codes are added, by the epic that needs them.
  - The Anki adapter alone maps a missing manifest resource or a SchemaVersion mismatch to `setup_required`.
  - The backend issues the ItemId when it returns a Draft, and Save is create-or-update keyed by that ItemId, so a retried Save is idempotent.

---

## Should-fix

### H9. Who owns manifest edits, and does a template change bump SchemaVersion?

- **Setup epic:** owns `manifest.py`.
- **Items epic:** owns the template markup and CSS (Deferred, OQ-5).
- **Result:** Items adds a back-only field for a template need, or edits templates and bumps `SchemaVersion` "to be safe". That forces a confirmed migration step with no data change, and Setup has no step registered for it.
- **Rule:** `manifest.py` has one owner (the Setup epic), and feature epics change it only through that owner's review. Template or CSS-only changes never bump `SchemaVersion` and are fixed by Setup's ordinary diff repair. Any field-list change bumps it and ships its migration step in the same change.

### H10. The codec quietly breaks search, Write typing, and newlines

- **Codec owner:** uses `html.escape(text)`, which defaults to `quote=True`. So `l'eau` is stored as `l&#x27;eau`, and nothing on the write side turns `\n` into `<br>` ("adds no markup").
- **Items owner:** implements FR-22 search as an Anki search expression. `l'eau` never matches.
- **Templates owner:** shows multi-line Examples as one run-on line in AnkiMobile.
- **Rule (AD-9):** the codec escapes only `& < >` and writes `\n` as `<br>`, its only markup. Item search fetches the Language's notes through the adapter and matches in the service on decoded values, like AD-12, not through Anki search syntax.

### H11. Delete Item's media scope against Setup's orphan definition

- **Items:** "delete its managed media" deletes only the file named in `Audio`.
- **Setup:** defines an orphan as "managed media whose ItemId has no note". A leftover from a failed Save step 4, for an Item that still exists, is then never reported.
- **Rule (AD-7):** a managed file is an orphan if and only if no managed note's `Audio` field references it. Delete Item removes every managed file whose name carries its ItemId.

### H12. Which deck a new note is added to, and the Pronounce leak

AD-6 step 3 moves cards after the add, but the deck passed to `addNote` isn't fixed.

- **Items agent:** adds to `…::Study::<Lang>::<Cat>::Understand`.
- **Result:** if step 3 fails, the Pronounce card sits in a Study deck and appears in AnkiMobile study. A "tolerated" leftover then causes user-visible harm.
- **Rule (AD-6):** `addNote` targets the Item's Pronunciation leaf deck, so a failed move can only hide Study cards, never expose Pronounce cards to Anki study.

### H13. Serving stored Reference audio

Pronunciation (FR-31), Item detail, and Draft playback all need stored audio bytes.

- **Pronunciation:** adds `GET /api/pronunciation/audio/<itemId>`.
- **Items:** adds `GET /api/items/<itemId>/audio`.
- **Audio:** adds `GET /api/audio/<mediaName>`, which leaks the media name and Prefix (AD-8 spirit).
- **Rule:** one `GET /api/audio/items/<itemId>`, owned by `features/audio`, reading through `AnkiStore`.

### H14. Attempt reference text: from the client or from Anki?

- **Pronunciation:** the client posts `targetText`.
- **Second agent:** reads the Item under the lock (AD-14: "Target text as reference").
- **Result:** with Anki down, one build can still assess and the other fails with `anki_unavailable`. The UX expects an Assessment failure to be retryable, without an Anki dependency.
- **Rule (AD-14):** the Attempt request carries `itemId`, `language`, and `targetText` from the current card. The Attempt path never touches `AnkiStore`.

### H15. The Save multipart layout

- **Draft editor:** sends form fields per key.
- **Items route:** expects one JSON part validated by the AD-11 Pydantic model.
- **Rule (conventions):** Save is `multipart/form-data` with exactly two parts: `item` (`application/json`, the Save model) and optional `audio` (`audio/mpeg`).

### H16. Allowed in-memory state

- **Audio:** caches the Azure voice catalog.
- **Setup:** keeps the last Apply result for "returning to Setup shows the verification result".
- **Pronunciation:** keeps a session flag.
- **Result:** AD-2 lists the lock and the Sync scheduler as the *only* runtime state. A strict reviewer rejects all three; a loose builder adds more.
- **Rule (AD-2):** in-memory state is limited to the lock, the Sync scheduler/coalescer, and a TTL'd Voice-catalog cache. The Setup result is always recomputed by diff, never stored.

### H17. The Voice preference key

Draft editor, Item detail, and the Audio module each write `localStorage` under their own key (`voice:en-US`, `ll.voice.en`, …). FR-29 then appears broken across screens.

- **Rule (AD-13):** one `static/voice-pref.js`, owned by Audio, with the key `languagelab.voice.<locale>`. It is the only `localStorage` accessor.

### H18. The Origin-versus-Host comparison behind Tailscale Serve

- The Runtime middleware compares `Origin` (`https://mini.tailnet.ts.net`) to `Host`.
- Depending on proxy header handling, `Host` may be `127.0.0.1:8787`, and the scheme is never part of `Host`.
- **Result:** an implementation that string-compares rejects every mobile write. One that strips too much accepts anything on localhost.
- **Rule (AD-16):** compare the Origin's `host[:port]` with the `Host` header, or with `X-Forwarded-Host` when the peer is loopback. A missing Origin on non-GET is rejected. `sendBeacon` is covered because it is a same-origin POST that carries Origin.

---

## What survived

- AD-1, AD-4 (except the wildcard), AD-5's "a use case is one port call", AD-6's ordering (except the deck and same-hash cases), AD-8's "no note ids outside the adapter", AD-12, AD-15's logging rule, and AD-18 all held up. I couldn't build a contradiction against them that both units could satisfy.
- The fixed ord → Exercise → deck mapping in AD-3 is the strongest single decision in the spine. It removes a whole class of Items/Setup/Pronunciation drift.

---
title: Rubric review — LanguageLab architecture spine
reviewed: architecture-languagelab.md (status draft, 2026-10-08)
against: prd-languagelab.md, addendum.md, .memlog.md
date: 2026-10-08
---

# Rubric Review: LanguageLab Architecture Spine

## Verdict

This is a strong spine. The paradigm is clear and the ports/adapters boundary is crisp, and most ADs name a real divergence and a rule that can be enforced. The stack versions are verified as current. Before feature epics start, it needs three Anki-operational fixes: full-sync handling, the scope of the deck-options preset, and the initial deck for a new note. It also needs one missing AD covering setup gating and SchemaVersion compatibility. None of these changes the paradigm.

## Checklist Results

| Criterion | Result | Notes |
| --- | --- | --- |
| Fixes the real divergence points for feature epics | Mostly | Missing: setup-gating/`setup_required` rule, SchemaVersion forward-compat, initial deck of a new note, deck-preset ownership, FR-22 search mechanism (F1–F4, F9) |
| Every Rule enforceable and prevents its divergence | Mostly | AD-16 does not prevent DNS rebinding (F5); AD-5 depends on one worker (F7); AD-11 "strict" is not what Pydantic emits by default (F6) |
| Nothing under Deferred lets units diverge | Pass | Deferred items are each local to one feature/adapter. "Exact API endpoint list" is safe given AD-13/AD-15 + conventions |
| Named tech verified-current | Pass | PyPI checked 2026-10-08: fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.0, pydantic-settings 2.15.0, httpx 0.28.1, av 19.0.1, pytest 9.1.1, ruff 0.16.10, uv 0.12.24 all latest. GH actions checkout v7.0.1, setup-uv v10.2.0, action-gh-release v3.0.3 latest. av 19.0.1 has `cp312-abi3` macOS arm64 wheel (usable on 3.14) but requires **macOS 14+** (F12) |
| Covers PRD capabilities | Pass (minor gaps) | Every FR group maps to a module + AD. Gaps: FR-22 search over `RussianAlternatives` (F9); FR-36 "before session" ordering (F10) |
| Altitude dimensions decided/deferred/open | Partial | Deployment & environments: decided. Infra/provider: decided (single provider each, OpenRouter fallbacks). **Operations**: upgrade/rollback, Sync health visibility, secrets file permissions and dev/release coexistence are not addressed (F1, F4, F11, F13) |

## Findings

### F1 — HIGH — AD-17 / AD-3: schema-changing Setup silently breaks Sync forever

**Fact (verified in AnkiConnect `plugin/__init__.py`):** `sync` calls `col.sync_collection(...)` and **raises** unless the result is `NO_CHANGES` or `NORMAL_SYNC`. It then calls `mw.onSync()`, which runs a second GUI sync with media in the background. It also raises `sync: auth not configured` when the profile is not logged in. `modelFieldAdd`/`modelFieldRemove`/`modelFieldRename` save through `models.update_dict` with no confirmation dialog, which marks the collection as *full sync required*.

**Consequence:** After any migration that touches note-type fields, and possibly after first-time `createModel` (verify this), every AnkiConnect `sync` raises. AD-17 says Sync failures are only logged and "never surface in the UI". AnkiWeb and AnkiMobile would then diverge silently and indefinitely. This breaks UJ-3/UJ-4 and FR-36's convergence goal. The manual fix (a one-way full sync in Anki Desktop) can also discard AnkiMobile reviews done since the last good sync.

**Fix:**
- Add to AD-3: a Setup plan marks each schema-changing step as `requiresFullSync`. Setup runs a normal Sync *before* apply, so no mobile reviews are pending. After apply, Setup tells the user to do a one-way **upload** from Anki Desktop.
- Amend AD-17 so the last Sync outcome (ok, failed, full-sync-required, auth missing) is kept in memory and shown by the Setup/readiness check (FR-5). It still never blocks a request.

### F2 — HIGH — AD-3 / FR-8: deck-options preset ownership and scope are wrong or unspecified

1. **Shared presets.** Anki deck options are *shared presets* (deck config ids). If the Study decks sit on the user's `Default` preset, saving "bury off" through `saveDeckConfig` changes every deck the user has on that preset. That violates NFR-1 and FR-8's "other options untouched". AD-4's boundary check can't catch this, because a preset isn't named as a manifest resource.
2. **Pronunciation decks also need burying off.** With the v3 scheduler, siblings are buried *when a card is answered*, using the answered card's home-deck config. So answering a Pronounce card through `answerCards` in a Pronunciation deck that uses a bury-on preset buries that day's Understand/Produce/Write siblings. That defeats UJ-4's independent progress.

**Fix:** In AD-3, make the manifest declare one preset named `<Prefix>` (created with `cloneDeckConfigId`, assigned with `setDeckConfigId`). Assign it to **all managed Study and Pronunciation decks**, and have Setup manage only its three bury flags (`new.bury`, `rev.bury`, `buryInterdayLearning`). AD-4 should reject `saveDeckConfig` on any preset that isn't the manifest preset. Raise the Pronunciation-deck point upstream as a PRD FR-8 clarification.

### F3 — MEDIUM — AD-6: initial deck of a new note, and AnkiConnect duplicate rejection

- **Initial deck.** `addNote` takes one `deckName` for all four cards, and AD-6 step 3 moves them afterwards. The spine never says which deck step 2 uses. If it is a Study deck and step 3 fails, the Pronounce card is studied in AnkiMobile. If it is a Pronunciation deck, the three Study cards show up in the LanguageLab queue. AD-6 tolerates misplaced cards "until Setup repairs", but where they land decides how bad that is. **Fix:**
  - Pin the initial deck in AD-6, for example the item's Pronunciation leaf deck.
  - Define the pronunciation queue query as manifest Pronunciation deck **and** template ord 3 (`card:<Pronounce template name>`), so a misplaced Study card can never enter it.
- **Duplicate rejection.** By default, AnkiConnect's `createNote` rejects a note whose first field duplicates an existing note of the same model. The Capture note type's first field is `Text` (A3 order), so two Captures with the same text would fail. For Items, it depends on the field order, which the spine doesn't fix. If `Target` comes first, FR-19's "Create anyway" fails inside Anki. **Fix:** Add a rule that the adapter always sends `options.allowDuplicate: true`, since duplicate policy belongs to AD-12 and not to Anki. Optionally, fix field order in AD-3 (`Target` first as the sort field, `ItemId` hidden).

### F4 — MEDIUM — Missing AD: setup gating and SchemaVersion compatibility (operations: upgrade/rollback)

`setup_required` is in the error enum, but no rule says **when** a feature returns it. As written, each epic will decide independently whether to check the manifest diff. The Captures epic might write notes into a half-built structure while the Items epic checks first. Nothing covers what an **older** wheel does when it meets notes or note types at a higher `SchemaVersion`. Rollback by running an older `uvx --from <old wheel>` after a migration is the natural operator move, and today it is undefined.

**Fix:** Add an AD.
- At startup and after Setup apply, the app computes a cached `SetupState` (`ready` / `needs_setup` / `needs_migration` / `newer_schema`).
- Every Anki-writing use case except Setup returns `409 setup_required` unless the state is `ready`.
- `newer_schema` blocks all writes and tells the user to run the newer release.
- Reads remain allowed.
- Document the upgrade procedure in `docs/`: stop, start new wheel, Setup, confirm migration.

### F5 — MEDIUM — AD-16: Origin == Host does not stop DNS rebinding

A malicious page in a browser on the Mac Mini can DNS-rebind its own hostname to `127.0.0.1`. Its requests then carry `Origin: http://evil.example:8787` and `Host: evil.example:8787`, which match, so state-changing calls pass. GET `/api` (captures, items) is also readable, and the rule does not cover GET at all. This is the standard localhost-service attack, and it is the threat AD-16 names.

**Fix:** Replace the comparison with a **Host allowlist** checked on every request (`127.0.0.1:<port>`, `localhost:<port>`, and the Tailscale MagicDNS name discovered at startup or configured in `.env`). For non-GET requests, also require that `Origin` is on the same allowlist. Tailscale Serve preserves the incoming `Host`, but check that during the FR-2 acceptance test. Comparison should ignore the scheme (`https` origin vs plain-HTTP upstream).

### F6 — MEDIUM — AD-11: "Its JSON Schema (strict)" is not what Pydantic emits

OpenAI-style strict structured output, which OpenRouter passes through and `require_parameters` selects for, requires:
- `additionalProperties: false` on every object;
- **every** property listed in `required`, with optional values expressed as `"type": [..., "null"]`;
- no unsupported keywords such as `default`, plus some `format`/`pattern` limits that vary by provider (for example Gemini).

`Model.model_json_schema()` emits defaults and omits optional fields from `required`, so the providers would reject it or silently drop strictness.

**Fix:** In AD-11, name one exporter, `domain.schemas.strict_json_schema(model)`, as the only producer of the wire schema. Category models use `extra="forbid"` and `T | None` with no defaults for optional generated fields. A unit test asserts the exported schema satisfies the strict-mode constraints.

### F7 — LOW — AD-5: lock correctness assumes one process

An in-process `asyncio.Lock` serializes only within one uvicorn worker. Running dev (`uv run`, a dev Prefix) and release at the same time against the same AnkiConnect creates two locks. The release instance's Sync would also upload the `LanguageLabDev` decks to AnkiWeb and AnkiMobile.

**Fix:** In AD-5, state "single uvicorn process, `workers=1`, no `--reload` in release". In the Environments section, say dev and release are not run at the same time against the same Anki profile, or that dev uses a separate Anki profile.

### F8 — LOW — AD-9: escaping must not touch quotes

Python's `html.escape` escapes `'` and `"` by default. The Anki editor stores raw apostrophes. Anki search, and the user's own browsing in Anki, would then miss `don&#x27;t`.

**Fix:** In AD-9, escape only `& < >` (`html.escape(s, quote=False)`), and keep the read path's unescape as is.

### F9 — LOW — FR-22 search mechanism is an unfixed divergence point

FR-22 search (Target + Russian meaning, both Categories) has no AD. AD-12 forbids Anki search expressions for duplicates only. After AD-10, "Russian meaning" spans `Russian` and `RussianAlternatives`, and it's open whether search goes through an Anki `findNotes` expression (which runs on escaped, raw field HTML) or through service-side matching on decoded values.

**Fix:** Add one line to AD-12 or AD-10: search fetches the Language's notes and matches service-side with `normalize_target` over `target`, `russian` and `russianAlternatives`.

### F10 — LOW — AD-17 / AD-5 vs FR-36 and UJ-3 ordering

The PRD has "LanguageLab syncs **and then** shows the first card" (UJ-3) and a Sync "before" each session (FR-36). The spine reads the first card before enqueuing the Sync. That's a defensible latency trade-off, but it contradicts the PRD as written, so record it as an explicit amendment the way AD-10 does. Also, the glossary ends a session when "the queue is empty", while AD-17 lists only router unmount and `pagehide`. Add queue-empty as an end trigger. On iOS, prefer `visibilitychange` → `hidden` alongside `pagehide`, because `pagehide` doesn't fire reliably on app switch.

### F11 — LOW — Operations: Sync blocks Anki and the follow-on GUI sync

AnkiConnect runs `sync_collection` on Anki's main thread and then starts `mw.onSync()`, a background GUI sync with media. Requests that arrive during that GUI sync may fail or stall even though the LanguageLab lock has been released. This doesn't change any AD, but the Anki adapter epic should treat a transient AnkiConnect error just after a Sync as `anki_unavailable`, and the request should not be retried automatically, per the Deferred note. Put it in the Deferred line on adapter timeouts so the adapter epic sees it.

### F12 — LOW — Stack: platform floor not stated

`av 19.0.1` macOS arm64 wheels are tagged `macosx_14_0`, and `requires-python >=3.14` means `uvx` downloads a managed CPython. State the Mac Mini floor (macOS 14+, Apple silicon) in Stack, or the first `uvx` run could fall back to building PyAV from source.

### F13 — LOW — Operations: secrets and release hygiene

- The `.env` holds the Azure and OpenRouter keys. In `docs/`, say `chmod 600 ~/.config/language-lab/.env`, and have `settings.py` warn if the file is group- or world-readable.
- The CI release job should fail when the tag `vX.Y.Z` doesn't equal the `pyproject.toml` version.
- Name the build backend (for example `uv_build` or `hatchling`) and confirm that `static/` and `adapters/anki/templates/` are included as package data. The whole client and every card template ship inside the wheel, so a missing glob breaks a release silently.

## Factual Check: External Systems

| Claim in spine | Status |
| --- | --- |
| AnkiConnect API version 6; actions listed in memlog (answerCards ease 1–4, sync, storeMediaFile, deleteMediaFile, getMediaFilesNames, findCards, cardsInfo, notesInfo, addNote, updateNoteFields, deleteNotes, suspend, createModel, updateModelTemplates/Styling, modelFieldAdd, createDeck, saveDeckConfig, cloneDeckConfigId, setDeckConfigId, changeDeck, multi) | Correct |
| `addNote` takes one deck, so cards are moved with `changeDeck` | Correct. The initial deck still needs specifying (F3) |
| `answerCards` reports failure | Partly. It returns a list of booleans (`false` for an unknown card) rather than raising, so the adapter must check each element. It also answers cards that are not due, so the service must confirm the card is still in the queue |
| `sync` behaves like a normal sync call | Incomplete. It raises on full-sync-required or missing auth, and starts a follow-on GUI sync (F1, F11) |
| Azure REST short audio accepts WAV PCM 16 kHz mono / OGG Opus | Correct (Microsoft Learn, REST short audio) |
| Pronunciation assessment one-shot is at most 30 s | Correct. The REST short-audio doc says "for pronunciation assessment, the audio duration should be no more than 30 seconds" (general limit 60 s) |
| Prosody via REST, en-US only | Correct. `EnableProsodyAssessment` is a REST `Pronunciation-Assessment` header parameter. Adapter note: use `format=detailed` and `Granularity=Phoneme` to get phoneme-level results |
| Azure TTS via REST (MP3, voice list) | Correct (`/cognitiveservices/v1` + `X-Microsoft-OutputFormat`, `/cognitiveservices/voices/list`) |
| OpenRouter `models` fallback array + `provider.require_parameters=true` + `json_schema` strict | Correct. The strict schema shape is the risk (F6) |
| FastAPI static + catch-all shell + `/api` | Correct. Mount `/static` and register `/api` routers before the catch-all GET route, and make the catch-all return 404 JSON for unknown `/api/*` paths so they don't get the HTML shell |
| iOS Safari MediaRecorder emits `audio/mp4` (AAC), PyAV decodes it in memory | Correct |

## Over-specified or Obvious Rules

These aren't wrong, but they cost reading time without preventing a real divergence. Consider moving them to the Conventions table or deleting them.

- **AD-18, third bullet** (OpenRouter `models` array + `require_parameters`). This is adapter wire detail inherited verbatim from addendum A4, not a configuration rule. Move it to AD-11 or leave it to the adapter.
- **AD-5, last sentence** (first card read before pre-session Sync). This is a single-feature sequencing detail and belongs in the pronunciation epic. If kept, it needs the PRD amendment note (F10).
- **Conventions "Python" row** ("async throughout; one `httpx.AsyncClient` per adapter"). These are defaults no one would diverge on.
- **Stack: pytest and ruff pinned to patch versions.** These are dev tools, not runtime divergence points. A lockfile covers them.
- **AD-2's mention of `localStorage` Voice-per-locale** duplicates AD-13 and FR-29. That's harmless.

The remaining ADs earn their place. AD-7, AD-8, AD-9, AD-12 and AD-14 each settle something two epics would otherwise settle differently.

## Deferred Section Check

| Item | Can two units diverge? |
| --- | --- |
| Card template visuals | No. Items epic owns them; AD-3 fixes location, AD-10 fields |
| Exact API endpoints | No, given AD-13/AD-15 and path conventions. Consider adding the HTTP status per error code (e.g. `anki_unavailable` → 503, `setup_required` → 409, `validation_failed` → 422) to the AD-15 enum, so routes don't pick different statuses for the same code |
| Pronunciation queue cap | No (single feature) |
| Capture search, spend guardrails | No |
| Timeouts/retry per adapter | No (adapter-local). Add the F11 note |
| Tailscale URL discovery | No, **unless** F5's Host allowlist depends on it. Then it becomes an input to AD-16 and should say so |
| Live-Anki test harness | No |

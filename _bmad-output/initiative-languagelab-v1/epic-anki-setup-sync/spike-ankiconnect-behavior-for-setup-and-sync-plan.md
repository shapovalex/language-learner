---
title: 'Spike: AnkiConnect behavior for Setup and Sync'
type: 'feature'
ticket: '2'
created: '2026-10-14'
status: 'built'
baseline_revision: 'a4109aedc5346d58cd1aba783ba95bcdb58ab38f'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context:
  - '{project-root}/_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md'
  - '{project-root}/_bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The rest of epic 2 (manifest, preview and apply, migrations, Sync) depends on AnkiConnect behaviour nobody has observed: the reply shape of each action it uses, whether field changes raise a modal in Anki Desktop, how `sync` reports full-sync-required, not-logged-in and offline, and which deck-config keys hold the three sibling-burying flags.

**Approach:** Extend `language-lab-record-fixtures anki` with a guarded probe and a sync probe. The user runs them from a released wheel on the Mac Mini, in a throwaway Anki profile logged in to a throwaway AnkiWeb account. They record redacted fixtures to `tests/fixtures/anki/`, and a findings doc answers each question with the fixture that shows it.

## Boundaries & Constraints

**Always:**
- The probe touches only `LLProbe`-prefixed note types, decks, presets and media.
- Before any write, it refuses (exit 1, one stderr line, no writes) when:
  - the active profile holds any note type whose name starts with `LanguageLab`, or
  - the active profile is not the one named by a required `--profile`.
- Fixtures are redacted: profile names become `LLProbeProfile`, email addresses become `redacted@example.com`, and nothing else private is kept. Read before commit.
- Everything stays stdlib-only, like the rest of the recorder. Bare `anki` and `anki --url` keep printing the version exchange (2.1's tests pass unchanged). `serve` and `status` are unchanged.
- The probe is re-runnable in the same throwaway profile: it reuses `LLProbe` resources that already exist rather than failing.
- Runs on the Mac Mini go through `uvx --from <wheel>` only (no clone).

**Decision (user, 2026-10-14):** the Mac Mini runs the latest Anki and AnkiConnect, which keep legacy v6 at `/` and add JSON-RPC API v1 at `/api/v1`. The probe records every listed action over v6. The sync probe records v6 `sync` both standalone and inside `multi`, and v1 `collection.sync` polled through `operations.get` until a terminal state or `waitingForUser`, capped at 120 s. If `/api/v1` doesn't answer, or refuses permission, the reply is recorded as the fixture.

**Decision (user, 2026-10-14, review loop 1):** `anki sync` pauses after each of its three exchanges (v6 `sync`, then v6 `multi[sync]`, then v1 `collection.sync` with its polling). At each pause it waits for Enter, so the user can let Anki's sync finish and note any dialog before the next exchange starts. `--yes` skips the pauses, for tests.

**Never:**
- No change to `src/language_lab/adapters/`, `features/` or the app. The spike records and decides; it does not implement Setup or Sync.
- No deletion of anything the probe didn't create.
- No test reaches a real Anki.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Probe, clean throwaway profile | `anki probe --profile P --out DIR`, P active, no `LanguageLab*` note types | One `<action>.json` `{request, response}` per probed action in DIR, redacted; exit 0 | None |
| Guard: managed note types present | `modelNames` includes `LanguageLab Capture` or `LanguageLabDev …` | Exit 1, one stderr line naming the offending note type; only read actions sent | No traceback |
| Guard: wrong profile | Active profile ≠ `--profile` | Exit 1, one stderr line naming both; only read actions sent | No traceback |
| Action returns an error | AnkiConnect `{"error": "…"}` for one action | Fixture records the error reply; the probe continues and exits 0 | Error recorded, not raised |
| Sync probe | `anki sync --profile P --label L --out DIR [--yes]` | `sync-L.json` holding the v6 standalone and `multi`-wrapped exchanges and the v1 `collection.sync` plus `operations.get` exchanges, with a pause for Enter between the three (skipped by `--yes`) | Same guard as the probe |
| AnkiConnect down | Nothing on `--url` | Exit 1, one stderr line naming the URL | No traceback |

</frozen-after-approval>

## Code Map

- `src/language_lab/tools/record_tailscale_fixtures.py:286-319` -- `_anki(url)` (urllib POST, the error tuple `OSError, ValueError, http.client.HTTPException`), and `run()` argparse. Reuse the POST/except shape. The docstring's `anki` paragraph says the reply carries nothing private; revise it for the probe's redaction.
- `tests/support/anki_connect.py:93` -- `run_stub_ankiconnect(replies)` answers by action only and records `.received`. Extend it so a reply can be a callable of the request body (needed for `multi` and sequenced `getDeckConfig`), keeping the existing mapping usage.
- `tests/support/recorder.py:36` -- `run_recorder_anki(url)`. Add a helper that passes extra args.
- `tests/integration/test_record_anki_fixtures.py` -- the existing three tests stay unchanged.
- `tests/fixtures/README.md:30-38` -- the AnkiConnect section. Add the probe fixtures and the re-record commands.
- Naming (addendum A3, arch AD-3/AD-4):
  - Real note types are `<Prefix> Capture|English Vocabulary|…`, so the guard matches the name prefix `LanguageLab`, which also covers `LanguageLabDev`.
  - Decks use `::`.
  - The preset is named the bare Prefix.
- AnkiConnect v6 facts (from the upstream README):
  - Envelope is `{result, error}`.
  - `getActiveProfile` exists.
  - `sync` alone returns null on acceptance; inside `multi` it waits for the final result.
  - Bury flags: `new.bury`, `rev.bury`, top-level `buryInterdayLearning`.
  - There is no `deleteModel`.
  - The newest add-on needs Anki 26.08+ and also offers API v1 at `/api/v1`.
- AnkiConnect v1 (upstream API_V1.md):
  - JSON-RPC 2.0 at `POST /api/v1`: `{"jsonrpc":"2.0","id":n,"method":…,"params":{}}`.
  - Errors look like `{"error":{"code","message","data":{"type"}}}`, for example 1011 `authenticationRequired`.
  - `collection.sync {includeMedia?}` returns `{operationId, method, session}`.
  - `operations.get {operationId}` returns the operation state: `queued|running|waitingForUser|succeeded|failed|cancelled`, with a result or error only once terminal. The final result is a `SyncResult`.
  - Permission may be required (`access.requestPermission`); the runbook says to grant it in Anki.

- Attempt 1 (reverted in review loop 1, kept for reuse): the diff is at `/private/tmp/claude-501/-Users-oleksii-projects-language-learner/112f7c49-1696-47b0-a36a-fa8499ba3059/scratchpad/spike-2-2-attempt1.diff`, and its new files are in `…/scratchpad/attempt1/`. Reuse it, with the Plan Change Log's corrections applied.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/tools/record_tailscale_fixtures.py` -- add `anki probe` and `anki sync` (sub-subcommands of `anki`; bare `anki` unchanged), the guard, the redaction and the per-action fixture writer.
  - The probe runs in this order:
    - `getProfiles`, `getActiveProfile`, `modelNames` → guard
    - `createModel LLProbe Probe` → `modelFieldNames` → pause: "watch Anki Desktop for a dialog, then press Enter" → `modelFieldAdd` → `modelFieldNames`
    - `modelTemplates`, `modelStyling`, `updateModelTemplates`, `updateModelStyling`
    - `createDeck LLProbe::Study`, `deckNames`
    - `cloneDeckConfigId LLProbe`, `setDeckConfigId`, `getDeckConfig` (before) → `saveDeckConfig` with the three bury flags off → `getDeckConfig` (after)
    - `addNote` into `LLProbe::Study`, `findNotes`, `notesInfo`
    - `storeMediaFile LLProbe_probe.mp3`, `getMediaFilesNames LLProbe_*`
  - `--yes` skips the pause, for tests.
  - Rationale: one guarded run covers every action the ticket lists.
- [x] `tests/support/anki_connect.py`, `tests/support/recorder.py` -- callable replies; recorder arg passthrough -- probe tests.
- [x] `tests/integration/test_record_anki_probe.py` -- one test per matrix row against the stub. Assert the files written, the redaction (a profile name and an email in replies never reach the files), and that the guard sends no write action -- the matrix.
- [x] `_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md` -- the runbook and an unfilled findings template.
  - Runbook steps:
    - make a throwaway profile and AnkiWeb account
    - record the Anki and AnkiConnect versions
    - run `probe`
    - run `sync` with each label: `normal`, `after-field-change` (before uploading), `logged-out`, `offline`
    - read the fixtures
  - Template: one row per question (modal, the 3 sync states, bury keys, re-run behaviour, and whether the adapter should stay on v6 or move Sync, or everything, to v1) with answer, fixture and design consequence for entries 4, 6, 9 and 10.
- [x] `tests/fixtures/README.md` -- document the probe fixtures, the commands, and that they are pending the Mac Mini run.

**Acceptance Criteria:**
- Given the stub AnkiConnect, when `make test` and `make lint` run, then all pass, including 2.1's recorder tests unchanged.
- Given a `LanguageLab Capture` note type in the stub's `modelNames`, when the probe runs, then the stub received no write action.
- Given the released wheel on the Mac Mini and the runbook (HITL), when the user runs it, then `tests/fixtures/anki/` holds one recorded response per probed action and every findings row is answered with its fixture.

## Implementation Notes

- Repeated actions get suffixed fixtures: `modelFieldNames-after`, `getDeckConfig-initial` (the deck's preset before the probe touches it, used to reuse an existing `LLProbe` preset on a re-run) and `getDeckConfig-after`.
- Re-run: `createModel` and `cloneDeckConfigId` are skipped when the `LLProbe` resources exist; `modelFieldAdd` adds the next free `LLProbeExtra<n>` so the dialog question is observable on every run. `saveDeckConfig` is sent only when the deck's preset is named `LLProbe`.
- Guard refusals write no files at all; the guard reads are written only after it passes, and only by `probe` (`sync` writes just `sync-<label>.json`).
- `modelFieldAdd` gets a 120 s timeout so a modal waiting on the user doesn't read as AnkiConnect down; the probe prints how long it took.
- In `sync`, a v6 or v1 request that gets no answer after the guard is recorded as `{"noReply": ...}` rather than exiting; v1 HTTP errors are recorded as `{"httpStatus", "body"}`. Consecutive identical `operations.get` replies (ignoring `id`) are kept once, with `pollCount`.
- Redaction also replaces the home folder with `/Users/redacted`.
- Review loop 1: the notes above describe attempt 1, whose code was reverted. The re-implementation keeps them, except where the Plan Change Log corrects them.

## Plan Change Log

- **Loop 1 (2026-10-14).**
  - **Trigger:** review found that the three sync exchanges run back to back (intent_gap). The user decided: pause for Enter between them, with `--yes` to skip.
  - **Amended:** the frozen decision and the matrix row, the Code Map pointer to attempt 1, and these constraints.
  - **Known-bad states to avoid:**
    - (1) Redaction must replace only string values *equal to* a profile name, never substrings. With the runbook's `--profile Probe`, attempt 1 turned `LLProbe Probe` into `LLLLProbeProfile LLProbeProfile`. The email and home-folder substitutions stay substring-based. Add a test using `--profile Probe`.
    - (2) v1 polling must not treat an unrecognised reply shape as terminal. Keep polling until the state is terminal or `waitingForUser`, or the 120 s cap is reached.
    - (3) `addNote` must not send `allowDuplicate`, so the re-run records Anki's duplicate handling.
    - (4) When a request gets no reply after the guard has passed, the stderr line also says to answer any open Anki dialog and re-run.
  - **KEEP from attempt 1:**
    - the guard (reads only, refusal messages, and `sync` not writing guard fixtures)
    - the reuse of `LLProbe Probe` and the `LLProbe` preset, the next free `LLProbeExtra<n>` field, and the 120 s `modelFieldAdd` timeout with its elapsed-time print
    - `saveDeckConfig` only on the `LLProbe` preset
    - the `{"noReply"}` and `{"httpStatus","body"}` recordings, and the de-duplicated polls with `pollCount`
    - the stub's callable replies and its v1 `method` matching, and `run_recorder_anki_args`
    - the runbook R1–R11 and Q1–Q7 layout (update R6 and R8–R10 for the pauses), and the fixtures README section

## Review Triage Log

Pass 1 (quick lens plus one orchestrator finding): high 1, medium 3, low 3, false 1, maybe-false 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Redaction swaps profile-name substrings everywhere, so with the runbook's `--profile Probe` every `LLProbe…` name and some config keys come out garbled | high | patch | `_Redactor.text` uses `str.replace` over all strings and keys. The runbook's R1/R4 use `Probe`. Fix: replace only string values equal to a profile name; keep the email and home substitutions. |
| The three sync exchanges run back to back, so v6 `sync` (ack-only) can still be running or raise a dialog when `multi` and v1 start, confounding Q2–Q4 | medium | intent_gap | `_anki_sync` sends them with no wait. The frozen matrix puts all three in one run and one file, and the plan doesn't settle how to isolate them. Asked the human. |
| v1 polling treats an unrecognised reply shape (`state is None`) as terminal, so the final `SyncResult` may never be recorded | medium | patch | `_v1_sync` breaks on `state is None`, and the reply shape is unverified. Fix: keep polling until terminal or the 120 s cap. |
| `addNote` always sends `allowDuplicate: True`, so the re-run can't show duplicate handling (findings Q6) | medium | patch | `_probe_actions` addNote options. Fix: drop the option; the re-run's error is then recorded. |
| A dialog left open past a timeout is reported as "cannot reach AnkiConnect… open Anki" | low | patch | `_anki_probe` maps `_NoReply` to that message. Fix: the message also says to answer any open Anki dialog and re-run. |
| A crash between `cloneDeckConfigId` and `setDeckConfigId` makes a second `LLProbe` preset on the next run | low | rejected | Needs a crash at that exact point, and v6 has no list-presets action, so the fix adds lookup logic. |
| The stub ignores the request path; `noReply` and non-200 v1 replies are untested | low | rejected | `v1_url` is a single concatenation; testing it needs new stub capabilities for an unlikely defect. |
| `AGENTS.md` rules are out of scope for this diff | false | rejected | The user chose on 2026-10-14 to commit their `AGENTS.md` edit with this work. |

Pass 2 (quick lens plus one orchestrator finding): high 0, medium 1, low 3, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| The `multi` child `{"action":"sync"}` has no `version`, so AnkiConnect answers it in v4 form (bare result, no envelope), and the v6 `multi` fixture misrepresents v6 | medium | patch | Line 727. Upstream legacy docs say each `multi` child needs its own `version`. Fix: send `{"action":"sync","version":6}` and assert it in the sync test. |
| `anki sync` silently records `{"noReply"}` after the guard, so the user at the pause isn't told that the step timed out (Change Log item 4) | low | patch | `_v6_sync` and `Probe.v1` record without printing. Fix: print one stderr line naming the exchange and saying to answer any open Anki dialog. |
| `tests/README.md` support table doesn't list `run_recorder_anki_args()` or the stub's callable replies and v1 `method` matching | low | patch | The diff changes both helpers but not the table. Fix: update the two rows. |
| Real profile names inside longer strings (error texts, paths) are not redacted | low | rejected | Only exact matches are replaced, by design (loop 1). The throwaway profile's replies rarely embed other profile names, a substring rule brings back the `Probe` mangling, and runbook R11 makes reading every fixture before commit mandatory. |

## Verification

**Commands:**
- `make test` -- expected: all pass
- `make lint` -- expected: clean

**Manual checks (if no CLI):**
- The Mac Mini run from the runbook. The user's real profile and `LanguageLabDev` are untouched: the guard refuses there.

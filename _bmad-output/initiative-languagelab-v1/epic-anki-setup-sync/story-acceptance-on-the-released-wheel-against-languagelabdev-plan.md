---
title: 'Acceptance on the released wheel against LanguageLabDev'
type: 'chore'
ticket: '13'
created: '2026-10-21'
status: 'done'
baseline_revision: '4d30c2b67a83f3ec4c3b152dd0c45a8b867140e3'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Epic 2's Done-when 1, 2, 5 and the deck-option half of 3 rest on real Anki, which runs only on the Mac Mini; CI proves the rest against fakes and recorded fixtures. Nothing yet records the released wheel doing Setup and Sync against a real collection.

**Approach:** Give the user a step-by-step runbook for the Mac Mini, have them run it on the released wheel with `ANKI_PREFIX=LanguageLabDev`, record each result, cite the CI tests for the migration half of 3 and for 4, and fix or ticket every finding.

## Boundaries & Constraints

**Always:**
- The run uses a released wheel that contains entries 1–12 (`v0.4.0`, cut by the user with `scripts/cut_release.sh 0.4.0`), started with `uvx --from <wheel URL> language-lab` as `docs/install.md` says, in release mode (no `LANGUAGE_LAB_DEV`), with `ANKI_PREFIX=LanguageLabDev` as an environment override (`docs/configuration.md`). A doc step that fails or misleads is a finding.
- The Prefix `LanguageLabDev` starts empty in the user's Anki: no deck, note type, or preset named `LanguageLabDev…`. The runbook says how to check and how to clear it.
- Every clause of the ticket's verify is a runbook step with the exact command or action and the expected result: readiness tiles each pass and fail on their own (AnkiConnect, Azure, OpenRouter, the Prefix in the subtitle, `fullSync` in `/api/setup/readiness`); preview leaves Anki unchanged (AnkiConnect `deckNames`, `modelNames` before and after); confirmed apply; "Setup applied and verified"; a second run shows "Nothing to change."; the three bury flags off in Anki Desktop on the `LanguageLabDev` preset; a deck option the user changes in Anki Desktop survives a rerun; Sync log lines at startup, after five minutes, and at shutdown; with Anki quit, the app keeps answering, the Sync failure is logged, and shutdown ends within 30 s.
- It also measures the preview time on the user's real collection (deferred-work entry on `read_leftovers`, handed to entry 13).
- Each step gets a recorded result: pass, fail, or not run with the reason. No step is marked passed without the user's reported result.
- Done-when 3 (migration half) and 4 cite named CI tests from entries 6, 8 and 9 by file and test name.
- Every finding is fixed in this story (verified by `make lint` and `make test`, noted as needing a new release) or appended to `deferred-work.md`.
- The repo is public: no real tailnet name, login, AnkiWeb account, or IP is committed.

**Never:**
- No write to a ticket file. No new dependency, route, or console script. No change under `src/` except to fix a finding.
- No Setup or Sync run against the `LanguageLab` release Prefix.
- No `LANGUAGE_LAB_DEV` on the Mac Mini: dev mode never Syncs.

</frozen-after-approval>

## Code Map

- `_bmad-output/test-artifacts/acceptance/device-acceptance-1-10.md` -- the pattern to follow: runbook, results table, findings list.
- `docs/setup.md`, `docs/anki.md`, `docs/install.md`, `docs/configuration.md` -- what the user follows; `tests/unit/test_docs_consistency.py` guards them. `scripts/cut_release.sh` moves the wheel URLs on release.
- `src/language_lab/static/screens/setup.js` -- screen strings to expect: tile labels in `CHECKS` (`ankiConnect`, `azure`, `openrouter`), subtitle "…under the prefix **<Prefix>**", "Nothing to change.", "Apply setup", "Setup applied and verified", `FULL_SYNC_*` (tile shows only while `fullSync` fails).
- `src/language_lab/features/setup/routes.py` -- `GET /api/setup/readiness` (`{prefix, checks:[{id, ok}]}`), `GET /api/setup/plan`; usable with `curl` on the Mac Mini.
- `src/language_lab/adapters/anki/manifest.py` `BURY_FLAGS` -- the preset owns only `new.bury`, `rev.bury`, `buryInterdayLearning`; every other deck option is the user's.
- `src/language_lab/features/sync/service.py`, `scheduler.py` -- terminal lines `Sync with AnkiWeb: ok` / `Sync with AnkiWeb failed: <outcome>`; startup Sync not awaited, `INTERVAL_S = 300`, shutdown capped at `SHUTDOWN_CAP_S = 30` with a warning line. Disabled in dev mode (`app.py` `create_app`).
- CI evidence: `tests/integration/test_anki_migrations.py` (`test_migrations_never_run_at_startup_or_on_a_preview`, `test_a_confirmed_plan_runs_its_migration_and_verifies`), `tests/integration/test_anki_prefix_guard.py` (`test_guard_rejects_writes_outside_the_prefix_before_sending_anything`, `test_composed_app_client_rejects_an_out_of_prefix_write`), `tests/api/test_setup_state.py` (`test_a_gated_write_is_the_409_setup_required_envelope`), `tests/api/test_setup_migrations.py` and `tests/e2e/test_setup_full_sync.py` for the failing `fullSync` tile, which an empty Prefix cannot produce.
- `_bmad-output/initiative-languagelab-v1/deferred-work.md` -- append findings here.
- This machine has no Anki; every Mac Mini step is the user's.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/acceptance/setup-sync-acceptance-2-13.md` -- write the runbook: release, empty-Prefix check, start command, readiness (pass and each fail: Anki quit; `AZURE_SPEECH_KEY=` and `OPENROUTER_API_KEY=` overrides), preview with AnkiConnect snapshots before and after, apply, verify, second run, bury flags in Anki Desktop, deck-option rerun, Sync timeline, AnkiConnect down, preview timing; then the CI evidence table, a results table, and a findings list -- ticket verify
- [x] HITL: the user cuts `v0.4.0`, runs the runbook on the Mac Mini, and reports each result and the relevant terminal lines
- [x] Findings -- fix each (docs, `src/`, tests) or append it to `deferred-work.md`
- [x] `_bmad-output/test-artifacts/acceptance/setup-sync-acceptance-2-13.md` -- fill in results and the disposition of each finding

**Acceptance Criteria:**
- Given the filled-in runbook, when a reader checks it against the ticket's verify, then Done-when 1, 2, 5 and the deck-option half of 3 each have a recorded Mac Mini result, and the migration half of 3 and Done-when 4 each cite a named, passing CI test.
- Given the findings list, when each entry is read, then it names a commit in this story or a `deferred-work.md` entry.
- Given the repo after the story, when `make lint` and `make test` run, then both pass.

## Implementation Notes

- Runbook written; every Mac Mini step is `not run` until the user reports. Pre-run finding 1 (stale "not used yet" sentence in `docs/configuration.md`) fixed; finding 2 (empty Prefix cannot exercise `read_leftovers` growth) keeps the deferred-work entry open. Cited CI tests: 67 passed; `make lint` and `make test` (650 passed) green.
- 2026-10-21: the user cut `v0.4.0` and ran the runbook on the Mac Mini, in the spike 2.2 probe profile. Recorded with output: A2, A3, A5, B0–B2, C2–C5, D3, D4. The first startup Sync was `auth_required` (profile not logged in to AnkiWeb); the runbook now says to log in first (finding 3), and after logging in it was `ok`. The user reported every other step as passing in one line and chose to record them as passes on their word, without output; the runbook marks those rows so. No product defect found.

## Plan Change Log

## Review Triage Log

Pass 1 (quick, 2026-10-21): 7 findings — high 0, medium 3, low 2, false 2, maybe-false 0.

| Finding | Verdict | Route | Evidence |
| --- | --- | --- | --- |
| AC 1 unmet: every Mac Mini step `not run` | false | reject | The HITL task is open by design; the runbook may not claim a pass without the user's run (frozen Always). Not a defect of the diff. |
| Findings row 1 names no commit | false | reject | The fix is uncommitted at review time; the hash is added at commit, before the PR. |
| `read_leftovers` deferred entry still points at entry 13, which can't measure growth | medium | patch | Finding 2 says the growth case needs real cards; `deferred-work.md` unchanged. Append a new entry re-pointing it. |
| `docs/configuration.md` overstates what readiness checks | low | patch | `app.py` reads only `OPENROUTER_API_KEY` for OpenRouter; Azure checks key and region. Direct correction. |
| No precondition that the three keys are set before C1/C4/C5 | medium | patch | `docs/install.md` lets them be empty; C1 then fails and C4/C5 can't show one failing alone. |
| Leftover `LanguageLabDev_*` media not checked or cleared | medium | patch | `setup_diff._repairs` offers unreferenced `<Prefix>_*` media as repairs, breaking D2's "no Optional repairs". |
| Part F has no fresh start | low | patch | Last start is C6; F1's "before any page" can't be observed and F2's timing drifts. Restart at F. |

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass
- `uv run pytest -q tests/integration/test_anki_migrations.py tests/integration/test_anki_prefix_guard.py tests/api/test_setup_state.py tests/api/test_setup_migrations.py` -- expected: all pass (the cited evidence)

**Manual checks (if no CLI):**
- The runbook's results table has no empty cell.

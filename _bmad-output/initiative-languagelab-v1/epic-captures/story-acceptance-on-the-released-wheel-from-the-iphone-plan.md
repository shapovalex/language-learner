---
title: 'Acceptance on the released wheel from the iPhone'
type: 'chore'
ticket: '4'
created: '2026-10-22'
status: 'in-progress'
baseline_revision: '678e83f5517cfeef91f204ed1d4efb460ad360ff'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Epic 3's Done-when 1–4 and the deferred R-03 check rest on real Anki and real iOS Safari, which only the Mac Mini, iPhone and iPad have. The `suspend` and `deleteNotes` replies the tests use are hand-built and were never checked against real Anki.

**Approach:** Give the user a step-by-step runbook, have them run it on the released wheel with `ANKI_PREFIX=LanguageLabDev` from the iPhone over Tailscale (plus iPad and desktop), record each result, record the real `suspend` and `deleteNotes` exchanges as fixtures and check the test simulator against them, and fix or ticket every finding.

## Boundaries & Constraints

**Always:**
- The run uses a released wheel with entries 1–3 (`v0.5.0`, cut by the user with `scripts/cut_release.sh 0.5.0`), started with `uvx --from <wheel URL> language-lab` in release mode (no `LANGUAGE_LAB_DEV`) and `ANKI_PREFIX=LanguageLabDev`, reached through Tailscale Serve as `docs/remote-access.md` says. A doc step that fails or misleads is a finding.
- Precondition: the `LanguageLabDev` Prefix is set up (Setup says "Nothing to change.", or the runbook has the user apply it first). Captures made in the run live only under that Prefix.
- Every clause of the ticket's verify is a runbook step with the exact action and expected result, using the app's real copy:
  - DW1: save from iPhone; `cardsInfo` shows the card suspended (`queue` -1) in `LanguageLabDev::Captures`; the note visible in Anki Desktop's browser; a `curl` replay of `POST /api/captures` with the same `captureId` (loopback Origin) answers 201 with the stored body and `findNotes` count stays 1.
  - DW2: list text and "Captured …" time, newest first, on iPhone (list under compose, detail own screen with "‹ Captures") and desktop/iPad landscape (two panes, "N Captures · newest first").
  - DW3: "Delete this Capture?", Cancel keeps it, Delete permanently removes only that note (count before/after).
  - DW4: Anki quit → Save shows "Not saved — Anki isn't reachable", text kept, Try again; Anki reopened → Try again saves exactly one note.
  - R-03 on iPhone and iPad: dirty compose box, edge swipe-back raises "Discard unsaved changes?" / "This Capture isn't saved."; Keep editing keeps the text; Discard leaves; return from another app after a minute keeps the text and the dirty state.
- The user records the real `suspend` (on a new and an already-suspended card) and `deleteNotes` (present and missing id) replies with `curl` on `LanguageLabDev` cards only. They become `tests/fixtures/anki/suspend.json` and `deleteNotes.json` (`{"request","response"}`), and a test checks the simulator in `tests/support/anki_state.py` answers the same shape; a mismatch is a finding.
- Each step gets pass, fail, or not run with the reason. No step is marked passed without the user's reported result.
- Every finding is fixed in this story (verified by `make lint` and `make test`, noted as needing a new release) or appended to `deferred-work.md`. The R-03 deferred-work entry gets its outcome recorded in the acceptance file.
- The repo is public: no real tailnet name, login, AnkiWeb account, IP, or non-`LanguageLabDev` deck or note type is committed.

**Never:**
- No write to a ticket file. No new dependency, route, or console script. No change under `src/` except to fix a finding.
- No Capture saved or deleted under the `LanguageLab` release Prefix. No `LANGUAGE_LAB_DEV` on the Mac Mini.

</frozen-after-approval>

## Code Map

- `_bmad-output/test-artifacts/acceptance/setup-sync-acceptance-2-13.md` -- the pattern: header block, `WHEEL` and `ac()` helpers, lettered parts with Do/Expect tables, CI evidence, Results, Findings. `device-acceptance-1-10.md` -- iOS steps (B9 swipe, B10 background) to mirror for R-03.
- `src/language_lab/static/screens/captures.js` -- copy: "New Capture", placeholder "Paste or type a word, phrase or sentence", "Save Capture", "Not saved — Anki isn't reachable" + body, "Try again", "No Captures yet.", "Newest first", "`N Captures · newest first`", "Captured today · HH:MM", "Delete Capture", "Delete this Capture?", "Delete permanently", "This Capture isn't in Anki.", "Choose a Capture to see it here.".
- `src/language_lab/static/router.js` -- `setDirty`, `onPopState` (re-pushes the dirty URL then asks; `/captures` ↔ `/captures/<id>` stays on screen, so the R-03 swipe must leave Captures, e.g. come from `/en/items`), `describeLoss` "This Capture isn't saved."; `index.html` `#unsaved-alert` "Discard unsaved changes?", Discard, Keep editing.
- `src/language_lab/features/captures/routes.py` -- `POST /api/captures` `{captureId, text}` (lowercase UUIDv4) → 201 `{captureId, text, createdAt}`; `GET /api/captures`; `DELETE` 204.
- `src/language_lab/app.py` `AllowListMiddleware` -- non-GET `/api` needs an allowed Origin: from the Mac Mini, `-H 'Origin: http://127.0.0.1:8787'`.
- `src/language_lab/adapters/anki/store.py` `create_capture` -- `addNote` into `manifest.card_deck(model, 0)` (`LanguageLabDev::Captures`), `notesInfo` for cards, `suspend` (result ignored); `delete_capture` -- `deleteNotes` (result ignored).
- `tests/support/anki_state.py` -- simulator `suspend` returns `changed` bool, `deleteNotes` returns `null` ignoring missing ids; docstring says "hand-built until … entry 4". Same note in docstrings of `tests/integration/test_anki_captures.py` and `test_anki_capture_delete.py`. `tests/support/anki_connect.py` `anki_fixture(name)` loads `{"request","response"}`.
- `tests/fixtures/README.md` -- add an "Epic 3 acceptance" section for the two new files.
- CI evidence to cite: `tests/integration/test_anki_captures.py`, `test_anki_capture_delete.py`, `tests/api/test_captures*.py`, `tests/e2e/test_captures_compose.py`, `test_captures_list.py`, `test_captures_delete.py`, `test_unsaved_alert.py` (pick test names at implementation).
- `_bmad-output/initiative-languagelab-v1/deferred-work.md` -- R-03 entry (line 8); append findings here.
- This machine has no Anki or iOS device; every device step is the user's.

## Tasks & Acceptance

**Execution:**
- [ ] `_bmad-output/test-artifacts/acceptance/captures-acceptance-3-4.md` -- write the runbook: A release `v0.5.0` and helpers; B start, health `0.5.0`, Prefix set up; C save from iPhone, suspended in Anki, replay no duplicate (DW1); D list on iPhone, iPad, desktop (DW2); E delete with Cancel and confirm (DW3); F Anki down then Try again (DW4); G R-03 swipe-back and background on iPhone and iPad; H record `suspend`/`deleteNotes` replies; then CI evidence, Results, Findings -- ticket verify
- [ ] HITL: the user cuts `v0.5.0`, runs the runbook, reports each result and pastes the H replies
- [ ] `tests/fixtures/anki/suspend.json`, `tests/fixtures/anki/deleteNotes.json`, `tests/fixtures/README.md` -- write the recorded exchanges, document them
- [ ] `tests/integration/test_anki_captures.py`, `tests/integration/test_anki_capture_delete.py`, `tests/support/anki_state.py` -- add a test per action that the simulator's reply to the recorded request equals the recorded response; replace the "hand-built" notes
- [ ] Findings -- fix each or append to `deferred-work.md`; fill in results and dispositions in the acceptance file

**Acceptance Criteria:**
- Given the filled-in runbook, when checked against the ticket's verify, then Done-when 1–4 and R-03 each have a recorded device result, and each cites the passing CI tests that back it.
- Given the findings list, when each entry is read, then it names a commit in this story or a `deferred-work.md` entry.
- Given the repo after the story, when `make lint` and `make test` run, then both pass, and no committed file holds a private name or address.

## Implementation Notes

- Implemented directly in the session (no subagent), from the plan.
- 2026-10-22: runbook written at `_bmad-output/test-artifacts/acceptance/captures-acceptance-3-4.md`, every device step `not run` until the user reports. Cited CI tests: 166 passed. Part H records four exchanges (`suspend` on an unsuspended and an already-suspended card, `deleteNotes` on a present and a missing note), so the fixtures will be `suspend.json`, `suspend-already.json`, `deleteNotes.json`, `deleteNotes-missing.json`.
- Waiting on the HITL run.

## Plan Change Log

## Review Triage Log

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass
- `uv run pytest -q tests/integration/test_anki_captures.py tests/integration/test_anki_capture_delete.py` -- expected: all pass, including the fixture checks

**Manual checks (if no CLI):**
- The runbook's Results table has no empty cell; `grep -nE 'ts\.net|@' ` on the new files shows only placeholders.

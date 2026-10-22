---
title: 'Acceptance on the released wheel from the iPhone'
type: 'chore'
ticket: '4'
created: '2026-10-22'
status: 'built'
baseline_revision: '678e83f5517cfeef91f204ed1d4efb460ad360ff'
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
  Decision (2026-10-22, human): the user ran part H but pasted no replies and chose to finish acceptance without them; the fixtures and the simulator check move to `deferred-work.md`.
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
- [x] `_bmad-output/test-artifacts/acceptance/captures-acceptance-3-4.md` -- write the runbook: A release `v0.5.0` and helpers; B start, health `0.5.0`, Prefix set up; C save from iPhone, suspended in Anki, replay no duplicate (DW1); D list on iPhone, iPad, desktop (DW2); E delete with Cancel and confirm (DW3); F Anki down then Try again (DW4); G R-03 swipe-back and background on iPhone and iPad; H record `suspend`/`deleteNotes` replies; then CI evidence, Results, Findings -- ticket verify
- [x] HITL: the user cuts `v0.5.0`, runs the runbook, reports each result and pastes the H replies
- [ ] (deferred: no replies pasted) `tests/fixtures/anki/suspend.json`, `tests/fixtures/anki/deleteNotes.json`, `tests/fixtures/README.md` -- write the recorded exchanges, document them
- [ ] (deferred: no replies pasted) `tests/integration/test_anki_captures.py`, `tests/integration/test_anki_capture_delete.py`, `tests/support/anki_state.py` -- add a test per action that the simulator's reply to the recorded request equals the recorded response; replace the "hand-built" notes
- [x] Findings -- fix each or append to `deferred-work.md`; fill in results and dispositions in the acceptance file

**Acceptance Criteria:**
- Given the filled-in runbook, when checked against the ticket's verify, then Done-when 1–4 and R-03 each have a recorded device result, and each cites the passing CI tests that back it.
- Given the findings list, when each entry is read, then it names a commit in this story or a `deferred-work.md` entry.
- Given the repo after the story, when `make lint` and `make test` run, then both pass, and no committed file holds a private name or address.

## Implementation Notes

- Implemented directly in the session (no subagent), from the plan.
- 2026-10-22: runbook written at `_bmad-output/test-artifacts/acceptance/captures-acceptance-3-4.md`, every device step `not run` until the user reports. Cited CI tests: 166 passed. Part H records four exchanges (`suspend` on an unsuspended and an already-suspended card, `deleteNotes` on a present and a missing note), so the fixtures were to be four files, not the Code Map's two; the `deferred-work.md` entry lists the four exchanges.
- 2026-10-22: the user cut `v0.5.0` and ran the runbook. C7 first answered `422 validation_failed` because `$ID` wasn't set to the CaptureId; C6 and E1 now set it with one command (finding 1). The user then reported every step passing in one line, with no output, and chose to record them as passes on their word. H3–H6 replies were not pasted and the user chose to finish without them: those rows are `not run`, no fixtures or simulator test were added, and the check is in `deferred-work.md` (finding 2). The R-03 outcome is recorded in the acceptance file. No product defect found, no `src/` change. `make lint` clean and `make test` 772 passed after the run; again after the review patches.

## Plan Change Log

- Review pass 1, finding 1 (intent_gap, already resolved). The frozen Always required the `suspend`/`deleteNotes` fixtures and a simulator test; the user chose to finish without pasting the replies. The frozen block now records that decision; the two tasks stay unchecked as deferred. KEEP: the runbook and the recorded results.

## Review Triage Log

### Pass 1 (quick) — high 0 · medium 0 · low 9 · false 1 · maybe-false 0

| # | Finding | Verdict | Route | Evidence |
|---|---------|---------|-------|----------|
| 1 | Fixtures and simulator test from the frozen Always missing | low | intent_gap | Real. Resolved by the human's "finish acceptance"; decision written into the frozen block, Change Log entry added. No code to revert. |
| 2 | Implementation Notes name four fixture files, Code Map two | low | patch | Notes now say four were planned and point at the deferred entry, which lists the four exchanges. |
| 3 | Finding 1 names no commit | low | patch | The hash is added once the fix is committed, as in story 2.13. |
| 4 | R-03 outcome put in deferred-work as a no-work entry, not in the acceptance file | low | patch | Entry removed (uncommitted, this story's own); part G and the Results now record the outcome and close R-03. |
| 5 | C6/E1 passes recorded against reworded steps | low | patch | C6 note: the user set `ID` with the new command (my reply to C7). E1 note: run with the earlier wording. |
| 6 | H3–H6 `not run` while H7 `pass` | low | patch | They ran without kept output: now `pass` with "reply not pasted, not compared"; finding 2 says the steps ran. |
| 7 | CI evidence claims recorded fixtures for suspend/deleteNotes | low | patch | Intro now says those replies are still hand-built (finding 2). |
| 8 | Test docstrings say "hand-built until entry 4" | low | patch | Three docstrings now say story 3.4 didn't record them and point at deferred-work.md. |
| 9 | Device evidence is a single blanket report | false | reject | The user chose to record passes on their word; each row says so, as story 2.13 did. Not a defect of the diff. |
| 10 | No record of `make test` | low | patch | Implementation Notes record `make test` 772 passed. |

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass
- `uv run pytest -q tests/integration/test_anki_captures.py tests/integration/test_anki_capture_delete.py` -- expected: all pass (the fixture checks are deferred)

**Manual checks (if no CLI):**
- The runbook's Results table has no empty cell; `grep -nE 'ts\.net|@' ` on the new files shows only placeholders.

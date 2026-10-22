---
title: 'Upgrade, migration, and full-sync docs'
type: 'feature'
ticket: '12'
created: '2026-10-21'
status: 'built'
baseline_revision: '53f829d6c5cc3a70f8c8e2d0c9476fd498e88b7e'
route: 'oneshot'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-12.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The docs don't say how to run Setup, upgrade to a new release and confirm its migration, why an older wheel must never run after a migration, or how to do the one-way Upload to AnkiWeb; `docs/anki.md` and `README.md` still say the release doesn't talk to Anki. The 11 red-phase cases in `tests/unit/test_docs_setup_upgrade.py` are skipped.

**Approach:** Add `docs/setup.md` with the four headings the ATDD checklist names (Run Setup, Upgrade to a new release, Never downgrade after a migration, Upload to AnkiWeb after a full sync), quoting `static/screens/setup.js` copy and `MESSAGES[SYNC_REQUIRED]` verbatim and stating spike 2.2 Q2 (no full-sync signal reaches LanguageLab). Move anki.md's "Full sync after a migration" there, drop its stale "not yet" sentences, index the page and the four topics in `docs/README.md` and the root `README.md`, and lift `RED_PHASE`.

</frozen-after-approval>

## Implementation Notes

Oneshot: docs only, about 80 lines across four Markdown files plus removing the skip marker. Copy sources: `setup.js` constants (`APPLY_LABEL`, `FULL_SYNC_*`, `NEWER_SCHEMA_ALERT`, "Migrate" group, change-list heading/note), `domain/errors.py` `SYNC_REQUIRED`, install command from `docs/install.md` (v0.3.0). Don't invent a logged-out screen string (checklist green-phase note).

Files: new `docs/setup.md`; `docs/anki.md` (stale sentences gone, full-sync section reduced to a link), `docs/README.md` (page row, four checklist rows), `README.md` (stale sentence, link), `docs/install.md` (stale Requirements sentence, from review), `tests/unit/test_docs_setup_upgrade.py` (RED_PHASE lifted). Kept the "Full sync after a migration" heading in anki.md as a pointer so old links still land.

## Review Triage Log

Quick pass: 3 findings, all real (0 high, 2 medium, 1 low), all patched; 1 deferred.
- medium, patch: Run Setup step 4 called Create/Repair/Migrate "kinds"; `setup.js` KINDS are resource kinds and the action is the count chip. Reworded, and the Upgrade steps now say rows with a "Migrate" chip.
- medium, patch + defer: "the tile stays until you click" doesn't hold across a restart; `SyncService._full_sync_required` is in memory only (`features/sync/service.py:37`). The doc now says to upload before stopping LanguageLab. Persisting the flag is deferred (code change, predates this story).
- low, patch: `docs/install.md` Requirements still said the Anki features "arrive" later. Reworded.

## Verification

**Commands:**
- `make test` -- expected: all pass, none of the 2.12 cases skipped
- `make lint` -- expected: clean

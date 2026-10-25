---
runScope: "story"
runKey: "story-6-2"
workflowStatus: "completed"
stepsCompleted: ["step-01-preflight-and-context", "step-02-generation-mode", "step-03-test-strategy", "step-04-generate-tests", "step-04c-aggregate", "step-05-validate-and-complete"]
lastStep: "step-05-validate-and-complete"
lastSaved: "2026-10-24"
storyId: "6.2"
storyKey: "6-2"
storyFile: ""
storySource: "_bmad-output/initiative-languagelab-v1/epic-reference-audio/tickets.toml (entry 2)"
atddChecklistPath: "_bmad-output/test-artifacts/atdd/atdd-checklist-6-2.md"
generatedTestFiles:
  - "tests/api/test_item_audio_lifecycle.py"
  - "tests/integration/test_anki_audio_lifecycle.py"
  - "tests/e2e/test_item_audio.py"
inputDocuments:
  - "AGENTS.md"
  - "_bmad/config.toml"
  - "_bmad-output/initiative-languagelab-v1/epic-reference-audio/tickets.toml (entry 2)"
  - "_bmad-output/initiative-languagelab-v1/epic-reference-audio/epic-reference-audio.md"
  - "_bmad-output/initiative-languagelab-v1/epic-reference-audio/story-preview-and-save-reference-audio-from-a-draft-plan.md"
  - "_bmad-output/test-artifacts/atdd/atdd-checklist-6-1.md"
  - "_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md"
  - "_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md"
  - "_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md"
  - "pyproject.toml"
  - "tests/conftest.py"
  - "tests/README.md"
  - ".agents/skills/bmod-tea/knowledge/data-factories.md"
  - ".agents/skills/bmod-tea/knowledge/component-tdd.md"
  - ".agents/skills/bmod-tea/knowledge/test-quality.md"
  - ".agents/skills/bmod-tea/knowledge/test-healing-patterns.md"
  - ".agents/skills/bmod-tea/knowledge/test-levels-framework.md"
  - ".agents/skills/bmod-tea/knowledge/test-priorities-matrix.md"
  - ".agents/skills/bmod-tea/knowledge/ci-burn-in.md"
acceptanceCriteria:
  - {"id": "AC-1", "idSource": "generated", "text": "Opening an Item with saved Reference audio re-reads Anki and plays its current clip from /api/media in a labelled Reference audio card; an Item without audio shows no play control."}
  - {"id": "AC-2", "idSource": "generated", "text": "Regenerate audio is an explicit Preview that shows Current vs Preview; Keep current discards the Preview and leaves the Item and its audio unchanged."}
  - {"id": "AC-3", "idSource": "generated", "text": "After Use preview, Save changes uploads the exact previewed MP3 with audio=replace under the existing ItemId; nothing is written before Save."}
  - {"id": "AC-4", "idSource": "generated", "text": "Removing audio stays local as an unsaved change until Save changes, which sends audio=remove with no audio file."}
  - {"id": "AC-5", "idSource": "generated", "text": "Editing the Target of an Item with audio shows \"Audio no longer matches the text.\" with Regenerate audio, and Save changes still succeeds with audio=keep."}
  - {"id": "AC-6", "idSource": "generated", "text": "Save with audio=remove on an existing Item clears its Audio field and then deletes the superseded managed media, in AD-6 order under one Anki lock."}
  - {"id": "AC-7", "idSource": "generated", "text": "A failed note write during removal stops before any media deletion and preserves the previous Audio field and media."}
  - {"id": "AC-8", "idSource": "generated", "text": "A superseded-media cleanup failure after a successful note write reports an error without rollback, a retry succeeds, and Setup reports the leftover clip as a repairable orphan."}
  - {"id": "AC-9", "idSource": "generated", "text": "Changing Voice on Item detail never synthesizes or writes Anki; only the explicit Regenerate audio action requests a Preview, and it writes nothing."}
  - {"id": "AC-10", "idSource": "generated", "text": "A failed Save changes retains the edits and the pending audio change, and retry resends the same audio intent and bytes."}
  - {"id": "AC-11", "idSource": "generated", "text": "A failed audio Preview on Item detail shows \"Couldn't make the audio. Current audio is unchanged.\" and keeps the current clip playable."}
---

# ATDD Checklist: Story 6.2 — Regenerate, keep, and remove audio on existing Items

## Preflight

Create mode inferred from the explicit story request. Approved high-risk ticket entry 2 in epic 6
is the story source; no leaf story file exists. Its prerequisites are merged on main: 6.1 (PR #53),
5.1 and 5.3. No pre-existing 6-2 checklist; fresh run on up-to-date `main` (98cc414).

Stack detection: backend (pyproject.toml, no package.json), with a static browser client and
Python Playwright (pytest-playwright). pytest config, conftest, fakes, Anki collection replay and
6.1 audio helpers (`tests/support/audio.py`, `audio_screen.py`) are available. No epic-6 or
system test design exists in `test-design/` or the legacy root; priorities derive from the ticket's
high risk and AD-6's write-order contract.

Playwright-utils and Pact flags are true but their gates are closed (no package.json, no JS
Playwright runner, no Pact artifacts). Only the seven core/backend fragments in inputDocuments
apply. Browser coverage stays because the story explicitly promises responsive Item detail UI.

Registry: generated ids in source order from the ticket description, then its verify clause,
supplemented by EXPERIENCE.md's Item detail TTS-failure copy and the epic's FR-23 copy.

### Already satisfied on main (baseline regressions, no red leaf)

These verify-clause promises were delivered by 6.1/5.3 and are guarded by passing tests, so a new
red scaffold would pass immediately. They stay as regressions and green-phase journeys:

| Promise | Existing passing coverage |
| --- | --- |
| Replacement keeps old media until note write succeeds | `tests/integration/test_anki_audio_save.py::TestAudioSave::test_failed_note_write_retains_previous_values_and_stops_cleanup`, `::test_replacement_cleans_superseded_media_only_after_successful_note_write` |
| Same-hash media is retained | `tests/integration/test_anki_audio_save.py::test_same_item_id_retry_keeps_same_hash_media_and_does_not_duplicate_note` |
| Preview never writes Anki (HTTP) | `tests/api/test_reference_audio.py::TestReferenceAudio::test_preview_returns_memory_only_mp3_without_anki_writes` |
| Item detail exposes saved `audio` | `tests/api/test_reference_audio.py::TestReferenceAudio::test_item_detail_exposes_the_saved_reference_filename` |
| Confirmed deletion removes only that Item's managed media | `tests/integration/test_anki_item_delete.py::test_delete_removes_only_the_scoped_note_cards_and_matching_media_in_order`, `::test_media_names_are_filtered_by_item_id_and_the_managed_filename_contract` |
| Replacement cleanup failure is retryable | 6.1 adapter code path; explicit replace-variant regression is green-phase work (see expansions) |

## Generation mode

AI generation from the ticket, architecture, UX and existing Python tests. No recording: the
backend stack mandates AI generation and the Item detail audio card does not exist yet.

## Test strategy

One primary red-phase leaf per criterion, no parametrized expansion.

| Criterion | Level | Priority | Primary first-failing assertion |
| --- | --- | --- | --- |
| AC-1 | E2E | P1 | bytes of the Item detail player equal the stored MP3 |
| AC-2 | E2E | P1 | after Keep current, the card offers no Preview and Save sends `audio=keep` |
| AC-3 | E2E | P0 | uploaded `audioFile` bytes equal the previewed MP3, `audio=replace`, same ItemId |
| AC-4 | E2E | P0 | Save sends `audio=remove` with no `audioFile`, zero writes before Save |
| AC-5 | E2E | P1 | stale warning visible after Target edit; Save then sends `audio=keep` |
| AC-6 | API | P0 | status 200 for `audio=remove`, then write order `updateNoteFields`, `deleteMediaFile` |
| AC-7 | Integration | P0 | outcome code `anki_unavailable` from the note write, then no `deleteMediaFile` |
| AC-8 | Integration | P0 | first remove's outcome code is `anki_unavailable` after `updateNoteFields` succeeded |
| AC-9 | E2E | P0 | zero Preview and Save requests after a Voice change |
| AC-10 | E2E | P0 | retry's audio intent and bytes equal the failed attempt's |
| AC-11 | E2E | P1 | inline TTS alert visible with the exact copy |

Workers: A (API/integration) owns AC-6, AC-7, AC-8. B (browser) owns AC-1–AC-5, AC-9–AC-11.
P0: AC-3/4/6/7/8/9/10 (data integrity, write order, no-write guarantees, retained edits).
P1: AC-1/2/5/11.

Red-phase rules: each leaf's first assertion isolates the newly promised value; transition
criteria perform the transition (Keep current, Use preview, Remove, Target edit, failed Save then
retry). Setup through the existing EditableItemApi-style doubles or collection replay stays
opaque. Module-level reasoned `pytest.mark.skip` (pytest's test.skip) until task activation.
Python sync Playwright has no outer promise matcher: missing Item-detail controls will stop
browser journeys at a locator before later state assertions; recorded as a validation limit.

## Execution mode

Config `auto`, capability probe on. Subagent launch is available; no agent-team runtime.
Resolved mode: subagent. Worker A (API/integration) and Worker B (browser) ran in parallel;
both reproduced the 11-entry registry exactly. Node-only playwright-utils/Pact mandates are
inapplicable (no package.json, JS runner or Pact artifacts), so there are no deviations to roll up.

## Generated scaffolds and coverage

11 primary leaves: 1 API, 2 adapter integration, 8 browser. Every file has a reasoned
module-level `pytest.mark.skip`. Each leaf's first docstring line carries exactly one id.

| Criterion | Primary scaffold |
| --- | --- |
| AC-1 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_opening_an_item_plays_its_current_saved_clip` |
| AC-2 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_keep_current_discards_the_preview_and_save_keeps_the_audio` |
| AC-3 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_use_preview_uploads_the_exact_clip_only_when_saved` |
| AC-4 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_remove_audio_is_local_until_save_sends_the_remove_intent` |
| AC-5 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_target_edit_warns_of_stale_audio_and_still_saves_with_keep` |
| AC-6 | `tests/api/test_item_audio_lifecycle.py::TestItemAudioRemoval::test_remove_clears_the_audio_field_then_deletes_the_superseded_clip` |
| AC-7 | `tests/integration/test_anki_audio_lifecycle.py::TestAudioRemovalFailures::test_failed_note_write_during_removal_keeps_the_field_and_clip` |
| AC-8 | `tests/integration/test_anki_audio_lifecycle.py::TestAudioRemovalFailures::test_cleanup_failure_after_the_note_write_is_retryable_and_setup_repairable` |
| AC-9 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_changing_voice_never_synthesizes_or_writes` |
| AC-10 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_failed_save_retains_the_pending_audio_and_retry_resends_it` |
| AC-11 | `tests/e2e/test_item_audio.py::TestExistingItemAudio::test_failed_preview_reports_and_keeps_the_current_clip` |

Viewports: phone (AC-1/3/5/10), desktop (AC-2/4/9/11). AC-3 is French Sentence (fr-CA).

## Supporting helpers

- `tests/support/audio.py` (extended): `remove_parts()` (multipart `item` only, `audio=remove`),
  `stored_with_audio()` (stored English Vocabulary note referencing its AD-7 clip),
  `remove_audio()` (adapter call resolving inside `settle`). Existing helpers unchanged.
- `tests/support/item_audio_screen.py` (new): per-page `ItemAudioApi` double for Item detail
  read (`audio` name), `/api/media`, Voices, Preview and multipart Save. It uses
  `preview_error`/`save_error` switches and observes FormData as 6.1 does (WebKit omits
  intercepted file bytes). It also provides locators scoped to `main` and a probe that returns
  the bytes behind each native player (blob or same-origin URL). The stored clip is SECOND_MP3
  and every Preview is MP3.

## Proposed contracts and UI selectors

- Save: existing `POST /api/items/{lang}` multipart now accepts `audio=remove` with only the
  `item` part; `remove` plus an `audioFile` stays 422. AD-6 order: update the note with an
  empty Audio field, then delete the superseded managed clip. No media store step.
- Adapter: `save_item(..., AudioIntent.REMOVE)` with no `audio_bytes`. AC-8 expects a retry to
  re-send `updateNoteFields` (idempotent last-write-wins); if the builder skips the redundant
  write, adjust that ordering assertion and record why.
- UI (scaffold choices; builder may rename and update tests): region `Reference audio` on Item
  detail; `Voice` combobox; `Regenerate audio` = explicit Preview (also offered beside the stale
  warning); `Keep current` / `Use preview`; compare labels `CURRENT` / `PREVIEW · NOT SAVED`
  (exact text matched, so CSS-only uppercasing needs the test updated); `Remove audio` (epic
  delegates removal copy); a pending removal counts as one unsaved change. Copy
  `Audio no longer matches the text.` and `Couldn't make the audio. Current audio is unchanged.`
  are fixed by the epic/EXPERIENCE.md.

## Implementation checklist

- [ ] AC-6: accept `remove` in `_SaveIntent` and the adapter; skip media storage, write empty
  Audio, then delete the superseded managed clip under the existing lock, gate and Prefix guard.
- [ ] AC-7: a note-write failure stops before any media deletion; no compensation.
- [ ] AC-8: a cleanup failure after the note write surfaces `anki_unavailable`; retry succeeds;
  the leftover stays for Setup's `orphanMedia` repair.
- [ ] AC-1: add the Item detail audio card; play the saved clip from `/api/media/<name>`; no
  player when `audio` is null.
- [ ] AC-9: Voice changes update `voice-pref.js` only; `Regenerate audio` is the sole synthesis trigger.
- [ ] AC-2/AC-3: compare pair with Keep current / Use preview; keep the accepted Blob in screen
  memory; upload it via `api.js` multipart only on Save changes (`audio=replace`).
- [ ] AC-4: `Remove audio` sets a pending `remove` intent counted in the unsaved chip and router alert.
- [ ] AC-5: compare the edit buffer's Target with the clip's Target; show the stale warning
  with `Regenerate audio`; Save still sends `audio=keep`.
- [ ] AC-10: a failed Save keeps edits, pending intent and Blob; retry resends identical bytes.
- [ ] AC-11: inline TTS alert in the card; current clip and any accepted Preview unchanged.

Green-phase expansions: tablet width and WebKit runs; Voice-list failure and Try again on Item
detail; undoing a pending removal; Blob URL revocation on replace/discard/leave; `hasAudio` in
the list after replace/remove; replace-intent cleanup failure plus retry (explicit regression);
same-hash replacement on an existing Item through HTTP; remove on an Item without audio
(no-op cleanup); `remove`+`audioFile` 422 with zero writes; Setup gate refusing remove; deletion
after a regenerate removes current and leftover clips of that Item only. Real Azure/device
evidence belongs to 6.4.

## Activation and downstream handoff

There is no leaf story file to update. Pass `epic-reference-audio/tickets.toml` entry 2, this
checklist and generatedTestFiles to bmad-build. Remove one module skip at a time for the
current task, confirm RED, implement, confirm GREEN, then refactor.

```sh
.venv/bin/pytest tests/api/test_item_audio_lifecycle.py tests/integration/test_anki_audio_lifecycle.py tests/e2e/test_item_audio.py -q
.venv/bin/pytest tests/e2e/test_item_audio.py --browser webkit -q
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Validation limits

Python sync Playwright has no outer promise matcher. With skips stripped, only AC-1 fails at
its own assertion: the player bytes come back empty instead of the stored clip. The other seven
browser journeys stop at the missing Voice/card controls, so their later transitions have not
run yet and need re-observation once the card exists. API/integration leaves fail directly at
their first criterion assertion. Browser doubles do not prove real Anki or Azure behaviour.

## Validation and completion — 2026-10-24

- Registry/static check: 11 ids, exactly one leaf per id, every leaf carries exactly one
  declared id; both worker registries match. 7 P0, 4 P1.
- Normal run with related regressions (6.1 audio API/adapter/Draft, 5.1 Item edit):
  **78 passed, 11 skipped**, no errors.
- Temporary activation (scratch plugin stripping skip markers, 2 s browser timeouts):
  **11 failed, 0 passed, 0 errors**. AC-6 fails with 422 instead of 200. AC-7 and AC-8 fail
  with `validation_failed` instead of `anki_unavailable`. Browser failures are as noted above.
- Aggregation fix: Save waits now wait for the Save response, not for the unsaved chip to
  disappear (which could pass before the upload was recorded). Helper imports hoisted.
- Ruff check/format clean across the repository (330 files); `git diff --check` clean.
- Machine-readable mapping: `atdd-validation-6-2.json`.

ATDD scaffolding is complete; story 6.2 implementation remains pending. Next: bmad-build with
this checklist and tickets.toml entry 2. Per AGENTS.md this ATDD run is committed to main and pushed.

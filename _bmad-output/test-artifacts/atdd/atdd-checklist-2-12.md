---
runScope: 'story'
runKey: 'story-2-12'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.12'
storyKey: '2-12'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 12)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-12.md'
generatedTestFiles:
  - 'tests/unit/test_docs_setup_upgrade.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entries 9, 11, 12)'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md (Boundaries: docs for upgrade, never-downgrade, full-sync upload; newer_schema decision of 2026-10-14)'
  - '_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md (Q2 full sync never reported, Q3 logged out)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/static/screens/setup.js (screen copy), src/language_lab/domain/errors.py (MESSAGES), src/language_lab/features/sync/service.py'
  - 'docs/README.md, docs/anki.md, tests/unit/test_docs_consistency.py (story 1.9 pattern and helpers)'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'docs/setup.md "Run Setup" quotes the change list (What will change in Anki / Nothing changes until you apply.), Apply setup, and links the backup section' }
  - { id: 'AC-2', idSource: 'generated', text: 'docs/setup.md "Upgrade to a new release" gives the current release uvx command and says to confirm the Migrate rows with Apply setup' }
  - { id: 'AC-3', idSource: 'generated', text: 'docs/setup.md "Never downgrade after a migration" quotes the newer_schema alert verbatim' }
  - { id: 'AC-4', idSource: 'generated', text: 'docs/setup.md "Upload to AnkiWeb after a full sync" gives the one-way upload in the screen words: Full sync required, its fix, I''ve uploaded, and the sync_required refusal' }
  - { id: 'AC-5', idSource: 'generated', text: 'The upload section states the spike-recorded behavior: LanguageLab can''t see whether the upload happened, so the tile stays until the user clicks' }
  - { id: 'AC-6', idSource: 'generated', text: 'docs/README.md links each of the four topics to its docs/setup.md heading' }
  - { id: 'AC-7', idSource: 'generated', text: 'docs/anki.md no longer says the release does not talk to Anki or has no migration yet' }
---

# ATDD Checklist: Story 2.12, Upgrade, migration, and full-sync docs

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 12 (`risk = "low"`). There is no story file, so this checklist holds the criteria. All ids are generated:
  - The description's topics, in order: running Setup (AC-1), upgrading by running the new wheel and confirming any migration (AC-2), never downgrading after a migration (AC-3), the one-way Upload to AnkiWeb step (AC-4).
  - Verify: "each topic maps to a named docs section" is AC-6. "The copy matches the Setup screen strings" is the `screen()` quotes in AC-1 to AC-4. "And the spike's recorded sync behavior" is AC-5.
  - AC-7 comes from the copy check. anki.md still says "This release does not talk to Anki yet", which is no longer true.
- **Stack:** `backend` (pyproject, pytest). Generation mode is AI generation; no recording is needed.
- **Test design:** none for epic 2. Priority is P2 (low risk, docs), matching `test_docs_consistency.py`.
- **Level:** unit. The docs are files, read with the regex helpers of `tests/unit/test_docs_consistency.py` (story 1.9), which this file imports.

### Defaults taken without a question

- **One new page, `docs/setup.md`**, with the headings `Run Setup`, `Upgrade to a new release`, `Never downgrade after a migration`, `Upload to AnkiWeb after a full sync`. The section "Full sync after a migration" in `docs/anki.md` moves there; anki.md may link to it. A heading is renamed in the page and in the test's constants together.
- **The screen is the source of truth for copy.** `screen(copy)` first asserts that `"copy"` is a string literal in `setup.js`, then the docs must contain it verbatim. If someone rewords a button or alert on the screen, the doc test fails until the docs follow. The sync refusal is read from `MESSAGES[ErrorCode.SYNC_REQUIRED]`.
- **Existing global checks cover the rest.** `test_docs_consistency.py` already checks every page under `docs/`: the release asset URL is current, every relative link resolves (including the backup anchor), there are no unknown env keys, and the README links to every docs page. The README therefore needs a link to `docs/setup.md`.

## Test strategy

| AC | Scenario (primary red leaf) | Level | Priority | First failing assertion |
| --- | --- | --- | --- | --- |
| AC-1 | `TestRunSetup::test_section_quotes_the_preview_and_the_apply_button` | unit | P2 | docs/setup.md has no heading 'Run Setup' |
| AC-2 | `TestUpgrade::test_section_runs_the_new_wheel_and_confirms_the_migration` | unit | P2 | no heading 'Upgrade to a new release' |
| AC-3 | `TestNeverDowngrade::test_section_quotes_the_newer_schema_alert` | unit | P2 | no heading 'Never downgrade after a migration' |
| AC-4 | `TestUploadToAnkiWeb::test_section_gives_the_one_way_upload_step_in_the_screens_words` | unit | P2 | no heading 'Upload to AnkiWeb after a full sync' |
| AC-5 | `TestUploadToAnkiWeb::test_section_states_the_spikes_recorded_sync_behavior` | unit | P2 | same heading |
| AC-6 | `TestIndex::test_index_links_each_topic_to_its_heading[<topic>]` ×4 | unit | P2 | `setup.md#<slug>` not in index links |
| AC-7 | `TestAnkiPage::test_anki_page_no_longer_says_setup_is_to_come[<stale>]` ×2 | unit | P2 | stale sentence still in anki.md |

No E2E, API, or integration tests: the story changes only docs, and the copy it quotes is already covered by the e2e tests of stories 2.7 to 2.9.

### Green-phase additions (not red leaves)

- Upgrade section: says a migration never runs at startup, only inside a confirmed plan (entry 9), and links the backup section.
- Optional: the upload section mentions the logged-out case (spike Q3). Check the readiness copy first; the screen has no such string yet, so don't invent one.
- Refactor candidate (sweep, entry 14): move the doc helpers from `test_docs_consistency.py` to `tests/support/docs.py`.

## Red-phase verification

- With `RED_PHASE` skipping: `uv run pytest` gives 635 passed, 11 skipped. `ruff check` and `ruff format --check` are clean.
- With the skip lifted (scratch copy): 11 failed. Each fails on a missing heading, a missing index link, or stale anki.md text, never on a `screen()` quote. So every quoted string exists in `setup.js` today.

## Implementation handoff (bmad-build)

1. Write `docs/setup.md` with the four headings and the copy above. Move "Full sync after a migration" from anki.md and rename it to the new heading.
2. Remove the two "not yet" sentences from `docs/anki.md`.
3. Add the page to the `docs/README.md` pages table and the four topic rows to its checklist table. Link `docs/setup.md` from the root `README.md`.
4. Delete `RED_PHASE` and its decorators in `tests/unit/test_docs_setup_upgrade.py`, then run `make test` and `make lint`.

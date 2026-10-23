- source_plan: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/story-studio-styles-and-vendored-figtree-plan.md`
  summary: Confirm the AC-2 focus-ring test's WebKit Alt+Tab passes on the Linux WebKit CI runner (tag runs).
  evidence: Unverified, medium if it fails, because it would block release tags. It passes on macOS WebKit. The first `v*` tag CI run, or `make test-webkit` on Linux, settles it.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/story-install-and-configuration-docs-plan.md`
  summary: Update the `LANGUAGE_LAB_PUBLIC_HOST` comment in `src/language_lab/env.example` to say the tailnet name is discovered from Tailscale when the key is empty.
  evidence: The comment says "Leave empty if you only use it on this machine" and omits discovery, but `with_tailnet_host()` in `app.py` discovers it when empty, as `docs/configuration.md` states. Low. Story 1.9 could not touch `src/`.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/story-device-acceptance-over-tailscale-serve-plan.md`
  summary: Check the unsaved-changes alert on iOS Safari swipe-back and return-from-background on iPhone and iPad, in the first epic whose screen calls `setDirty` (R-03).
  evidence: Story 1.10's device run could not raise the alert, because no screen in v0.2.0 can have unsaved changes. Playwright WebKit covers browser back, but a real iOS edge swipe and bfcache restore are unverified.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/story-device-acceptance-over-tailscale-serve-plan.md`
  summary: Record the per-step results of the story 1.10 device run (parts A to D and E2 of `_bmad-output/test-artifacts/acceptance/device-acceptance-1-10.md`) on iPhone, iPad and desktop, including the LAN probes for 8787 and 8765.
  evidence: On 2026-10-14 the user ran v0.2.1 on the Mac Mini, recorded both Tailscale fixtures, said they were satisfied with how it works, and postponed reporting the steps. Those rows say "not run", so AC2 reach and R-12 have no recorded evidence yet.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/story-sync-feature-coalesced-scheduled-non-blocking-plan.md`
  summary: After a Sync stops polling (120 s budget, `waitingForUser` or `cancelled`), the Anki lock is released while Anki may still be syncing or showing a dialog, and the v1 operation is never cancelled.
  evidence: maybe-false, medium if true (unverified). `AnkiConnectStore.sync()` returns without cancelling the operation, per the user's 2026-10-21 decision. Settle it with a Mac Mini run that calls `reachable()` and a second Sync while a `waitingForUser` Sync is open in Anki Desktop.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/story-managed-manifest-template-files-and-field-codec-plan.md`
  summary: Decide how `decode_field` reads Anki-editor empty-line markup (`a<div><br></div><div>b</div>`), which today reads as three newlines instead of one blank line.
  evidence: Unverified (medium if true). Settled by recording a `notesInfo` of a field edited with blank lines in the Mac Mini Anki and adding it as an AC-11 row.

- source_plan: `_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/story-opt-in-repairs-for-leftovers-plan.md`
  summary: Bound the cost of the opt-in repair reads (one `cardsInfo` of every managed card) on each Setup preview and each checkbox toggle for large collections.
  evidence: `read_leftovers` in adapters/anki/setup_gate.py sends `cardsInfo` for every manifest note type's card under the Anki lock on every preview and server re-plan; AnkiConnect renders each card's question and answer, so the read grows with the collection and could approach the 15 s lock wait. Measure on the Mac Mini at device acceptance (entry 13).
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/story-upgrade-migration-and-full-sync-docs-plan.md`
  summary: Persist the full-sync-required flag so the "Full sync required" tile survives a LanguageLab restart.
  evidence: `SyncService._full_sync_required` is in memory only (`src/language_lab/features/sync/service.py:37`), set only by `SetupService._apply`; a restart after a field-changing migration but before the upload drops the reminder. docs/setup.md now warns about this.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/story-acceptance-on-the-released-wheel-against-languagelabdev-plan.md`
  summary: Measure the Setup preview's `read_leftovers` cost on the Mac Mini at the first run with real LanguageLab cards (epic-capture-to-item); it moves there from entry 13.
  evidence: Story 2.13 ran Setup against an empty `LanguageLabDev` Prefix, which holds no managed cards, so its preview timings (steps D3 and D8 of `_bmad-output/test-artifacts/acceptance/setup-sync-acceptance-2-13.md`) cannot show the `cardsInfo` read growing with many LanguageLab cards. The story 2.11 entry above still names entry 13 for that measurement.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-captures/story-acceptance-on-the-released-wheel-from-the-iphone-plan.md`
  summary: Record the real AnkiConnect `suspend` (unsuspended and already-suspended card) and `deleteNotes` (present and missing note) replies as `tests/fixtures/anki/` exchanges and test the simulator in `tests/support/anki_state.py` against them.
  evidence: In story 3.4's run (part H of `_bmad-output/test-artifacts/acceptance/captures-acceptance-3-4.md`) the user reported H3–H6 passing but pasted no replies, and chose to finish without them, so the hand-built replies are still unchecked against real Anki. The adapter ignores both results (`adapters/anki/store.py` `create_capture`, `delete_capture`), so only an error reply would change behavior.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-capture-to-item/story-card-templates-and-acceptance-on-the-released-wheel-plan.md`
  summary: Record a `notesInfo` of a Hint edited with blank lines in the Mac Mini Anki and settle how `decode_field` reads it (AC-11 row).
  evidence: Story 4.4's run (part H of `_bmad-output/test-artifacts/acceptance/capture-to-item-acceptance-4-4.md`) was reported passing with no `notesInfo` pasted, so the stored markup is still unrecorded.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-capture-to-item/story-card-templates-and-acceptance-on-the-released-wheel-plan.md`
  summary: Measure the Setup preview's `read_leftovers` cost (`/api/setup/plan` timing and card count) on the Mac Mini with real LanguageLab cards.
  evidence: Story 4.4's run (part I of the 4.4 acceptance file) was reported passing with no timings or card count pasted.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-capture-to-item/story-card-templates-and-acceptance-on-the-released-wheel-plan.md`
  summary: Record the real AnkiConnect `changeDeck`, `updateNoteFields` and `cardsInfo` replies as `tests/fixtures/anki/` exchanges and test the simulator in `tests/support/anki_state.py` against them.
  evidence: Story 4.4's run (part J of the 4.4 acceptance file) was reported passing with no replies pasted, so the hand-built replies noted in `tests/support/anki_state.py` and `tests/integration/test_anki_item_save.py` are still unchecked.
- source_plan: `_bmad-output/initiative-languagelab-v1/plan-ci-test-speed.md`
  summary: Make `closed_port()` and `released_app` port allocation race-free now that tests run in parallel under pytest-xdist.
  evidence: maybe-false, unverified medium. Both free a bound port before using it, so a concurrent xdist worker could take it. A burn-in or CI failure that names a refused-connection or released-app bind test would prove it.

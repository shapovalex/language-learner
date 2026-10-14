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

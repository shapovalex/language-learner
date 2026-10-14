- source_plan: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/story-studio-styles-and-vendored-figtree-plan.md`
  summary: Confirm the AC-2 focus-ring test's WebKit Alt+Tab passes on the Linux WebKit CI runner (tag runs).
  evidence: Unverified, medium if it fails, because it would block release tags. It passes on macOS WebKit. The first `v*` tag CI run, or `make test-webkit` on Linux, settles it.
- source_plan: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/story-install-and-configuration-docs-plan.md`
  summary: Update the `LANGUAGE_LAB_PUBLIC_HOST` comment in `src/language_lab/env.example` to say the tailnet name is discovered from Tailscale when the key is empty.
  evidence: The comment says "Leave empty if you only use it on this machine" and omits discovery, but `with_tailnet_host()` in `app.py` discovers it when empty, as `docs/configuration.md` states. Low. Story 1.9 could not touch `src/`.

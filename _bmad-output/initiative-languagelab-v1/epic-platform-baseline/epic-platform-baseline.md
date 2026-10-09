---
type: epic
title: "Platform baseline: run and reach"
parent: initiative-languagelab-v1
covers: [CAP-1]
after: []
assignee: ""
risk: medium
---

# Platform baseline: run and reach

## Description

The release, runtime, and client shell every later epic builds on: a versioned wheel built by CI, started with one documented `uvx` command, reachable privately over Tailscale HTTPS from iPhone, iPad, and desktop, with the four-destination navigation (Captures, English, French, Setup), the error envelope, content-free logging, the host/Origin allow-list, the test harness, and the dev environment. Delivers CAP-1 in the spec.

## Outcome

The user starts a released LanguageLab on the Mac Mini and reaches its shell from all three devices with microphone permission granted — AC1 and AC2.

## Done when

1. A `vX.Y.Z` tag produces a GitHub release with the wheel, and `uvx --from <release> language-lab` starts it on the Mac Mini, loading `~/.config/language-lab/.env` and binding only `127.0.0.1` (AC1).
2. iPhone Safari, iPad Safari, and a desktop browser open the shell over Tailscale Serve HTTPS, move between Captures, English, French, and Setup by real paths, and grant microphone permission (AC2).
3. A request from a host or Origin not on the allow-list gets `403 forbidden_origin` in the error envelope, and the log shows one content-free line per request with its request id (AD-15, AD-16).
4. Docs cover every FR-4 item except model-evaluation fixtures (install, configuration and `.env.example`, Tailscale Serve, keyless-AnkiConnect warning, Prefix study convention, backup).
5. `uv run` dev mode with `LANGUAGE_LAB_DEV=1` runs, and CI runs pytest and ruff on every tag.

## Boundaries

`pyproject.toml`, `app.py` composition root and middleware, `settings.py` (every `.env` key, including Azure and OpenRouter, declared here), `domain/errors.py`, static shell with `router.js` (navigation, unsaved-changes alert, `setDirty`, `confirmLeave`, flash), `api.js`, Studio CSS tokens and vendored fonts, `tests/fakes/` scaffold, CI release workflow, `docs/`. Not any Anki access, Setup content, or feature screens beyond empty destinations.

## References

- parent — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, CAP-1
- prd — prd-languagelab/prd-languagelab.md, FR-1–FR-4, NFR-5–NFR-11, AC1–AC2
- architecture — architecture-languagelab/architecture-languagelab.md, AD-13, AD-15, AD-16, AD-18, Stack, Structural Seed
- ux — ux-languagelab/EXPERIENCE.md (navigation, states), DESIGN.md (Studio tokens, type)

## Notes

- Decision (2026-10-08): this epic owns the test harness, dev Prefix convention, and Studio styles that later epics reuse.
- Decision (2026-10-08): the FR-4 upgrade/never-downgrade and full-sync docs go to epic-anki-setup-sync; model-evaluation fixtures go to epic-capture-to-item.

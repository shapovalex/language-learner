---
runScope: 'epic'
runKey: 'epic-1'
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
inputDocuments:
  - _bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md
  - _bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml
  - _bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md
  - _bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-1–FR-4, §5.2, NFR-5–NFR-11, AC1–AC2)
  - _bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md (A1, A2)
  - _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md (CAP-1)
  - _bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (navigation, overlays, unsaved, a11y floor)
  - '{tea-knowledge}/risk-governance.md'
  - '{tea-knowledge}/probability-impact.md'
  - '{tea-knowledge}/test-levels-framework.md'
  - '{tea-knowledge}/test-priorities-matrix.md'
  - '{tea-knowledge}/nfr-criteria.md'
  - '{tea-knowledge}/playwright-cli.md'
lastSaved: '2026-10-10'
---

# Test Design Progress — Epic 1

## Step 1: Mode

- Mode: Epic-Level (user selected Epic 1: Platform baseline)
- Epic: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md` (11 entries in its `tickets.toml`)
- Prerequisites: epic + stories with verify criteria present; architecture, PRD, spec, UX available as context.

## Step 2: Context

- Config: tea_use_playwright_utils=true, tea_use_pactjs_utils=true, tea_pact_mcp=mcp, tea_browser_automation=auto, test_stack_type=auto.
- Detected stack: **fullstack (planned)**. The repo is greenfield, with no source code, `pyproject.toml` or tests yet. The architecture fixes a Python 3.14 / FastAPI backend plus a vanilla-JS static client; tests are pytest + pytest-playwright (Python). No Node, so the JS-only Playwright Utils and Pact.js Utils don't apply.
- Contract testing: not relevant (no Pact artifacts, a single in-process API with one first-party client).
- No prior system-level test design exists.
- Existing coverage: none. Browser exploration was skipped: there's no running app, and playwright-cli isn't installed.
- Testable requirements: FR-1–FR-4, NFR-5/6/7/9/10/11, AC1, the reach part of AC2, AD-13/15/16/18, and the 11 entries' `verify` criteria.
- Integration points: Tailscale Serve (X-Forwarded-Host, Origin), the `tailscale status` discovery, GitHub Actions release, uvx wheel install, ~/.config .env, browser History API.
- Known gaps: the epic deliberately has no separate E2E suite (entry 10 is the acceptance run), and the user plans to define the test strategy separately. LAN unreachability (FR-2) is verified only manually.

## Step 3: Risk Assessment (epic-level; no testability review)

| ID | Cat | Risk (grounding) | P | I | Score | Action |
|---|---|---|---|---|---|---|
| R-01 | SEC | AD-16 takes the effective host from `X-Forwarded-Host` when present. After a DNS rebind, an attacker page is same-origin with `evil.example:8787`, so it can set that header without a preflight and pass the host check. GET /api needs no Origin, so reads succeed. That defeats AD-16's "Prevents: … reading LanguageLab through … DNS rebinding". | 2 | 3 | 6 | MITIGATE |
| R-02 | SEC | Content leaks into logs or the envelope: validation errors echo input, tracebacks, query strings, the uvicorn access log (AD-15, NFR-7, entry 3) | 2 | 3 | 6 | MITIGATE |
| R-03 | TECH | The router misses a leave path while dirty: pill, Menu, back link, browser back/swipe, unload. `popstate` fires after the URL changes, so cancelling it needs a re-push. That means silent loss of a Draft or edits in later epics (AD-13, NFR-4, entry 7) | 3 | 2 | 6 | MITIGATE |
| R-04 | OPS | The released wheel doesn't run: static assets missing from the wheel, tag ≠ pyproject version, or deps (pydantic-core, av) don't install on macOS 14 / Py 3.14. CI on Linux doesn't prove the macOS `uvx` install (AC1, entries 1 and 8) | 2 | 2 | 4 | MONITOR |
| R-05 | SEC | Tailscale Serve's real Host / X-Forwarded-Host / Origin differ from what's assumed, so legitimate tailnet writes are rejected. Only the manual entry 10 proves it (AD-16, architecture Testing convention) | 2 | 2 | 4 | MONITOR |
| R-06 | SEC | A secret is echoed on a startup failure: pydantic ValidationError prints `input_value` (entry 2 "no secret echoed", NFR-6/7) | 2 | 2 | 4 | MONITOR |
| R-07 | TECH | An unknown /api path falls through to the shell catch-all instead of a 404 envelope, or a non-/api path 404s instead of serving the shell (AD-13 vs AD-15 route order, entry 3) | 2 | 2 | 4 | MONITOR |
| R-08 | TECH | Stale client after an upgrade: asset URLs are versioned, but if the shell HTML is cached it still references old URLs (AD-13 "stale assets after an upgrade") | 2 | 2 | 4 | MONITOR |
| R-09 | TECH | Automated tests run Chromium only, while the targets are iPhone/iPad Safari (NFR-10). WebKit-only regressions (sheet focus trap, History API) show up only at entry 10 | 2 | 2 | 4 | MONITOR |
| R-10 | OPS | Tailscale discovery blocks or crashes startup when tailscale is absent or hangs. It must be non-fatal, and no timeout is specified (entry 4, FR-1) | 2 | 2 | 4 | MONITOR |
| R-11 | DATA | The dev-mode guard fails, so dev writes the release Prefix in later epics. Anki deck names are case-insensitive, so `languagelab` would collide with `LanguageLab` (AD-4 "one Prefix matching another", entry 2) | 1 | 3 | 3 | DOCUMENT |
| R-12 | SEC | The server binds to a non-loopback address, which exposes the app on the LAN (NFR-5, FR-2). `LANGUAGE_LAB_HOST` is configurable | 1 | 3 | 3 | DOCUMENT |
| R-13 | OPS | Docs drift from the code: the command, keys or asset name don't match the repo (FR-4, entry 9) | 2 | 1 | 2 | DOCUMENT |
| R-14 | TECH | The Playwright live-server port isn't on the allow-list after entry 4, which breaks every E2E test (entry 4 description) | 2 | 1 | 2 | DOCUMENT |

### Mitigations for high risks

- **R-01**: architect decision needed before entry 4. Options: (a) trust `X-Forwarded-Host` only when `Host` is itself loopback **and** XFH equals the configured tailnet host (still spoofable locally); (b) also require Origin, or `Sec-Fetch-Site: same-origin`, on GET /api; (c) check `Host` too, if Tailscale Serve preserves it. Capture the real headers early: record them in entry 4's fixture, not only in entry 10. A P0 test pins whichever rule is chosen: a foreign `Host` plus an allowed `X-Forwarded-Host` on GET /api. Owner: Architect, then Dev for entry 4.
- **R-02**: sentinel-string tests. Put a unique token in the path, query, body and headers. Then trigger a validation error, an unknown /api path, an unhandled exception and a 403. Assert the token is absent from both the response and captured stdout/stderr, and assert exactly one log line per request. Owner: Dev for entry 3, with a regression guard in entry 4.
- **R-03**: a Playwright matrix of leave paths (pill, Menu row, back link, `history.back()`, direct `navigate`, `beforeunload`) × {clean, dirty} × {Keep editing, Discard, Esc}, at 390/820/1280 px, also run under WebKit. Owner: Dev for entry 7.

### NFR planning

| Category | In scope | Threshold | Evidence |
|---|---|---|---|
| Security | yes | Binary: loopback bind; host/Origin allow-list → 403; no secrets in responses, static files or logs | pytest API tests, log capture, manual LAN probe (entry 10) |
| Reliability | yes | Startup fails non-zero on an invalid Prefix; tailscale discovery non-fatal. **Discovery timeout UNKNOWN** | pytest settings/startup tests with a fake `tailscale` |
| Maintainability | yes | ruff + pytest green on every tag (entry 8). **CI on push/PR: not planned** | CI logs |
| Compatibility / a11y | yes | 390/820/1280 px; aria-current, focus trap/return, labelled alertdialog (EXPERIENCE a11y floor) | Playwright (Chromium + WebKit), device run (entry 10) |
| Performance | no | **UNKNOWN**: no thresholds for epic 1; single user | none planned |

### Clarifications (not risks)

- Q1: The X-Forwarded-Host trust rule (R-01).
- Q2: Discovery timeout for `tailscale status` (R-10).
- Q3: Cache-Control on the shell HTML (R-08).
- Q4: Should the unknown client path → /captures redirect happen in the server or in router.js?
- Q5: Should the dev guard compare the Prefix case-insensitively (R-11)?
- Q6: Run ruff/pytest on push as well as on tags?

## Step 4: Coverage Plan (summary; full matrix in test-design-epic-1.md)

- Levels: Unit (pytest), API (pytest + ASGI client against `create_app`), Integration (subprocess or built wheel), E2E (pytest-playwright against the live-server fixture), Manual (HITL, entries 8 and 10).
- Counts: P0 23 automated + 7 manual checks; P1 29; P2 8; P3 2.
- Effort: ~60–90 h automated test development inside the stories, plus ~3–4 h of manual acceptance.
- Execution: the whole suite runs in one job (<15 min) on push and on tag; WebKit runs on tag. There are no nightly or weekly suites in this epic.
- Gates: P0 100%, P1 ≥95%, R-01..R-03 mitigated, and the Q1 decision recorded before entry 4 merges.

## Step 5: Output

- Execution mode: sequential (epic-level runs as a single worker).
- Output: `_bmad-output/test-artifacts/test-design/test-design-epic-1.md`
- Checked against checklist.md. Fixed during the check: timeline as a week range, the residual-risk section, the in-run execution order. No browser sessions were opened, and no temp artifacts were created.

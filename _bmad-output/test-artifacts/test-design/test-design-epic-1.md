---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-10-10'
inputDocuments:
  - _bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md
  - _bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml
  - _bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md
  - _bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md
  - _bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md
  - _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md
  - _bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md
---

# Test Design: Epic 1 - Platform baseline: run and reach

**Date:** 2026-10-10
**Author:** Oleksii Shapovalov (with TEA)
**Status:** Draft

---

## Executive Summary

**Scope:** Epic-level test design for Epic 1 (`epic-platform-baseline`, CAP-1). It covers 11 entries: FR-1–FR-4, NFR-5/6/7/9/10/11, AC1, and the reach part of AC2.

**Risk Summary:**

- Total risks identified: 14
- High-priority risks (≥6): 3. They are R-01 (X-Forwarded-Host trust lets a DNS-rebinding read through), R-02 (content leaking into logs or the envelope) and R-03 (the router missing a leave path).
- Critical categories: SEC (host/Origin boundary, log hygiene), TECH (client router), OPS (release wheel)

**Coverage Summary:**

- P0 scenarios: 23 automated plus 7 manual (HITL) checks (~35–45 hours)
- P1 scenarios: 29 (~20–30 hours)
- P2/P3 scenarios: 10 (~4–7 hours)
- **Total effort**: ~60–85 hours of test development, built inside the stories, plus ~3–4 hours of manual acceptance (~1.5–2.5 weeks of part-time work, spread across entries 1–10)

**Key decision needed before entry 4:** the trust rule for `X-Forwarded-Host` (R-01, Q1).

---

## Not in Scope

| Item | Reasoning | Mitigation |
| --- | --- | --- |
| **Any Anki, OpenRouter or Azure access** | The epic boundary says "Not any Anki access, Setup content, or feature screens beyond empty destinations" | Covered from Epic 2 on. Epic 1 only scaffolds `tests/fakes/` |
| **Microphone grant (rest of AC2)** | Moved to epic-pronunciation-review by the 2026-10-08 decision | Epic 7's test design |
| **FR-4 upgrade, full-sync and model-evaluation docs** | Moved to epic-anki-setup-sync and epic-capture-to-item | Those epics' doc checks |
| **Performance or load testing** | Single user, and no thresholds exist for this epic | None. Revisit if a startup-time or latency target appears |
| **Contract testing (Pact)** | There's one in-process API with one first-party client, and no Pact artifacts | The API tests pin the envelope shape |
| **Playwright Utils / Pact.js Utils** | Both are TypeScript-only, and NFR-11 rules out Node. Tests use pytest-playwright | N/A |
| **Visual regression** | Only empty destinations ship in this epic | E2E style checks (P2) plus the device run |

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | SEC | AD-16 takes the effective host from `X-Forwarded-Host` when present. After a DNS rebind, an attacker page is same-origin with `evil.example:8787`, so it can set that header **without a CORS preflight** and pass the host check. GET /api needs no Origin, so reads succeed. That defeats AD-16's stated "Prevents: … reading LanguageLab through … DNS rebinding". In Epic 1 only `/api/health` is exposed; from Epic 3 on, Captures and Items are. | 2 | 3 | 6 | Get an architect decision on the trust rule (see Mitigation Plans), and capture the real Tailscale Serve headers in entry 4's fixture. A P0 API test pins the rule. | Architect → Dev (entry 4) | Before entry 4 merges |
| R-02 | SEC | Content leaks into logs or the envelope. The leak paths are validation errors (FastAPI echoes `input`), tracebacks, query strings and the uvicorn access log. Grounded in AD-15, NFR-7 and entry 3. | 2 | 3 | 6 | Sentinel-string tests across every failure path, plus a one-line-per-request assertion | Dev (entry 3, guard in entry 4) | Entry 3 |
| R-03 | TECH | The router misses a leave path while dirty: pill, Menu, back link, browser back/swipe, or unload. `popstate` fires after the URL has already changed, so cancelling it needs a re-push. A miss means silent loss of a Draft or edits in Epics 4–6. Grounded in AD-13, NFR-4 and entry 7. | 3 | 2 | 6 | A Playwright matrix of leave paths × {Keep editing, Discard, Esc} at three widths, also run under WebKit | Dev (entry 7) | Entry 7 |

### Medium-Priority Risks (Score 3-4)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-04 | OPS | The released wheel doesn't run: static assets aren't packaged, the tag ≠ the pyproject version, or deps (pydantic-core, av) don't install on macOS 14 / Py 3.14. CI on Linux doesn't prove the macOS `uvx` install (AC1, entries 1 and 8). | 2 | 2 | 4 | CI smoke-installs the built wheel in a clean env and checks `/api/health` plus a static asset. Add a tag/version guard and the manual Mac Mini run in entry 8. Optionally add a `macos-14` smoke job. | Dev (entries 1 and 8), User (HITL) |
| R-05 | SEC | Tailscale Serve's real `Host` / `X-Forwarded-Host` / `Origin` differ from what's assumed, so legitimate tailnet writes get `forbidden_origin`. Today only the manual entry 10 proves it (AD-16, architecture Testing convention). | 2 | 2 | 4 | Record the real headers once (`tailscale serve` + an echo route or a log) into a fixture used by the entry 4 tests. Re-verify in entry 10. | Dev (entry 4), User (entry 10) |
| R-06 | SEC | A secret is echoed on a startup failure, or exposed to the browser. pydantic `ValidationError` prints `input_value` by default (entry 2 "no secret echoed", NFR-6/7). | 2 | 2 | 4 | Put sentinel secrets in a temp `.env`, force a failure, and assert stderr and the responses don't contain them | Dev (entry 2) |
| R-07 | TECH | Route order: an unknown `/api/*` falls through to the shell catch-all instead of a 404 envelope, or a deep client path returns 404 instead of the shell (AD-13 vs AD-15) | 2 | 2 | 4 | API tests on both sides of the boundary | Dev (entries 1 and 3) |
| R-08 | TECH | Stale client after an upgrade. Asset URLs are versioned, but if Safari caches the shell HTML, it keeps referencing old URLs (AD-13 "stale assets after an upgrade"). | 2 | 2 | 4 | Assert versioned asset URLs, plus the shell's `Cache-Control` once Q3 is decided | Dev (entry 1) |
| R-09 | TECH | Automated tests run Chromium only, while the targets are iPhone and iPad Safari (NFR-10). WebKit-only regressions (focus trap, History API) would show up only at entry 10. | 2 | 2 | 4 | Run the nav and unsaved E2E suites under the Playwright `webkit` project as well. The device run stays the final check. | Dev (entries 5–7) |
| R-10 | OPS | Tailscale discovery blocks or crashes startup when `tailscale` is absent or hangs. It must be non-fatal, and no timeout is specified (entry 4, FR-1). | 2 | 2 | 4 | Unit tests with a fake runner: missing binary, non-zero exit, timeout, recorded status JSON | Dev (entry 4) |
| R-11 | DATA | The dev-mode guard fails, so dev writes the release Prefix in later epics. Anki deck names are case-insensitive, so `languagelab` would collide with `LanguageLab` (AD-4 "one Prefix matching another", entry 2). | 1 | 3 | 3 | Unit tests for the exact and case-variant refusal (pending Q5) | Dev (entry 2) |
| R-12 | SEC | The server binds a non-loopback address, which exposes the app on the LAN. `LANGUAGE_LAB_HOST` is configurable (NFR-5, FR-2). | 1 | 3 | 3 | Assert the default bind is `127.0.0.1`, and run the manual LAN probes for 8787 and 8765 in entry 10 | Dev (entry 2), User (entry 10) |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
| --- | --- | --- | --- | --- | --- | --- |
| R-13 | OPS | Docs drift from the code: the command, `.env` keys or release asset name don't match the repo (FR-4, entry 9) | 2 | 1 | 2 | Document. A docs-consistency test (P2) |
| R-14 | TECH | The Playwright live-server port isn't on the allow-list after entry 4, which breaks every E2E test (entry 4 description) | 2 | 1 | 2 | Document. A fixture smoke test (P1) |

### Residual Risk After Mitigation

- **R-01**: low if option (a) or (c) holds. Under option (a), a local process that sets both a loopback Host and the tailnet XFH can still pass, but a local process can already reach keyless AnkiConnect (the FR-4 warning). So this matches the accepted local-trust boundary.
- **R-03**: iOS swipe-back and bfcache behaviour stays partly manual (entry 10).
- **R-04**: macOS-specific install failures stay manual unless a `macos-14` CI job is added.

### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

## NFR Planning

**Purpose:** This section captures the epic's NFR thresholds, the planned validation, and the evidence expected for a later `nfr-assess`. It isn't a final evidence audit.

| NFR Category | Requirement / Threshold | Risk Link | Planned Validation | Evidence Needed |
| --- | --- | --- | --- | --- |
| Security: access boundary | Binary: bind to `127.0.0.1` only (NFR-5). A foreign effective host → 403 `forbidden_origin`. Non-GET /api without an allowed Origin → 403 (AD-16) | R-01, R-05, R-12 | API tests (P0) plus the manual LAN probe and Tailscale header check (entry 10) | pytest report, entry 10 checklist |
| Security: secrets | Credentials never reach the browser (NFR-6) and are never echoed on failure | R-06 | API/integration tests with sentinel secrets | pytest report |
| Security / Observability: logs | No content in logs. One line per request: id, method, route template, status, code, duration. stdout/stderr only (NFR-7, NFR-9, AD-15) | R-02 | API tests with captured logs | pytest report |
| Reliability | An invalid Prefix → non-zero exit (AD-4). Tailscale discovery is non-fatal (entry 4) | R-10, R-11 | Unit tests plus a startup integration test | pytest report |
| Maintainability | ruff and pytest (with Playwright browsers) green on every `vX.Y.Z` tag (entry 8) | R-04 | The CI release workflow | GitHub Actions log |
| Compatibility / Accessibility | Usable at 390 / 820 / 1280 px (FR-3, NFR-10). aria-current, Menu sheet focus trap and return, `alertdialog` labelled, focus ring, inputs ≥16px (EXPERIENCE a11y floor) | R-03, R-09 | Playwright E2E (Chromium + WebKit) plus the device run | Playwright report, entry 10 checklist |
| Performance | N/A for Epic 1 | - | None | - |

**Unknown thresholds:** the Tailscale discovery timeout (Q2) and a startup-time target (none is set; N/A for a single user). Performance is N/A.

---

## Entry Criteria

- [ ] Q1 (the X-Forwarded-Host trust rule) is decided and recorded in the architecture spine before entry 4 starts
- [ ] Entry 1 pins the dev dependencies (pytest, ruff, pytest-playwright and, if the coverage gate is kept, pytest-cov), so no later entry adds any
- [ ] The Playwright browsers (chromium, webkit) are installable locally and in CI
- [ ] The Tailscale Serve headers have been recorded once from the Mac Mini, as the fixture for entry 4 (R-05)

## Exit Criteria

- [ ] All P0 automated tests pass, and all P0 manual checks in entries 8 and 10 are signed off
- [ ] All P1 tests pass, or their failures are triaged and ticketed
- [ ] R-01, R-02 and R-03 are mitigated, each with a passing test
- [ ] AC1 and the reach part of AC2 are demonstrated on real devices (entry 10)
- [ ] The tag workflow is green on `v0.1.0`

---

## Test Coverage Plan

Test levels:

- **Unit**: pytest on pure functions and Settings.
- **API**: pytest with an ASGI client against `create_app(settings)` and captured logs.
- **Integration**: a subprocess or the built wheel.
- **E2E**: pytest-playwright against the live-server fixture from entry 5.
- **Manual**: HITL by the user.

The table rows describe the tests to write. They aren't execution timing.

### P0 (Critical)

**Criteria**: Critical business, security, data-integrity, or compliance impact with no safe workaround.

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| Allow-list: `127.0.0.1:<port>`, `localhost:<port>` and the tailnet host pass; a foreign `Host` → 403 `forbidden_origin` in the envelope (entry 4) | API | R-01 | 4 | Dev | Parametrized. A middleware test sits at API level because that's the boundary where it runs. |
| Spoofed `X-Forwarded-Host`: a foreign `Host` plus an allowed XFH on GET /api, handled per the Q1 rule; a legitimate XFH from the recorded Tailscale fixture passes | API | R-01, R-05 | 2 | Dev | Encodes the rebinding case explicitly |
| Origin on non-GET /api: missing → 403, foreign → 403, allowed (compared without scheme) → passes | API | R-01 | 3 | Dev | |
| No content in the response or the log: a unique sentinel in path, query, body and headers on a validation error, an unknown /api path, an unhandled exception and a 403 | API | R-02 | 4 | Dev | Assert the sentinel is absent from the response body and from captured stdout/stderr |
| Exactly one log line per request with the AD-15 fields (route template, not the raw path); the uvicorn access log is off; a 403 also gets a requestId and one line | API | R-02 | 2 | Dev | Catches middleware-order bugs between the request-id and allow-list middleware |
| Startup with an invalid `ANKI_PREFIX` exits non-zero, and a sentinel secret in `.env` never shows in stderr | Integration | R-06, R-11 | 2 | Dev | A subprocess run against a temp `HOME` |
| `/api/health` and the served static files contain no settings values beyond the version | API | R-06 | 1 | Dev | NFR-6 |
| Dev mode reads the repo-root `.env`, and refuses `ANKI_PREFIX=LanguageLab` and its case variants | Unit | R-11 | 3 | Dev | Case-insensitivity depends on Q5 |
| Default bind is `127.0.0.1:8787` | Unit | R-12 | 1 | Dev | Settings default plus the uvicorn config handed off |
| Built-wheel smoke: `uv build` → install into a clean venv → start → `/api/health` returns the pyproject version, a versioned static asset returns 200, and `/any/deep/path` returns the shell | Integration | R-04, R-07 | 1 | Dev | Runs in CI before the release upload. It proves that the assets are packaged. |
| **Manual:** the release install on the Mac Mini, `uvx --from <release asset URL> language-lab`, loads `~/.config/language-lab/.env` and listens on 127.0.0.1 only (entry 8) | Manual | R-04, R-12 | 1 | User | AC1 |
| **Manual:** iPhone Safari, iPad Safari and a desktop browser load the HTTPS shell in a secure context, and every destination opens by nav and by direct URL (entry 10) | Manual | R-09 | 3 | User | AC2 (reach). Check `window.isSecureContext` in the console or with a debug badge. |
| **Manual:** a non-GET /api from the desktop browser over Tailscale is accepted, and one from another Origin is rejected | Manual | R-05 | 1 | User | |
| **Manual:** `<LAN IP>:8787` and `<LAN IP>:8765` are unreachable from another device | Manual | R-12 | 2 | User | FR-2 |

**Total P0**: 23 automated tests (~35–45 hours) plus 7 manual checks (~2–3 hours)

### P1 (High)

**Criteria**: Core, frequent, or complex behavior with material user reach and a limited workaround.

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| Unsaved alert while dirty, on every leave path (pill, Menu row, back link, browser back): the alert shows, Keep editing stays, Discard navigates, Esc cancels, and focus starts on Keep editing | E2E | R-03 | 6 | Dev | Browser back must leave the URL unchanged on Keep editing |
| `router.confirmLeave()` resolves true on Discard and false on Keep editing; both body variants render (`{count}` / "This Draft isn't saved."); the dialog is `role=alertdialog` with a labelled title and description | E2E | R-03 | 2 | Dev | Uses a test-only screen or a `setDirty` hook from the page |
| `beforeunload` is registered only while dirty | E2E | R-03 | 1 | Dev | Assert the listener effect via `page.on('dialog')` on reload |
| `navigate(path, { flash })` shows the message once, and it's gone after the next navigation | E2E | - | 1 | Dev | |
| Every destination (`/captures`, `/en/items`, `/en/pronunciation`, `/fr/items`, `/fr/pronunciation`, `/setup`) is reachable by nav, by direct load and by browser back, with aria-current correct | E2E | R-09 | 3 | Dev | One test per width (390/820/1280), looping over destinations |
| Phone Menu sheet: `role=dialog` labelled "Menu", focus moves to the current row and is trapped, and Esc, scrim tap and Menu close it and return focus to Menu | E2E | R-09 | 2 | Dev | Also runs under WebKit |
| Envelope shape for each produced code (`validation_failed`, `not_found`, `internal_error`, `forbidden_origin`): `{error:{code,message,requestId}}`, camelCase | API | R-07 | 2 | Dev | |
| `api.js` parses the envelope into a typed error and is the only `fetch` caller | E2E | R-07 | 1 | Dev | Route `/api/health` to a 500 envelope with `page.route` and assert the rendered error. A grep check covers "only caller". |
| Route boundary: an unknown `/api/x` → 404 envelope (not the shell); non-/api GETs → the shell; `/static/<version>/…` URLs carry the release version | API | R-07, R-08 | 3 | Dev | |
| Settings: unknown keys are ignored, `OPENROUTER_MODELS` parses in order, and every Settings field appears in `.env.example` | Unit | R-13 | 3 | Dev | The last test reflects over the Settings model |
| Tailscale discovery: parses the recorded status fixture; a missing binary, a non-zero exit or a timeout → no tailnet host, and startup continues | Unit | R-10 | 3 | Dev | The runner is injected, so no real `tailscale` call |
| Release workflow fails when the tag differs from the pyproject version | Integration | R-04 | 1 | Dev | A script step unit-tested locally, or a dry run on a throwaway tag |
| The live-server fixture passes the allow-list (its port is in settings) | E2E | R-14 | 1 | Dev | A smoke test that runs first |

**Total P1**: 29 tests (~20–30 hours)

### P2 (Medium)

**Criteria**: Secondary behavior with narrower user reach and an acceptable workaround.

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| Figtree is applied, and every request goes to the app origin (none to an external host) | E2E | - | 1 | Dev | Entry 5 verify. Record requests with `page.on('request')`. |
| Base styles: a visible focus ring on Tab, input font-size ≥16px | E2E | - | 2 | Dev | |
| An unknown client path redirects to `/captures` | E2E | - | 1 | Dev | The level depends on Q4 (server or router) |
| The shell response carries the agreed `Cache-Control` | API | R-08 | 1 | Dev | Blocked on Q3 |
| Docs consistency: commands, `.env` keys and the release asset name in `docs/` match the console script, Settings and the workflow; each FR-4 item maps to a named section | Unit | R-13 | 2 | Dev | Entry 9 verify, as a script |
| Startup prints the local URL, and the Tailscale URL when known | Integration | R-10 | 1 | Dev | FR-1 |

**Total P2**: 8 tests (~3–5 hours)

### P3 (Low)

**Criteria**: Rare, cosmetic, or experimental behavior with minimal impact and an easy workaround.

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| Studio token values in `static/css` match DESIGN.md | Unit | - | 1 | Dev | A parse-and-compare script |
| Safe-area insets on iPhone (notch and home bar) | Manual | - | 1 | User | During the entry 10 run |

**Total P3**: 2 tests (~1 hour)

---

## Execution Strategy

**Philosophy:** Run every functional scenario on each change while the suite stays under 15 minutes. P0–P3 is priority, not execution timing.

- **Every push / pull request (recommended, Q6):** ruff plus all Unit, API and Integration tests, and the E2E suite on Chromium. The expected runtime is a few minutes.
- **Every `vX.Y.Z` tag (entry 8):** the same set plus the WebKit E2E project and the built-wheel smoke test, before the release upload.
- **Order within a run:** the live-server smoke test first, then P0, P1, and P2/P3 (pytest markers `p0`/`p1`/`p2`). Use `pytest-xdist` only if the suite outgrows 15 minutes; it's unlikely at ~60 tests.
- **Nightly / Weekly:** none for this epic. No long-running or expensive suites exist.
- **Manual (HITL):** the entry 8 release run on the Mac Mini and the entry 10 device acceptance. Repeat them after any change to the AD-16 middleware or the release workflow.

---

## Resource Estimates

### Test Development Effort

| Priority | Count | Hours/Test | Total Hours | Notes |
| --- | --- | --- | --- | --- |
| P0 | 23 (+7 manual) | ~1.5–2.0 | ~35–45 (+2–3 manual) | Security middleware, log capture, wheel smoke |
| P1 | 29 | ~0.75–1.0 | ~20–30 | Router and dialog E2E dominate |
| P2 | 8 | ~0.5 | ~3–5 | |
| P3 | 2 | ~0.25–0.5 | ~1 | |
| **Total** | **61 (+8 manual)** | **-** | **~60–85** | **~1.5–2.5 weeks, spread across entries 1–10** |

### Prerequisites

**Test Data and Fixtures:**

- A `settings_factory` fixture that builds `Settings` from a temp `.env` (and a temp `HOME` for `~/.config`), with auto-cleanup
- A `log_capture` fixture that collects the app logger plus stdout/stderr per request
- A `live_server` fixture (entry 5) with its port registered in the allow-list
- `tests/fixtures/tailscale-status.json` and `tests/fixtures/tailscale-serve-headers.json`, recorded once from the Mac Mini
- A `dirty_screen` test hook: a way to call `router.setDirty({...})` from Playwright without a feature screen

**Tooling:**

- pytest and an ASGI test client (httpx `ASGITransport`) for the API level
- pytest-playwright with the chromium and webkit projects
- ruff
- pytest-cov, only if the coverage gate is kept (it must then be pinned in entry 1)

**Environment:**

- Local runs: Python 3.14 via uv; no Anki, Tailscale or network needed
- CI: GitHub Actions with Playwright browsers installed; optionally a `macos-14` wheel smoke job (R-04)
- Manual: the Mac Mini with Tailscale Serve, plus an iPhone, an iPad and a desktop on the tailnet

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (no exceptions), and the manual P0 checks are signed off
- **P1 pass rate**: ≥95% (failures need a ticket)
- **P2/P3 pass rate**: ≥90% (informational)
- **High-risk mitigations**: R-01, R-02 and R-03 are complete, or have a written waiver

### Coverage Targets

- **Security scenarios (SEC)**: 100% of the rows above pass
- **Backend line coverage** (`app.py`, `settings.py`, `domain/errors.py`, middleware): ≥80%, if pytest-cov is adopted
- **Leave paths in the router**: 100% of the paths listed in EXPERIENCE "Unsaved changes"

### Non-Negotiable Requirements

- [ ] All P0 tests pass
- [ ] No high-risk (≥6) items unmitigated
- [ ] Security tests (SEC category) pass 100%
- [ ] Performance targets: N/A for Epic 1
- [ ] Planned NFR evidence exists, or `nfr-assess` has documented CONCERNS or waivers

---

## Mitigation Plans

### R-01: X-Forwarded-Host trust lets a DNS-rebinding read through (Score: 6)

**Mitigation Strategy:** Decide the trust rule before entry 4. Candidates:

- **(a)** Validate `Host` **and** `X-Forwarded-Host`. Accept XFH only when it equals the tailnet host and `Host` is loopback (`127.0.0.1:<port>` / `localhost:<port>`). This holds if Tailscale Serve forwards with a loopback Host; the recorded headers will show whether it does.
- **(b)** Additionally require `Sec-Fetch-Site: same-origin`/`none`, or an allowed Origin, on GET /api. All target browsers send Fetch Metadata.
- **(c)** Drop XFH and check `Host` only, if Tailscale Serve preserves the public Host.

Record the decision as an amendment to AD-16. Then write the P0 spoof test first (red), and implement entry 4 against it.

**Owner:** Architect (decision), Dev (entry 4)
**Timeline:** Before entry 4 merges
**Status:** Planned
**Verification:** The P0 API test "foreign Host + allowed XFH on GET /api" passes with the chosen behaviour, the Tailscale header fixture passes, and entry 10 confirms the tailnet works.

### R-02: Content leaks into logs or the envelope (Score: 6)

**Mitigation Strategy:** Override FastAPI's `RequestValidationError` handler so it returns field locations without `input`/`ctx` values. Use a catch-all `Exception` handler that logs only the code and requestId. Run uvicorn with `access_log=False`. Log the route template, not `request.url`. Then write the sentinel tests described in P0.
**Owner:** Dev (entry 3)
**Timeline:** Entry 3, re-run on every later entry
**Status:** Planned
**Verification:** The P0 sentinel tests and the one-line-per-request test pass, and stay in the default suite for all later epics.

### R-03: The router misses a leave path while dirty (Score: 6)

**Mitigation Strategy:** Make a single `navigate()` choke point that every pill, Menu row and back link goes through. On `popstate` while dirty, re-push the current URL before showing the alert, so Keep editing leaves the URL unchanged. Register `beforeunload` only while dirty. Then run the P1 E2E matrix under both Chromium and WebKit.
**Owner:** Dev (entry 7)
**Timeline:** Entry 7
**Status:** Planned
**Verification:** The P1 unsaved-alert tests pass on Chromium and WebKit, and the entry 10 device run checks iOS swipe-back by hand.

---

## Assumptions and Dependencies

### Assumptions

1. Tests never reach real Anki, OpenRouter, Azure or Tailscale. Tailscale is exercised through recorded fixtures and an injected runner (architecture Testing convention).
2. Playwright WebKit is close enough to iOS Safari for automated regression checks. Real-device behaviour is proven only in entry 10.
3. The epic note "no separate end-to-end suite" means no additional journey suite. The per-story Playwright tests above are part of each story's verify step, not a separate suite.
4. Anki deck names compare case-insensitively, which is why R-11 tests case variants. Confirm with Q5.

### Dependencies

1. Q1 decision (X-Forwarded-Host trust rule). Required before entry 4.
2. Recorded Tailscale Serve headers and status JSON from the Mac Mini. Required before entry 4.
3. Entry 5's `live_server` fixture. Required before entries 6 and 7.
4. A GitHub release permission for the workflow. Required by entry 8.

### Risks to Plan

- **Risk**: The user's separate test strategy (epic note, 2026-10-08) changes levels or tooling.
  - **Impact**: Some P1 E2E rows could move or merge.
  - **Contingency**: Use Edit mode on this document. The risk register and the P0 rows are tool-agnostic.
- **Risk**: Tailscale Serve sends headers that make option (a) or (c) impossible.
  - **Impact**: R-01 needs option (b), which touches every GET in later epics.
  - **Contingency**: Option (b) is implemented once in the middleware, so features don't change.

### Open Clarifications

| ID | Question | Affects |
| --- | --- | --- |
| Q1 | What is the trust rule for `X-Forwarded-Host` versus `Host`, and is Origin or Fetch Metadata required on GET /api? | R-01, entry 4 |
| Q2 | What is the timeout for Tailscale discovery at startup? | R-10, entry 4 |
| Q3 | What `Cache-Control` should the shell HTML carry? (`no-cache` is suggested) | R-08, entry 1 |
| Q4 | Should the unknown-client-path redirect to `/captures` happen in the server (302) or in `router.js`? | P2 row, entries 1 and 6 |
| Q5 | Should the dev guard refuse `LanguageLab` case-insensitively? | R-11, entry 2 |
| Q6 | Should ruff and pytest run on push/PR as well as on tags? | Execution strategy, entry 8 |

---

## Follow-on Workflows (Manual)

- Run `/bmad-testarch-framework` to scaffold the pytest + pytest-playwright structure: fixtures, the `live_server` fixture, the log capture.
- Run `/bmad-testarch-atdd` to generate failing P0 tests, starting with R-01 and R-02. This is a separate workflow and isn't run automatically.
- Run `/bmad-testarch-automate` for broader coverage once the implementation exists.

---

## Approval

**Test Design Approved By:**

- [ ] Product owner / Tech lead / QA (single-person project): Oleksii Shapovalov. Date: ____

**Comments:**

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope |
| --- | --- | --- |
| **AD-16 middleware** | Every later epic's requests pass through it | The P0 allow-list and Origin tests stay in the default suite |
| **Error envelope and log middleware** | Every later epic's errors and logs | The P0 sentinel and one-line tests stay in the default suite |
| **router.js (`setDirty`, `confirmLeave`, flash)** | Draft editor (Epic 4), Item detail (Epics 5 and 6) | The P1 unsaved-alert matrix |
| **Settings** | Every adapter in Epics 2–7 | Settings unit tests, plus the `.env.example` completeness test |
| **Release workflow** | Every release | The wheel smoke test and the tag/version guard |

---

## Appendix

### Knowledge Base References

- `risk-governance.md` - Risk classification framework
- `probability-impact.md` - Risk scoring methodology
- `test-levels-framework.md` - Test level selection
- `test-priorities-matrix.md` - P0-P3 prioritization
- `nfr-criteria.md` - NFR planning categories

### Related Documents

- Spec: `_bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md` (CAP-1)
- PRD: `_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md` (FR-1–FR-4, NFR-5–NFR-11, AC1–AC2)
- Epic: `_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md` and `tickets.toml`
- Architecture: `_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md` (AD-13, AD-15, AD-16, AD-18)
- UX: `_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md`

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `bmad-testarch-test-design`
**Version**: 4.0 (BMad v6)

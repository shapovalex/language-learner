---
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight', 'step-02-select-framework', 'step-03-scaffold-framework', 'step-04-docs-and-scripts', 'step-05-validate-and-summary']
lastStep: 'step-05-validate-and-summary'
lastSaved: '2026-10-10'
---

# Test Framework Setup — Progress

## Step 1: Preflight

- **Detected stack:** `fullstack` (effective). Manifests show backend only (`pyproject.toml`, FastAPI 0.143), but the app serves a vanilla-JS browser client from `src/language_lab/static/`. NFR-11 rules out Node, so the browser layer is tested from Python with pytest-playwright.
- **Language / toolchain:** Python ≥3.14, uv (uv_build backend), ruff 0.16.10.
- **Existing framework:** pytest 9.1.1 configured in `pyproject.toml` (`testpaths = ["tests"]`, `addopts = "-ra"`). One test module (`tests/test_app.py`, story 1.1) and an empty `tests/fakes/` package. No `conftest.py`, no `playwright.config.*`, no `cypress.*`. Dev group already pins pytest-playwright 0.10.0 and pytest-cov 7.1.0. No conflict.
- **Context docs:** architecture (`architecture-languagelab.md`: hexagonal ports, in-memory fakes in `tests/fakes/`, adapters tested via recorded HTTP fixtures, no real Anki/OpenRouter/Azure, optional live-Anki opt-in marker), Epic 1 test design (`test-design-epic-1.md`: `settings_factory`, `log_capture`, `live_server` fixtures, Tailscale fixtures, `p0`/`p1`/`p2` markers, chromium + webkit projects, widths 390/820/1280).
- **Auth:** none at app level; Host/Origin allow-list (AD-16) — the live server port must be on the allow-list (R-14).
- **Playwright Utils / Pact.js Utils:** config enables them, but both are TypeScript-only and Node is excluded (NFR-11) → N/A.

## Step 2: Framework Selection

- **Backend / API / unit:** pytest 9.1.1 (already pinned). FastAPI `TestClient` for API-level tests; in-memory port fakes in `tests/fakes/`.
- **Browser E2E:** Playwright via **pytest-playwright 0.10.0** (Python), projects `chromium` (every push) and `webkit` (tag runs, R-09 iOS Safari proxy).
- **Why Playwright:** multi-browser incl. WebKit (targets are iPhone/iPad Safari), tight API+UI integration (`page.route` for envelope tests), same pytest runner/fixtures/markers as the backend suite.
- **Why not Cypress:** requires Node (excluded by NFR-11), no WebKit parity.
- **Not used:** Playwright Utils, Pact.js Utils (TypeScript-only). No contract testing — single-process app with no consumer/provider split.

## Step 3: Scaffold

- **Execution mode:** sequential (no subagents requested).
- **Knowledge loaded (disabled branch, Python + Playwright):** fixture-architecture, data-factories, test-quality, network-first, playwright-config.
- **Layout:** `tests/{unit,integration,api,e2e}/`, `tests/support/` (pure helpers), `tests/support/fixtures/` (pytest plugins loaded by root `conftest.py`), existing `tests/fakes/`. `tests/test_app.py` moved to `tests/api/test_app.py` (PYPROJECT path adjusted).
- **Config (`pyproject.toml`):** `--strict-markers`, `--strict-config`, `xfail_strict`, markers `unit/integration/api/e2e` (auto-applied by directory), `smoke`, `p0`–`p3`, `live_anki` (skipped unless `--live-anki`); Playwright `--tracing=retain-on-failure --screenshot=only-on-failure`; coverage source `language_lab` with branch coverage.
- **Run order:** root conftest sorts smoke → p0 → p1 → p2 → p3 → unmarked (test design §execution order).
- **Fixtures:** `settings_factory` (env-isolated Settings, temp HOME/cwd, monkeypatch auto-cleanup), `log_capture` (`language_lab.*` records), `live_server` (uvicorn in a thread on a pre-bound socket; `settings.port` == served port, R-14), `live_server_settings` (override point), `base_url` (`--base-url`/`PYTEST_BASE_URL` else live server), e2e `context` with timeouts action 15s / navigation 30s / expect 10s.
- **Helpers:** `tests/support/network.py` (`stub_api_error` AD-15 envelope, `record_requests`), `tests/support/viewports.py` (390/820/1280).
- **Samples:** `tests/unit/test_settings_factory.py` (fixture + parametrize), `tests/e2e/test_shell.py` (smoke, network-first wait, error stub, same-origin requests, 3 widths).
- **Deviations:** no `playwright.config.ts`/`.nvmrc` (Python, no Node); no root `.env.example` (owned by story 2); no faker / domain factories (no domain types yet; no new dev deps per entry 1); no per-test 60s timeout (pytest-timeout not pinned); no Pact (no consumer/provider boundary — gate closed).

## Step 4: Docs and Scripts

- `tests/README.md`: setup, run commands (local/headed/debug/base-url/live-anki), layout, fixtures, markers, rules, enforcement, CI plan, references.
- `Makefile`: `test`, `test-fast`, `test-e2e`, `test-webkit`, `test-integration`, `test-cov`, `test-ci`, `browsers`.
- Enforcement hook: `.claude/hooks/tea-enforce.cjs` (byte-identical copy, sha256 e94cc2dd…f594d), `.tea/enforce-config.json` (testGlobs `tests/**/test_*.py`, `**/*_test.py`; no pact/exclude globs), hooks merged into existing `.claude/settings.json` (PreToolUse/PostToolUse/Stop). Verified: blocks a `time.sleep` write (exit 2); all three current test files pass `--post`.
- Note: `.claude/` is gitignored in this repo, so the hook and its registration stay local to this machine; `.tea/enforce-config.json` is committable.

## Step 5: Validation and Summary

- **Checklist:** preflight ✔, structure ✔, config ✔ (pytest ini, not playwright.config — Python stack), fixtures ✔, docs + scripts ✔, enforcement hook ✔. Gap fixed during validation: README troubleshooting section added.
- **Defect found and fixed:** `base_url` override defined in a `pytest_plugins` module lost to pytest-playwright's fallback plugin (registered later) → every `page.goto("/…")` failed. Moved to `tests/e2e/conftest.py`.
- **Execution:** `uv run pytest --browser chromium --browser webkit` → 31 passed in 2.9 s. `ruff check` and `ruff format --check` clean. Collection order puts the smoke test first.
- **Not covered by the checklist's JS-centric items (by design):** `.nvmrc`, `playwright.config.ts`, faker factories, HTML reporter (pytest-playwright has none; JUnit XML via `make test-ci`), retries (no pytest-rerunfailures pinned), parallelism (pytest-xdist deferred per test design until >15 min).
- **Next:** commit; `/bmad-testarch-ci` for the GitHub Actions pipeline; story 5 reuses `live_server`/`base_url` rather than creating its own; story 2 extends `settings_factory` with a temp `.env` once Settings loads one.

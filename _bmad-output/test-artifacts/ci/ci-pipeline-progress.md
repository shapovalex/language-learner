---
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight', 'step-02-generate-pipeline', 'step-03-configure-quality-gates', 'step-03b-render-evaluation-plans', 'step-04-validate-and-summary']
lastStep: 'step-04-validate-and-summary'
lastSaved: '2026-10-10'
---

# CI Pipeline Setup — Progress

## Step 1: Preflight

- **Git:** repo present; remote `origin` → github.com/shapovalex/language-learner
- **test_stack_type:** `fullstack` (auto) — Python/FastAPI backend (`pyproject.toml`) serving static frontend (`src/language_lab/static/`), browser E2E via pytest-playwright. No Node (NFR-11).
- **test_framework:** pytest 9.1.1 + pytest-playwright 0.10.0 (`[tool.pytest.ini_options]` in `pyproject.toml`); levels unit/api/integration/e2e via markers; `make test-ci` emits JUnit XML.
- **Local run:** `make test-ci` → 26 passed, 1 warning (Starlette httpx deprecation), 1.56 s. `ruff check` + `ruff format --check` clean.
- **ci_platform:** `github-actions` (no existing CI config; inferred from github.com remote)
- **Environment:** Python 3.14 (`.python-version`), uv with `uv.lock` (cache key), Playwright browsers chromium + webkit (`make browsers`).
- **TEA flags:**
  - `tea_use_playwright_utils: true` — not applicable: Python stack, no `package.json`; burn-in uses pytest repetition instead of `runBurnIn`.
  - `tea_use_pactjs_utils: true` — skipped: no contract tests (`pact/`, `tests/contract/`) or pact dependencies.
- **Checkpoint:** none found → fresh run.

## Step 2: Generate Pipeline

- **Execution mode:** sequential
- **Output:** `.github/workflows/test.yml` (adapted from `github-actions-template.yaml`)
- **Jobs:** `lint` (ruff check + format) → `test` (Chromium, `make test-ci`) → `burn-in` (PRs) / `webkit` (`v*` tags) → `report` (always)
- **Deviations from template, grounded in the Epic 1 test design:**
  - No sharding: the suite takes ~1.5 s, and the design calls for "whole suite in one job (<15 min)".
  - No retries: the design pins the dev deps in entry 1 ("no later entry adds any"), so neither pytest-rerunfailures nor xdist is added. Burn-in is the flakiness control.
  - No weekly cron: "no nightly or weekly suites in this epic". A `v*` tag trigger was added for WebKit (R-09).
  - Python/uv instead of Node: `astral-sh/setup-uv` with the uv cache keyed on `uv.lock`, `UV_LOCKED=1`, and the Playwright browser cache keyed on `uv.lock`.
- **Contract testing:** skipped (no Pact artifacts; NFR-11 rules out Node).
- **Security:** no `inputs.*` or `github.event.*` in `run:` blocks; `permissions: contents: read`.

## Step 3: Quality Gates

- **Burn-in:** `make burn-in BURN_IN=10` on PRs, E2E only (fullstack → enabled), exit on first failure.
- **Count reconciliation:** collected (`pytest --collect-only`) must equal the JUnit `tests` count, otherwise the job fails.
- **Pass rates:** any failure fails the job, so P0 = 100% and P1 = 100% (stricter than the ≥95% target).
- **No `continue-on-error`** on any test step. The `report` job fails if any needed job failed or was cancelled.
- **Notifications:** GitHub default failure emails, plus a link to the artifacts in the run summary. No Slack.
- **Fragments:** `ci-burn-in.md` guidance applied. Not applicable: `burn-in.md` and `playwright-utils-mandate.md` (Python stack); Pact fragments (no contract tests).

## Step 3b: Evaluation Plans

- evaluation plans: none

## Step 4: Validate & Summary

- `actionlint` 1.7.12: clean. YAML parses.
- Local parity: `make lint` passes, `make test-ci` → 26/26, reconcile 26 == 26, and `make burn-in BURN_IN=2` is clean.
- **Helpers:** Makefile targets `lint`, `burn-in` (BURN_IN=N) and `ci-local`, matching the repo's Makefile idiom instead of `scripts/*.sh`.
- **Docs:** the CI section of `tests/README.md` (triggers, gates, artifacts, caching, secrets: none). It stands in for `docs/ci.md`, since the repo has no `docs/`.
- **Secrets:** none required.
- **Open (entry 8 / R-04):** built-wheel smoke test, release upload, optional `macos-14` smoke job.
- **Not yet verified:** first run on GitHub (needs a push).

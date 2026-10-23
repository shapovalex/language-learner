---
title: 'Cut CI test wall-clock time'
type: 'chore'
ticket: ''
created: '2026-10-23'
status: 'built'
baseline_revision: 'd6de987354410d2bfff48bb3568c98377613337a'
route: 'oneshot'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** PR runs of the Test Pipeline take 12–20 min. Measured on run 39973044870: pytest ~3 min serial (959 tests, E2E 145 s of it); `playwright install --with-deps` swings from 18 s to 8 min on slow Ubuntu apt mirrors; burn-in (E2E ×3, ~7 min) waits for the test job before it starts, then pays setup and install a second time.

**Approach:** Run the suite in parallel with pytest-xdist (local: 92 s → 22 s, all 959 pass). Install only the Chromium headless shell, without the apt deps, on push/PR. Start burn-in alongside the test job instead of after it.

</frozen-after-approval>

## Implementation Notes

Oneshot because the change is about 30 lines across config and docs: the workflow, the Makefile, one pinned dev dependency, and the README's CI section.

- `pyproject.toml` / `uv.lock`: add `pytest-xdist==3.8.0` to dev deps.
- `Makefile`: `test-ci`, `burn-in`, `test`, `test-e2e`, `test-fast` add `-n auto`. Fixtures are worker-safe: each worker binds its own free port for `live_server`, and settings/release fixtures use tmp dirs. JUnit is still one merged file, so the reconcile step stays valid.
- `.github/workflows/test.yml`: `playwright install --only-shell chromium` (headless runs use the shell; the runner image already ships Chrome's system libs). Burn-in becomes `needs: lint`. Update the header comment.
- `.github/workflows/release.yml`: `-n auto`. Keep `--with-deps`, because WebKit needs it.
- `tests/README.md`: describe the parallel run and the new job graph.

## Verification

**Commands:**
- `uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `make test-ci` -- expected: 959 passed, JUnit holds 959
- CI on the PR -- expected: green; test job well under 2 min, burn-in runs at the same time as test

## Review Triage Log

Quick review: 0 high, 2 medium, 3 low, 1 false, 1 maybe-false.

- medium, patch: under `load` distribution each worker running a wheel test built its own wheel and started its own `uvx` app. Fixed by putting both wheel modules in `xdist_group("release_wheel")` and passing `--dist loadgroup` everywhere `-n auto` runs.
- medium, maybe-false, deferred: `closed_port()` and `released_app` free a port and use it later. Another xdist worker could grab it in that gap. Not seen across 3 local full runs. A burn-in failure that names one of those tests would settle it.
- low, patch: the README Setup/Running sections didn't mention xdist. Updated.
- low, patch: the README promised smoke-first order. Now says it is a queue order under xdist.
- low, patch: `test-integration` was the only serial target and the Makefile comment was inaccurate. Both fixed.
- false: "make test-ci not run with the reconcile". It was run: 959 collected, and the JUnit file reports 959. The CI check waits for the PR run.

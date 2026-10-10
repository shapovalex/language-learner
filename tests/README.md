# Tests

pytest for everything, plus [pytest-playwright](https://playwright.dev/python/) for the browser.
There is no Node here (NFR-11), so Playwright runs from Python against the real app on a loopback port.

## Setup

```bash
uv sync                 # dev group: pytest, pytest-playwright, pytest-cov, ruff
make browsers           # uv run playwright install chromium webkit (once per Playwright version)
```

## Running

| Command | What it runs |
| --- | --- |
| `make test` / `uv run pytest` | Everything; E2E on Chromium |
| `make test-fast` | Everything except E2E (no browser) |
| `make test-e2e` | E2E only |
| `make test-webkit` | E2E on Chromium and WebKit (tag runs; iPhone/iPad Safari proxy) |
| `make test-cov` | Fast suite with branch coverage of `language_lab` |
| `uv run pytest -m p0` | One priority |
| `uv run pytest tests/e2e --headed --slowmo 300` | Watch the browser |
| `PWDEBUG=1 uv run pytest tests/e2e -k shell` | Playwright Inspector, step through |
| `uv run pytest tests/e2e --base-url http://127.0.0.1:8787` | E2E against an app you started yourself |
| `uv run pytest --live-anki -m live_anki` | Opt-in tests against a real Anki (dev Prefix) |

A failed E2E test leaves a trace and a screenshot under `test-results/`.
Open the trace with `uv run playwright show-trace test-results/<test>/trace.zip`.

## Layout

```
tests/
  conftest.py          level markers, priority order, --live-anki, loads support fixtures
  unit/                pure logic, no I/O
  api/                 HTTP through FastAPI TestClient
  integration/         adapters against recorded HTTP fixtures (from Epic 2)
  e2e/                 Playwright against the live server; conftest sets timeouts
  fakes/               one in-memory fake per port (AD-1)
  support/
    live_server.py     run_live_server(): uvicorn in a thread on a pre-bound socket
    network.py         stub_api_error() (AD-15 envelope), record_requests()
    viewports.py       PHONE 390 / TABLET 820 / DESKTOP 1280
    fixtures/          pytest fixtures, one concern per module
```

Helpers in `support/` are plain functions, and `support/fixtures/` wraps them as fixtures.
Write the function first, then the fixture.

### Fixtures

| Fixture | Scope | Purpose |
| --- | --- | --- |
| `settings_factory` | function | `make(env={...}, **overrides) -> Settings` with every `LANGUAGE_LAB_*` cleared and HOME/cwd in `tmp_path`. Cleaned up by monkeypatch |
| `log_capture` | function | `.records` / `.messages` from `language_lab.*` loggers at INFO+. Use `capsys` for stdout |
| `live_server` | session | The real `create_app(settings)` on a free port. `settings.port` is the served port, so the AD-16 allow-list accepts it (R-14) |
| `live_server_settings` | session | Override it to change what the live server runs with |
| `base_url` (in `e2e/conftest.py`) | session | `--base-url` / `PYTEST_BASE_URL` if given, else `live_server.url`. `page.goto("/x")` resolves against it |
| `page`, `context` | function | From pytest-playwright. Timeouts: action 15 s, navigation 30 s, `expect` 10 s |

### Markers

The level markers `unit`, `integration`, `api` and `e2e` are applied from the directory, so don't add them by hand.
Priority markers come from the test design: `smoke`, `p0` to `p3`. Within a run, smoke tests go first, then P0 to P3, then unmarked tests.
`live_anki` tests are skipped unless you pass `--live-anki`.
`--strict-markers` is on, so register any new marker in `pyproject.toml`.

## Rules of the road

- **No real externals.** Tests never reach real Anki, OpenRouter, Azure or Tailscale. Services use `tests/fakes/`, and adapters use recorded HTTP fixtures under `tests/fixtures/`.
- **Network-first.** Arm the wait before the action that triggers the request (`with page.expect_response("**/api/x"): page.goto(...)`), and register `stub_api_error` before `goto`. Never `time.sleep` or `page.wait_for_timeout`.
- **Selectors.** Use roles and accessible names first (`get_by_role`, `get_by_label`); the UI's a11y floor makes them stable. Fall back to `data-testid` only where there is no accessible name.
- **Isolation.** Build settings and env through `settings_factory`, never `os.environ` directly. Each test's data comes from its own factory call. Use unique IDs (`uuid.uuid4()`) when data only needs to be unique, and named constants when the value *is* the requirement.
- **One concern per test.** Group three or more tests in a `Test…` class, and use `pytest.mark.parametrize` for tables. Keep assertions in the test body.
- **Skips carry a reason.** Write `pytest.mark.skip(reason="… until X")`. Don't commit a bare skip.
- **Widths.** UI tests that depend on layout parametrize over `viewports.ALL`.

## Write-time enforcement

A Claude Code hook (`.claude/hooks/tea-enforce.cjs`, registered in `.claude/settings.json`) checks every write to `tests/**/test_*.py`.
It blocks hard waits (H1), focused tests (C2), tautological assertions (C3), flows that assert nothing (C4) and test files over 1000 lines (H5).
It warns on disabled tests (C1).
The rules and their severities come from the TEA criteria registry (`bmad-testarch-test-review/steps-c/criteria-registry.md`), not from the hook.
To switch a rule off, add its id to `disabledRules` in `.tea/enforce-config.json` and explain why in the commit.
Don't edit the hook itself: `hookSha256` detects a drifted copy.

## CI

GitHub Actions, in `.github/workflows/test.yml`. It follows the Epic 1 test design: one job, Chromium, and no Node.

| Trigger | Jobs |
| --- | --- |
| Push to `main` | lint → test (Chromium) → report |
| Pull request to `main` | lint → test → burn-in (E2E ×10) → report |
| `vX.Y.Z` tag | lint → test → E2E on Chromium + WebKit (R-09) → report |

- **Lint:** `ruff check` and `ruff format --check`. Findings show as PR annotations.
- **Test:** `make test-ci`. Afterwards the job checks that the JUnit report holds every collected test, so a suite that silently stops running part of itself fails.
- **Burn-in:** `make burn-in` runs the E2E suite 10 times, and one failure fails the job. Nothing is retried: a flaky test should fail here, not be rerun into green.
- **Gates:** every test must pass, so P0 is 100% and P1 is held to 100%, stricter than the ≥95% in the design. The report job fails if any job failed or was cancelled.
- **Artifacts:** `test-results-chromium` and `test-results-webkit` are always uploaded: JUnit, plus a trace, screenshot and video for failed E2E tests. `burn-in-failures` is uploaded on failure. Each is kept 30 days and linked from the run summary.
- **Caching:** uv's cache keyed on `uv.lock`, and Playwright browsers in `~/.cache/ms-playwright`.
- **Secrets:** none. Tests never reach real externals.
- **Notifications:** GitHub's default emails for failed runs on your own pushes and PRs.

Run the same thing locally with `make ci-local` (lint, `test-ci`, then 3 burn-in iterations), or `make burn-in BURN_IN=20` to hunt a flake.

Not in CI yet: the built-wheel smoke test and the release upload belong to entry 8 (R-04), along with an optional `macos-14` smoke job.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Executable doesn't exist at …/ms-playwright/…` | The browsers aren't installed for this Playwright version. Run `make browsers` |
| `Page.goto: Cannot navigate to invalid URL` | `base_url` isn't reaching the context. Keep the `base_url` override in a conftest: a fixture in `support/fixtures/` loses to pytest-playwright's own plugin |
| E2E gets `403 forbidden_origin` (from entry 4 on) | The live server's port isn't on the allow-list. Change `live_server_settings`; don't hand-build the app with a different port |
| `live server did not start` | Startup raised. Run `uv run pytest tests/e2e -x -s` to see the traceback |
| `'foo' not found in markers configuration option` | Register the marker in `pyproject.toml` (`--strict-markers`) |
| A test passes alone but fails in the suite | Leaked env or state. Build settings with `settings_factory`, and patch with `monkeypatch` only |

## References

TEA knowledge fragments used in this setup: `fixture-architecture`, `data-factories`, `test-quality`, `network-first`, `playwright-config`.
See `_bmad-output/test-artifacts/test-design/test-design-epic-1.md` for the risk-driven test plan.

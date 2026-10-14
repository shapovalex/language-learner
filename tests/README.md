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
| `make test-webkit` | E2E on Chromium and WebKit (covered by release.yml's tag run; iPhone/iPad Safari proxy) |
| `make test-cov` | Fast suite with branch coverage of `language_lab` |
| `uv run pytest -m p0` | One priority |
| `uv run pytest tests/e2e --headed --slowmo 300` | Watch the browser |
| `PWDEBUG=1 uv run pytest tests/e2e -k shell` | Playwright Inspector, step through |
| `uv run pytest tests/e2e --base-url http://127.0.0.1:8787` | E2E against an app you started yourself |
| `uv run pytest --live-anki -m live_anki` | Opt-in tests against a real Anki (dev Prefix) |
| `uv run pytest tests/integration --wheel dist/<wheel>` | Smoke a wheel you built instead of building a fresh one (release.yml does this) |

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
  fixtures/            recorded inputs from real externals (Tailscale status and Serve headers, AnkiConnect exchanges under anki/; see its README)
  support/
    live_server.py     run_live_server(): uvicorn in a thread on a pre-bound socket
    app_env.py         config_values() factory, write_dotenv(), dotenv_keys(), isolated_environ()
    network.py         stub_api_error() (AD-15 envelope, returned), HeldRoute (hold a request, see the loading state, then fulfill_json()), record_requests(), record_resources() (with resource type)
    design_tokens.py   DESIGN.md front matter -> expected --color/--space/--radius/--font-* properties; css_custom_properties()
    shell.py           parse_shell() (viewport meta, stylesheet links), fetch_stylesheets() through a TestClient, following @import
    dom.py             append_to_body() / prepend_to_body() for test-only markup, computed_style(), px(), settle_fonts()
    navigation.py      the six DESTINATIONS, nav locators (main_nav, language_nav, menu_button, menu_sheet), go_by_nav() per width
    keys.py            tab() / shift_tab() per browser (WebKit's Tab skips links)
    unsaved.py         the router's setDirty / confirmLeave / navigate from the page, the alert's locators, LEAVE_PATHS per width (R-03)
    probes.py          add_probe_routes(): test-only /api routes for validation and crash paths; sentinel(), error_envelope()
    startup.py         run_language_lab(): main() in a subprocess, killed if it keeps running
    release.py         pyproject_version(), run_tag_check() (the release guard), build_wheel(), run_released_app() (uvx --from <wheel>), non_loopback_address()
    anki_connect.py    anki_fixture() (tests/fixtures/anki/), AnkiConnectReplay (httpx MockTransport: replies per action or a failure, records .sent), the failure kinds, run_stub_ankiconnect() (loopback server for the recorder)
    aio.py             settle() / settled(): run a coroutine, get its result or its exception to assert on
    ports.py           public_methods(): a port's, fake's or adapter's public functions with signatures (AD-1)
    recorder.py        run_recorder_status(), run_recorder() (serve), run_recorder_anki()
    hosts.py           app_client() (allowed Host + same-origin Origin, AD-16), local_hosts(), TAILNET_HOST, FOREIGN_HOST, recorded Tailscale inputs
    viewports.py       PHONE 390 / TABLET 820 / DESKTOP 1280
    fixtures/          pytest fixtures, one concern per module
```

Helpers in `support/` are plain functions, and `support/fixtures/` wraps them as fixtures.
Write the function first, then the fixture.

### Fixtures

| Fixture | Scope | Purpose |
| --- | --- | --- |
| `settings_factory` | function | `make(env={...}, **overrides) -> Settings` with every app variable (`LANGUAGE_LAB_*`, `ANKI_*`, `AZURE_SPEECH_*`, `OPENROUTER_*`) cleared and HOME/cwd in `tmp_path`. Cleaned up by monkeypatch |
| `config_files` | function | `.home` (`~/.config/language-lab/.env`) and `.repo` (`./.env`) inside the isolated HOME/cwd, with `write_home(values)` / `write_repo(values)` |
| `settings_loader` | function | `load(env={...}) -> Settings` through `load_settings()`, the startup path, in the same isolation |
| `log_capture` | function | `.records` / `.messages` from `language_lab.*` loggers at INFO+, `.request_lines` (the AD-15 per-request JSON lines, parsed), `.all_text` (every logger, for leak checks). Use `capsys` for stdout |
| `probe_client` | function | `TestClient` over `create_app(...)` plus the probe routes, with `raise_server_exceptions=False` so a crash comes back as its 500 response |
| `live_server` | session | The real `create_app(settings)` on a free port. `settings.port` is the served port, so the AD-16 allow-list accepts it (R-14) |
| `live_server_settings` | session | Override it to change what the live server runs with |
| `release_wheel` | session | The wheel from `--wheel PATH`, else a fresh `uv build --wheel` into a temp dir |
| `released_app` | module | `release_wheel` under `uvx --from <wheel> language-lab`, temp HOME whose `~/.config/language-lab/.env` is the only config (port and tailnet host set there only); `.app.url`, `.app.output`, `.port`, `.config` |
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
- **Allowed hosts.** Build every `TestClient` with `app_client(app, settings)`. A bare `TestClient` sends `Host: testserver`, which the AD-16 allow-list rejects with 403.
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

GitHub Actions. `.github/workflows/test.yml` covers pushes to `main` and PRs. It follows the Epic 1 test design: one job, Chromium, and no Node.
Tag runs are `.github/workflows/release.yml` only (see Release below).

| Trigger | Jobs |
| --- | --- |
| Push to `main` | lint → test (Chromium) → report |
| Pull request to `main` | lint → test → burn-in (E2E ×10) → report |

- **Lint:** `ruff check` and `ruff format --check`. Findings show as PR annotations.
- **Test:** `make test-ci`. Afterwards the job checks that the JUnit report holds every collected test, so a suite that silently stops running part of itself fails.
- **Burn-in:** `make burn-in` runs the E2E suite 10 times, and one failure fails the job. Nothing is retried: a flaky test should fail here, not be rerun into green.
- **Gates:** every test must pass, so P0 is 100% and P1 is held to 100%, stricter than the ≥95% in the design. The report job fails if any job failed or was cancelled.
- **Artifacts:** `test-results-chromium` is always uploaded: JUnit, plus a trace, screenshot and video for failed E2E tests. `burn-in-failures` is uploaded on failure. Each is kept 30 days and linked from the run summary.
- **Caching:** uv's cache keyed on `uv.lock`, and Playwright browsers in `~/.cache/ms-playwright`.
- **Secrets:** none. Tests never reach real externals.
- **Notifications:** GitHub's default emails for failed runs on your own pushes and PRs.

Run the same thing locally with `make ci-local` (lint, `test-ci`, then 3 burn-in iterations), or `make burn-in BURN_IN=20` to hunt a flake.

### Release

`.github/workflows/release.yml` runs on a `vX.Y.Z` tag: the tag guard (`scripts/check_release_tag.py`, tag must equal `v<pyproject version>`) → ruff → `uv build --wheel` → pytest on Chromium + WebKit (R-09) with `--wheel dist/<wheel>`, so the built-wheel smoke (R-04) runs on the exact file released → a separate publish job (the only one with `contents: write`) attaches the wheel to the GitHub release.
Artifacts: `wheel` and `test-results-release`, each kept 30 days.

Not in CI yet: an optional `macos-14` smoke job.

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

---
runScope: 'story'
runKey: 'story-1-4'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-11'
storyId: '1.4'
storyKey: '1-4'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml (entry 4)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-1-4.md'
generatedTestFiles:
  - 'tests/api/test_host_origin_allow_list.py'
  - 'tests/unit/test_tailscale_discovery.py'
  - 'tests/integration/test_startup_tailnet.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-15, AD-16, Structural Seed)'
  - '_bmad-output/test-artifacts/test-design/test-design-epic-1.md'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-1-5.md (conventions)'
  - 'pyproject.toml'
  - 'src/language_lab/app.py'
  - 'src/language_lab/settings.py'
  - 'src/language_lab/domain/errors.py'
  - 'tests/conftest.py'
  - 'tests/README.md'
  - 'tests/e2e/conftest.py'
  - 'tests/e2e/test_shell.py'
  - 'tests/support/fixtures/api.py'
  - 'tests/support/fixtures/settings.py'
  - 'tests/support/fixtures/logs.py'
  - 'tests/support/fixtures/live_server.py'
  - 'tests/support/live_server.py'
  - 'tests/support/app_env.py'
  - 'tests/support/probes.py'
  - 'tests/support/startup.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'The allow-list holds 127.0.0.1:<port>, localhost:<port> and the tailnet host; a request with a foreign Host gets 403' }
  - { id: 'AC-2', idSource: 'generated', text: 'The tailnet host comes from LANGUAGE_LAB_PUBLIC_HOST when it is set' }
  - { id: 'AC-3', idSource: 'generated', text: 'Otherwise the tailnet host is discovered at startup from Tailscale; discovery parses a recorded Tailscale status fixture' }
  - { id: 'AC-4', idSource: 'generated', text: 'Discovery is non-fatal when Tailscale is absent or fails' }
  - { id: 'AC-5', idSource: 'generated', text: 'The effective host takes X-Forwarded-Host into account (amended by Q1: Host and X-Forwarded-Host must both be allowed); the tailnet host via X-Forwarded-Host passes' }
  - { id: 'AC-6', idSource: 'generated', text: 'Every non-GET /api request needs an Origin whose host[:port] is on the allow-list, compared without scheme; a missing or foreign Origin gets 403' }
  - { id: 'AC-7', idSource: 'generated', text: 'A rejection is 403 forbidden_origin in the envelope, with one log line' }
  - { id: 'AC-8', idSource: 'generated', text: 'Startup prints the Tailscale URL when it is known' }
  - { id: 'AC-9', idSource: 'generated', text: 'The Playwright live-server fixture from entry 5 keeps passing by putting its port in settings' }
---

# ATDD Checklist: Story 1.4, Host and Origin allow-list with tailnet discovery

## Run context

- **Story source:** epic-platform-baseline `tickets.toml` entry 4. There's no story file, so the criteria come from the ticket's description and `verify`, in source order, with generated ids AC-1 to AC-9.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). Every leaf runs at unit, integration or API level. No browser leaf is needed, and AC-9 is covered by the existing E2E smoke test.
- **Test design:** `test-design-epic-1.md`. P0 rows: allow-list and foreign Host, spoofed `X-Forwarded-Host` (R-01), Origin on non-GET /api, one log line on a 403. P1 rows: Tailscale discovery parse and failures (R-10), the live-server fixture smoke (R-14). P2 row: startup prints the Tailscale URL. High risk linked: **R-01** (score 6).
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node. No Pact artifacts exist, so contract testing isn't relevant.
- **Affected components:** `src/language_lab/app.py` (allow-list middleware, `with_tailnet_host`, `main()`), `src/language_lab/adapters/tailscale.py` (new), `src/language_lab/adapters/__init__.py` (new).
- **Execution:** sequential, one worker for every level. The suite is small and Python-only.

### Decisions taken with the user (2026-10-11)

| Question | Decision |
| --- | --- |
| Q1 / R-01: the `X-Forwarded-Host` trust rule | **Both must pass.** `Host` must be on the allow-list, and `X-Forwarded-Host`, when present, must be on it too. A DNS-rebinding page has a foreign `Host`, so no XFH it sets can rescue it. The rule holds whether Tailscale Serve keeps the public `Host` or rewrites it to loopback. No Fetch Metadata check on GET. Recorded as an amendment to AD-16. |
| Q2 / R-10: the discovery timeout | **2 seconds** for `tailscale status --json`. Recorded in AD-16. |
| R-05: Tailscale fixtures | **Synthesized now** from Tailscale's documented formats, and marked as synthetic in `tests/fixtures/README.md`. Replace them with real Mac Mini recordings before entry 10. |

### Defaults taken without asking (follow existing conventions)

- **A foreign Host is rejected on every path**, not only `/api` (AD-16: "every request"). The body is the envelope on `/api` and plain text elsewhere, matching how 404 and 500 already split. The tests assert the 403 status on the shell and static paths, and the envelope only on `/api`.
- **The allow-list check runs inside `RequestLogMiddleware`**, so a 403 gets a request id and exactly one log line (test design: "catches middleware-order bugs").

## Generation mode (step 2)

AI generation. The stack is `backend`, so there's no recording. The behaviour sits at the ASGI boundary and in a subprocess adapter, with no UI to record.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | API | P0 | `GET` with `Host: evil.example:<port>` on `/api/health`, `/captures` and a static file | status is 403 |
| AC-2 | Unit | P1 | `with_tailnet_host(settings, discover)` with `LANGUAGE_LAB_PUBLIC_HOST` set | `.public_host` is the configured value |
| AC-3 | Unit | P1 | `discover_tailnet_host(run=fake)` over the recorded status JSON | returns `mac-mini.tail1234.ts.net` |
| AC-4 | Unit | P1 | The fake runner raises or returns a failure (7 cases) | returns `None` and doesn't raise |
| AC-5 | API | P0 | A foreign Host with the tailnet XFH (rebinding), and a loopback Host with a foreign XFH | status is 403 |
| AC-6 | API | P0 | `POST` to the probe validate route with a missing, foreign or `null` Origin | status is 403 |
| AC-7 | API | P0 | A foreign-host GET and a missing-Origin POST | envelope `code` is `forbidden_origin` |
| AC-8 | Integration | P2 | `main()` in-process with `uvicorn.run` replaced and `LANGUAGE_LAB_PUBLIC_HOST` in the `.env` | stdout contains `https://mac-mini.tail1234.ts.net/` |
| AC-9 | E2E (existing) | smoke | `test_live_server_answers_on_its_settings_port` | already green, so no red leaf |

- **AC-1 vs AC-7.** AC-1 owns the status code, and AC-7 owns the envelope and log line. AC-7's first assertion is the `code`, so the two leaves don't fail on the same thing first.
- **AC-5 is the R-01 test.** The rebinding case is the one the test design asked to "pin explicitly". The legitimate case (the recorded Serve headers) is a secondary assertion in the same leaf.
- **AC-6's `missing` case posts a valid body,** so today it returns 200 and only an Origin check can turn it into 403. The scheme-free comparison (`https://127.0.0.1:<port>` against an http app) and the Serve fixture's POST are secondary assertions.
- **AC-2 to AC-4 import the adapter inside each test,** so the file collects before `language_lab.adapters.tailscale` exists. Their red failure is `ModuleNotFoundError` or `AttributeError`, which is the honest red for a new module. Move the import to the top once the module exists.
- **AC-8 uses `LANGUAGE_LAB_PUBLIC_HOST`, not discovery,** so the leaf can't depend on a module that doesn't exist yet, and no real `tailscale` runs (AC-2 says discovery isn't called when the setting is present).
- **AC-9 has no red leaf.** It can't fail before implementation. The risk is that existing `TestClient` tests start getting 403, and this run fixed that in support code (see below). Green feasibility was proven against a stand-in.

## TDD Red Phase (Current)

✅ Red-phase scaffolds generated: **8 leaves (one per criterion except AC-9), 20 parametrized cases, all skipped with `RED_PHASE`**. Each case was run with the skip stripped and failed for the expected reason.

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/api/test_host_origin_allow_list.py` | API | 4 (10): AC-1, AC-5, AC-6, AC-7 |
| `tests/unit/test_tailscale_discovery.py` | Unit | 3 (9): AC-2, AC-3, AC-4 |
| `tests/integration/test_startup_tailnet.py` | Integration | 1 (1): AC-8 |

Red-phase failure reasons, observed with the skip markers stripped:

- AC-1 (3 paths): `assert 200 == 403`
- AC-2: `AttributeError: module 'language_lab.app' has no attribute 'with_tailnet_host'`
- AC-3, AC-4 (8 cases): `ModuleNotFoundError: No module named 'language_lab.adapters'`
- AC-5 (2 cases): `assert 200 == 403`
- AC-6 (3 cases): `assert 200 == 403`
- AC-7 (2 cases): `assert None == 'forbidden_origin'`
- AC-8: `assert 'https://mac-mini.tail1234.ts.net/' in 'LanguageLab running at http://127.0.0.1:8787/\n'`

**Green feasibility, checked and reverted.** A throwaway `adapters/tailscale.py`, an `AllowListMiddleware` inside `RequestLogMiddleware`, `with_tailnet_host()` and one print in `main()` turned all 20 cases green. The whole suite then passed, E2E included: **115 passed**. The first stand-in run broke 5 existing tests that POST without an `Origin`. That led to the `same_origin` default in `app_client()` below. The stand-in was removed, and `src/` is unchanged.

With the scaffolds skipped, the suite stays green: **95 passed, 20 skipped**. `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P0 | `test_foreign_host_is_rejected_on_every_path[path]` | 403 for `evil.example:<port>`; then `127.0.0.1:<port>`, `localhost:<port>` and the tailnet host get 200, and `127.0.0.1:<port+1>` gets 403 |
| AC-2 | P1 | `test_public_host_setting_wins_over_discovery` | `with_tailnet_host(...).public_host` equals the configured host; then discovery wasn't called; then with no setting, the discovered host is used |
| AC-3 | P1 | `test_discovery_reads_the_tailnet_name_from_tailscale_status` | returns `mac-mini.tail1234.ts.net` (trailing dot stripped); then the runner ran `… status --json` once |
| AC-4 | P1 | `test_discovery_failure_yields_no_tailnet_host[case]` | returns `None` for a missing binary, a permission error, a timeout, a non-zero exit, unparseable output, `BackendState: NeedsLogin` and no `Self.DNSName`; then the runner got `timeout=2.0` |
| AC-5 | P0 | `test_forwarded_host_can_neither_rescue_nor_spoof[case]` | 403 for a rebinding Host with the tailnet XFH, and for a loopback Host with a foreign XFH; then the recorded Serve headers get 200 |
| AC-6 | P0 | `test_write_without_an_allowed_origin_is_rejected[case]` | 403 for a missing, foreign or `null` Origin; then `https://127.0.0.1:<port>` and the Serve headers pass (the scheme isn't compared) |
| AC-7 | P0 | `test_rejection_is_the_forbidden_origin_envelope_with_one_log_line[case]` | envelope `code` is `forbidden_origin`; then status 403, the fixed message, exactly one log line `(403, forbidden_origin)` with the envelope's request id, and no header value in the log |
| AC-8 | P2 | `test_startup_prints_the_tailscale_url_when_known` | stdout has `https://<tailnet host>/`; then `uvicorn.run` was called once |
| AC-9 | smoke | `test_live_server_answers_on_its_settings_port` (existing, green) | already met: the live server's port comes from settings (R-14), so no red leaf |

## Implementation contract the tests encode

- **`language_lab/adapters/tailscale.py`** (new, plus `adapters/__init__.py`):
  - `discover_tailnet_host(run=None) -> str | None`. With no `run` it uses `subprocess.run`. It calls `run([<tailscale binary>, "status", "--json"], …, timeout=2.0)`, reads `stdout` as text, and returns `Self.DNSName` without the trailing dot.
  - It returns `None` unless the exit code is 0, the JSON parses, `BackendState` is `"Running"` and `DNSName` is non-empty.
  - It never raises for `OSError` (missing binary, permission), `subprocess.TimeoutExpired` or bad JSON.
  - The binary path is yours to choose (`tailscale` on PATH, or the macOS app bundle's CLI). Only `args[-2:]` is asserted.
- **`language_lab.app.with_tailnet_host(settings, discover) -> Settings`**. If `settings.public_host` is set, it returns it unchanged and doesn't call `discover`. Otherwise it returns a copy with `public_host=discover()`. `main()` calls it with `tailscale.discover_tailnet_host` (through the module attribute, so a later test can monkeypatch it), after `load_settings()` and before `create_app`.
- **The allow-list** comes from settings alone: `{f"127.0.0.1:{port}", f"localhost:{port}", public_host}` (the last only when set). That keeps `create_app(settings)`'s signature, and the live server's port reaches it through settings (R-14). The tailnet entry has no port: Serve is on 443, and browsers omit default ports.
- **The middleware**, in order, on every HTTP request:
  1. `Host` must be in the allow-list. If `X-Forwarded-Host` is present, it must be in the allow-list too.
  2. For a non-GET request under `/api`, `Origin` must be present, and its `host[:port]` (the scheme stripped) must be in the allow-list. `null` is not allowed.
  3. On failure: 403. On `/api` the body is `error_envelope(FORBIDDEN_ORIGIN, request_id)`. Set `state["error_code"] = "forbidden_origin"`, so the AD-15 log line carries it. Elsewhere, a plain-text 403.
  - It must be added so that it runs **inside** `RequestLogMiddleware`. In Starlette that means `add_middleware(AllowList…)` before `add_middleware(RequestLogMiddleware)`, since the last one added is outermost.
- **`main()`** prints a line containing `https://<public_host>/` after the local URL line, whenever `public_host` is known (configured or discovered).

## Fixture and support changes (made in this run)

- `tests/fixtures/tailscale-status.json` (new, **synthetic**): `tailscale status --json` with `BackendState: Running` and `Self.DNSName: mac-mini.tail1234.ts.net.`
- `tests/fixtures/tailscale-serve-headers.json` (new, **synthetic**): what Serve forwards for a tailnet browser POST. `Host` and `X-Forwarded-Host` are both the tailnet name, and `Origin` is `https://<tailnet>`.
- `tests/fixtures/README.md` (new): marks both as synthetic and explains how to record the real ones.
- `tests/support/hosts.py` (new): `TAILNET_HOST`, `FOREIGN_HOST`, `DISCOVERY_TIMEOUT_S`, `local_hosts()`, `local_url()`, `app_client()`, `tailscale_status_text()`, `tailscale_status(**overrides)`, `serve_headers()`.
- **Every existing `TestClient` now goes through `app_client()`:** `tests/support/fixtures/api.py` (`probe_client`), `tests/api/test_app.py` (2 sites), `tests/api/test_request_log.py` (1), `tests/api/test_shell_styles.py` (1). `app_client()` sends `Host: 127.0.0.1:<port>`, and by default the same-origin `Origin` a browser sends. Without that, every API test would get 403 once the middleware lands (proven with the stand-in). The allow-list tests pass `same_origin=False`.
- `tests/README.md`: the layout lists `hosts.py` and `fixtures/`, and a rule says to build every `TestClient` with `app_client()`.
- `architecture-languagelab.md` AD-16: the Checks bullet now carries the Q1 amendment, and a new Discovery bullet carries the Q2 timeout.

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` line.
2. Run it, for example `uv run pytest tests/unit/test_tailscale_discovery.py` or `uv run pytest tests/api/test_host_origin_allow_list.py -k rebinding`.
3. Watch it fail for the reason listed above, implement, and watch it pass.
4. If it fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes: no `RED_PHASE` markers remain in the three files, and `make test` and `make lint` pass. Then remove the `RED_PHASE` definitions and move the adapter import in `test_tailscale_discovery.py` to the top of the file.

Suggested order: AC-3 → AC-4 → AC-2 → AC-1 → AC-5 → AC-6 → AC-7 → AC-8.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-4 | Startup continues when discovery returns `None`: `main()` reaches `uvicorn.run` and prints no `https://` line (R-10, "non-fatal" at the startup level) | P1 |
| AC-8 | The discovered case: no `LANGUAGE_LAB_PUBLIC_HOST`, `tailscale.discover_tailnet_host` monkeypatched to a host, and the URL printed | P2 |
| AC-5 | The loopback-rewrite variant: `Host: 127.0.0.1:<port>` + tailnet XFH passes (if the real recording shows Serve rewrites Host) | P1 |
| AC-6 | `PUT`, `PATCH` and `DELETE` without an Origin also get 403 (parametrize the method once a product route exists) | P1 |
| AC-6 | GET /api with a foreign Origin but an allowed Host still passes (AD-16 checks Origin on non-GET only) | P2 |
| AC-1 | Host compared case-insensitively (`LOCALHOST:<port>`, `Mac-Mini.tail1234.ts.net`) | P3 |
| AC-1 | `<tailnet>:443` (an explicit default port) is treated like `<tailnet>` | P3 |
| AC-1 | A shell or static 403 is plain text, not the envelope (R-07 convention) | P2 |
| AC-7 | A 403 envelope carries no header value at all: sentinel Host and Origin values are absent from the body | P1 |
| AC-9 | Re-run the E2E suite under WebKit after the middleware lands (`make test-webkit`) | P1 |
| R-05 | Replace both synthetic Tailscale fixtures with Mac Mini recordings, then re-run this file | P0 (before entry 10) |

## Open items

- **The Tailscale fixtures are synthetic.** The Q1 rule makes the tests pass either way, but the fixtures must be replaced with real recordings before entry 10 (R-05). See `tests/fixtures/README.md`.
- **The test design's entry criteria** ("Q1 decided and recorded in the architecture spine", "Tailscale Serve headers recorded") are met for Q1 by the AD-16 amendment. The headers are covered only provisionally, by the synthetic fixture.
- **AC-9 has no red leaf.** It's a "keeps passing" criterion. The run proved it against a stand-in, after moving every `TestClient` onto `app_client()`.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (ticket description and verify), pytest and pytest-playwright are configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-9), and no supplied ids collide
- [x] Every new leaf maps to exactly one AC (docstring `AC-n:`). Every AC except AC-9 (a "keeps passing" criterion, recorded) has exactly one red leaf
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one, and each red failure was observed for the expected reason
- [x] No unimplemented setup response is parsed before the criterion assertion. The only setup calls are fixture loads and `.env` writes, which exist today.
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `bmad-build` on entry 4
- [x] No CLI browser sessions were opened. The red-check plugin lives in the session scratchpad, not the repo.

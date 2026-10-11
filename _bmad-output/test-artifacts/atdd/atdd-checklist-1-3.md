---
runScope: 'story'
runKey: 'story-1-3'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-11'
storyId: '1.3'
storyKey: '1-3'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml (entry 3)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-1-3.md'
generatedTestFiles:
  - 'tests/unit/test_errors.py'
  - 'tests/api/test_error_envelope.py'
  - 'tests/api/test_request_log.py'
  - 'tests/e2e/test_api_client.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md'
  - '_bmad-output/test-artifacts/test-design/test-design-epic-1.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-13, AD-15)'
  - 'pyproject.toml'
  - 'src/language_lab/app.py'
  - 'src/language_lab/static/api.js'
  - 'tests/conftest.py'
  - 'tests/README.md'
  - 'tests/api/test_app.py'
  - 'tests/e2e/conftest.py'
  - 'tests/e2e/test_shell.py'
  - 'tests/support/fixtures/logs.py'
  - 'tests/support/network.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'domain/errors.py defines the twelve-code enum from AD-15' }
  - { id: 'AC-2', idSource: 'generated', text: 'Every /api failure (validation error, unknown route, unhandled exception) returns the envelope {error:{code,message,requestId}}' }
  - { id: 'AC-3', idSource: 'generated', text: 'The envelope never echoes input values' }
  - { id: 'AC-4', idSource: 'generated', text: 'Request-id middleware logs exactly one line per request with request id, method, route template, status, code and duration' }
  - { id: 'AC-5', idSource: 'generated', text: 'The request log line carries no query string, body or field values' }
  - { id: 'AC-6', idSource: 'generated', text: 'The uvicorn access log is off' }
  - { id: 'AC-7', idSource: 'generated', text: 'api.js parses the envelope into a typed error' }
---

# ATDD Checklist: Story 1.3, Error envelope and content-free request log

## Run context

- **Story source:** epic-platform-baseline `tickets.toml` entry 3. There is no story file, so the criteria come from the ticket's description and `verify` clauses in source order, with generated ids AC-1 to AC-7.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). AC-7 is client code, which the epic tests with pytest-playwright (dev-only, NFR-11).
- **Test design:** `test-design-epic-1.md`. Risks: R-02 (content in logs or the envelope, score 6) and R-07 (route boundary).
- **Execution:** sequential. There was a single worker for both levels; the suite is small and Python-only.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node.
- **Affected components:** `src/language_lab/domain/errors.py` (new), `src/language_lab/app.py` (handlers, middleware, `uvicorn.run(access_log=False)`), `src/language_lab/static/api.js`.

### Decisions taken with the user (2026-10-11)

| Question | Decision |
| --- | --- |
| Request log format | **One JSON object per line** on logger `language_lab.request`: `{"requestId","method","route","status","code","durationMs"}`. `code` is `null` on success. |
| Status for `validation_failed` | **422** (FastAPI default). Only the body becomes the envelope. |
| api.js typed error | **`export class ApiError extends Error`** with `status`, `code`, `message`, `requestId` and `details`. A non-envelope failure becomes `code: "internal_error"`, `requestId: null`. |
| Reaching the validation and crash paths | **Test-only probe routes** (`tests/support/probes.py`) inserted ahead of the shell catch-all. Nothing test-only ships in `src`. |

## Generation mode (step 2)

AI generation. The stack is `backend`, so there's no recording. AC-7's browser check uses pytest-playwright's `page.evaluate` against the served `api.js`, with no selectors to record.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion | Risk |
| --- | --- | --- | --- | --- | --- |
| AC-1 | Unit | P1 | Import `ErrorCode` from `language_lab.domain.errors` | its set of values == the twelve AD-15 codes | R-07 |
| AC-2 | API | P0 | Validation error, unknown `/api` path, raised exception (one leaf, parametrized ×3) | `error.code` == the expected code | R-02, R-07 |
| AC-3 | API | P0 | 422 with one sentinel in path, query, body and a header | the sentinel isn't in the response body | R-02 |
| AC-4 | API | P0 | A raised exception on a templated route | exactly one `language_lab.request` line | R-02 |
| AC-5 | API | P0 | 422 with a sentinel in path, query, body and a header | the line's `route` is the template, not the raw path | R-02 |
| AC-6 | API | P1 | `main()` hands `access_log=False` to `uvicorn.run` | `kwargs["access_log"] is False` | R-02 |
| AC-7 | E2E | P1 | `/api/health` stubbed to a 503 envelope, then `request()` called | the thrown error is an `ApiError` | R-07 |

- There are no duplicate levels. AC-2 and AC-3 assert the response, and AC-4 and AC-5 assert the log, against the same probes.
- AC-3's red leaf takes the validation path, the only path that echoes input today. The other paths go to the green-phase backlog.
- AC-5's negative claim (no sentinel) would pass vacuously with no line logged. Its first assertion is therefore the positive one, the route template.

## TDD Red Phase (Current)

✅ Red-phase scaffolds generated: **7 leaves (9 collected items, AC-2 parametrized ×3), all `@pytest.mark.skip`**. Each one was checked to fail for the expected reason when un-skipped.

| File | Level | Leaves |
| --- | --- | --- |
| `tests/unit/test_errors.py` | Unit | 1 (AC-1) |
| `tests/api/test_error_envelope.py` | API | 2 (AC-2, AC-3) |
| `tests/api/test_request_log.py` | API | 3 (AC-4, AC-5, AC-6) |
| `tests/e2e/test_api_client.py` | E2E | 1 (AC-7) |

Red-phase failure reasons, observed with the skip markers stripped:

- AC-1: `ModuleNotFoundError: No module named 'language_lab.domain'`
- AC-2: `assert None == 'validation_failed'` / `'not_found'` / `'internal_error'`. The bodies are FastAPI's `{"detail": ...}` and Starlette's plain-text 500.
- AC-3: `assert 'sentinel-…' not in '{"detail":[…sentinel…]}'`. FastAPI echoes `input` today.
- AC-4: `assert 0 == 1`. No request line is logged yet.
- AC-5: `assert [] == ['/api/_probe/validate/{item_id}']`
- AC-6: `assert None is False`. `uvicorn.run` gets only `host` and `port`.
- AC-7: `assert False is True`. `api.js` throws a plain `Error`, and there's no `ApiError` export.

With the scaffolds skipped, the fast suite stays green (60 passed, 8 skipped) and so does E2E (6 passed, 1 skipped). `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion | Risk |
| --- | --- | --- | --- | --- |
| AC-1 | P1 | `test_error_code_enum_holds_the_twelve_ad15_codes` | `{c.value for c in ErrorCode} == AD15_CODES` | R-07 |
| AC-2 | P0 | `test_api_failure_returns_envelope[validation\|unknown-route\|unhandled]` | `envelope.get("code") == code`, then status, `{"error"}` only, keys ⊆ AD-15, non-empty `message` and `requestId` | R-02, R-07 |
| AC-3 | P0 | `test_validation_envelope_does_not_echo_input` | the sentinel isn't in `response.text` | R-02 |
| AC-4 | P0 | `test_one_line_per_request_with_ad15_fields` | `len(request_lines) == 1`, then exact keys, `requestId` == envelope's, `GET` / `BOOM_ROUTE` / 500 / `internal_error`, `durationMs ≥ 0` | R-02 |
| AC-5 | P0 | `test_log_line_carries_no_request_content` | `routes == [VALIDATE_ROUTE]`, then the sentinel isn't in any logger's output or in stdout/stderr | R-02 |
| AC-6 | P1 | `test_main_turns_off_uvicorn_access_log` | `calls[0].get("access_log") is False` | R-02 |
| AC-7 | P1 | `test_request_throws_api_error_parsed_from_envelope` | `thrown["isApiError"] is True`, then `status`, `code`, `message` and `requestId` match the stub | R-07 |

## Implementation contract the tests encode

- **`src/language_lab/domain/errors.py`** (plus `domain/__init__.py`): `class ErrorCode(StrEnum)` with exactly the twelve AD-15 values.
- **Envelope:** every non-2xx `/api` response body is exactly `{"error": {"code", "message", "requestId", "details"?}}`. Validation → 422 `validation_failed`, unknown `/api` → 404 `not_found` (the catch-all's `HTTPException(404)` maps here), unhandled → 500 `internal_error`. `message` is a fixed, human string per code, never built from input. Leave out `details`, or fill it only with field locations (`["body", "count"]`), never values.
- **Request log:** logger `language_lab.request`, one INFO record per request, `getMessage()` is one JSON object with keys exactly `requestId`, `method`, `route`, `status`, `code`, `durationMs`. `route` is the matched route's `path` template (`request.scope["route"].path`). `code` is `null` on success. The envelope's `requestId` and the line's are the same value.
- **Crash path (watch out):** Starlette runs an `Exception` handler in `ServerErrorMiddleware`, *outside* user middleware, and then re-raises. Uvicorn then logs the traceback, which carries the input (here, the sentinel in `item_id`). Catch unhandled exceptions inside the request middleware: build the 500 envelope there, log the one line, and don't re-raise. The AC-4 test runs exactly this path.
- **`main()`:** `uvicorn.run(..., access_log=False)`. It also needs a stdout handler for `language_lab` (NFR-9). **Update `test_main_prints_url_and_binds_settings`** in `tests/api/test_app.py`: it asserts the exact kwargs `{"host", "port"}`.
- **`api.js`:** `export class ApiError extends Error` with `status`, `code`, `message`, `requestId` and `details`. `request()` throws it on any non-OK response. A body that isn't an envelope becomes `code: "internal_error"`, `requestId: null`. `main.js` keeps its catch, so `test_shows_message_when_api_fails` stays green.
- **Probe routes stay in tests.** `tests/support/probes.py` inserts them at the front of `app.router.routes`, so the handlers and middleware must be installed by `create_app` and must apply to routes added later. App-level handlers and middleware do.

## Fixture and support changes (made in this run)

- `tests/support/probes.py` (new): `add_probe_routes(app)` (`POST /api/_probe/validate/{item_id}` with typed path, query and body; `GET /api/_probe/boom/{item_id}` raising with `item_id` in the message), plus `sentinel()` and `error_envelope(response)`.
- `tests/support/fixtures/api.py` (new): the `probe_client` fixture, registered in `tests/conftest.py`.
- `tests/support/fixtures/logs.py`: `LogCapture.request_lines` (parsed JSON lines from `language_lab.request`) and `LogCapture.all_text` (every logger).
- `tests/support/network.py`: `stub_api_error` now returns the envelope it serves.
- `tests/README.md`: the layout and fixture tables are updated.

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` line.
2. Run it, for example `uv run pytest tests/api/test_error_envelope.py`, or `uv run pytest tests/e2e/test_api_client.py` for AC-7.
3. Watch it fail for the reason listed above, implement, and watch it pass.
4. If it fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes: no `RED_PHASE` markers remain in the four files, and `make test` and `make lint` pass.

Suggested order: AC-1 → AC-2 → AC-3 → AC-4 → AC-5 → AC-6 → AC-7.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-2 | `HTTPException` raised from a route with other statuses (e.g. 405 on `POST /api/health`) maps to an envelope with a fitting code | P1 |
| AC-2 | A non-`/api` failure (e.g. a missing `/static/...` file) stays a plain 404, not the envelope and not the shell (R-07 boundary) | P2 |
| AC-3 | Sentinel absent from the response on the unknown-route path (sentinel in path and query) and the crash path (sentinel in `item_id`) | P0 |
| AC-3 | A malformed JSON body (`content=b"{"+sentinel`) gives `validation_failed` without echoing the body | P0 |
| AC-4 | A 2xx request (`GET /api/health`) logs `code: null`, `status: 200`, `route: "/api/health"` | P1 |
| AC-4 | Two requests → two lines with distinct `requestId`s | P1 |
| AC-4 | A shell GET (`/captures`) also logs one line, with `route: "/{path:path}"` | P2 |
| AC-5 | Sentinel absent from all logs and stderr on the crash path. This catches the traceback leak described above. | P0 |
| AC-5 | Sentinel absent on the unknown-route path; `route` is the catch-all template, not the raw path | P0 |
| AC-6 | Integration: run the real server in a subprocess, make one request, and see exactly one JSON line on stdout and no `"GET /api/health HTTP/1.1"` access line | P1 |
| AC-7 | A non-envelope failure (HTML 502 from a proxy) → `ApiError` with `code: "internal_error"`, `requestId: null` | P1 |
| AC-7 | A network failure (`route.abort()`): decide whether it's an `ApiError` too | P2 |
| Entry 4 | A 403 `forbidden_origin` also gets the envelope, a requestId and one log line (middleware order, test design row) | P0 (entry 4) |

## Open items

- `details` has no defined content yet. The tests only allow the key. Field locations without values seem safe, but the developer should confirm.
- Network failures in `api.js` (no response at all) aren't covered by the ticket. See the backlog.
- AC-2 is one leaf parametrized over the three failures named in the ticket's `verify`. That makes 9 collected items for 7 criteria.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (ticket verify), pytest and pytest-playwright are configured, and the dev env runs
- [x] Every criterion has a stable generated id, and no supplied ids collide
- [x] Every leaf maps to exactly one AC (docstring `AC-n:`), and every AC has exactly one red leaf
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one, and each red failure was observed for the expected reason
- [x] No unimplemented setup response is parsed before the criterion assertion (the probes are test code and opaque)
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `dev-story` on entry 3
- [x] No CLI browser sessions were opened. The temp red-check plugin lives in the session scratchpad, not the repo.

---
title: 'Error envelope and content-free request log'
type: 'feature'
ticket: '3'
created: '2026-10-11'
status: 'built'
baseline_revision: '03cb825a3c3931f689f1e617c4c3937e524e9fa7'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-1-3.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `/api` failures come back as FastAPI's `{"detail": ...}` (which echoes input on 422) or Starlette's plain-text 500, uvicorn's access log writes raw paths and query strings, and `api.js` throws a bare `Error`. AD-15 requires one envelope, one content-free log line per request, and a typed client error.

**Approach:** Add `domain/errors.py` with the twelve-code `ErrorCode` enum. In `app.py`, install a request-id ASGI middleware that logs one JSON line per request and turns any unhandled exception into the 500 envelope, plus exception handlers mapping validation and HTTP errors to the envelope. Turn off the uvicorn access log, and give `api.js` an `ApiError`. Make the ATDD scaffolds from 03cb825 pass.

## Boundaries & Constraints

**Always:**
- Implement the "Implementation contract the tests encode" in the ATDD checklist (`context`): envelope shape, status per path (422 / 404 / 500), logger `language_lab.request`, line keys exactly `requestId, method, route, status, code, durationMs`, `route` = the matched route's path template, `code` null on success, same `requestId` in envelope and line.
- `message` is a fixed string per code, never built from input, exception text, or a client-supplied header.
- Unhandled exceptions are caught inside the request middleware: build the 500 envelope there, log the one line, and do not re-raise, so no traceback carrying input reaches uvicorn or stderr.
- Handlers and middleware are installed by `create_app`, so they apply to routes added afterward (the test probes).
- `main()` calls `uvicorn.run(..., access_log=False)` and attaches one stdout handler to the `language_lab` logger (NFR-9), without duplicating it on a second call.
- Decision (2026-10-11): the server omits `details` in this story. `api.js` still reads it when present.
- `main.js` keeps its catch, so the existing shell failure message still shows.
- Remove every `RED_PHASE` marker in `tests/unit/test_errors.py`, `tests/api/test_error_envelope.py`, `tests/api/test_request_log.py`, `tests/e2e/test_api_client.py`. Don't weaken any first assertion.

**Never:**
- No new dependencies, and nothing test-only in `src`.
- No host/Origin allow-list or `forbidden_origin` emission (entry 4), no `docs/` pages (entry 9).
- Non-`/api` paths keep their current behaviour: a missing `/static/...` file is a plain 404, and shell paths serve the shell. Only the request log applies to them.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Success | `GET /api/health` | 200 body unchanged; one line `route=/api/health`, `status=200`, `code=null` | No error expected |
| Validation | bad path/query/body on a typed route, or malformed JSON | 422 `validation_failed`, no input value anywhere in body or logs | Handler |
| Unknown `/api` | `GET /api/no-such-route?q=x` | 404 `not_found`; line `route=/{path:path}`, no raw path or query | Handler |
| Wrong method | `POST /api/health` | 405 envelope, code `not_found` | Handler |
| Crash | route raises with input in the message | 500 `internal_error`; message and traceback text absent from body, logs, stderr | Middleware |
| Non-`/api` 404 | `GET /static/<ver>/missing.js` | plain 404, as today | Unchanged |
| Client, envelope | non-OK with envelope | `ApiError` with `status`, `code`, `message`, `requestId`, `details` | Thrown |
| Client, non-envelope | HTML 502 from a proxy | `ApiError` `code=internal_error`, `requestId=null` | Thrown |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/__init__.py`, `src/language_lab/domain/errors.py` (new) -- `class ErrorCode(StrEnum)` with the twelve AD-15 values; a code→message table and a helper building the envelope dict. Later features will raise domain errors carrying an `ErrorCode`; this story only needs the enum and envelope builder.
- `src/language_lab/app.py` -- `create_app` gets the middleware and handlers; `main()` gets logging setup and `access_log=False`. Leave the shell route, `_RESERVED_PREFIXES` and the static mount as they are. Its `HTTPException(404)` for `api/...` is what the unknown-route path maps.
- `src/language_lab/static/api.js` -- add `export class ApiError extends Error`; `request()` reads the body as JSON when it can and throws `ApiError` on any non-OK response.
- `tests/api/test_app.py:106` -- `test_main_prints_url_and_binds_settings` asserts kwargs `== {"host", "port"}`; update to include `access_log: False`.
- `tests/support/probes.py`, `tests/support/fixtures/api.py` (`probe_client`, `raise_server_exceptions=False`), `tests/support/fixtures/logs.py` (`request_lines`, `all_text`), `tests/support/network.py` (`stub_api_error`) -- reuse, don't change.
- Starlette 1.7 / FastAPI 0.143: Starlette's router writes the matched route into the shared `scope["route"]`. A pure ASGI middleware that owns the `scope` dict reads it after the app returns, which `BaseHTTPMiddleware` does not guarantee. Use a pure ASGI middleware.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/__init__.py`, `src/language_lab/domain/errors.py` -- enum, fixed messages, envelope builder -- AD-15
- [x] `src/language_lab/app.py` -- request-id ASGI middleware (uuid4 id stored in `scope["state"]`, monotonic duration, catches exceptions → 500 envelope, captures status and envelope code from the response start/body or state, logs one JSON line); handlers for `RequestValidationError` and `StarletteHTTPException` that return the envelope for `/api` paths and defer to the default for others; `main()` logging and `access_log=False` -- AD-15, NFR-9
- [x] `src/language_lab/static/api.js` -- `ApiError` and envelope parsing -- AD-13, AD-15
- [x] `tests/api/test_app.py` -- update the kwargs assertion -- AC-6
- [x] the four ATDD files -- remove `RED_PHASE`; add the checklist's P0/P1 green-phase backlog: no sentinel on the unknown-route and crash paths (response, all logs, stderr), malformed JSON, success line with `code: null`, two requests give distinct ids, 405 envelope, non-`/api` 404 unchanged, non-envelope → `ApiError` `internal_error`, and a subprocess run of the real server showing one JSON line on stdout and no uvicorn access line -- matrix

**Acceptance Criteria:**
- Given the repo, when `make lint` and `make test` run, then both pass and no `RED_PHASE` marker remains.
- Given `uv run language-lab` in dev mode, when `/api/health` and `/api/nope?x=secret` are requested, then the terminal shows exactly two JSON request lines, neither contains `secret` or `/api/nope`, and no uvicorn access line appears.

## Implementation Notes

- Implemented by a coding subagent from this plan: `domain/errors.py` (enum, fixed `MESSAGES`, `error_envelope()`), and in `app.py` a pure ASGI `RequestLogMiddleware`, `_on_validation_error` / `_on_http_error` (non-`/api` paths defer to FastAPI's defaults), `_StdoutHandler` + idempotent `_configure_logging()`, and `access_log=False`. `api.js` gains `ApiError` and `toApiError()`.
- The subprocess test waits for uvicorn's "Uvicorn running on" line rather than sleeping, so it depends on that startup message.
- Not covered by this story: a network failure in `api.js` (no response) still throws the browser's error, not `ApiError`.
- Matrix audit: every row has a passing test. Success: `test_success_line_has_null_code`. Validation: AC-2/AC-3, AC-5, malformed JSON. Unknown `/api`: AC-2, `test_failure_envelope_does_not_echo_input`, `test_failure_logs_carry_no_request_content`. Wrong method: `test_wrong_method_gets_envelope`. Crash: AC-2, AC-4, and the two no-echo tests. Non-`/api` 404: `test_missing_static_file_stays_a_plain_404`. Client envelope / non-envelope: the two `test_api_client.py` tests. `make lint` passes; `uv run pytest` gives 87 passed, 0 skipped.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 1, low 3, false 0, maybe-false 0.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `app.py` `RequestLogMiddleware` except branch | A crash on a non-`/api` path returns the JSON envelope, against the plan's Never rule | low | patch | The except branch never checks `_is_api`, while both handlers do. A direct correction to the stated rule: plain-text 500 outside `/api`, still no re-raise. |
| 2 | `app.py` `_configure_logging()` via `main()` tests | Tests calling `main()` leave a stdout handler and INFO level on the global `language_lab` logger, so later `capsys` output depends on test order; idempotence untested | medium | patch | No fixture restores the logger, so the handler persists for the session. Fix: restore the logger's handlers and level around tests, and add an idempotence test. |
| 3 | `app.py` `RequestLogMiddleware` started-response branch | A crash after the response started logs status 500 while the client saw 200 | low | reject | This is the behaviour Design Notes prescribe, and no streaming route exists. Changing it means editing this plan. |
| 4 | `app.py` catch-all / `_code_for_status` | `POST /api/nope` gives 405 with `Allow: GET` instead of 404 | low | reject | Router behaviour from before this change; the envelope code is still `not_found` and nothing leaks. The client only calls existing routes, and a fix needs a new non-GET catch-all route. |

## Design Notes

HTTP status → code for `HTTPException`: 404 and 405 → `not_found`, 413 → `payload_too_large`, other 4xx → `validation_failed`, 5xx → `internal_error`. Handlers stash the code in `request.state`, so the middleware logs it without parsing bodies. The middleware sets `code="internal_error"` itself on a caught exception. If a response has already started when an exception arrives, the middleware can't send a new one: log the line with status 500 and close.

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass
- `grep -rn RED_PHASE tests/` -- expected: no output

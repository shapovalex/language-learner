---
title: 'Host and Origin allow-list with tailnet discovery'
type: 'feature'
ticket: '4'
created: '2026-10-11'
status: 'built'
baseline_revision: 'ad139a6561c217f9c7c185d0a45f499b913f1671'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-1-4.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The app answers any `Host` and any cross-site write, so a DNS-rebinding page or another site open on the Mac Mini can drive or read LanguageLab (AD-16). Startup also doesn't know or print the tailnet URL.

**Approach:** Add `adapters/tailscale.py` (`discover_tailnet_host`), `app.with_tailnet_host`, and an allow-list ASGI middleware running inside `RequestLogMiddleware`. `main()` resolves the tailnet host and prints its HTTPS URL. Make the ATDD scaffolds from ad139a6 pass.

## Boundaries & Constraints

**Always:**
- Implement the checklist's "Implementation contract the tests encode" (`context`): the adapter signature and failure rules, `with_tailnet_host(settings, discover)`, the allow-list `{127.0.0.1:<port>, localhost:<port>, public_host?}` built from settings alone, middleware order, and the `https://<public_host>/` startup line.
- AD-16 as amended (Q1): `Host` must be allowed, and `X-Forwarded-Host`, when present, must be allowed too. Non-GET `/api` needs an `Origin` whose `host[:port]` is allowed, scheme ignored; `null` and missing are rejected.
- Rejection: 403. On `/api` the `forbidden_origin` envelope with the request's id; elsewhere plain text. Exactly one AD-15 log line, `code: "forbidden_origin"`, and no header value in body or log.
- Discovery runs `tailscale status --json` with `timeout=2.0` and never raises; any failure means no tailnet host and startup continues (AD-16 Q2).
- `main()` calls discovery through the module attribute `tailscale.discover_tailnet_host`, and only when `LANGUAGE_LAB_PUBLIC_HOST` is unset.
- Remove every `RED_PHASE` marker and definition in the three ATDD files, and move the adapter import in `test_tailscale_discovery.py` to the top. Don't weaken any first assertion.

**Never:**
- No new dependencies, nothing test-only in `src`, no CORS, no login, no Fetch Metadata check.
- No changes to `create_app`'s signature, `tests/support/hosts.py` behaviour, or the Tailscale fixtures (R-05 replaces them later).
- No `docs/` pages (entry 9).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Local | `Host: 127.0.0.1:<port>` or `localhost:<port>` | served as today | None |
| Tailnet via Serve | `Host`/XFH = tailnet host, `Origin: https://<tailnet>` | served; POST accepted | None |
| Foreign Host | `Host: evil.example:<port>` on `/api`, shell, static | 403 (envelope on `/api` only) | Middleware |
| Rebinding + XFH | foreign `Host`, tailnet XFH | 403 | Middleware |
| Spoofed XFH | loopback `Host`, foreign XFH | 403 | Middleware |
| Write, bad Origin | non-GET `/api`, Origin missing / foreign / `null` | 403 `forbidden_origin` | Middleware |
| GET, foreign Origin | `GET /api/health`, allowed Host | 200 | None |
| Case / default port | `LOCALHOST:<port>`, `<tailnet>:443` | allowed | Normalised |
| Discovery fails | binary missing, timeout, non-zero exit, bad JSON, `NeedsLogin`, no `DNSName` | `None`; `main()` still serves, no `https://` line | Adapter |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/__init__.py`, `src/language_lab/adapters/tailscale.py` (new) -- `discover_tailnet_host(run=None) -> str | None`. Binary: `shutil.which("tailscale")`, else the macOS app bundle CLI `/Applications/Tailscale.app/Contents/MacOS/Tailscale`. Only `args[-2:]` and `timeout=2.0` are asserted.
- `src/language_lab/app.py` -- add the allow-list middleware (pure ASGI, like `RequestLogMiddleware`; read headers from `scope["headers"]`, set `scope["state"][_ERROR_CODE]`, read `_REQUEST_ID` from state for the envelope). In `create_app`, `add_middleware(AllowList…)` goes **before** `add_middleware(RequestLogMiddleware)` (last added is outermost). Add `with_tailnet_host`; in `main()` call it after `load_settings()` and print the HTTPS line after the local one. Reuse `_is_api`, `error_envelope`, `ErrorCode.FORBIDDEN_ORIGIN`.
- `src/language_lab/settings.py:39` -- `public_host` already exists with blank → `None`. Use `model_copy(update=...)`; don't edit.
- `tests/api/test_host_origin_allow_list.py`, `tests/unit/test_tailscale_discovery.py`, `tests/integration/test_startup_tailnet.py` -- red-phase scaffolds; un-skip.
- `tests/support/hosts.py` (`app_client`, `local_hosts`, `serve_headers`, `tailscale_status`), `tests/support/probes.py` (`VALIDATE_ROUTE`), `tests/support/fixtures/logs.py` -- reuse, don't change. Every existing `TestClient` already goes through `app_client()`.
- `tests/support/live_server.py` -- builds the app from settings with its port, so the E2E suite should keep passing untouched (AC-9).

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/adapters/__init__.py`, `src/language_lab/adapters/tailscale.py` -- discovery adapter -- AD-16 Discovery
- [x] `src/language_lab/app.py` -- allow-list middleware, `with_tailnet_host`, `main()` discovery and URL line -- AD-16, FR-1
- [x] the three ATDD files -- un-skip and tidy per the checklist's Next Steps
- [x] `tests/api/test_host_origin_allow_list.py`, `tests/integration/test_startup_tailnet.py` -- add the checklist's green-phase backlog rows except R-05 and the loopback-rewrite variant: startup continues with no `https://` line when discovery returns `None`; the discovered host is printed; PUT/PATCH/DELETE without Origin get 403 (on the probe routes, or a test-local route); GET `/api` with a foreign Origin passes; case-insensitive Host; `<tailnet>:443`; shell/static 403 is plain text; no sentinel header value in the 403 body or logs -- matrix

**Acceptance Criteria:**
- Given the repo, when `make lint` and `make test` run, then both pass, E2E included, and no `RED_PHASE` marker remains.
- Given `uv run language-lab` in dev mode with no `LANGUAGE_LAB_PUBLIC_HOST` and no Tailscale, when it starts, then it serves on loopback and prints no `https://` line; with Tailscale logged in, it prints `https://<machine>.<tailnet>.ts.net/`.

## Implementation Notes

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 0, low 3, false 0, maybe-false 0.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `app.py` `AllowListMiddleware._permits` | Only the first copy of a repeated `Host`, `X-Forwarded-Host` or `Origin` is checked, so a foreign second copy passes | low | patch | `headers.setdefault` keeps the first value; the rule says XFH "when present" must be allowed. The reviewer reproduced it with a raw ASGI scope. Nothing reads XFH today, so the impact is small, but checking every copy directly corrects the stated rule. |
| 2 | `tests/api/test_host_origin_allow_list.py`, `tests/integration/test_startup_tailnet.py` | New tests are top-level functions, not grouped in `Test…` classes as `tests/README.md` asks | low | reject | No test file in the repo uses a `Test…` class (all 0), including the red-phase scaffolds these extend. Regrouping is a restructure with no named harm, not a direct correction. |
| 3 | `tests/integration/test_startup_tailnet.py` `FakeDiscovery` | Near-copy of the unit test's `FakeDiscovery` instead of a shared helper | low | reject | A 6-line test double; moving it into `tests/support/` adds shared surface for negligible gain. |

## Design Notes

Normalise a host before comparing: lowercase, and strip `:443` (browsers omit the default HTTPS port Serve uses). Origin → host: drop everything up to `://`; reject when no `://` is present (covers `null`). A request with no `Host` header at all is rejected.

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass
- `grep -rn RED_PHASE tests/` -- expected: no output

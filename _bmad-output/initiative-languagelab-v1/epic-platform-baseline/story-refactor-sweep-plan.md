---
title: 'Refactor sweep'
type: 'refactor'
ticket: '11'
created: '2026-10-14'
status: 'built'
baseline_revision: 'b7a70f70be945c09bb1e971269215a8855f41e0d'
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

**Problem:** Entries 1–10 left small cleanups behind: a deferred `env.example` comment that omits tailnet discovery, two env parses for one dev-mode answer (`_dev_mode()` wrapped by `is_dev_mode()`, and `load_settings()` re-deriving `active_config_path()`), two middlewares that each build the same "envelope on `/api`, plain text elsewhere" error response, two copies of the router's focus-trap Tab cycling and of its `aria-current` toggle, and a test double (`FakeDiscovery`) copied between two test files.

**Approach:** Fix the deferred comment in `src/language_lab/env.example` (`LANGUAGE_LAB_PUBLIC_HOST`: empty means the app asks Tailscale at startup). Fold `_dev_mode()` into `is_dev_mode()`, have `load_settings()` use `active_config_path()`, and have `main()` read dev mode once. Extract one `_error_response(scope, status, code, text)` in `app.py` used by `RequestLogMiddleware` and `AllowListMiddleware`. In `router.js`, extract `cycleFocus(event, items)` for the alert and Menu Tab traps (keeping the Menu's Shift+Tab-from-outside → last item, which the alert adopts) and `markCurrent(links, isCurrent)` for the two `aria-current` loops. Move `FakeDiscovery` to `tests/fakes/discovery.py` and import it in both tests. No behavior, status code, body, log line, or public name used by tests changes; findings the earlier plans rejected as behavior changes (405 on unknown non-GET `/api`, raw template at `/static/<v>/index.html`, desktop gutter, forward-while-dirty) stay out.

</frozen-after-approval>

## Tasks & Acceptance

**Acceptance Criteria:**
- Given the cleanup, when `make lint`, `make test`, and `make test-webkit` run, then all pass with no test edited except imports of `FakeDiscovery`.
- Given `src/language_lab/env.example`, when a user reads the `LANGUAGE_LAB_PUBLIC_HOST` comment, then it says an empty value makes the app discover the tailnet name from Tailscale, matching `docs/configuration.md`.

## Implementation Notes

Oneshot: about 80 changed lines across six files, each a local, mechanical cleanup with existing test coverage.

- Done as planned on branch `story-1-11-refactor-sweep`: `env.example`, `settings.py` (`_dev_mode` folded into `is_dev_mode`), `app.py` (`_error_response`; `main()` imports `config_path` instead of `active_config_path`), `router.js` (`markCurrent`, `cycleFocus`), new `tests/fakes/discovery.py` imported by `tests/unit/test_tailscale_discovery.py` and `tests/integration/test_startup_tailnet.py`.
- The only observable difference: Shift+Tab with focus outside the alert's buttons now lands on the last button, as the Menu already did. Unreachable in practice: the alert opens with focus on Keep editing and the page beneath is inert.
- `make lint`, `make test` (330 passed) and `make test-webkit` (211 passed) are green.

## Review Triage Log

Pass 1 (quick): high 0, medium 0, low 3, false 0, maybe-false 0.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `app.py` `main()` + `settings.py` `load_settings()` | Normal startup still parses `LANGUAGE_LAB_DEV` twice, and the two calls decide the config path separately | low | reject | True, and unchanged from before this change. The duplicated code the Problem names (`_dev_mode` wrapper, `load_settings` re-deriving the path) is gone. A divergence needs the env or cwd to change between two calls a few lines apart, and fixing it means changing `load_settings()`'s signature, which many tests call. |
| 2 | `env.example` `LANGUAGE_LAB_PUBLIC_HOST` | "without Tailscale" omits the other discovery failures (not running, logged out, CLI not found) listed in `docs/remote-access.md` | low | patch | Reworded to "if Tailscale can't answer, the app is reachable on this machine only". |
| 3 | `settings.py` `is_dev_mode()` docstring | Closing quotes end a text line, unlike every other multi-line docstring in `src/` | low | patch | Rewritten as a summary line, a blank line, then the body, with the closing quotes on their own line. |

## Verification

**Commands:**
- `make lint` -- expected: no ruff findings
- `make test` -- expected: all pass
- `make test-webkit` -- expected: all pass

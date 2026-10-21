---
title: 'Sync feature: coalesced, scheduled, non-blocking'
type: 'feature'
ticket: '10'
created: '2026-10-21'
status: 'built'
baseline_revision: 'fa690783e1dc6e5024ff7652ee6c35404941d132'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-10.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing Syncs Anki with AnkiWeb yet. AD-17 and FR-36 need one owner of every Sync that coalesces requests, runs at startup, every five minutes and at graceful shutdown, and never blocks or fails work.

**Approach:** Add the `SyncRequester` port and `features/sync` (a coalescing `SyncService` plus a lifespan scheduler on an injected clock), move `AnkiStore.sync()` to AnkiConnect API v1 (`collection.sync` polled through `operations.get`, spike 2.2 Q7) returning a `SyncOutcome`, and wire it in `app.py`. The ATDD checklist's "Implementation contract" is the spec for names and signatures.

## Boundaries & Constraints

**Always:**
- At most one Sync running and one pending; every Sync goes through `AnkiStore.sync`, which holds the Anki lock for the whole Sync within a 120 s budget.
- `request()` returns at once; `request_and_wait()` returns the status of a Sync that started after the call; `last_status()` is memory only.
- A failure is one WARNING line on `language_lab.sync` naming the outcome, no traceback, kept as the last status, never raised. `ok` is one INFO line.
- Startup requests and doesn't wait; shutdown waits for its Sync at most 30 s, then closes the client as today.
- Dev mode (`settings.dev`): no Sync at all, nothing scheduled.
- Other AnkiConnect actions stay on v6; v1 errors carry no upstream text (AD-15).
- `full_sync_required` stays `False` (no reply reports it, spike Q2); entry 9 sets it.

**Never:**
- No HTTP endpoint or readiness tile for the status (entry 9).
- No feature imports `features/sync` directly; `app.py` injects it (AD-1, AD-13).
- No weakening of the ATDD tests' first assertions; no real time in tests.

**Decision (user, 2026-10-21):** v1 `waitingForUser` and `cancelled` are terminal: stop polling, report `ANKIWEB_UNREACHABLE`, release the lock at once.

**Decision (user, 2026-10-21):** an unexpected non-`AppError` exception from the store becomes `ANKI_UNAVAILABLE`, logged as one WARNING line with no traceback, never raised.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| v1 Sync succeeds | polls end `succeeded` | `SyncOutcome.OK` | None |
| Logged out | `failed`, `data.type == authenticationRequired` | `AUTH_REQUIRED` | WARNING line |
| Other failure | `failed`, any other type | `ANKIWEB_UNREACHABLE` | WARNING line |
| Dialog in Anki / cancelled | poll state `waitingForUser` or `cancelled` | `ANKIWEB_UNREACHABLE` at once | WARNING line; lock released |
| Hung poll | never terminal within budget | `ANKIWEB_UNREACHABLE` | WARNING line; lock released |
| AnkiConnect down / lock busy / bug | store raises `AppError` or another exception | `ANKI_UNAVAILABLE` / `ANKI_BUSY` / `ANKI_UNAVAILABLE` status | WARNING line, not raised |
| Ten concurrent requests | one Sync running | at most two Syncs total | None |
| Shutdown, AnkiConnect hung | shutdown Sync never ends | shutdown completes at 30 s | the Sync task is cancelled |
| Dev mode | `LANGUAGE_LAB_DEV=1` | zero store calls; `request_and_wait()` → `DISABLED` | None |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/client.py` -- add `invoke_v1(method, **params)` POSTing JSON-RPC 2.0 to `url.rstrip("/") + "/api/v1"`; reuse `invoke`'s except shape. Drop `_TIMEOUTS_S`'s `sync` entry (no v6 sync any more); keep `SYNC_TIMEOUT_S` only if used.
- `src/language_lab/adapters/anki/store.py:25` -- `sync()` becomes the v1 poll loop; constructor gains `poll_interval_s=1.0`, `sync_budget_s=120.0`. Note the failed poll's error is inside `result.error`, not the JSON-RPC envelope (`tests/fixtures/anki/sync-logged-out.json`).
- `src/language_lab/ports/anki_store.py:16` -- `sync() -> SyncOutcome`; port, fake and adapter change together (`tests/unit/test_anki_store_port.py`).
- `src/language_lab/app.py:258-283` -- `create_app(..., clock=None)`, build `SyncService(anki_store, enabled=not settings.dev)`, scheduler start/stop in `lifespan` before `anki_client.aclose()`.
- `tests/fakes/anki_store.py` -- extend per the checklist (`gated`, `outcome`, `finish()`, counters); keep `syncs`.
- `tests/integration/test_anki_adapter.py:38-60` -- drop the `sync` row and `SYNC_OK` import; docstring line 4 mentions 120 s for `sync`.
- `tests/support/anki_connect.py:20` -- `SYNC_OK` becomes unused; remove if nothing else imports it.
- Tests to un-skip and hoist imports: `tests/unit/test_sync_requester_port.py`, `tests/unit/test_sync_service.py`, `tests/integration/test_anki_sync.py`, `tests/api/test_sync_lifespan.py`.
- Reuse: `tests/support/clock.py` (`FakeClock` has `async sleep`), `tests/support/lifespan.py`. Fake style: `tests/fakes/discovery.py`.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/sync.py` -- `SyncOutcome` StrEnum and frozen `SyncStatus` per the contract.
- [x] `src/language_lab/adapters/anki/client.py`, `store.py`, `ports/anki_store.py`, `tests/fakes/anki_store.py`, `tests/integration/test_anki_adapter.py` -- v1 Sync and the port change together.
- [x] `src/language_lab/ports/sync_requester.py`, `tests/fakes/sync_requester.py` -- port and fake.
- [x] `src/language_lab/features/sync/{__init__,service,scheduler}.py` -- `SyncService` (futures for running and pending, catches `AppError`, logs) and `SyncScheduler(requester, clock, enabled)` with `start()`/`stop()`; a default `asyncio.sleep` clock.
- [x] `src/language_lab/app.py` -- `clock=` and the lifespan wiring.
- [x] The four ATDD files -- remove `RED_PHASE`, hoist imports.
- [x] `tests/unit/test_sync_service.py` -- add the backlog's P1 cases: disabled service makes no call; an unexpected exception from the store is logged and the next request still Syncs.

**Acceptance Criteria:**
- Given the 17 ATDD cases un-skipped, when `make test` runs, then all pass with no `RED_PHASE` left.
- Given the real adapter on a refused port (`test_default_wiring…`, live server E2E), when the app starts and stops, then startup and shutdown stay within their existing bounds.
- Given `make lint`, then it is clean.

## Implementation Notes

- `SyncService.aclose()` (not on the port) cancels the running Sync and drops the pending one; the lifespan calls it after `SyncScheduler.stop()`, so a hung shutdown Sync is cancelled and its lock released before the client closes.
- `request_and_wait()` awaits its future through `asyncio.shield`, so the shutdown cap cancelling one waiter never cancels a Sync other callers share.
- The scheduler logs one WARNING on `language_lab.sync` when the 30 s shutdown cap wins (backlog P2).
- v1 calls use the client's 10 s per-request timeout; the 120 s budget bounds the whole poll loop via `asyncio.timeout`, inside the lock.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 2, false 0, maybe-false 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `SyncService.aclose()` cancels the running task, so the waiter only `_run` resolves stays pending forever | medium | patch | Grouped with the next row (root cause: `aclose()` doesn't give every waiter a status). The reviewer's probe showed the running-Sync waiter still waiting after 0.5 s. Fix: `_run` resolves its waiter on cancel; pending resolved with `ANKI_UNAVAILABLE`. |
| `aclose()` cancels the pending future, so its awaiters get `CancelledError`, breaking the port's "Never raises" | medium | patch | Same root cause and fix as above. |
| No test pins the shutdown cancellation; deleting `await sync.aclose()` still passes | low | patch | Confirmed: `test_shutdown_…_30_s` checks only `exiting.done()`. Fix: a unit test of `aclose()` with waiters on the running and the pending Sync. |
| The 30 s-cap WARNING in `SyncScheduler.stop()` is untested | low | rejected | A coverage gap with no defect behind it; the line is a P2 extra beyond the plan's ACs. |
| After a budget timeout or `waitingForUser`/`cancelled`, the lock is released while Anki may still be syncing | maybe-false | defer | Follows the user's 2026-10-21 decision. Whether the next locked call misbehaves against a mid-Sync Anki is unknown; settle by a Mac Mini run calling `reachable()` during a `waitingForUser` Sync. If true, medium. |

## Design Notes

- Service: one `asyncio.Task` for the running Sync and one `Future` for the pending one. A request while idle starts a Sync; while running, it joins the pending future (creating it if absent); when the running Sync ends, a pending future starts the next Sync and resolves with its status. `request_and_wait()` while idle starts a Sync and awaits it; while running, awaits the pending one.
- Shutdown: cancel the interval task, then `asyncio.wait({wait_task, cap_task}, return_when=FIRST_COMPLETED)` and cancel the loser. Keep a reference to background tasks so they aren't garbage-collected.
- Catch `Exception` (not only `AppError`) around the store call so a bug can't kill the pending chain.

## Verification

**Commands:**
- `make test` -- expected: all pass, 0 skipped among the 2.10 files
- `make lint` -- expected: clean
- `grep -rn RED_PHASE tests/unit/test_sync_*.py tests/integration/test_anki_sync.py tests/api/test_sync_lifespan.py` -- expected: no output

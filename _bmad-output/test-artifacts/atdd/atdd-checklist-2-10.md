---
runScope: 'story'
runKey: 'story-2-10'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.10'
storyKey: '2-10'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 10)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-10.md'
generatedTestFiles:
  - 'tests/api/test_sync_lifespan.py'
  - 'tests/unit/test_sync_requester_port.py'
  - 'tests/unit/test_sync_service.py'
  - 'tests/integration/test_anki_sync.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-1, AD-2, AD-3, AD-5, AD-17)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-36, AC20)'
  - '_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md (Q2, Q3, Q4, Q7, Surprises)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-1.md (format and conventions)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'pyproject.toml'
  - 'src/language_lab/app.py'
  - 'src/language_lab/settings.py'
  - 'src/language_lab/domain/errors.py'
  - 'src/language_lab/ports/anki_store.py'
  - 'src/language_lab/adapters/anki/{client,lock,store}.py'
  - 'src/language_lab/features/setup/{routes,service}.py'
  - 'src/language_lab/tools/record_tailscale_fixtures.py (the v1 path and polling the spike used)'
  - 'tests/README.md, tests/conftest.py'
  - 'tests/fakes/anki_store.py'
  - 'tests/fixtures/anki/sync-normal.json, sync-after-field-change.json, sync-logged-out.json'
  - 'tests/support/{aio,anki_connect,app_env,hosts,live_server,ports,startup}.py, tests/support/fixtures/{settings,logs,api,live_server,release}.py'
  - 'tests/unit/test_anki_store_port.py, tests/integration/test_anki_adapter.py, tests/api/test_setup_readiness.py'
  - '.claude/hooks/tea-enforce.cjs (H1 hard-wait rule)'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'ports/SyncRequester declares requesting a Sync, requesting and awaiting one, and reading the last status, and its fake in tests/fakes/ matches it' }
  - { id: 'AC-2', idSource: 'generated', text: 'features/sync coalesces requests to at most one running and one pending Sync: ten concurrent requests make at most two Syncs' }
  - { id: 'AC-3', idSource: 'generated', text: 'Every Sync goes through AnkiStore.sync, which runs under the Anki lock within the 120 s timeout' }
  - { id: 'AC-4', idSource: 'generated', text: 'The app lifespan requests a Sync at startup' }
  - { id: 'AC-5', idSource: 'generated', text: 'The app lifespan requests a Sync every five minutes' }
  - { id: 'AC-6', idSource: 'generated', text: 'The app lifespan requests a Sync at graceful shutdown, capped at 30 s, so a hung AnkiConnect does not delay shutdown past 30 s' }
  - { id: 'AC-7', idSource: 'generated', text: 'Setup has a request-and-await call, made outside the lock' }
  - { id: 'AC-8', idSource: 'generated', text: 'Dev mode disables all Sync' }
  - { id: 'AC-9', idSource: 'generated', text: 'Sync failures are logged and never raised, so a failing or hung AnkiConnect fails no request' }
  - { id: 'AC-10', idSource: 'generated', text: 'The last Sync status, including full-sync-required, is kept in memory' }
---

# ATDD Checklist: Story 2.10, Sync feature: coalesced, scheduled, non-blocking

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 10. There is no story file. AC-1 to AC-10 come from the ticket's description, in source order. The lifespan clause is split three ways (startup, interval, shutdown), so each trigger gets its own leaf. The verify clauses are folded into the matching criterion: ten concurrent requests into AC-2, hung AnkiConnect at shutdown into AC-6, failing AnkiConnect into AC-9, and no Sync in dev mode into AC-8. All ids are generated.
- **Stack:** `backend` (pyproject, pytest, no `package.json`). This story has no UI, so there are no E2E leaves.
- **Test design:** none for epic 2. Priorities follow the ticket's risk (medium), FR-36 and AC20 ("failures don't block anything"), and AD-5/AD-17.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and there are no contract artifacts.
- **Affected components:**
  - New: `domain/sync.py`, `ports/sync_requester.py`, `features/sync/` (service and scheduler), `tests/fakes/sync_requester.py`.
  - Changed: `adapters/anki/{client,store}.py` (v1 Sync), `ports/anki_store.py` (`sync()` returns an outcome), `app.py` (`clock=` plus the lifespan), `tests/fakes/anki_store.py` (the sync gate).

### Decisions taken with the user (2026-10-21)

| Question | Decision |
| --- | --- |
| Move `sync()` to AnkiConnect API v1 in this story (spike 2.2, Q7)? | **Yes.** `AnkiStore.sync()` sends v1 `collection.sync` on `/api/v1` and polls `operations.get` to the end, under the lock, within a 120 s budget. It returns a `SyncOutcome` (`ok`, `auth_required`, `ankiweb_unreachable`) and still raises `anki_unavailable` and `anki_busy`. The 2.1 test that pins a v6 `sync` body gets its `sync` row removed (see the contract). |
| How do tests control time? | **Injected clock.** The scheduler awaits `clock.sleep(seconds)` for both the 300 s interval and the 30 s shutdown cap, defaulting to `asyncio.sleep`. `create_app(settings, *, anki_store=None, clock=None)` passes it through. Tests use `FakeClock`, which moves only on `advance()`. |

### Defaults taken without a question

- **Outcome mapping** (spike Q3/Q4):
  - `succeeded` maps to `ok`.
  - `failed` with `data.type == "authenticationRequired"` maps to `auth_required`.
  - Any other `failed`, or a poll that runs past the budget, maps to `ankiweb_unreachable`.
  - The service turns a raised `anki_unavailable` / `anki_busy` into the outcome of the same name.
  - `ok` claims only that Anki reported the Sync finished. Per the spike's Surprises, it doesn't prove AnkiWeb has the change.
- **`full_sync_required` stays `False` in this story.** No Sync reply reports it (spike Q2). `SyncStatus` carries the field, and entry 9 sets it when Setup applies a field-changing step and shows the tile.
- **No HTTP surface.** The status lives in memory only (AD-2). Readiness exposes it in entry 9.
- **Terminal lines.** One line per finished Sync on the `language_lab.sync` logger: INFO for `ok`, WARNING for a failure. The failure line names the outcome value and has no traceback. Entry 13's acceptance step reads the Syncs in the terminal.
- **Dev mode:** `request_and_wait()` returns `SyncStatus(DISABLED)` at once, `request()` does nothing, and `last_status()` stays `None`.
- **Test isolation (made in this run):** `isolated_environ()` now points `ANKI_CONNECT_URL` at a refused loopback port. Once startup and shutdown Sync land, a release-mode subprocess test (startup, released wheel) would otherwise Sync the developer's real collection, and the process env beats the `.env`.

## Generation mode (step 2)

AI generation. The stack is `backend`, so recording is skipped. Execution was **sequential**, written in this session, with no subagents.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Unit | P1 | Compare the public methods of `SyncRequester`, `FakeSyncRequester` and `SyncService` | the port's names are exactly `{"request", "request_and_wait", "last_status"}` |
| AC-2 | Unit | P0 | Gated fake: one request starts a Sync, then nine concurrent requests arrive, then each in-flight Sync is finished | `store.sync_calls == 2` |
| AC-3 | Integration | P0 | `AnkiConnectStore.sync()` over a MockTransport replaying `sync-normal`, `sync-after-field-change`, `sync-logged-out`, and synthetic unrecorded-failure and never-ends runs | `outcome == SyncOutcome(expected)` |
| AC-4 | API (lifespan) | P0 | Enter the lifespan with a gated fake, so the startup Sync never ends on its own | `store.sync_calls == 1` |
| AC-5 | API (lifespan) | P0 | Advance the FakeClock 299 s, 1 s, then 300 s | calls at 300 s == calls at start + 1 |
| AC-6 | API (lifespan) | P0 | The startup Sync ends, the shutdown Sync hangs, and the clock is advanced 29.9 s then 0.1 s | the shutdown made exactly one more Sync call |
| AC-7 | Unit | P1 | `request_and_wait()` while a Sync runs. The running Sync fails, the pending one succeeds | the awaited outcome is `ok` (the pending Sync's) |
| AC-8 | API (lifespan) | P0 | Dev settings: startup, 600 s on the clock, shutdown | `store.sync_calls == 0` |
| AC-9 | Unit | P0 | For each of `anki_unavailable`, `anki_busy`, `auth_required` and `ankiweb_unreachable`: `request_and_wait()` and `request()` | the awaited result is not an exception |
| AC-10 | Unit | P1 | `last_status()` before any Sync, after an `auth_required` Sync, then after an `ok` one | after the failure, it equals `SyncStatus(AUTH_REQUIRED, full_sync_required=False)` |

- **One leaf per criterion.** AC-3 and AC-9 are parametrized tables in one leaf each.
- **Red-phase imports.** The modules under test are imported in each leaf's body, so collection stays green. The lifespan leaves call `create_app(..., clock=...)` in the body, so their red reason is the missing parameter, not an opaque unpack error. Hoist the imports when green.
- **No duplicate coverage.**
  - The adapter is covered at Integration (recorded replies).
  - Coalescing, waiting, failure handling and status are covered at Unit (fake store).
  - Triggers and dev mode are covered through the real `create_app` lifespan, with no HTTP.
- **Negative paths at high risk.** Every failure kind gets a row in AC-9, and AC-3 has failed, unrecorded-failure and budget-overrun rows. In AC-6, AnkiConnect is hung. AC-5 checks just before the deadline, so a shorter interval fails it.
- **No real time.** The scenarios run on FakeClock time and loop turns (`drain`, `until`). `bounded()` (5 s) and `LIFESPAN_BOUND_S` are real-time caps that only fire when the code under test hangs.

## TDD Red Phase (Current)

Scaffolds generated: **10 leaves, 17 cases, all `@RED_PHASE` (`pytest.mark.skip`)**.

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/unit/test_sync_requester_port.py` | Unit | 1 (1): AC-1 |
| `tests/unit/test_sync_service.py` | Unit | 4 (7): AC-2, AC-7, AC-9 (4), AC-10 |
| `tests/integration/test_anki_sync.py` | Integration | 1 (5): AC-3 |
| `tests/api/test_sync_lifespan.py` | API (lifespan) | 4 (4): AC-4, AC-5, AC-6, AC-8 |

Observed with the skip markers stripped (a scratchpad plugin, not committed): **17 failed**.

- 13 cases: `ModuleNotFoundError` for `language_lab.domain.sync` or `language_lab.features.sync`, raised in the test body.
- AC-4 and AC-6: `TypeError: FakeAnkiStore.__init__() got an unexpected keyword argument 'gated'`.
- AC-5 and AC-8: `TypeError: create_app() got an unexpected keyword argument 'clock'`.

**Green feasibility, checked and removed.** Throwaway stand-ins turned all **17 of 17** cases green:

- `domain/sync.py`, the port, `SyncService` (futures for running and pending) and `SyncScheduler` (`asyncio.wait` of the Sync against `clock.sleep(30)`)
- `invoke_v1` and the polling `sync()` in the adapter
- the lifespan wiring
- the gated fake and `FakeSyncRequester`

Each mutation below was caught:

| Mutation | Caught by |
| --- | --- |
| Waiters share the running Sync (no pending) | AC-2, AC-7 |
| Every request starts its own Sync | AC-2 |
| Interval 60 s | AC-5 |
| No shutdown cap | AC-4, AC-6 |
| Startup awaits its Sync | AC-4, AC-6 |
| A store failure escapes the service | AC-7, AC-9 (`anki_unavailable`, `anki_busy`) |
| A failure is not logged | AC-9 (all four) |
| `authenticationRequired` not mapped | AC-3 `logged-out` |
| Budget overrun raises | AC-3 `never-ends` |
| Dev mode ignored | AC-8 |

With the stand-ins in place, the rest of the suite showed what the build must update. The `sync` row of `test_store_sends_ankiconnect_v6_with_the_action_timeout` fails as expected. `test_anki_store_port_declares_readiness_and_sync_and_the_fake_matches` fails until the port's `sync` returns `SyncOutcome` too. Nothing else failed.

The stand-ins were deleted (`git checkout` of the four changed files, removal of the new ones). With the scaffolds skipped, the suite stays green (**374 passed, 17 skipped**), and `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P1 | `test_sync_requester_port_declares_request_wait_and_status_and_the_fake_matches` | port names; then `request` and `request_and_wait` are coroutines, `last_status` isn't; the fake's and the service's signatures equal the port's |
| AC-2 | P0 | `test_ten_concurrent_requests_make_at_most_two_syncs` | `sync_calls == 2`; then `max_in_flight == 1`; nothing left in flight |
| AC-3 | P0 | `test_sync_runs_v1_collection_sync_to_its_end_and_reports_the_outcome` [normal, after-field-change, logged-out, unrecorded-failure, never-ends] | the outcome; then the first request is `collection.sync`, then only `operations.get` with its `operationId`; all go to `/api/v1`; no v6 `action`; the default budget is 120 s |
| AC-4 | P0 | `test_startup_requests_a_sync_without_waiting_for_it` | `sync_calls == 1`; then the Sync is still in flight once startup returns |
| AC-5 | P0 | `test_a_sync_is_requested_every_five_minutes` | +1 at 300 s; then none at 299 s; +2 at 600 s; 1 at start |
| AC-6 | P0 | `test_shutdown_requests_a_sync_and_waits_for_it_at_most_30_s` | +1 call at shutdown; then shutdown is still open at 29.9 s and closed at 30 s, with no error |
| AC-7 | P1 | `test_request_and_wait_returns_the_status_of_a_sync_started_after_the_call` | outcome `ok`; then still waiting after the first Sync ended; 2 calls |
| AC-8 | P0 | `test_dev_mode_never_syncs` | `sync_calls == 0` (shutdown also returns at once, inside the bound) |
| AC-9 | P0 | `test_a_failed_sync_is_logged_and_never_raised` [anki_unavailable, anki_busy, auth_required, ankiweb_unreachable] | not an exception; then the outcome; `request()` returns `None`; two WARNING lines on `language_lab.sync` naming the outcome; no traceback |
| AC-10 | P1 | `test_the_last_sync_status_is_kept_in_memory` | `SyncStatus(AUTH_REQUIRED, False)` after the failure; then `SyncStatus(OK, False)`; `None` before; reading it made no Sync call |

## Implementation contract the tests encode

- **`domain/sync.py`:**
  - `class SyncOutcome(StrEnum)`: `OK="ok"`, `AUTH_REQUIRED="auth_required"`, `ANKIWEB_UNREACHABLE="ankiweb_unreachable"`, `ANKI_UNAVAILABLE="anki_unavailable"`, `ANKI_BUSY="anki_busy"`, `DISABLED="disabled"`. The two Anki values equal their `ErrorCode` values.
  - `@dataclass(frozen=True) class SyncStatus: outcome: SyncOutcome; full_sync_required: bool = False`.
- **`ports/anki_store.py`:** `async def sync(self) -> SyncOutcome`. It still raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`. Update the port, the fake and the adapter together (2.1's AC-1 test compares the three).
- **`ports/sync_requester.py`:** `class SyncRequester(Protocol)` with exactly:
  - `async def request(self) -> None`: returns at once.
  - `async def request_and_wait(self) -> SyncStatus`: the status of a Sync that started after the call.
  - `def last_status(self) -> SyncStatus | None`: memory only.
- **`features/sync/service.py`:** `SyncService(anki: AnkiStore, *, enabled: bool)` implements the port with the exact port signatures.
  - **Coalescing:** at most one Sync running and one pending. Every request made while a Sync runs is served by the single pending Sync, which starts when the running one ends.
  - **No new lock:** it takes no Anki lock itself. `AnkiStore.sync` does.
  - **Failures:** it catches `AppError` from the store and maps its code to the outcome. It never raises to a caller, keeps the status as `last_status()`, and logs one line on `language_lab.sync`. That line is WARNING for a failure, naming `outcome.value`, with no `exc_info`, and INFO for `ok`.
  - **Disabled** (dev): no store call. `request_and_wait()` returns `SyncStatus(DISABLED)`.
- **Scheduler** (`features/sync/`, wired in `app.py`'s lifespan):
  - **Clock:** it takes a clock with `async sleep(seconds)`, defaulting to an `asyncio.sleep` clock.
  - **Startup:** `await request()` (non-blocking), then a task that loops `clock.sleep(300)` → `request()`.
  - **Shutdown:**
    1. Cancel the loop.
    2. Race `request_and_wait()` against `clock.sleep(30)` with `asyncio.wait(FIRST_COMPLETED)`, then cancel the loser. A hung Sync must not keep the process.
    3. Then close the AnkiConnect client, as today.
  - **Dev:** with `settings.dev`, nothing is scheduled, requested or awaited.
- **`app.py`:** `create_app(settings, *, anki_store=None, clock=None)` builds `SyncService(anki_store, enabled=not settings.dev)`. Later entries inject it as `SyncRequester` (Setup in 9, Pronunciation in epic 7). Features never import it directly (AD-1, AD-13).
- **`adapters/anki/client.py`:** a v1 call, e.g. `invoke_v1(method, **params)`. It POSTs `{"jsonrpc": "2.0", "id", "method", "params"}` to `url.rstrip("/") + "/api/v1"` and returns `result`.
  - A transport error, a non-2xx status, a non-object body or a JSON-RPC `error` raises `AppError(ANKI_UNAVAILABLE)`, with no upstream text (AD-15).
  - v6 `invoke` is unchanged for every other action.
- **`adapters/anki/store.py`:**
  - **Constructor:** `AnkiConnectStore(client, lock, *, poll_interval_s: float = 1.0, sync_budget_s: float = 120.0)`.
  - **Under the lock:** all of `sync()` runs inside `lock.hold()`. It sends `collection.sync`, then polls `operations.get` with `{"operationId": …}` every `poll_interval_s` until `succeeded` or `failed`.
  - **Budget:** the whole Sync is bounded by `sync_budget_s` (`asyncio.timeout`). Running out maps to `ankiweb_unreachable`.
  - **Outcomes:** the mapping is listed under the defaults above. It never sends a v6 `sync`.
- **`tests/fakes/anki_store.py`:**
  - **Constructor:** `FakeAnkiStore(*, available=True, busy=False, gated=False, outcome=SyncOutcome.OK)`. `outcome` is a mutable attribute.
  - **Counters:** `sync_calls` (every call), `syncs` (successful, as today), `in_flight`, `max_in_flight`.
  - **Ungated `sync()`:** raises for `busy` / not `available`, as today, else returns `outcome`.
  - **Gated `sync()`:** waits until `finish(end=SyncOutcome.OK)` ends the oldest in-flight call. An `ErrorCode` `end` raises `AppError(end)`, and a `SyncOutcome` `end` is returned.
- **`tests/fakes/sync_requester.py`:** `FakeSyncRequester` with the port's exact signatures. It counts requests and has a settable status, for entries 9 and the Pronunciation epic.
- **Existing tests to update in the build:**
  - Drop the `("sync", "sync", SYNC_TIMEOUT_S, None)` row (and `SYNC_OK` if unused) from `tests/integration/test_anki_adapter.py::test_store_sends_ankiconnect_v6_with_the_action_timeout`. AC-3 replaces it.
  - The AC-4 lock test there still covers `reachable()`.

## Fixture and support changes (made in this run)

- `tests/support/clock.py` (new):
  - `FakeClock`: `sleep()` parks until `advance()` reaches its deadline, and wakes chained sleepers in order. `.requested` and `.sleeping` show what was asked for.
  - `drain()` and `until()` yield loop turns and never wait on time.
  - `bounded()` caps a scenario at 5 s real time.
- `tests/support/lifespan.py` (new): `start_lifespan(app)` enters `app.router.lifespan_context` within `LIFESPAN_BOUND_S`, and the returned stack's `aclose()` is shutdown.
- `tests/support/anki_connect.py`:
  - `AnkiConnectReplay` answers by v6 `action` or v1 `method`. A reply may be a callable of the body.
  - New helpers: `API_V1_PATH`, `v1_sync_replies()`, `recorded_v1_sync(label)` (replays `sync-<label>.json`, echoing each request's `id`, last poll repeating), and `synthetic_v1_sync("unrecorded-failure" | "never-ends")`.
  - `StubReply` moved up to sit beside `Failure`.
- `tests/support/app_env.py`: `isolated_environ()` sets `ANKI_CONNECT_URL` to a refused loopback port unless `extra` overrides it.
- `tests/README.md`: the new helpers and the `isolated_environ` note.

## Next Steps (Task-by-Task Activation)

1. Pick a task and remove its `@RED_PHASE` line.
2. Run it, e.g. `uv run pytest tests/integration/test_anki_sync.py`.
3. Watch it fail for the reason above, implement, and watch it pass. Then hoist its in-body imports.
4. If a test fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes:
   - No `RED_PHASE` markers remain in the four files.
   - `make test` and `make lint` pass.

Suggested order:

1. `domain/sync.py` + the adapter's v1 Sync (AC-3), with the port, fake and 2.1 test updates in the same change.
2. Port and fakes (AC-1).
3. `SyncService` (AC-2, AC-9, AC-10, AC-7).
4. Scheduler and lifespan with `clock=` (AC-4, AC-5, AC-6, AC-8).

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-8 | `SyncService(enabled=False)`: `request()` and `request_and_wait()` make no store call; the latter returns `DISABLED`; `last_status()` stays `None` | P1 |
| AC-9 | An unexpected exception from the store is logged and becomes a failed status, not a crash of the Sync task (the next request still Syncs) | P1 |
| AC-9 | With a failing fake, `GET /api/setup/readiness` still answers 200 during startup and shutdown (no request fails) | P1 |
| AC-3 | The lock is held for the whole Sync: a `reachable()` started mid-Sync sends its `version` only after the last poll; with the lock held, `sync()` is `anki_busy` and sends nothing | P1 |
| AC-3 | `collection.sync` refused, an HTTP 500, or a JSON-RPC `error` reply is `anki_unavailable` | P1 |
| AC-6 | The shutdown cap logs one WARNING line naming the 30 s cap | P2 |
| AC-4 | The startup Sync's failure is logged, and the app still serves requests | P2 |
| AC-5 | A periodic request while a Sync is still running coalesces (no second concurrent Sync) | P2 |
| AC-7 | `request_and_wait()` with nothing running starts a Sync and returns its status; an INFO line on `ok` | P2 |
| AC-10 | `full_sync_required` is carried unchanged by later Syncs (entry 9 sets it; pin the carry-over then) | P3 |
| — | The `live_server` E2E run and `test_default_wiring…` (real adapter, closed port) stay green with startup and shutdown Syncs, and neither slows past its bound | P2 |

## Open items

- **Offline replies are still unrecorded** (spike Q4). `ankiweb_unreachable` for an unknown `data.type` rests on a synthetic fixture (`networkError`). Add a recording when an offline failure is first seen, as the spike suggests.
- **`ok` is weaker than "synced to AnkiWeb"** (spike Surprises: v1 reported `succeeded` while a one-way sync was pending). No user-facing copy should say "synced" from this status alone. Entry 9 owns the full-sync tile.
- **"Outside the lock" for Setup** is a caller obligation. Entry 9's apply must `request_and_wait()` before taking the lock for its field-changing steps, or it waits out the 15 s lock and gets `anki_busy`. Pin it in entry 9's ATDD.
- **The poll interval** (1 s) isn't fixed by the spike's findings (the recorder used 1 s). Tests pass 0.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (the ticket description and verify, the spike findings, and the decisions recorded with the user), pytest is configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-10), with no collisions
- [x] Every leaf's docstring carries exactly one `AC-n`, and each criterion has exactly one red-phase leaf (10 leaves)
- [x] Every scaffold is skipped with a reason, and none has placeholder assertions
- [x] The first assertion is the criterion-defining one. The stand-in run showed each leaf reaching it, and the mutation table shows each failing on its own branch
- [x] No unimplemented setup result is parsed before the criterion assertion. The lifespan leaves gather observations and assert after the scenario
- [x] State transitions are exercised: running → pending (AC-2, AC-7), before/after the interval (AC-5), before/at the cap (AC-6), failure → success (AC-10)
- [x] Existing tests are unchanged in behavior and pass (374 passed, 17 skipped). `ruff check` and `ruff format --check` are clean
- [x] Story handoff: there's no story file, so this checklist is the handoff for `bmad-build` on entry 10
- [x] No browser sessions were opened. The unskip plugin and stand-in backups are in the session scratchpad, and the stand-ins were removed from the tree

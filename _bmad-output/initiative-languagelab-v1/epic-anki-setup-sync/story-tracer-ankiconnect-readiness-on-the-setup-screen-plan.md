---
title: 'Tracer: AnkiConnect readiness on the Setup screen'
type: 'feature'
ticket: '1'
created: '2026-10-14'
status: 'built'
baseline_revision: '5df646017fff1ed3da8640a711b5e551915747e4'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-1.md'
  - '{project-root}/_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** LanguageLab has no path to Anki yet. The Setup screen shows only a version line, so the user can't tell whether AnkiConnect, Azure and OpenRouter are ready, or which Prefix is in effect (FR-5).

**Approach:** Build the first thin slice through every layer: an `AnkiStore` port (readiness and sync only) with its fake; an AnkiConnect adapter (client, lock, store); `features/setup` serving `GET /api/setup/readiness`; the Setup screen's readiness tiles; and an `anki` subcommand in the fixture recorder. The red-phase ATDD scaffolds from commit 7e46054 are the contract (see the checklist in `context`).

## Boundaries & Constraints

**Always:**
- Dependency rule: `routes → service → {ports, domain}`. Adapters depend on `ports` and `domain` only. Only `app.py` constructs adapters (AD-1, AD-13, AD-18).
- Every `AnkiStore` method runs entirely inside `AnkiLock.hold()`. The lock waits up to 15 s, then raises `anki_busy`. AnkiConnect requests time out after 10 s, or 120 s for `sync`, and all go through one `httpx.AsyncClient` that is closed at app shutdown (AD-5).
- Error messages come from `MESSAGES` only. No AnkiConnect or httpx text and no key values appear in bodies or logs (AD-15, NFR-6).
- `anki_unavailable` and `anki_busy` return HTTP 503 through the existing envelope.
- `tests/support/live_server.py` injects `FakeAnkiStore()` in the same change that makes `setup.js` call readiness.
- Un-skip the scaffolds one at a time. Never weaken a first assertion.

**Decision (user, 2026-10-14):** when readiness itself fails (`anki_busy` or any error envelope), Setup shows the envelope's message in place of the tiles and keeps the version line. This state is added to EXPERIENCE.md.

**Never:**
- No live Azure or OpenRouter calls: readiness checks only that the keys are configured.
- No full-sync-required check (entry 9), no Apply button and no change preview (later entries).
- No change to the recorder's `serve` or `status` behaviour or its console-script name.
- No test reaches real Anki.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All pass | Anki reachable, Azure key and region set, OpenRouter key set | 200 `{"prefix": P, "checks": [ankiConnect, azure, openrouter all ok:true]}` | None |
| One check fails | Anki down, or Azure key or region empty, or OpenRouter key empty | 200; only that check is `ok:false`; its tile reads "… not reachable/configured" and its `role="alert"` hint follows it | None |
| Anki busy | Lock wait passes 15 s | 503 `anki_busy` envelope | The screen shows the envelope message in place of the tiles. The version line stays. |
| AnkiConnect failure | Refused, timed out, non-2xx, non-JSON, or non-null `error` | `AppError(anki_unavailable)`; `reachable()` returns False | No upstream text leaks |
| Recorder, Anki down | `anki --url` to a closed port | Exit 1, one stderr line naming the URL | No traceback |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/errors.py` -- `ErrorCode.ANKI_UNAVAILABLE`/`ANKI_BUSY` exist; `MESSAGES`, `error_envelope`. Add `AppError(Exception)` with `.code`.
- `src/language_lab/app.py:241-267` -- `create_app(settings)`. Add the `anki_store` kwarg, a lifespan that closes the client, an `AppError` handler that reuses `_envelope_response` (:68) and sets `request.state.error_code` (:84), and include the setup router before the SPA catch-all (:261).
- `src/language_lab/settings.py:60-64` -- `anki_connect_url`, `anki_prefix`, `azure_speech_key` (SecretStr), `azure_speech_region`, `openrouter_api_key` (SecretStr). Use these and don't change them.
- `src/language_lab/static/api.js:39-49` -- `request()` throws `ApiError`. Add `getReadiness()` next to `getHealth()`.
- `src/language_lab/static/screens/setup.js` -- today the h1 and the version line, with a `mounted` flag. Extend it in place.
- `src/language_lab/static/css/studio.css` -- has no tile, hint or skeleton classes yet. Add them from DESIGN.md: `readiness-tile`, `readiness-fix-hint` and `skeleton`, with the grid `repeat(auto-fit,minmax(200px,1fr))`, pass/fail colours, and the check/cross icons.
- `src/language_lab/tools/record_tailscale_fixtures.py:275-288` -- argparse subparsers, stdlib only. Add `anki`. Keep the module name; `pyproject.toml:19` and `tests/support/recorder.py` stay unchanged.
- `tests/fakes/discovery.py` -- the pattern for the new `tests/fakes/anki_store.py`.
- `tests/support/live_server.py` -- `run_live_server` calls `create_app`. Inject the fake there.
- Red scaffolds (contract): `tests/unit/test_anki_store_port.py`, `tests/integration/test_anki_adapter.py`, `tests/api/test_setup_readiness.py`, `tests/e2e/test_setup_readiness.py`, `tests/integration/test_record_anki_fixtures.py`. Helpers are in `tests/support/{anki_connect,aio,ports,network,recorder}.py`.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/errors.py` -- add `AppError(code)`, whose str is the fixed message -- typed domain failures
- [x] `src/language_lab/ports/{__init__,anki_store}.py` -- `AnkiStore(Protocol)`: `async reachable() -> bool`, `async sync() -> None` -- AC-1
- [x] `src/language_lab/adapters/anki/{__init__,client,lock,store}.py` -- `AnkiConnectClient(url, *, transport=None)` with `invoke` and `aclose`; `AnkiLock(wait_seconds=15.0).hold()` using `asyncio.timeout`; `AnkiConnectStore(client, lock)` -- AC-2..4
- [x] `tests/fakes/anki_store.py` -- `FakeAnkiStore(*, available=True, busy=False)` -- AC-1
- [x] `src/language_lab/features/{__init__,setup/__init__,setup/service,setup/routes}.py` -- the readiness service over port and settings; an `APIRouter` built from injected deps -- AC-5
- [x] `src/language_lab/app.py` -- the kwarg, default wiring, lifespan, `AppError` handler (503), router -- AC-5
- [x] `tests/support/live_server.py` -- inject `FakeAnkiStore()` -- no real Anki in E2E
- [x] `src/language_lab/static/{api.js,screens/setup.js,css/studio.css}` -- skeleton, subtitle with the Prefix in bold, "Ready to go?" list, tiles, hints, error state, version line kept -- AC-6
- [x] `src/language_lab/tools/record_tailscale_fixtures.py` -- the `anki [--url]` subcommand -- AC-7, AC-8
- [ ] Five scaffold files -- remove `RED_PHASE` and hoist imports; add the P1 backlog cases from the checklist (busy → 503 envelope, no key in the body or log, unwired default with Anki down → false, reachable False per failure kind, unstubbed E2E all-pass)
- [x] `_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md` -- add the AnkiConnect and Azure fail copy and fix hints, and the busy-error state

**Acceptance Criteria:**
- Given the five scaffold files, when `make test` runs, then every case passes and none is skipped as `RED_PHASE`.
- Given the change, when `make lint` and `make test-webkit` run, then both pass.
- Given the existing `test_record_tailscale_fixtures.py`, `test_shell`, `test_navigation` and `test_studio_styles`, when the suite runs, then they pass unchanged.
- Given the released wheel on the Mac Mini, when `/setup` loads with Anki open and then closed, then it shows "AnkiConnect reachable" and then "AnkiConnect not reachable" with its hint (HITL, manual).

## Implementation Notes

- `tests/support/aio.py`: `settle()` now runs `asyncio.run` on a worker thread. Once the E2E session starts, Playwright's sync API keeps a loop running in the main thread, so the p1 adapter cases (ordered after the e2e p0s) failed with "asyncio.run() cannot be called from a running event loop". AC-4 now calls `settle()` instead of `asyncio.run()`; no assertion changed.
- `tests/support/live_server.closed_port()`: on macOS a bound but non-listening socket drops SYNs (7.8 s connect timeout), so "nothing listens" tests close the socket first.
- `live_server_settings` sets placeholder Azure/OpenRouter keys so the unstubbed E2E sees all checks pass.
- The skeleton label is a `<div>`, not a `<p>`: `test_navigation.test_setup_ignores_health_after_unmount` reads the screen's first `<p>` as the version line.
- The fix hint sits inside its tile's `<li>`, so it follows its tile at every width.
- The app closes the `AnkiConnectClient` it built in the lifespan; an injected store is never closed by the app.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 4, false 0, maybe-false 0, rejected (plan edit) 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Recorder `_anki()` misses `http.client.HTTPException` (BadStatusLine, IncompleteRead), so a non-AnkiConnect listener gives a traceback | low | patch | The reviewer reproduced it. The contract says one stderr line and no traceback. Fix: add `http.client.HTTPException` to the except. |
| Recorder docstring says no value is written as received, but `anki` prints AnkiConnect's response verbatim | low | patch | `record_tailscale_fixtures.py:22` "Neither writes…" now covers three subcommands. Fix: scope the sentence to `serve`/`status` and say `anki` prints its reply as received. |
| The all-pass E2E test reads `live_server_settings`, but `--base-url` (tests/README.md:25) points the page at a different app | low | patch | `base_url` in `tests/e2e/conftest.py:24` skips the live server when it is explicit, so the test checks the invented settings against another app. Fix: the test requests `live_server` and navigates to `live_server.url + "/setup"`. |
| `features/setup/service.py` imports `Settings`, against the frozen rule `routes → service → {ports, domain}` | low | patch | Arch line 48 and the plan's Always rule. Later Setup entries extend this service, so the coupling would spread. Fix: `app.py` passes the service `prefix`, `azure_configured` and `openrouter_configured`, and the service doesn't import settings. |
| The plan's scaffold task checkbox is still `[ ]` | — | rejected | The fix is an edit to this build's plan. |

## Design Notes

The readiness copy lives in `setup.js` keyed by check id. The server sends only `{id, ok}` (an ATDD decision), so a later `fullSyncRequired` adds one entry without an API break. The subtitle is a single `<p>` with the Prefix in `<b>`; Playwright's text match ignores the tag.

## Verification

**Commands:**
- `make test` -- expected: all pass, 0 RED_PHASE skips
- `make test-webkit` -- expected: all pass
- `make lint` -- expected: clean
- `grep -rn RED_PHASE tests/` -- expected: no hits in the five story files

**Manual checks (if no CLI):**
- Mac Mini, released wheel: Manual checks 1 and 2 in the ATDD checklist (tile states; record `version.json` via `uvx --from "$WHEEL" language-lab-record-fixtures anki`).

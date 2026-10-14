---
runScope: 'story'
runKey: 'story-2-1'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-14'
storyId: '2.1'
storyKey: '2-1'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 1)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-1.md'
generatedTestFiles:
  - 'tests/api/test_setup_readiness.py'
  - 'tests/e2e/test_setup_readiness.py'
  - 'tests/unit/test_anki_store_port.py'
  - 'tests/integration/test_anki_adapter.py'
  - 'tests/integration/test_record_anki_fixtures.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (Design Paradigm, AD-1, AD-2, AD-3, AD-4, AD-5, AD-15, AD-16, AD-17, Conventions, Structural Seed)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Setup copy, Readiness tile, Skeleton, J5)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md (Readiness tile, Skeleton)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Setup.dc.html'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-SetupStates.dc.html'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-1-8.md (format and conventions)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'pyproject.toml'
  - 'src/language_lab/app.py'
  - 'src/language_lab/settings.py'
  - 'src/language_lab/domain/errors.py'
  - 'src/language_lab/static/screens/setup.js'
  - 'src/language_lab/static/api.js'
  - 'src/language_lab/tools/record_tailscale_fixtures.py'
  - 'tests/README.md'
  - 'tests/conftest.py'
  - 'tests/e2e/conftest.py'
  - 'tests/fixtures/README.md'
  - 'tests/support/fixtures/settings.py'
  - 'tests/support/fixtures/live_server.py'
  - 'tests/support/live_server.py'
  - 'tests/support/network.py'
  - 'tests/support/recorder.py'
  - 'tests/integration/test_record_tailscale_fixtures.py'
  - 'tests/e2e/test_shell.py, test_navigation.py, test_studio_styles.py (the Setup version line)'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'ports/AnkiStore declares the readiness and sync signatures only, and its in-memory fake in tests/fakes/ matches it' }
  - { id: 'AC-2', idSource: 'generated', text: 'adapters/anki/client.py sends AnkiConnect API v6 requests through one httpx.AsyncClient, with a 10 s timeout by default and 120 s for sync' }
  - { id: 'AC-3', idSource: 'generated', text: 'Every AnkiConnect failure maps to anki_unavailable' }
  - { id: 'AC-4', idSource: 'generated', text: 'lock.py holds one asyncio.Lock around every AnkiStore call; waiting more than 15 s for it returns anki_busy' }
  - { id: 'AC-5', idSource: 'generated', text: 'GET /api/setup/readiness, wired in app.py, reports AnkiConnect reachability, Azure and OpenRouter keys configured, and the Prefix in effect, each check passing and failing on its own' }
  - { id: 'AC-6', idSource: 'generated', text: 'The Setup screen shows one tile per check with a skeleton, fix hints, and the subtitle naming the Prefix' }
  - { id: 'AC-7', idSource: 'generated', text: 'An anki subcommand of language-lab-record-fixtures records AnkiConnect''s version response' }
  - { id: 'AC-8', idSource: 'generated', text: 'The bare command keeps its Tailscale behavior, so existing docs stay true' }
  - { id: 'AC-9', idSource: 'generated', text: 'On the Mac Mini, the released wheel''s /setup shows AnkiConnect reachable with Anki open and unreachable with it closed' }
---

# ATDD Checklist: Story 2.1, Tracer: AnkiConnect readiness on the Setup screen

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml` entry 1. There is no story file. AC-1 to AC-8 come from the ticket's description in source order. The client clause is split in two: AC-2 is the request contract and AC-3 is the failure mapping, so each gets one leaf. AC-9 is the verify clause about the Mac Mini. The verify clauses "each check passing and failing on its own", "lock timeout returning anki_busy" and "Playwright shows the tiles" are already part of AC-5, AC-4 and AC-6. All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The ticket's verify names Playwright for the tiles, so AC-6 runs through pytest-playwright (dev-only, NFR-11), as stories 1.3 and 1.6 did.
- **Test design:** none for epic 2. Priorities follow the ticket's risk (medium), AD-5 (the lock bounds every Anki call, NFR-3) and FR-5 (readiness).
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node. No contract-testing artifacts exist.
- **Affected components (new):** `ports/anki_store.py`, `adapters/anki/{client,lock,store}.py`, `features/setup/{routes,service}.py`, `domain/errors.py` (an `AppError` carrying an `ErrorCode`), `app.py` (`create_app(settings, *, anki_store=None)` plus the AppError handler), `static/screens/setup.js` and `static/api.js`, the `anki` subcommand of the recorder, and `tests/fakes/anki_store.py`.
- **Existing tests:** none change. `test_shell`, `test_navigation` and `test_studio_styles` keep waiting for `LanguageLab v<version>` on `/setup`. `tests/support/live_server.py` must inject the fake once `create_app` accepts it (see the contract).

### Decisions taken with the user (2026-10-14)

| Question | Decision |
| --- | --- |
| Test seam for the AnkiStore | **`create_app(settings, *, anki_store: AnkiStore \| None = None)`.** The default builds the real adapter from `ANKI_CONNECT_URL`. API tests and the live server inject `FakeAnkiStore`. E2E failing states stub `/api/setup/readiness` in the browser. Adapter tests use `httpx.MockTransport` replaying the recorded fixture. |
| Readiness response shape | **Ids and ok, with the copy in the client.** `{"prefix": "<Prefix>", "checks": [{"id": "ankiConnect", "ok": bool}, {"id": "azure", "ok": bool}, {"id": "openrouter", "ok": bool}]}`, in tile order. `setup.js` owns the labels and fix hints. Entry 9 adds `fullSyncRequired`. |
| When "Azure configured" passes | **Key and region both non-empty** (`AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`). |
| The Setup version line | **Kept.** Setup still shows `LanguageLab v<version>` from `/api/health` below the tiles, so the three existing E2E tests stay untouched. |

### Defaults taken without a question (stated at preflight, not objected to)

- `anki_unavailable` and `anki_busy` both return HTTP 503 through the AD-15 envelope.
- When the lock wait times out, readiness returns the `anki_busy` envelope. It doesn't show a tile.
- `language-lab-record-fixtures anki [--url URL]` prints the fixture JSON on stdout, the way `status` does. The default URL is `http://127.0.0.1:8765`.
- `tests/fixtures/anki/version.json` is synthetic (`{"result": 6, "error": null}`, from AnkiConnect's documented v6 reply) until the Mac Mini recording replaces it, as the Tailscale fixtures were in epic 1.

## Generation mode (step 2)

AI generation. The stack is `backend`, so step 2 skips recording, and the Setup tiles don't exist yet. Selectors come from the a11y floor (roles and accessible names) and the copy in EXPERIENCE.md and the mockups.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Unit | P1 | Compare the public coroutine methods of `AnkiStore`, `FakeAnkiStore` and `AnkiConnectStore` | the port's method names are exactly `{"reachable", "sync"}` |
| AC-2 | Integration | P1 | `AnkiConnectStore.reachable()` and `.sync()` over a MockTransport that replays `tests/fixtures/anki/version.json` and the documented sync reply | the bodies sent are exactly `[{"action": <action>, "version": 6}]` |
| AC-3 | Integration | P0 | `AnkiConnectClient.invoke("version")` against refused, timed out, HTTP 500, an error reply, and a non-JSON reply | the outcome's `code` is `anki_unavailable` |
| AC-4 | Integration | P0 | The test holds the lock and calls `store.reachable()` with `AnkiLock(wait_seconds=0.05)` | the outcome's `code` is `anki_busy` |
| AC-5 | API | P0 | `GET /api/setup/readiness` over the fake: all pass, then each check failing alone (Anki down, Azure key empty, Azure region empty, OpenRouter key empty) | status `200` |
| AC-6 | E2E | P1 | Hold the readiness call, see the skeleton, then answer it with OpenRouter failing and the `LanguageLabDev` Prefix | the skeleton `status` "Checking Anki and your keys…" is visible |
| AC-7 | Integration | P2 | `language-lab-record-fixtures anki --url <stub AnkiConnect>` | exit code `0` |
| AC-8 | Integration (existing) | P2 | `tests/integration/test_record_tailscale_fixtures.py`, unchanged | n/a: already green, must stay green |
| AC-9 | Manual (HITL) | P0 | Released wheel on the Mac Mini, Anki open, then closed | n/a: the tile reads "AnkiConnect reachable", then "AnkiConnect not reachable" |

- **One leaf per automated criterion.** AC-2, AC-3 and AC-5 are parametrized tables in one leaf each. AC-5's all-pass row is a case in it, so an endpoint that always fails can't pass.
- **Red-phase imports.** The modules under test don't exist yet, so each leaf imports them in its body and collection stays green. Hoist the imports when the test goes green.
- **No duplicate coverage.** The adapter is tested at Integration (MockTransport), the service and route at API (fake), and the screen at E2E (stubbed browser route). The E2E test doesn't re-check per-check logic.
- **Negative paths at high risk.** The AC-3 table covers every failure kind. AC-4 checks that a busy lock sends no request at all. AC-5 has one failing row per check.

## TDD Red Phase (Current)

Scaffolds generated: **7 leaves, 16 cases, all `@RED_PHASE` (`pytest.mark.skip`)**. Execution was sequential: the API, E2E and backend levels were written in this session, and no subagents were spawned.

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/unit/test_anki_store_port.py` | Unit | 1 (1): AC-1 |
| `tests/integration/test_anki_adapter.py` | Integration | 3 (8): AC-2 (2), AC-3 (5), AC-4 (1) |
| `tests/api/test_setup_readiness.py` | API | 1 (5): AC-5 |
| `tests/e2e/test_setup_readiness.py` | E2E | 1 (1): AC-6 |
| `tests/integration/test_record_anki_fixtures.py` | Integration | 1 (1): AC-7 |

Observed with the skip markers stripped (a scratchpad plugin, not committed): **16 failed**.

- AC-1 to AC-5: `ModuleNotFoundError` for `language_lab.adapters.anki` or `tests.fakes.anki_store`, raised in the test body (the imports sit there so collection stays green).
- AC-6 fails at its first assertion: `get_by_role("status").filter(has_text="Checking Anki and your keys…")` is not found. The Aria snapshot shows today's Setup screen: heading "Setup" and "LanguageLab v0.2.1".
- AC-7 fails at its first assertion: `assert 2 == 0`, from `invalid choice: 'anki' (choose from 'serve', 'status')`.

**Green feasibility, checked and removed.** Throwaway stand-ins (about 60 lines in total) turned AC-1 to AC-4 green: the port as a `Protocol`, `AnkiConnectClient`, `AnkiLock` on `asyncio.timeout`, `AnkiConnectStore` and `FakeAnkiStore`. That's 9 of 9 cases. Each mutation was caught by one case:

| Mutation | Caught by |
| --- | --- |
| `sync` uses the 10 s timeout | AC-2 `sync` |
| An AnkiConnect `error` reply passes through as a result | AC-3 `error-reply` |
| `reachable()` swallows `anki_busy` as "not reachable" | AC-4 |
| The store doesn't take the lock | AC-4 |

`HeldRoute` was probed on Chromium and WebKit against today's `/api/health` call on `/setup` (2 passed). It held the request, the version line stayed absent, and then rendered the stubbed version. The stand-ins and the probe test were deleted. With the scaffolds skipped, the whole suite stays green (330 passed, 16 skipped), and `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P1 | `test_anki_store_port_declares_readiness_and_sync_and_the_fake_matches` | port methods == `{"reachable", "sync"}`; then all are coroutines; the fake's and the adapter's signatures equal the port's |
| AC-2 | P1 | `test_store_sends_ankiconnect_v6_with_the_action_timeout` [reachable, sync] | bodies sent == `[{"action": …, "version": 6}]`; then read timeout 10 s / 120 s; the URL is `ANKI_CONNECT_URL`; the result is `True` / `None` |
| AC-3 | P0 | `test_every_ankiconnect_failure_is_anki_unavailable` [refused, timed-out, http-500, error-reply, not-json] | `outcome.code == anki_unavailable`; then it's an exception; AnkiConnect's error text isn't in it |
| AC-4 | P0 | `test_a_call_waiting_past_the_lock_limit_is_anki_busy` | `outcome.code == anki_busy`; then no request was sent; `AnkiLock().wait_seconds == 15` |
| AC-5 | P0 | `test_readiness_reports_each_check_on_its_own` [all-pass, anki-closed, azure-key-unset, azure-region-unset, openrouter-unset] | status 200; then `(id, ok)` pairs in tile order; `prefix` is the configured Prefix |
| AC-6 | P1 | `test_setup_shows_a_skeleton_then_one_tile_per_check` | the skeleton status is visible; then 3 tiles with the expected text; exactly one alert, the OpenRouter hint; the subtitle names `LanguageLabDev`; the skeleton is gone |
| AC-7 | P2 | `test_record_fixtures_anki_prints_the_version_exchange` | exit 0; then stdout == `tests/fixtures/anki/version.json`; the stub got exactly the fixture's request; no traceback |
| AC-8 | P2 | Existing `tests/integration/test_record_tailscale_fixtures.py`, unchanged | Already green; it must stay green after the recorder change |
| AC-9 | P0 | Manual 1 below | — |

### Manual checks (HITL, the user)

1. **On the Mac Mini, from the released wheel:** with Anki and AnkiConnect open, `/setup` shows "AnkiConnect reachable". Close Anki and reload: it shows "AnkiConnect not reachable" with its fix hint. The subtitle names `LanguageLab` (AC-9).
2. **Record the fixture there:** `uvx --from "$WHEEL" language-lab-record-fixtures anki > version.json`. Read it, replace `tests/fixtures/anki/version.json` with it, and update the date line in `tests/fixtures/README.md`. AC-2 and AC-7 must stay green on the recorded file.

## Implementation contract the tests encode

- **`domain/errors.py`:** `AppError(Exception)` has `.code: ErrorCode`. Its `str()` never carries AnkiConnect or httpx text (AD-15). `app.py` maps `AppError` to the envelope, with 503 for `anki_unavailable` and `anki_busy`.
- **`ports/anki_store.py`:** `class AnkiStore(Protocol)` with exactly two methods:
  - `async def reachable(self) -> bool`: `False` when AnkiConnect is unavailable. It raises `AppError(ANKI_BUSY)` when the lock wait runs out.
  - `async def sync(self) -> None`: raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
- **`tests/fakes/anki_store.py`:** `FakeAnkiStore(*, available: bool = True, busy: bool = False)`. Its two port methods have the port's exact signatures. With `busy`, both raise `anki_busy`. When unavailable, `reachable()` is `False` and `sync()` raises `anki_unavailable`.
- **`adapters/anki/client.py`:** `AnkiConnectClient(url: str, *, transport: httpx.AsyncBaseTransport | None = None)` builds one `httpx.AsyncClient`. `async invoke(action, **params)` POSTs `{"action", "version": 6}` (plus `"params"` only when given) to `url`. The per-request timeout is 10 s, or 120 s for `sync`. It returns `result`. Anything else raises `AppError(ANKI_UNAVAILABLE)`: an httpx error, a non-2xx status, a body that isn't JSON or isn't an object, or a non-null `error`. Close the client at app shutdown.
- **`adapters/anki/lock.py`:** `AnkiLock(wait_seconds: float = 15.0)` exposes `.wait_seconds` and `hold()`, an async context manager. `hold()` raises `AppError(ANKI_BUSY)` when the wait runs out. Use `asyncio.timeout` (or `wait_for`) on the acquire, never a poll.
- **`adapters/anki/store.py`:** `AnkiConnectStore(client, lock)`. Every method runs entirely inside `lock.hold()` (AD-5). `reachable()` turns `anki_unavailable` into `False` and lets `anki_busy` through.
- **`features/setup/{service,routes}.py` + `app.py`:**
  - `GET /api/setup/readiness` returns `{"prefix": settings.anki_prefix, "checks": [{"id": "ankiConnect"}, {"id": "azure"}, {"id": "openrouter"}]}`, each with its `ok`.
  - `azure` passes when the key and the region are both non-empty, and `openrouter` when its key is non-empty. Key values never appear in the body or the logs.
  - `create_app(settings, *, anki_store: AnkiStore | None = None)` builds `AnkiConnectStore(AnkiConnectClient(settings.anki_connect_url), AnkiLock())` when none is given. Features never import the adapter (AD-1, AD-13).
- **`tests/support/live_server.py`:** `run_live_server` passes `anki_store=FakeAnkiStore()` to `create_app`. **Land this in the same change that makes `setup.js` call readiness.** Otherwise every E2E test that opens `/setup` reaches the developer's real AnkiConnect, which breaks the "no real externals" rule.
- **`static/api.js` + `static/screens/setup.js`:**
  - `getReadiness()` in `api.js`.
  - The screen keeps the h1 "Setup", then the subtitle `Creates or repairs everything LanguageLab manages under the prefix <prefix>. Safe to run again.` as one text node or element.
  - While the request is pending, it shows a skeleton with `role="status"` and the label "Checking Anki and your keys…", removed once the request settles.
  - A heading "Ready to go?" labels a `<ul>` (`aria-labelledby`). It holds one `<li>` per check, in response order.
  - Tile text when passing: "AnkiConnect reachable", "Azure configured", "OpenRouter configured". When failing: "AnkiConnect not reachable", "Azure not configured", "OpenRouter not configured".
  - Each failing tile is followed by its fix hint with `role="alert"`, inside `main`:
    - AnkiConnect: "Open Anki on the Mac mini and check that the AnkiConnect add-on is installed, then reload this page."
    - Azure: "Add your Azure Speech key and region to the LanguageLab configuration on the Mac mini, restart LanguageLab, then reload this page."
    - OpenRouter: "Add your OpenRouter key to the LanguageLab configuration on the Mac mini, restart LanguageLab, then reload this page."
  - The `LanguageLab v<version>` line stays.
- **Recorder:** add `anki [--url URL]` (default `http://127.0.0.1:8765`) next to `serve` and `status`.
  - It POSTs `{"action": "version", "version": 6}` and prints `{"request": …, "response": …}` (indent 2) on stdout, exiting 0.
  - If AnkiConnect can't be reached, it exits 1 with one stderr line naming the URL and no traceback.
  - It stays stdlib-only (`urllib.request`), like the rest of the module.
  - If the module is renamed (e.g. `tools/record_fixtures.py`), update `pyproject.toml`'s console script and `RECORDER_COMMAND` in `tests/support/recorder.py` together. `serve` and `status` don't change (AC-8).

## Fixture and support changes (made in this run)

- `tests/fixtures/anki/version.json` (new): synthetic `{"request": {"action": "version", "version": 6}, "response": {"result": 6, "error": null}}`.
- `tests/support/anki_connect.py` (new):
  - `ANKI_URL`, `ANKI_CONNECT_VERSION`, `SYNC_OK`, `UNSUPPORTED` and `anki_fixture()`.
  - The failure kinds (`refused`, `timed_out`, `server_error`, `error_reply`, `not_json`).
  - `AnkiConnectReplay`: a MockTransport answering per action and recording `.sent` (body, URL, read timeout).
  - `run_stub_ankiconnect()`: a loopback `ThreadingHTTPServer` for the recorder subprocess.
- `tests/support/aio.py` (new): `settled()` / `settle()` return a coroutine's result or its exception, so the assertions stay in the test body.
- `tests/support/ports.py` (new): `public_methods()`.
- `tests/support/network.py`: `HeldRoute(page, path)` holds a request until `fulfill_json(body)`. It waits for the route with Playwright round trips and a deadline, never a sleep.
- `tests/support/recorder.py`: `run_recorder_anki(url)`.
- `tests/README.md` and `tests/fixtures/README.md`: the new helpers, the `anki/` fixture and how to record it.

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` line.
2. Run it, for example `uv run pytest tests/integration/test_anki_adapter.py -k unavailable`.
3. Watch it fail for the reason above, implement, and watch it pass. Then hoist its in-body imports to the top of the module.
4. If a test fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes:
   - No `RED_PHASE` markers remain in the five files.
   - `make test` and `make lint` pass.
   - `make test-webkit` passes for the Setup screen.
   - Manual checks 1 and 2 are done.

Suggested order: `domain/errors.py` + AC-3 (client) → AC-4 (lock) → AC-2 (store) → AC-1 (port + fake) → AC-5 (`features/setup`, `create_app`) → `live_server` injection + AC-6 (`setup.js`) → AC-7 (recorder) → release → Manual 1 and 2.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-5 | Readiness with `FakeAnkiStore(busy=True)` returns 503 with the `anki_busy` envelope | P1 |
| AC-5 | No key value appears in the readiness body or its request-log line (`log_capture`) | P1 |
| AC-5 | `create_app(settings)` without injection, with `ANKI_CONNECT_URL` on a closed loopback port, reports `ankiConnect` false. This covers the real wiring with no Anki | P1 |
| AC-3 | `AnkiConnectStore.reachable()` is `False` for each failure kind (what readiness relies on) | P1 |
| AC-6 | Unstubbed against the live server (fake injected): three tiles, no alert when all pass | P1 |
| AC-6 | The AnkiConnect and Azure fix-hint copy; one alert per failing tile when two fail | P2 |
| AC-6 | A readiness error envelope (`anki_busy`) shows a message in place of the tiles; the version line still shows | P2 |
| AC-6 | Phone width (`viewports.PHONE`): tiles stack and the hint follows its tile | P3 |
| AC-4 | Two concurrent store calls run one after the other (the second request starts after the first reply) | P2 |
| AC-2 | `reachable()` and `sync()` go through one `httpx.AsyncClient`, and app shutdown closes it | P2 |
| AC-7 | `anki` against a closed port exits 1 with one stderr line naming the URL, no traceback; `--help` lists `anki` | P2 |
| AC-1 | The fake's `busy` path raises `anki_busy` from both methods | P3 |

## Open items

- **A lock with no timeout at all hangs AC-4 instead of failing it.** There's no `pytest-timeout` in the dev deps. The mutation check used "store skips the lock" and "busy swallowed" instead. The CI job timeout is the backstop.
- **`tests/fixtures/anki/version.json` is synthetic** until Manual 2. Epic 1 handled Tailscale the same way in story 1.10.
- **What "reachable" means for an unexpected API version** (a `version` reply other than 6) isn't decided, and the tests don't pin it. Spike 2.2 is the place to settle it.
- **The UX doesn't specify how the screen shows a readiness error** (`anki_busy`). The backlog row proposes the error message in place of the tiles. Confirm it with the UX owner or decide it in the build.
- **The AnkiConnect and Azure fix hints are new copy.** They're modeled on the mocked OpenRouter hint, and the test pins only the OpenRouter one. Add the other two to EXPERIENCE.md when the build lands.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (the ticket's description and verify, plus the decisions recorded with the user), pytest and pytest-playwright are configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-9), and no supplied ids collide
- [x] Every new leaf maps to exactly one AC (docstring `AC-n:`). AC-1 to AC-7 each have exactly one leaf. AC-8 is covered by the existing tests, and AC-9 is manual (HITL by the ticket)
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one. AC-6 and AC-7 were observed failing at it. AC-1 to AC-5 fail on the missing module, and the stand-in run showed each reaching and passing its first assertion
- [x] No unimplemented setup response is parsed before the criterion assertion. The AC-6 skeleton check runs before the stub is fulfilled
- [x] Existing tests are unchanged and pass (330 passed, 16 skipped). `ruff check` and `ruff format --check` are clean
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `bmad-build` on entry 1
- [x] No browser sessions were left open. The unskip plugin and the stand-in backups are in the session scratchpad. The stand-in modules and the probe test were deleted from the tree

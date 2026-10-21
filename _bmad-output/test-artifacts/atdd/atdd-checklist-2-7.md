---
runScope: 'story'
runKey: 'story-2-7'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.7'
storyKey: '2-7'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 7)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-7.md'
generatedTestFiles:
  - 'tests/integration/test_anki_setup_apply.py'
  - 'tests/unit/test_setup_apply_service.py'
  - 'tests/api/test_setup_apply.py'
  - 'tests/e2e/test_setup_apply.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/story-prefix-guard-and-setup-preview-without-touching-anki-plan.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-3 Setup flow, AD-4, AD-5, AD-15)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Setup key strings, Buttons, Progress card, Verification banner, State Patterns, J5)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md (Disabled button, Progress card, Verification banner)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-SetupStates.dc.html'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-6, FR-8)'
  - '_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md (Q5, Q6, reply shapes, Surprises)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-6.md (format, conventions, open items)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'src/language_lab/adapters/anki/{client,guard,store,setup_diff,manifest,lock}.py, ports/anki_store.py, domain/{setup,errors}.py, features/setup/{routes,service}.py, app.py'
  - 'src/language_lab/static/screens/setup.js, static/api.js'
  - 'tests/README.md, tests/fakes/anki_store.py, tests/support/{anki_state,anki_connect,aio,clock,network,navigation,hosts}.py'
  - 'tests/integration/test_anki_setup_preview.py, tests/api/test_setup_plan.py, tests/e2e/test_setup_preview.py, tests/e2e/test_navigation.py (LATE_HEALTH)'
  - 'tests/fixtures/anki/: createDeck, createModel, updateModelTemplates, updateModelStyling, cloneDeckConfigId, setDeckConfigId, saveDeckConfig, getDeckConfig'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'Apply re-diffs Anki under the lock and refuses a plan hash that no longer matches the fresh diff with plan_changed, sending no write' }
  - { id: 'AC-2', idSource: 'generated', text: 'Apply runs the Create and Repair items to completion and verifies by a fresh diff: the result has no discrepancies (Migrate items stay, for entry 9) and a second preview equals it' }
  - { id: 'AC-3', idSource: 'generated', text: 'Apply writes only through the Prefix guard: every write sent was checked by the guard, and a set-up LanguageLabDev beside the Prefix is untouched' }
  - { id: 'AC-4', idSource: 'generated', text: 'Apply creates and assigns the <Prefix> preset to every managed Study and Pronunciation deck, setting only the three bury flags off; a repair leaves user-set deck options and the Default preset untouched' }
  - { id: 'AC-5', idSource: 'generated', text: 'A preset save Anki refuses (saveDeckConfig answers false, spike 2.2) does not stop the run: the other items apply and verify reports the preset as the one discrepancy' }
  - { id: 'AC-6', idSource: 'generated', text: 'The run completes server-side when the client disconnects: a cancelled apply request leaves the run going, and its result is kept as finished' }
  - { id: 'AC-7', idSource: 'generated', text: 'POST /api/setup/apply carrying the plan hash returns the verification {verified, planHash, discrepancies}, and a second GET /api/setup/plan shows what is left' }
  - { id: 'AC-8', idSource: 'generated', text: 'POST /api/setup/apply with a stale plan hash is the 409 plan_changed envelope, and nothing is applied' }
  - { id: 'AC-9', idSource: 'generated', text: 'GET /api/setup/apply/status reports the run: idle before any run, finished with the result after one' }
  - { id: 'AC-10', idSource: 'generated', text: 'The Setup screen disables Apply setup with "Fix the failing check to continue." while a readiness check fails' }
  - { id: 'AC-11', idSource: 'generated', text: 'Apply setup posts the plan hash and shows the Applying card "Applying setup and verifying… Keep Anki open." with Apply disabled while the run is pending' }
  - { id: 'AC-12', idSource: 'generated', text: 'A verified run shows the verified banner "Setup applied and verified" in place of the change list' }
  - { id: 'AC-13', idSource: 'generated', text: 'A run with discrepancies shows the discrepancy banner with the count, the expected vs. found list, and Run Setup again, which applies the current plan' }
  - { id: 'AC-14', idSource: 'generated', text: 'Leaving Setup does not cancel the run; coming back re-reads Anki and shows the Applying card, the result, or the current change list' }
---

# ATDD Checklist: Story 2.7, Confirmed apply and verify

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 7 (`risk = "high"`). There is no story file, so this checklist holds the criteria. AC-1 to AC-14 follow the ticket's description in source order, with the verify clauses folded in:
  - "a stale hash refused" is AC-1 (adapter) and AC-8 (route).
  - "apply then a second preview empty" is AC-2 (real adapter, in-memory Anki) and AC-7 (route, fake).
  - "user-set deck options other than the bury flags untouched by a repair" is AC-4.
  - "a disconnect mid-apply still completing" is AC-6.
  - "Playwright shows Applying, verified, and discrepancy states" is AC-11, AC-12, AC-13.
  - AC-5 comes from spike 2.2 (`saveDeckConfig` answered `false`), per the decision below.

  All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The screen part runs through pytest-playwright, as in stories 2.1 and 2.6 (dev-only, NFR-11).
- **Test design:** none for epic 2. Priorities follow the ticket's risk (high), NFR-1 (the Prefix boundary), FR-6 (confirmed apply, verify, idempotent), FR-8 (user deck options are left alone) and AD-3 (re-diff before apply, run to completion).
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and no contract artifacts exist.
- **Affected components:**
  - Changed: `domain/errors.py` (`plan_changed`), `ports/anki_store.py`, `adapters/anki/store.py` (`setup_apply`), `tests/fakes/anki_store.py`, `features/setup/{routes,service}.py`, `app.py` (409 for `plan_changed`), `static/api.js`, `static/screens/setup.js`, `static/css/studio.css`.
  - Possibly new: an apply module in `adapters/anki/` (any name) that turns plan items into AnkiConnect writes.
  - Tests: `tests/support/anki_state.py` answers writes when asked, and `tests/support/network.py` gains `record_json_bodies()`.

### Decisions taken with the user (2026-10-21)

| Question | Decision |
| --- | --- |
| What does a stale plan hash return? | **409 `plan_changed`.** A new AD-15 code with a fixed message, "Anki changed since the preview. Review the changes and apply again." The screen re-reads the plan and shows the current change list. This amends the AD-15 code list. |
| How does the screen learn about a run after leaving and coming back? | **POST waits, plus a status read.** POST /api/setup/apply returns the verification once the run ends. The run is a server-side task that the request only awaits. A status endpoint reports `idle`, `running` or `finished` with the result. |
| What does Apply do with Migrate items (entry 9 makes them runnable)? | **Apply the rest.** Create and Repair items run. Migrate items are skipped and stay in the verification as discrepancies until entry 9. |
| How is the bury-flag write treated, given spike 2.2's `saveDeckConfig` answered `false`? | **Save, then verify.** Read the preset with `getDeckConfig`, change only the three flags, and `saveDeckConfig` it. `false` is a failed step: the run goes on and verify reports the preset. Entry 13 on the Mac Mini proves a real save. |

### Defaults taken without a question

- **Port:** `AnkiStore.setup_apply(plan_hash: str) -> SetupPreview`. Under one lock hold, the adapter:
  1. reads and diffs again, and raises `AppError(PLAN_CHANGED)` before any write if `plan_hash(items)` differs;
  2. runs every Create and Repair item, skipping Migrate;
  3. reads and diffs again, and returns that preview as the verification.

  Its items are the discrepancies. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)` as the preview does.
- **A failed write step** (an AnkiConnect `error`, or `saveDeckConfig` answering `false`) doesn't end the run. The verification shows what didn't take. A failed read (Anki gone) raises `anki_unavailable`.
- **Writes, per item** (AnkiConnect v6 names, guarded):
  - deck Create: `createDeck`, in manifest order (parents first).
  - note type Create: `createModel`, with `modelName`, `inOrderFields`, `css` and `cardTemplates` `[{Name, Front, Back}]`. It covers that note type's templates Create too.
  - templates Repair: `updateModelTemplates` for the card templates that exist, `modelTemplateAdd` for a missing one, and `updateModelStyling` for the CSS. AnkiConnect ignores unknown names in `updateModelTemplates`.
  - preset Create: `cloneDeckConfigId` with `name: <Prefix>` (no `cloneFrom`, so Anki clones its Default, id 1). Then `setDeckConfigId` on every preset deck, then the save below.
  - preset Repair: `setDeckConfigId` for preset decks not on it, then `getDeckConfig` of a preset deck, the three flags set off, and `saveDeckConfig` of that config. No second clone.
  - **A created Study or Pronunciation deck gets the preset**, even when the plan has no preset item. Anki puts a new deck on its Default preset, so without this, verify reports a preset Repair after a missing deck is recreated. The green-feasibility run found this through AC-2's `missing-deck` case.
- **Service:**
  - `SetupService.apply(plan_hash) -> ApplyResult`, where `ApplyResult` is `{"verified": bool, "planHash": str, "discrepancies": [{"action", "kind", "name"}]}`. `planHash` is `plan_hash(verification.items)`, which is what a fresh preview hashes to while Anki stays as verify found it.
  - The service runs `store.setup_apply` in an `asyncio` task it keeps, and the request awaits it shielded. A cancelled request (a disconnect) leaves the task running.
  - A second apply while one runs awaits the same run.
  - `SetupService.apply_status() -> ApplyStatus` is `{"state": "idle" | "running" | "finished", "result": ApplyResult | None}`. A run that raised isn't recorded, so the status stays what it was.
- **Routes:**
  - `POST /api/setup/apply` takes `{"planHash": str}`. It answers 200 with `ApplyResult`, 409 `plan_changed`, 503 `anki_busy`/`anki_unavailable`, or 422 `validation_failed`.
  - `GET /api/setup/apply/status` answers with `ApplyStatus`. It is a separate path, so a held POST in the browser never holds the status read.
  - `app.py` maps `plan_changed` to 409.
- **Screen:**
  - **Apply setup** (Primary) shows once readiness and the plan have arrived, and only when the plan has items ("Nothing to change" still shows no button). When any readiness check fails, it is disabled with the muted reason "Fix the failing check to continue." beside it.
  - **While a run is pending:** the progress card (`role="status"`, "Applying setup and verifying… Keep Anki open.") replaces the change list, and Apply setup stays disabled.
  - **Verified:** a `role="status"` banner, "Setup applied and verified" / "Decks, note types, templates and deck options match what LanguageLab expects.", replaces the change list. Apply setup is hidden.
  - **Discrepancies:** a `role="alert"` banner, "Setup applied, but 1 thing doesn't match" or "Setup applied, but N things don't match", with "Anki was changed. Review the difference below, then run Setup again.". One row per discrepancy, as `<kind> · <name>` with a muted expected-vs-found line. **Run Setup again** POSTs the result's `planHash`.
  - **Row labels:** `deck` "Deck", `noteType` "Note type", `templates` "Card templates and CSS", `preset` "Deck options".
  - **Expected vs. found:**
    - create deck: "Expected this deck; found none."
    - create noteType: "Expected this note type; found none."
    - create templates: "Expected LanguageLab's card templates and CSS; found none."
    - create preset: "Expected this deck options preset; found none."
    - repair templates: "Expected LanguageLab's card templates and CSS; found different ones."
    - repair preset: "Expected sibling burying off on every Study and Pronunciation deck; found it on, or a deck on another preset."
    - migrate noteType: "Expected LanguageLab's fields; found different ones."
  - **Coming back:** `mount` reads the status, still before `getHealth()` (the `LATE_HEALTH` rule).
    - `running`: the progress card, polling the status every 1 s until it is finished.
    - `finished`, with `result.planHash` equal to the fresh plan's `planHash`: that result's banner.
    - Otherwise: the current change list with Apply setup.
  - **On 409 `plan_changed`:** re-read the plan and show the current change list, with the message as an inline alert.

## Generation mode (step 2)

AI generation. Recording is skipped: the stack is `backend`, and the screen states are stubbed at the network. Execution is **sequential**, in this session, with no subagents (as in stories 2.1 to 2.6).

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Integration | P0 | Preview an empty Prefix, add a managed deck in Anki, then apply the old hash | the outcome's code is `plan_changed` |
| AC-2 | Integration | P0 | 12-row table: empty Prefix (alone and beside a set-up Dev), each repairable change, and a field change | the verification's items equal the expected set (empty, or the Migrate) |
| AC-3 | Integration | P0 | Apply an empty Prefix beside a set-up `LanguageLabDev` through a spying guard | the writes sent equal the writes the guard checked, and there are some |
| AC-4 | Integration | P0 | `repair` (flag on, user options, a deck on Default) and `create` (Default with user options and a flag on) | the `<Prefix>` preset's three flags are all off |
| AC-5 | Integration | P1 | Flag on and a changed template, with `saveDeckConfig` refusing | the verification is exactly the preset Repair |
| AC-6 | Unit | P0 | Gated fake: start the apply, cancel the request mid-run, then let the store finish | the store's apply completed once |
| AC-7 | API | P0 | Fake with four items: `verified` and `discrepancies` cases | status 200 |
| AC-8 | API | P0 | Fake with items, POST a hash that isn't the plan's | status 409 |
| AC-9 | API | P1 | Status before a run, then after one | the status before any run is `{"state": "idle", "result": null}` |
| AC-10 | E2E | P0 | Stubbed failing AnkiConnect check, plan with items | Apply setup is disabled |
| AC-11 | E2E | P0 | Held POST /api/setup/apply after a click on Apply setup | the progress card's line is visible |
| AC-12 | E2E | P0 | POST answers verified | "Setup applied and verified" is visible |
| AC-13 | E2E | P1 | POST answers 1 or 2 discrepancies, then Run Setup again | the banner title with the count is visible |
| AC-14 | E2E | P1 | `left-while-running` (click Apply, leave by nav, come back), `finished-unchanged`, `finished-anki-changed` | per case: the progress card, the verified banner, or an enabled Apply setup |

- **One leaf per criterion.** AC-2 and AC-4 are parametrized leaves. AC-13 is parametrized by count, and AC-14 by return state.
- **Red-phase imports.** Missing names are imported in each leaf's body, or reached through the object under test, so collection stays green. Hoist them when green.
- **No duplicate coverage.** The apply logic runs at Integration only, through the real store and client, against the in-memory collection, which now answers writes. The route tests (AC-7 to AC-9) use the fake and check status and shape. The disconnect is a service-level unit test with a gated fake. The E2E tests stub the network and check rendering only.
- **Negative paths at high risk.**
  - AC-1: a stale hash sends no write.
  - AC-3: Dev beside the Prefix is untouched.
  - AC-4: Default's own flags and user options survive.
  - AC-5: a refused save.
  - AC-8: a stale hash at the route.
  - AC-10: the disabled reason.
  - AC-14: Anki changed since verify.
- **Red phase is a state transition.** AC-2, AC-4 and AC-5 exercise the apply itself and assert the state after it. AC-6 asserts after the cancel. AC-14's `left-while-running` drives the leave and return.

## TDD Red Phase (Current)

Scaffolds generated: **14 leaves, 29 cases, all skipped with a `RED_PHASE` reason.**

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/integration/test_anki_setup_apply.py` | Integration | 5 (18): AC-1 (1), AC-2 (13), AC-3 (1), AC-4 (2), AC-5 (1) |
| `tests/unit/test_setup_apply_service.py` | Unit | 1 (1): AC-6 |
| `tests/api/test_setup_apply.py` | API | 3 (4): AC-7 (2), AC-8 (1), AC-9 (1) |
| `tests/e2e/test_setup_apply.py` | E2E | 5 (6): AC-10 (1), AC-11 (1), AC-12 (1), AC-13 (2), AC-14 (1) |

Observed with the skip markers stripped (a scratchpad plugin, not committed): **29 failed.**

| Count | Failure | Leaves |
| --- | --- | --- |
| 14 | `AttributeError: 'AnkiConnectStore' object has no attribute 'setup_apply'`, reached at the first assertion | AC-2, AC-5 |
| 1 | `assert None == 'plan_changed'` (the same missing method) | AC-1 |
| 1 | `assert [] != []`: no write was sent or checked | AC-3 |
| 2 | the `<Prefix>` preset's flags aren't all off (repair: `rev.bury` on; create: no preset) | AC-4 |
| 1 | `assert None == 1`: the fake has no `apply_gated` | AC-6 |
| 3 | `TypeError: FakeAnkiStore.__init__() got an unexpected keyword argument 'verified'` | AC-7, AC-9 |
| 1 | `assert 405 == 409` | AC-8 |
| 1 | `Locator expected to be disabled` (no Apply setup button) | AC-10 |
| 5 | `Locator.click: Timeout` on the Apply setup button | AC-11 to AC-14 |

**Green feasibility, checked and removed.** Throwaway stand-ins turned all **29 of 29** cases green:

- `plan_changed` and its 409;
- the port method, and the fake's `verified=`, `apply_gated=` and `finish_apply()`;
- `AnkiConnectStore.setup_apply`, with one write path per item;
- `SetupService.apply` (a shielded task) and `apply_status`;
- the two routes, `applySetup()` and `getApplyStatus()`;
- the screen states in `setup.js`.

The rest of the suite stayed green except the two expected failures below (499 passed in that run).

1. Story 2.6's exact port set `{"reachable", "sync", "setup_preview"}` in `tests/unit/test_anki_store_port.py` must gain `setup_apply`.
2. Story 1.3's twelve AD-15 codes in `tests/unit/test_errors.py` must gain `plan_changed` (the AD-15 amendment, below).

Each mutation below was caught, except where the table says otherwise:

| Mutation | Caught by |
| --- | --- |
| Apply skips the hash check | AC-1 (AC-8 uses the fake, so it can't see the adapter) |
| A preset Repair clones a second preset | AC-4 `repair`, AC-5 |
| The save sends a fresh config instead of the read one | AC-4 `repair`, `create` |
| The service awaits the run without `shield` | AC-6 |
| Writes go through the client's unguarded path | AC-3 |
| A created preset deck isn't put on the preset | AC-2 `missing-deck` |
| A refused save ends the run with an error | AC-5 |
| Apply writes something for a Migrate item | AC-2 `field-removed` |
| A missing card template isn't added (`updateModelTemplates` only) | AC-2 `missing-card-template` |
| Apply setup isn't disabled while a check fails | AC-10 |
| The discrepancy title is always plural | AC-13 `one` |
| No status polling while a run is `running` | AC-14 |
| **The return view ignores the hash compare** (shows any finished result) | **Not caught.** The `finished-anki-changed` branch is in the backlog |

The stand-ins were removed: `src/` and `tests/fakes/` were restored from git. With the scaffolds skipped, the suite stays green (**472 passed, 29 skipped**), and `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P0 | `test_apply_refuses_a_stale_plan_hash_before_any_write` | the outcome's code is `plan_changed`; then no write was sent; Anki holds only Default and the user's deck |
| AC-2 | P0 | `test_apply_runs_the_plan_and_verifies_it_with_a_fresh_diff` [empty-prefix, empty-prefix-beside-dev, changed-template, changed-css, missing-card-template, missing-deck, missing-note-type, bury-flag-on, deck-on-default-preset, no-preset, two-prefix-presets, user-deck-options, field-removed] | the verification's items equal the expected set (empty, or the one Migrate); then no duplicates; a fresh preview agrees; no unmanaged entries |
| AC-3 | P0 | `test_apply_writes_only_through_the_prefix_guard` | the writes sent equal the writes the guard checked, in order, and aren't empty; then Dev is unchanged; verified; an unguarded client raises `PrefixViolation` with no write sent |
| AC-4 | P0 | `test_apply_sets_only_the_bury_flags_and_assigns_the_preset_to_managed_decks` [repair, create] | the three flags are off on the `<Prefix>` preset; then exactly one preset has that name; every other key is as before (or as Default, for create); every preset deck is on it; Default and the other decks are unchanged |
| AC-5 | P1 | `test_a_refused_preset_save_is_reported_by_verify_and_the_rest_still_applies` | the verification is exactly the preset Repair; then the template is repaired; `saveDeckConfig` was sent; the flag is still on |
| AC-6 | P0 | `test_apply_completes_server_side_when_the_client_disconnects` | the store's apply completed once; then the request was cancelled; the status read `running` mid-run and `finished` with the result after |
| AC-7 | P0 | `test_apply_route_runs_the_confirmed_plan_and_returns_the_verification` [verified, discrepancies] | status 200; then the exact camelCase body; one apply; a second plan hashes to the body's `planHash` |
| AC-8 | P0 | `test_apply_route_refuses_a_stale_plan_with_409_plan_changed` | status 409; then code `plan_changed`, its fixed message and a request id; no apply; the plan is unchanged |
| AC-9 | P1 | `test_apply_status_is_idle_before_a_run_and_finished_with_its_result_after` | the body before any run is `{"state": "idle", "result": null}`; then 200; after a POST, `finished` with the POST's body |
| AC-10 | P0 | `test_apply_is_disabled_with_a_reason_while_a_readiness_check_fails` | Apply setup is disabled; then the reason is visible; the change list still shows |
| AC-11 | P0 | `test_apply_posts_the_plan_hash_and_shows_the_applying_card` | the progress line is visible; then it is in a `status` region; the POST body is `{"planHash"}`; Apply is disabled; the change list is gone |
| AC-12 | P0 | `test_a_verified_run_shows_the_verified_banner` | "Setup applied and verified" is visible; then the `status` banner's detail line; no change list, no Apply, no alert |
| AC-13 | P1 | `test_a_run_with_discrepancies_lists_them_and_offers_run_setup_again` [one, two] | the counted title is visible; then the `alert` banner's explanation; N rows with kind · name and expected/found; no Apply; Run Setup again POSTs the result's `planHash` |
| AC-14 | P1 | `test_leaving_does_not_cancel_and_coming_back_shows_the_run` | after Apply, leaving by nav and coming back mid-run, the progress line is visible; then Apply is disabled; once the status finishes with a result matching the fresh plan, the verified banner replaces it |

## Implementation contract the tests encode

- **`domain/errors.py`:** `ErrorCode.PLAN_CHANGED = "plan_changed"`, message "Anki changed since the preview. Review the changes and apply again.". `app.py` maps it to 409.
- **`AnkiStore.setup_apply(plan_hash: str) -> SetupPreview`** in the port, the adapter and the fake, with the same signature (`tests/unit/test_anki_store_port.py` compares them).
- **`AnkiConnectStore.setup_apply`:**
  - re-diff, refuse, run, verify, all under one lock hold, as in the defaults above;
  - every write through `self._client.invoke`, so the guard sees it (AC-3 spies on `PrefixGuard.check`);
  - `createModel` takes `modelName`, `inOrderFields`, `css` and `cardTemplates` `[{Name, Front, Back}]`;
  - `updateModelTemplates` and `updateModelStyling` take `model: {name, templates | css}`;
  - `modelTemplateAdd` takes `modelName` and `template: {Name, Front, Back}`;
  - `cloneDeckConfigId` takes `name` (no `cloneFrom`), `setDeckConfigId` takes `decks` and `configId`, and `saveDeckConfig` takes `config`.
- **`FakeAnkiStore(verified: SetupPreview | None = None, apply_gated: bool = False)`:** `setup_apply(plan_hash)` does the following, in order.
  - It raises `anki_busy` / `anki_unavailable` like the preview does.
  - It raises `plan_changed` unless the hash is `plan_hash(self.preview.items)`.
  - It counts `apply_calls`. With `apply_gated` it waits for `finish_apply()`, oldest first.
  - It sets `self.preview = verified` (empty by default), counts `applies`, and returns the verification.
- **`SetupService.apply(plan_hash)`** and **`SetupService.apply_status()`** (a plain method) as in the defaults. `ApplyResult` and `ApplyStatus` are TypedDicts like `Readiness`.
- **Routes:** `POST /api/setup/apply` and `GET /api/setup/apply/status`.
- **Screen:**
  - `applySetup(planHash)` and `getApplyStatus()` in `api.js`.
  - In `setup.js`, Apply setup is a `button` named "Apply setup". The reason is plain text, not a `<p>`, before data.
  - The progress card is a `role="status"` region holding the line. The banners are a `role="status"` and a `role="alert"` region, with discrepancy rows as `li` in the alert.
  - Run Setup again is a `button` inside the alert.
  - `mount` starts `getApplyStatus()` before `getHealth()`, and stops polling on unmount.
  - Styles: `progress-card`, `verification-banner-verified`, `verification-banner-discrepancy` and `button-disabled` (DESIGN.md).

## Fixture and support changes (made in this run)

- `tests/support/anki_state.py`:
  - `collection_replies(collection, *, writes=False, refuse_save=False)`: `writes=True` answers `WRITE_ACTIONS` the way AnkiConnect changes Anki, and `refuse_save=True` answers `saveDeckConfig` with `false`.
  - The collection follows AnkiConnect: `createDeck` makes parents on Default, `updateModelTemplates` ignores unknown card names, and `cloneDeckConfigId` without `cloneFrom` clones Default and keeps a duplicate name under its own key.
  - `sent_writes()` lists the writes sent. Story 2.6's preview tests are unchanged (writes stay unanswered by default).
- `tests/support/network.py`: `record_json_bodies(page, path)`.
- `tests/README.md`: both.

## Next Steps (Task-by-Task Activation)

1. Pick a task and remove its `@RED_PHASE` line.
2. Run it, e.g. `uv run pytest tests/integration/test_anki_setup_apply.py`.
3. Watch it fail for the reason above, implement, and watch it pass. Then hoist any in-body imports.
4. If a test fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes:
   - No story 2.7 `RED_PHASE` markers remain.
   - Story 2.6's exact port set includes `setup_apply`.
   - Story 1.3's AD-15 set includes `plan_changed`, and AD-15 in the architecture doc is amended.
   - The story 2.6 E2E module docstring no longer says no Apply button exists.
   - `make test` and `make lint` pass.

Suggested order:

1. `plan_changed` (with the AD-15 amendment).
2. The port, the fake and `AnkiConnectStore.setup_apply` (AC-1 to AC-5).
3. The service (AC-6).
4. The routes (AC-7 to AC-9).
5. The screen (AC-10 to AC-14).

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-14 | Coming back with a `finished` result whose `planHash` differs from the fresh plan shows the current change list with an enabled Apply, and no banner. The hash-compare mutation above survived | P1 |
| AC-8 | On the screen, a 409 `plan_changed` re-reads the plan, shows the current change list and an inline alert with the message | P1 |
| AC-6 | A second POST while a run is in flight awaits the same run (one store apply, two equal bodies) | P1 |
| AC-7 | `anki_busy` / `anki_unavailable` from `setup_apply` give the 503 envelope, and a body without `planHash` the 422 `validation_failed` | P1 |
| AC-1 | Apply holds the Anki lock once from the re-diff to the verify: a concurrent `reachable()` waits | P2 |
| AC-2 | An apply that loses Anki mid-run (a read fails) raises `anki_unavailable`, and the status stays as before the run | P2 |
| AC-2 | A second apply of a verified Prefix sends no write | P2 |
| AC-11 | A double click on Apply setup sends one POST | P2 |
| AC-12 | After a verified run, a reload shows the result banner (status `finished`, hashes equal) | P2 |
| AC-13 | Each expected/found line in the copy table renders for its (action, kind) | P3 |
| AC-11 | Phone width (390): the progress card and banners fit, and Apply is full width | P3 |

## Open items

- **AD-15 amendment.** `plan_changed` (409) is a new code, decided with the user on 2026-10-21. The build amends AD-15 in `architecture-languagelab.md` and story 1.3's code-set test together.
- **`saveDeckConfig` on real Anki.** Spike 2.2 saw `false`, with nothing saved. AnkiConnect's `saveDeckConfig` returns `false` when its save raises, which newer Anki builds may do. If it never works, every run ends with the preset as a discrepancy. Entry 13 on the Mac Mini must show a working save; if it can't, the bury flags need another write path (ticket it).
- **An extra card template** (2.6's `extra-card-template` Repair) is left out of AC-2. `updateModelTemplates` can't remove it, and `modelTemplateRemove` deletes that template's cards. Removing a user's cards needs a decision (likely entry 11's opt-in repairs), so verify keeps reporting it for now.
- **A `<Prefix>` preset no managed deck uses** still previews as Create (2.6 open item), and apply then clones a second one. The simulator keeps both, and verify stays clean once the decks use the new one. A leftover unused preset of the same name stays in Anki.
- **Template normalization.** If Anki rewrites saved templates or CSS (whitespace, line endings), verify reports Repairs after every run (2.6 open item). Entry 13 shows it.
- **Click-first E2E leaves.** AC-11 to AC-14 must click Apply setup before their criterion assertion. In the red phase the click is what fails (the button is new). AC-10 asserts the button itself first.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (the ticket description and verify, AD-3/AD-4/AD-5/AD-15, EXPERIENCE.md Setup strings, the S-SetupStates mockup, spike 2.2, and four decisions recorded with the user). pytest and pytest-playwright are configured, and the dev env runs.
- [x] Every criterion has a stable generated id (AC-1 to AC-14), with no collisions.
- [x] Every leaf's docstring carries exactly one `AC-n`, and each criterion has exactly one red-phase leaf (14 leaves).
- [x] Every scaffold is skipped with a reason naming what re-enables it, and none has placeholder assertions.
- [x] The first assertion is the criterion-defining one. The stand-in run showed each leaf reaching it, and the mutation table shows each failing on its own branch. AC-3's first assertion is non-vacuous (`!= []`).
- [x] No unimplemented setup result is parsed before the criterion assertion. The integration leaves assert on `settle`'s outcome. AC-6 reads its outcome with `getattr`. AC-7 and AC-9's fake construction raises in red, and nothing is derived from it (as story 2.6's AC-9).
- [~] E2E: AC-10 opens on its criterion assertion. AC-11 to AC-14 need the Apply setup click first (see Open items).
- [x] State transitions: AC-2, AC-4 and AC-5 apply and assert the state after it. AC-6 cancels mid-run. AC-14 leaves and returns mid-run.
- [x] Existing tests are unchanged in behavior and pass (472 passed, 29 skipped). `ruff check` and `ruff format --check` are clean.
- [x] Story handoff: there's no story file, so this checklist is the handoff for `bmad-build` on entry 7.
- [x] No browser sessions were opened outside pytest. The unskip plugin and stand-in backups are in the session scratchpad, and the stand-ins were removed from the tree.

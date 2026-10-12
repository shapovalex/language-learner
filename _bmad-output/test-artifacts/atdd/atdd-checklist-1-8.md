---
runScope: 'story'
runKey: 'story-1-8'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-12'
storyId: '1.8'
storyKey: '1-8'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml (entry 8)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-1-8.md'
generatedTestFiles:
  - 'tests/integration/test_release_tag.py'
  - 'tests/integration/test_release_wheel.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (Stack, Structural Seed, Environments)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-1, AC1)'
  - '_bmad-output/test-artifacts/test-design/test-design-epic-1.md'
  - '_bmad-output/test-artifacts/ci/ci-pipeline-progress.md'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-1-7.md'
  - '.github/workflows/test.yml'
  - 'pyproject.toml'
  - 'Makefile'
  - 'src/language_lab/__init__.py'
  - 'src/language_lab/app.py'
  - 'tests/README.md'
  - 'tests/conftest.py'
  - 'tests/support/app_env.py'
  - 'tests/support/startup.py'
  - 'tests/support/live_server.py'
  - 'tests/integration/test_startup_config.py'
  - 'tests/api/test_app.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'On a vX.Y.Z tag, .github/workflows/release.yml runs ruff and pytest with Playwright browsers installed' }
  - { id: 'AC-2', idSource: 'generated', text: 'The workflow fails if the tag differs from the pyproject version' }
  - { id: 'AC-3', idSource: 'generated', text: 'The workflow builds the wheel with uv' }
  - { id: 'AC-4', idSource: 'generated', text: 'The wheel is attached to a GitHub release: pushing v0.1.0 produces a GitHub release with the wheel' }
  - { id: 'AC-5', idSource: 'generated', text: '`uvx --from <release asset URL> language-lab` starts and loads ~/.config/language-lab/.env' }
  - { id: 'AC-6', idSource: 'generated', text: 'The started release listens on 127.0.0.1 only' }
---

# ATDD Checklist: Story 1.8, Tag-triggered release workflow

## Run context

- **Story source:** epic-platform-baseline `tickets.toml` entry 8. There is no story file. AC-1 to AC-4 come from the ticket's description in source order. AC-5 and AC-6 are the `verify` clauses about running the release. The verify clause "pushing v0.1.0 produces a GitHub release with the wheel" repeats the description, so it joins AC-4. All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). Everything here is a subprocess or the built wheel, so the level is Integration (`tests/integration`). The test design puts both the release guard and the built-wheel smoke at that level.
- **Test design:** `test-design-epic-1.md`, R-04 (OPS, score 4): the released wheel doesn't run because assets aren't packaged, the tag ≠ the pyproject version, or deps don't install. Rows: built-wheel smoke (P0, Integration, "runs in CI before the release upload"); release fails on a tag/version mismatch (P1, Integration, "a script step unit-tested locally"); the Mac Mini release run (P0, Manual, R-04 and R-12). The execution strategy puts WebKit E2E and the wheel smoke on every `vX.Y.Z` tag.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node. No browser is involved in these tests.
- **Affected components:** new `.github/workflows/release.yml`, new `scripts/check_release_tag.py`. `src/` is unchanged: the wheel already packages its assets (entry 1) and loads `~/.config/language-lab/.env` (entry 2).
- **Existing tests:** none change. `tests/conftest.py` gains the `--wheel` option and loads the new `release` fixtures.

### Decisions taken with the user (2026-10-12)

| Question | Decision |
| --- | --- |
| How the tag/version guard is built | **A Python script, `scripts/check_release_tag.py <tag>`.** It reads the version from `pyproject.toml` with `tomllib` and exits non-zero, naming both values, unless the tag is exactly `v<version>`. release.yml passes the tag through `env:`, which avoids script injection (ci-burn-in). The script is tested through a subprocess. |
| A structural test of release.yml | **None.** There's no YAML parser in the dev deps, and entry 1 decided no later entry adds any. The wiring (AC-1, AC-4) is checked by `actionlint` and by the HITL `v0.1.0` push, which the ticket's verify already requires. |
| Where the built-wheel smoke runs | **The default suite, plus `--wheel`.** It lives in `tests/integration` and runs on every push (about 1.5 s on a warm uv cache). By default it builds its own wheel. release.yml runs `uv build` first and then `pytest --wheel dist/<wheel>`, so the smoke runs against the exact file that gets attached. |

## Generation mode (step 2)

AI generation. The stack is `backend`, so step 2 skips recording. Nothing here has a UI.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Manual (HITL) + actionlint | P1 | The `v0.1.0` run shows ruff, Playwright install and pytest steps passing before build and upload | n/a (user decision: no YAML test) |
| AC-2 | Integration | P1 | Run the guard with `v<version>`, `v<next patch>`, `<version>`, `v<version>-rc1` | exit code: `0` for the match, `1` otherwise |
| AC-3 | Integration | P0 | `uv build --wheel` (or `--wheel`), start it under uvx, GET `/api/health`, a versioned asset, a deep client path | `/api/health` is `{"version": <pyproject version>}` |
| AC-4 | Manual (HITL) | P0 | Push `v0.1.0` | n/a: the GitHub release `v0.1.0` has `language_lab-0.1.0-py3-none-any.whl` |
| AC-5 | Integration + Manual on the Mac Mini | P0 | `uvx --from <wheel> language-lab`, with the port and tailnet host only in the temp HOME's `~/.config/language-lab/.env` | startup prints `LanguageLab running at http://127.0.0.1:<that port>/` |
| AC-6 | Integration + Manual on the Mac Mini | P0 | The same run. Connect to this machine's non-loopback address on the port | `ConnectionRefusedError` |

- **One leaf per automated criterion.** AC-2 is parametrized over four tags in one leaf. The matching tag is a case in it so that a guard which always fails can't pass. AC-3, AC-5 and AC-6 share one module-scoped uvx run (`released_app`), and each owns its own assertion.
- **AC-1 and AC-4 have no automated leaf.** That's the user's decision above. They're the manual checks below, and the ticket is `hitl = true` for exactly this run.
- **AC-5 proves the file was read, not just that startup succeeded.** The subprocess env has every app variable stripped (`isolated_environ`), and `LANGUAGE_LAB_PORT` and `LANGUAGE_LAB_PUBLIC_HOST` appear only in the temp HOME's `.env`. If release mode read anything else, the app would fail to start (no config) or bind 8787.
- **AC-6 makes a real connection.** On a machine with no non-loopback address it skips with a reason, which is the only branch. CI runners and the dev Mac both have one.
- **What's red and what's already green.** AC-2 is red: the script doesn't exist. **AC-3, AC-5 and AC-6 pass today when un-skipped**, because entries 1 and 2 built that behaviour. This story's job is to run them against the artifact it releases. They're skipped under the same `RED_PHASE` marker so they're switched on together with the `--wheel` step in release.yml. This is a regression guard for R-04, not a red phase, and it's reported as such.

## TDD Red Phase (Current)

Scaffolds generated: **4 leaves, 7 cases, all `@RED_PHASE` (`pytest.mark.skip`)**. Execution was sequential: one backend level, no API or E2E split.

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/integration/test_release_tag.py` | Integration | 1 (4): AC-2 |
| `tests/integration/test_release_wheel.py` | Integration | 3 (3): AC-3, AC-5, AC-6 |

Observed with the skip markers stripped (a scratchpad plugin, not committed):

- AC-2, 4 cases fail at the first assertion: `assert 2 == 0` / `assert 2 == 1`, from `can't open file '…/scripts/check_release_tag.py'`.
- AC-3, AC-5, AC-6: **3 passed** (see above). The same 3 pass with `--wheel <a wheel built separately>`.

**Green feasibility, checked and removed.** A throwaway `scripts/check_release_tag.py` (eight lines: `tomllib`, compare against `f"v{version}"`, print both values, exit 1 on a mismatch) turned AC-2 green. Mutations were caught as follows:

| Mutation | Caught by |
| --- | --- |
| Accepts the tag without `v` (`tag.lstrip("v") == version`) | AC-2 `missing-v` |
| Prefix match (`tag.startswith(f"v{version}")`) | AC-2 `pre-release-suffix` |
| Never fails | AC-2 `next-patch`, `missing-v`, `pre-release-suffix` |
| The release binds `0.0.0.0` (`LANGUAGE_LAB_HOST` in the home `.env`) | AC-6 (`DID NOT RAISE ConnectionRefusedError`) and AC-5 (the startup line) |

The stand-in and the fixture mutation were removed, and `scripts/` doesn't exist. With the scaffolds skipped, the whole suite stays green (167 passed, 56 skipped), and `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P1 | Manual 1 and 2 below | — |
| AC-2 | P1 | `test_release_tag_must_equal_pyproject_version` [matching, next-patch, missing-v, pre-release-suffix] | exit code; then the output names the tag and the version, with no traceback |
| AC-3 | P0 | `test_built_wheel_serves_its_version_assets_and_shell` | `/api/health` == `{"version": VERSION}`; then `/static/<VERSION>/main.js` is 200 JavaScript; `/any/deep/path` is the HTML shell referencing it |
| AC-4 | P0 | Manual 2 below | — |
| AC-5 | P0 | `test_uvx_start_loads_the_home_config` (+ Manual 3) | `LanguageLab running at http://127.0.0.1:<port from .env>/`; then `https://<tailnet host from .env>/`; no traceback |
| AC-6 | P0 | `test_uvx_start_listens_on_loopback_only` (+ Manual 3) | the LAN address refuses the port; then 127.0.0.1 answers `/api/health`; uvicorn reports `http://127.0.0.1:<port>` |

### Manual checks (HITL, the user)

1. **actionlint** on the new workflow is clean: `uvx --from actionlint-py actionlint .github/workflows/release.yml` (or a brew install). Covers AC-1's wiring.
2. **Push `v0.1.0`.** The release run is green, with ruff, Playwright install, pytest (including the `--wheel` smoke) and the guard all passing before upload. The GitHub release `v0.1.0` has `language_lab-0.1.0-py3-none-any.whl` attached (AC-1, AC-4).
3. **On the Mac Mini:** `uvx --from <release asset URL> language-lab` starts and prints `LanguageLab running at http://127.0.0.1:8787/` and the Tailscale URL (it read `~/.config/language-lab/.env`). `lsof -nP -iTCP:8787 -sTCP:LISTEN` shows `127.0.0.1` only, and `<LAN IP>:8787` is unreachable from another device (AC-5, AC-6, R-12).

## Implementation contract the tests encode

- **`scripts/check_release_tag.py <tag>`:** reads `[project].version` from the repo's `pyproject.toml`. It exits `0` only when `tag == f"v{version}"`, and `1` for anything else (another version, no `v`, any suffix). Either way it prints one line naming both the tag and the version, and never a traceback. The tests run it with the venv's Python from the repo root, as release.yml will. It's ruff-clean (`ruff check .` covers `scripts/`).
- **`.github/workflows/release.yml`:**
  - Trigger: `push: tags: ["v*.*.*"]`. The script is what enforces exactly `vX.Y.Z`.
  - Before anything is built: the guard, with the tag passed through `env:` (`TAG: ${{ github.ref_name }}`, then `run: uv run python scripts/check_release_tag.py "$TAG"`).
  - Lint and tests: `uv run ruff check .`, `uv run ruff format --check .`, `uv run playwright install --with-deps chromium webkit`, then `uv build --wheel` and `uv run pytest --browser chromium --browser webkit --wheel dist/<wheel>`. That covers the WebKit-on-tags row of the test design, and the smoke runs on the file that gets uploaded.
  - Upload only after all of the above pass, in a job (or step) that has `permissions: contents: write`. The other jobs keep `contents: read`. Use `softprops/action-gh-release` v3 (architecture Stack) with `files: dist/*.whl`. The asset name `language_lab-X.Y.Z-py3-none-any.whl` is what entry 9's docs will cite.
- **`uv` on PATH** for pytest: the wheel tests call `uv build` and `uvx`. setup-uv provides it in CI. They reuse `UV_CACHE_DIR` (or `uv cache dir`), so a warm cache keeps them around 1.5 s.
- **Server:** unchanged.

## Fixture and support changes (made in this run)

- `tests/support/release.py` (new): `REPO_ROOT`, `RELEASE_TAG_SCRIPT`, `pyproject_version()`, `next_patch()`, `run_tag_check()`, `build_wheel()`, `uv_cache_dir()`, `non_loopback_address()`, and `run_released_app()`. That last one runs `uvx --python <venv python> --from <wheel> language-lab` and waits for uvicorn's listening line through a reader thread and a queue deadline, not a sleep. It raises with the output if startup exits first.
- `tests/support/fixtures/release.py` (new): `release_wheel` (session: `--wheel PATH`, else a fresh build), and `released_app` (module: a temp HOME whose `~/.config/language-lab/.env` holds a full `config_values()` with a free port, and an env from `isolated_environ` plus `UV_CACHE_DIR`).
- `tests/conftest.py`: the `--wheel PATH` option, and `tests.support.fixtures.release` in `pytest_plugins`.
- `tests/README.md`: the `--wheel` run line, `release.py` under support, and the two fixtures.

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` line.
2. Run it: `uv run pytest tests/integration/test_release_tag.py` or `uv run pytest tests/integration/test_release_wheel.py`.
3. AC-2: watch it fail for the reason above, write the script, and watch it pass. AC-3, AC-5 and AC-6 pass at once. Un-skip them in the same change that adds the `--wheel` step to release.yml.
4. If a test fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes: no `RED_PHASE` markers remain in the two files; `make test` and `make lint` pass; actionlint is clean; Manual checks 2 and 3 are done.

Suggested order: AC-2 (script) → release.yml → AC-3, AC-5, AC-6 → actionlint → push `v0.1.0` → the Mac Mini run.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-4 | The wheel's filename version equals the tag's version (`language_lab-<X.Y.Z>-…` for `vX.Y.Z`), so the asset name in docs (entry 9) can't drift | P2 |
| AC-3 | The built wheel contains the Figtree license and every file under `static/` (a zip listing against the source tree) | P2 |
| R-04 | An optional `macos-14` job that smokes the wheel with uvx, since Linux CI doesn't prove the macOS install | P2 |
| AC-2 | The guard rejects an empty argument and extra arguments with a usage line, not a traceback | P3 |
| AC-6 | `localhost` (IPv6 `::1`) is refused too, or answers, depending on what uvicorn binds; decide and pin | P3 |

## Open items

- **AC-3, AC-5 and AC-6 aren't red.** The behaviour exists from entries 1 and 2. The story adds running them against the released artifact. They were checked green against a fresh build and against `--wheel`, and the bind mutation shows AC-5 and AC-6 can fail.
- **AC-1 and AC-4 rest on the HITL run.** That was chosen over a YAML test without a parser. If the workflow grows, revisit adding a parser to the dev deps.
- **test.yml also triggers on `v*` tags.** A tag will run both workflows (test.yml's WebKit job and release.yml). The implementer should decide whether test.yml drops its tag trigger now that release.yml runs the same set.
- **Action versions differ.** The architecture pins checkout v7 and setup-uv v10. test.yml uses v5 and v6. release.yml should follow the architecture. Aligning test.yml is out of scope (entry 11 sweep).
- **The wheel tests need `uv` and a warm cache.** On a cold cache, uvx downloads the dependencies (about 20 MB with `av`). The start timeout is 60 s.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (ticket description and verify, plus decisions recorded with the user), pytest is configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-6), and no supplied ids collide
- [x] Every new leaf maps to exactly one AC (docstring `AC-n:`). AC-2, AC-3, AC-5 and AC-6 each have exactly one leaf. AC-1 and AC-4 are manual by the user's decision (deviation recorded)
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one. AC-2's red failure was observed at it. AC-3, AC-5 and AC-6 are reported as already green, not as red
- [x] No unimplemented setup response is parsed before the criterion assertion
- [x] Existing tests are unchanged and pass (167 passed, 56 skipped). `ruff check` and `ruff format --check` are clean
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `bmad-build` on entry 8
- [x] No browser sessions were opened. The unskip plugin, the probe wheel and the fixture backup are in the session scratchpad, and `scripts/` was removed after the stand-in check

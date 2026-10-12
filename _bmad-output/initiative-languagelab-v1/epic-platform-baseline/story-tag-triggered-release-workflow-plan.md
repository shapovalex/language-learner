---
title: 'Tag-triggered release workflow'
type: 'feature'
ticket: '8'
created: '2026-10-12'
status: 'built'
baseline_revision: '83e05b89ddaeeefda88b2dd4c9d25b189f24d413'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-1-8.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing turns a version into a release. AC1 needs a `vX.Y.Z` tag to produce a GitHub release whose wheel runs with `uvx --from <asset URL> language-lab`, and R-04 needs that release blocked when the tag and the pyproject version disagree or the wheel doesn't run.

**Approach:** Add `scripts/check_release_tag.py` and `.github/workflows/release.yml`. On a `v*.*.*` tag the workflow checks the tag, then runs ruff, builds the wheel with uv, and runs pytest with Chromium and WebKit with `--wheel dist/<wheel>`. Only after all of that passes does a separate job attach the wheel to a GitHub release. Make the ATDD scaffolds from 83e05b8 pass.

## Boundaries & Constraints

**Always:**
- Implement the "Implementation contract the tests encode" in the ATDD checklist (`context`) for the script and the workflow.
- The guard script uses the stdlib only (`tomllib`, `sys`, `pathlib`). It reads `pyproject.toml` relative to its own file, not the cwd. It prints one line naming the tag and the version. It exits 0 only when `tag == f"v{version}"` and 1 otherwise. A missing argument or extra arguments get a usage line and exit 2, with no traceback.
- release.yml passes the tag through `env:` and never interpolates `${{ }}` into a `run:` script. Workflow-level `permissions: contents: read`. Only the publish job gets `contents: write`, and it needs the build job.
- Pin actions per the architecture Stack: `actions/checkout@v7`, `astral-sh/setup-uv@v10`, `softprops/action-gh-release@v3`. Use `actions/upload-artifact@v4` / `download-artifact@v4` as test.yml does. Set `UV_LOCKED: "1"`.
- The release asset is the one wheel `language_lab-X.Y.Z-py3-none-any.whl`. pytest smokes that exact file before it is uploaded.
- Decision (2026-10-12): test.yml drops its `v*` tag trigger, its `webkit` job, and the WebKit row and `needs` entry in its report. release.yml is the only tag pipeline.
- Remove every `RED_PHASE` marker in `tests/integration/test_release_tag.py` and `tests/integration/test_release_wheel.py`. Don't weaken any first assertion.

**Never:**
- No new dependencies, and no change to `src/`.
- Don't push a tag or create a release. The `v0.1.0` push and the Mac Mini run are the user's HITL checks.
- No sdist, no PyPI publish, no macOS job. Those are the P2 backlog.
- No `docs/` pages. They belong to entry 9.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Matching tag | `v0.1.0`, pyproject `0.1.0` | exit 0, line names both | No error expected |
| Wrong version | `v0.1.1` | exit 1, line names both | Workflow stops before build |
| No `v` / suffix | `0.1.0`, `v0.1.0-rc1` | exit 1, line names both | Same as above |
| Bad usage | no argument, or two | usage line on stderr, exit 2 | No traceback |
| Wheel smoke | `pytest --wheel dist/<wheel>` | AC-3, AC-5, AC-6 run on that file | Any failure blocks the publish job |

</frozen-after-approval>

## Code Map

- `scripts/check_release_tag.py` (new) -- the guard. `ruff check .` and `ruff format --check .` already cover `scripts/`.
- `.github/workflows/release.yml` (new) -- two jobs. `build` (contents: read): checkout, setup-uv with cache, `uv sync`, guard with `TAG: ${{ github.ref_name }}`, ruff check and format check, Playwright browser cache (key `…-playwright-release-${{ hashFiles('uv.lock') }}`), `uv run playwright install --with-deps chromium webkit`, `uv build --wheel`, `uv run pytest --browser chromium --browser webkit --wheel dist/language_lab-*.whl --junitxml=test-results/junit-release.xml`, then upload `dist/*.whl` as an artifact (test-results on `always()`). `publish` (needs build, contents: write): download the artifact to `dist/` and run action-gh-release with `files: dist/*.whl`.
- `.github/workflows/test.yml` -- triggers on `v*` tags today and has a tag-only `webkit` job. Remove the `tags: ["v*"]` trigger, the `webkit` job, `webkit` from `report.needs`, the `WEBKIT_RESULT` env and its summary row, and the "vX.Y.Z tag" line in the header comment.
- `tests/integration/test_release_tag.py`, `tests/integration/test_release_wheel.py` -- delete the `RED_PHASE` definition and each `@RED_PHASE` line, and the "Skipped until…" / "It is skipped so…" docstring sentences.
- `tests/support/release.py`, `tests/support/fixtures/release.py`, `tests/conftest.py` (`--wheel`) -- reuse them and don't change them. `run_tag_check` runs the script with `sys.executable` from the repo root.
- `tests/README.md` -- already lists `--wheel` and the fixtures. No change.
- `Makefile` -- no change. `make test` now builds a wheel and runs uvx, so `uv` must be on PATH; test.yml has it through setup-uv.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/check_release_tag.py` -- the guard per Boundaries -- AC-2, R-04
- [x] `.github/workflows/release.yml` -- as mapped -- AC-1, AC-3, AC-4
- [x] `.github/workflows/test.yml` -- drop the tag run as mapped -- one tag gate
- [x] `tests/integration/test_release_tag.py`, `tests/integration/test_release_wheel.py` -- un-skip as mapped. Add the P3 backlog case: no argument and two arguments exit 2 with no traceback -- matrix

**Acceptance Criteria:**
- Given the repo, when `make lint` and `make test` run, then both pass and no `RED_PHASE` marker remains.
- Given the new workflow, when actionlint runs on it, then it reports nothing.
- Given a fresh `uv build --wheel`, when `uv run pytest tests/integration --wheel dist/<wheel>` runs, then the wheel tests pass against that file.

## Implementation Notes

- Implemented by a coding subagent from this plan. The guard prints `Release tag <tag> matches|does not match pyproject version <version>`. On bad usage it prints `usage: check_release_tag.py <tag>` to stderr and exits 2.
- release.yml: `build` uploads the wheel with `if-no-files-found: error`, and `publish` passes `fail_on_unmatched_files: true`. The concurrency group doesn't cancel in-progress runs. All tasks are checked.
- Left as is: the `Makefile` comment "Tag runs: E2E under WebKit" on `test-webkit` is now slightly stale, because the plan says not to change the Makefile.
- Results: `make lint` passes, and `make test` gives 234 passed with 0 skipped (subagent). actionlint is clean on both workflows. `--wheel dist/<wheel>` gives 16 passed in tests/integration. Re-run here: the two release files give 9 passed with 0 skipped.
- Matrix audit: matching, wrong version, missing `v` and suffix → `test_release_tag_must_equal_pyproject_version` (4 cases). Bad usage → `test_release_tag_guard_rejects_bad_usage` (2 cases). Wheel smoke → the 3 tests in `test_release_wheel.py`. All of them ran and passed.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 1, low 1, false 2, maybe-false 0.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `tests/README.md` CI section and `make test-webkit` row; `Makefile` `test-webkit` comment | Still describes test.yml's tag trigger, its WebKit job and the `test-results-webkit` artifact, all of which this change removed. release.yml isn't mentioned | medium | patch | Confirmed at README lines 20 and 109–121. Docs-only fix, no public surface. Rewritten to describe release.yml as the tag pipeline. |
| 2 | `scripts/check_release_tag.py` `main` | `""` exits 1 as a mismatch instead of 2 as a usage error (ATDD P3 backlog row) | low | patch | Reproduced by the reviewer. Unreachable from a tag push (`ref_name` is never empty), but the fix is a one-condition correction. An `empty-argument` test case was added. |
| 3 | `scripts/check_release_tag.py` pyproject read | A missing or malformed pyproject prints a traceback | false | reject | The script reads the pyproject next to it in the same checkout. No reachable path has it missing or malformed, and failing loudly there is acceptable. |
| 4 | `release.yml` pytest step | A skipped AC-6 would still publish | false | reject | AC-6 skips only when there is no non-loopback interface. GitHub ubuntu runners always have one, since checkout and uv need network. The skip is the documented branch for such machines, per the ATDD checklist. |

## Design Notes

The publish job is separate so `contents: write` never coexists with running repo code (tests, uv sync). The build job hands over only the wheel. The pytest glob relies on `dist/` holding exactly one wheel on a fresh runner.

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass, 0 skipped from story 1.8
- `uvx --from actionlint-py actionlint .github/workflows/release.yml .github/workflows/test.yml` -- expected: no output
- `rm -rf dist && uv build --wheel && uv run pytest tests/integration --wheel dist/language_lab-0.1.0-py3-none-any.whl` -- expected: pass
- `uv run python scripts/check_release_tag.py v0.1.0; echo $?` -- expected: one line, `0`

**Manual checks (if no CLI):**
- The user pushes `v0.1.0`: the release run is green and the GitHub release has the wheel. On the Mac Mini, `uvx --from <asset URL> language-lab` prints the 127.0.0.1 URL and the Tailscale URL, and `lsof -nP -iTCP:8787 -sTCP:LISTEN` shows 127.0.0.1 only.

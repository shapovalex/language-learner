---
title: 'Install and configuration docs'
type: 'feature'
ticket: '9'
created: '2026-10-13'
status: 'built'
baseline_revision: 'fa9323067b85a19c454747a4a564a051f5abcd72'
route: 'full'
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

**Problem:** There is no `docs/`. FR-4 and the epic's Done-when 4 need first-time install and configuration docs, and entry 10 (device acceptance) has the user follow them on the Mac Mini. The README covers part of it, still says to build a wheel by hand, and lacks the keyless-AnkiConnect warning, the Study convention, and backup advice.

**Approach:** Add `docs/` pages for install, configuration, remote access, Anki conventions, and development, plus a unit test that keeps their commands, keys, and release asset name equal to the repo (R-13).

## Boundaries & Constraints

**Always:**
- Each FR-4 item in scope maps to one named heading: every config key explained (pointing at the packaged `env.example`), the one-time Tailscale Serve command, the keyless-AnkiConnect warning, study `<Prefix>::Study` and never the `<Prefix>` root, back up Anki before Setup or a migration.
- Also covered: install with the `uvx --from <release asset URL> language-lab` command; the `.env` location, that the app creates it with mode 600, and `chmod 600` for a hand-made file; dev mode with `LANGUAGE_LAB_DEV=1` and the `LanguageLabDev` Prefix.
- The install command names the current pyproject version and its real GitHub release asset URL. The test fails when they differ, so a version bump updates the docs.
- State only what the code does today. Where a page mentions Setup, migrations, or decks that later epics build, say they arrive with those features.
- Decision (2026-10-13): slim the README. It keeps the overview, requirements, a short quick start, and links into `docs/`. The install, Tailscale Serve, and configuration detail moves to `docs/`, and the hand-built-wheel step is removed. `docs/` is the one source of truth.
- Plain, direct prose in the README's existing voice. Commands in fenced `sh` blocks.

**Never:**
- No change under `src/`, no new dependency, no docs site generator.
- No model-evaluation fixtures doc (epic-capture-to-item) and no upgrade/never-downgrade or full-sync docs (epic-anki-setup-sync).
- No background-service, auto-start, or LAN-bind instructions (FR-1 out of scope, NFR-5).
- No real key, tailnet name, or machine name; use `mac-mini.tailnet-name.ts.net` as the README does.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Docs match repo | docs as written | consistency test passes | None |
| Version bump | pyproject version changed, docs not | test fails naming the stale asset URL | Fix docs |
| Unknown key | docs name a `LANGUAGE_LAB_*`/`ANKI_*`/`AZURE_*`/`OPENROUTER_*` key Settings lacks | test fails naming the key | Fix docs |
| Missing key | a Settings key absent from the configuration page | test fails naming the key | Fix docs |
| Renamed heading | an FR-4 heading removed | test fails naming the FR-4 item | Fix docs or the map |
| Broken link | a relative link in `docs/` or README to a missing file | test fails naming the link | Fix link |

</frozen-after-approval>

## Code Map

- `docs/` -- does not exist. New: `README.md` (index), `install.md`, `configuration.md`, `remote-access.md`, `anki.md`, `development.md`.
- `README.md` -- source for most wording: requirements, first-start prompt, startup lines, `tailscale serve --bg 8787` with status/reset, the macOS CLI path, the allow-list paragraph, the key table. Its "1. Build a wheel" step predates release.yml.
- `pyproject.toml` -- `[project.scripts] language-lab`, `version = "0.2.0"`.
- `.github/workflows/release.yml` -- attaches `dist/*.whl`. Live asset: `https://github.com/shapovalex/language-learner/releases/download/v0.2.0/language_lab-0.2.0-py3-none-any.whl` (public repo, no auth).
- `src/language_lab/settings.py` -- `Settings` (ten keys and defaults), `HOME_ENV_RELATIVE`, `DEV_PREFIX`, `PREFIX_PATTERN`, `NECESSARY_KEYS`, `create_config` (0600, never touches an existing file), the dev-prefix rule. Read only.
- `src/language_lab/env.example` -- the packaged template FR-4 calls `.env.example`; documents every key. Read only.
- `src/language_lab/app.py` `main()` -- the two startup lines; a no-terminal first start writes the file and exits.
- `tests/support/release.py` (`pyproject_version()`, `REPO_ROOT`), `tests/support/app_env.py` (`dotenv_keys()`) -- reuse in the test.

## Tasks & Acceptance

**Execution:**
- [x] `docs/install.md` -- requirements, the `uvx --from <asset URL> language-lab` command, first-start config prompt, startup lines, stopping -- FR-1, FR-4
- [x] `docs/configuration.md` -- file locations per mode, mode 600 and `chmod 600`, env overrides, every key with default and meaning, pointer to `env.example` -- FR-4, AD-18
- [x] `docs/remote-access.md` -- one-time `tailscale serve --bg 8787`, status/reset, macOS CLI path, allow-list and `LANGUAGE_LAB_PUBLIC_HOST`, port-change note -- FR-2, FR-4
- [x] `docs/anki.md` -- keyless-AnkiConnect warning, Prefix and the `::Study` convention, backup before Setup or a migration -- FR-4
- [x] `docs/development.md` -- clone, `uv sync`, `LANGUAGE_LAB_DEV=1 uv run language-lab`, `LanguageLabDev` and the refused release Prefix, test and lint commands -- epic Done-when 5
- [x] `docs/README.md` -- index with a table mapping each FR-4 item to its page and heading
- [x] `README.md` -- slim to overview, requirements, quick start (release command and dev command), and links into `docs/`; drop "Build a wheel" and the key table -- one source of truth
- [x] `tests/unit/test_docs_consistency.py` -- one test per matrix row, plus: every `language-lab` invocation uses the console-script name, and the `tailscale serve` port is the Settings default -- R-13, entry 9 verify

**Acceptance Criteria:**
- Given the repo, when `make lint` and `make test-fast` run, then both pass.
- Given `docs/README.md`, when a reader follows its FR-4 table, then each in-scope FR-4 item lands on a heading that states it.
- Given the install page's command, when it is run on a machine with uv, then it starts the released app.

## Implementation Notes

- The test's FR-4 map rows are `(item, file, heading, phrases)`: besides the heading existing, the text under it must contain the phrases, and `docs/README.md` must link to `file#anchor`. Anchors in relative links are checked against GitHub-style heading slugs.
- Two checks beyond the plan's list, both guarding a stated constraint: every `*.ts.net` name is the `mac-mini.tailnet-name.ts.net` placeholder, and the README links to every page in `docs/`.
- Prose does not repeat the version number; only the asset URL carries it (install.md, configuration.md's override example, README quick start), and all three are checked.
- The pages say this release does not talk to Anki yet and that the Anki, Azure and OpenRouter values are read and validated but not used.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 0, low 9, false 0, maybe-false 0. One further finding asked for edits to this plan and was rejected on that ground.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `docs/remote-access.md` "Allowed hosts" | The `.env` line `LANGUAGE_LAB_PUBLIC_HOST=…` is in an `sh` block, so it reads as a command; in a shell it changes nothing | low | patch | Confirmed in the diff. The plan keeps `sh` blocks for commands. Fence label changed and the placeholder named. |
| 2 | `README.md` overview and Anki requirement | Says the app stores everything in Anki and needs Anki running, while `docs/install.md` and `docs/anki.md` say this release does not talk to Anki | low | patch | The lines are unchanged from baseline but the slimmed README now contradicts `docs/`, which the plan makes the one source of truth. `app.py` has no Anki access. Wording aligned. |
| 3 | `docs/configuration.md` "Configuration keys" | "a new `.env` is that file with your answers filled in" is wrong in dev mode | low | patch | `render_config()` sets `ANKI_PREFIX=LanguageLabDev` when `dev` is true. Exception stated. |
| 4 | `src/language_lab/env.example`, `LANGUAGE_LAB_PUBLIC_HOST` comment | The template says "Leave empty if you only use it on this machine" and does not mention discovery, unlike the docs table | low | defer | Pre-existing, and `src/` is off limits here. `with_tailnet_host()` does discover when empty. Logged in deferred-work.md. |
| 5 | `tests/unit/test_docs_consistency.py` `_UV_RUN` | Every `uv run <anything>` in an `sh` block counts as an app invocation, so `uv run pytest` in the docs would fail with a console-script message | low | patch | The regex is `\buv run (\S+)`. `tests/README.md` already uses such commands, so a docs author would meet it. Narrowed to the plan's wording. |
| 6 | `tests/unit/test_docs_consistency.py` | The key table's Default column and the `curl`/URL port are not compared with Settings | low | reject | True, but a changed default is unlikely and the fix adds new parsing and assertions beyond the ticket's verify (console script, settings keys, release asset name). |
| 7 | `tests/unit/test_docs_consistency.py` `test_no_page_names_another_release_asset` | The README and `configuration.md` URLs are checked for staleness only; replacing the README command with a local path would pass | low | reject | That replacement is a deliberate edit, not drift. The drift case, a stale version, is caught on all three pages. |
| 8 | `tests/unit/test_docs_consistency.py` `_LINK` | Links with a title or reference-style links are not seen | low | reject | None exist in the docs or README. Supporting them adds parsing for a case nobody has written. |
| 9 | `tests/unit/test_docs_consistency.py` `test_heading_states_the_item` | `phrases: tuple[str]` annotates one element; rows pass two | low | patch | Confirmed in `FR4_MAP`. Changed to `tuple[str, ...]`. |
| 10 | this plan, Design Notes and Code Map | Design Notes says three-field map rows and Code Map says `dotenv_keys()`; the test uses four fields and `settings_env_names()` | low | reject | The fix is to edit this build's plan. Implementation Notes already records the four-field rows. |

## Design Notes

The test reads code blocks and inline code with regexes, no Markdown library. Keys are detected by the four env prefixes. The FR-4 map lives in the test as `(item, file, heading)` rows, so a rename is a deliberate edit.

## Verification

**Commands:**
- `make lint && make test-fast` -- expected: all pass
- `uv run pytest tests/unit/test_docs_consistency.py -v` -- expected: every case passes
- `curl -sIL -o /dev/null -w '%{http_code}\n' <the asset URL in docs/install.md>` -- expected: `200`

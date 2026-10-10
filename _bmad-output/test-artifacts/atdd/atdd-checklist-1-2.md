---
runScope: 'story'
runKey: 'story-1-2'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-10'
storyId: '1.2'
storyKey: '1-2'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml (entry 2)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-1-2.md'
generatedTestFiles:
  - 'tests/unit/test_settings_load.py'
  - 'tests/integration/test_startup_config.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md'
  - '_bmad-output/test-artifacts/test-design/test-design-epic-1.md'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md (A1, A2)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-4, AD-17, AD-18)'
  - 'pyproject.toml'
  - 'tests/conftest.py'
  - 'tests/README.md'
  - 'tests/support/fixtures/settings.py'
  - 'tests/support/live_server.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'Release mode loads ~/.config/language-lab/.env once at startup with every A2 key plus LANGUAGE_LAB_PUBLIC_HOST and LANGUAGE_LAB_DEV' }
  - { id: 'AC-2', idSource: 'generated', text: 'Unknown keys in the .env are ignored (extra=ignore)' }
  - { id: 'AC-3', idSource: 'generated', text: 'An invalid ANKI_PREFIX aborts startup with a non-zero exit and no secret echoed' }
  - { id: 'AC-4', idSource: 'generated', text: 'The dev flag (LANGUAGE_LAB_DEV) is exposed in Settings' }
  - { id: 'AC-5', idSource: 'generated', text: 'Dev mode reads the gitignored repo-root .env instead of ~/.config/language-lab/.env' }
  - { id: 'AC-6', idSource: 'generated', text: 'Dev mode refuses ANKI_PREFIX=LanguageLab (case-insensitively, per Q5)' }
  - { id: 'AC-7', idSource: 'generated', text: 'OPENROUTER_MODELS parses to a list in the configured order' }
  - { id: 'AC-8', idSource: 'generated', text: 'Every Settings field is present in a documented .env.example' }
---

# ATDD Checklist: Story 1.2, Configuration from ~/.config/language-lab/.env

## Run context

- **Story source:** epic-platform-baseline `tickets.toml` entry 2. There is no story file, so the criteria come from the ticket's description and `verify` clauses in source order, with generated ids AC-1 to AC-8.
- **Stack:** `backend` (pyproject, pytest). Mode: AI generation. There's no browser recording and no E2E: the story has no UI.
- **Execution:** sequential. There was one worker (API/unit/integration), and the E2E worker had nothing to produce.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node (test design, Not in Scope).
- **Test design:** `test-design-epic-1.md`. Risks: R-06 (secret echo), R-11 (dev Prefix guard), R-12 (bind default) and R-13 (`.env.example` drift).

### Decisions taken with the user (2026-10-10)

| Question | Decision |
| --- | --- |
| Q5: refuse `LanguageLab` case-insensitively in dev mode? | **Yes.** Anki deck names compare case-insensitively (R-11). |
| Load seam | **`language_lab.settings.load_settings() -> Settings`**. It reads `LANGUAGE_LAB_DEV` from the process env, picks the file and validates. `main()` calls it. `Settings(**overrides)` stays constructible directly. |
| Where is the dev "repo-root .env"? | **`./.env` in the current working directory.** `uv run language-lab` runs from the repo root. |

## TDD Red Phase (Current)

✅ Red-phase scaffolds generated: **8 tests, all `@pytest.mark.skip`**. Each is verified to fail for the expected reason when un-skipped.

| File | Level | Tests |
| --- | --- | --- |
| `tests/unit/test_settings_load.py` | Unit | 7 |
| `tests/integration/test_startup_config.py` | Integration (subprocess) | 1 |

Red-phase failure reasons, observed with the skip markers stripped:

- AC-1, 2, 4, 5, 6, 7: `AttributeError: module 'language_lab.settings' has no attribute 'load_settings'`
- AC-3: `assert None not in (None, 0)`. The server ignored the bad Prefix and was still running at the 15 s deadline.
- AC-8: `assert ['LANGUAGE_LAB_HOST', 'LANGUAGE_LAB_PORT'] == []`. There is no `.env.example` yet.

The fast suite stays green with the scaffolds skipped (20 passed, 8 skipped), and `ruff check` / `ruff format --check` pass.

## Acceptance Criteria Coverage

One primary scaffold per criterion. Its first assertion is the criterion-defining one.

| AC | Priority | Test | First assertion | Risk |
| --- | --- | --- | --- | --- |
| AC-1 | P0 | `test_release_mode_loads_home_config` | `settings.anki_prefix ==` the value from the temp `~/.config/language-lab/.env`, then all other A2 fields | R-12 |
| AC-2 | P1 | `test_unknown_keys_are_ignored` | load succeeds with `LANGUAGE_LAB_FUTURE_FLAG` and `SOME_OTHER_TOOL_TOKEN` present | R-13 |
| AC-3 | P0 | `test_invalid_prefix_aborts_startup_without_echoing_secrets` | `main()` exits non-zero on `ANKI_PREFIX=Language-Lab`; neither sentinel secret appears in stdout+stderr | R-06, R-11 |
| AC-4 | P1 | `test_dev_flag_is_exposed` | `settings.dev is True` under `LANGUAGE_LAB_DEV=1` | R-11 |
| AC-5 | P0 | `test_dev_mode_reads_repo_env_instead_of_home` | `settings.anki_prefix == "LanguageLabDev"` when both files exist with different Prefixes | R-11 |
| AC-6 | P0 | `test_dev_mode_refuses_release_prefix` | `load_settings()` raises `ValueError` whose message names `anki_prefix` | R-11 |
| AC-7 | P1 | `test_openrouter_models_parse_in_order` | `settings.openrouter_models == [...]` in the configured order, whitespace trimmed | — |
| AC-8 | P1 | `test_env_example_documents_every_settings_field` | no Settings env name is missing from `.env.example` | R-13 |

## Implementation contract the tests encode

`src/language_lab/settings.py`:

| Field | Env key | Type | Notes |
| --- | --- | --- | --- |
| `host` | `LANGUAGE_LAB_HOST` | `str` | default `127.0.0.1` (R-12) |
| `port` | `LANGUAGE_LAB_PORT` | `int` | default `8787` |
| `public_host` | `LANGUAGE_LAB_PUBLIC_HOST` | `str \| None` | default `None`. Used by entry 4. |
| `dev` | `LANGUAGE_LAB_DEV` | `bool` | default `False` |
| `anki_connect_url` | `ANKI_CONNECT_URL` | `str` | default `http://127.0.0.1:8765`. A plain `str`, so the value compares without a trailing slash. |
| `anki_prefix` | `ANKI_PREFIX` | `str` | must match `^[A-Za-z][A-Za-z0-9]*$` (AD-4) |
| `azure_speech_key` | `AZURE_SPEECH_KEY` | `SecretStr` | tests read `.get_secret_value()` (NFR-6, R-06) |
| `azure_speech_region` | `AZURE_SPEECH_REGION` | `str` | |
| `openrouter_api_key` | `OPENROUTER_API_KEY` | `SecretStr` | |
| `openrouter_models` | `OPENROUTER_MODELS` | `list[str]` | comma-separated and trimmed. pydantic-settings JSON-decodes `list` env values by default, so annotate with `NoDecode` (or equivalent) and split in a validator (AD-18). |

- The `ANKI_*`, `AZURE_*` and `OPENROUTER_*` fields carry no `LANGUAGE_LAB_` prefix. Give each one a string `validation_alias` (or drop `env_prefix` and alias all of them). The `settings_env_names()` helper reads a string alias first, then `env_prefix + name`.
- Every field needs a default, so `Settings()` and `Settings(host=..., port=...)` keep working for `tests/api/test_app.py` and the live server.
- `load_settings()`: if `LANGUAGE_LAB_DEV` is truthy in the process env, it uses `Path.cwd() / ".env"`. Otherwise it uses `Path.home() / ".config/language-lab/.env"`. Resolve both at call time, not at import, because tests move HOME and cwd. Process env still overrides the file (the pydantic-settings default).
- In dev mode, refuse `anki_prefix.casefold() == "languagelab"`.
- `main()` calls `load_settings()` once. A validation failure exits non-zero and prints a message that names the bad key **without** pydantic's `input_value`. A model-level validator's `input_value` is the whole input dict, secrets included (R-06). Print a hand-built message (or `errors(include_input=False)`) and `sys.exit(1)` / `SystemExit`. Don't let the traceback reach stderr.
- Add `.env.example` at the repo root with every key, documented, matching A2.

## Fixture and support changes (made in this run)

- `tests/support/app_env.py` (new): `config_values(**overrides)` factory (a complete valid A2 config with a unique Prefix and secrets), `write_dotenv`, `dotenv_keys`, `settings_env_names`, `isolated_environ`, `APP_ENV_PREFIXES` and `HOME_ENV_RELATIVE`.
- `tests/support/startup.py` (new): `run_language_lab(env=, cwd=)` runs `main()` in a subprocess. It returns `returncode=None` if the process is still running at the deadline, which it then kills.
- `tests/support/fixtures/settings.py`: `settings_factory` now clears `ANKI_*`, `AZURE_SPEECH_*` and `OPENROUTER_*` as well as `LANGUAGE_LAB_*`. There are two new fixtures: `config_files` (`.home` / `.repo` paths with writers) and `settings_loader` (calls `load_settings()` at call time, so the red phase doesn't break collection).
- `tests/README.md`: layout and fixture tables updated.

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` / `@pytest.mark.skip` line.
2. Run it: `uv run pytest tests/unit/test_settings_load.py -k <name>` or `uv run pytest tests/integration/test_startup_config.py`.
3. Watch it fail for the reason listed above, implement, and watch it pass.
4. Unexpected failure? Fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes: there are no skip markers left in the two files, `make test-fast` passes and `make lint` passes.

Suggested order: AC-1 → AC-2 → AC-7 → AC-4 → AC-5 → AC-6 → AC-3 → AC-8.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-1 | `main()` passes the port and host from the home `.env` to `uvicorn.run` (extend `test_main_prints_url_and_binds_settings` with `config_files`) | P0 |
| AC-1 | `load_settings()` with no `.env` anywhere falls back to `127.0.0.1:8787` (R-12). Decide whether a missing release file is fatal. | P1 |
| AC-1 | `repr(settings)` and `str(settings)` don't contain either secret (SecretStr) | P1 |
| AC-3 | Parametrize invalid Prefixes: `1Lab`, `Lab::X`, `Lang Lab`, `""`, `Labé` → `ValueError` at unit level | P1 |
| AC-3 | The dev-mode refusal through `main()` also exits non-zero with no secret in the output. A model validator's `input_value` is the full dict. | P0 |
| AC-3 | The error output names `ANKI_PREFIX` so the user knows what to fix | P2 |
| AC-5 | A key set only in the home file is **not** loaded in dev mode | P1 |
| AC-5 | Release mode ignores `./.env` in cwd | P1 |
| AC-6 | Case variants `languagelab` and `LANGUAGELAB` are refused (Q5), and `LanguageLabDev` is accepted | P0 |
| AC-7 | An empty value → `[]`; a trailing comma and blank entries are dropped | P2 |
| AC-8 | Every key in `.env.example` maps to a Settings field (the other direction, so no stale keys) | P2 |
| — | `/api/health` and the static files contain no settings values beyond the version (test design P0, R-06) | P0 |

## Open items

- Is a missing `~/.config/language-lab/.env` in release mode fatal or are defaults used? The ticket doesn't say, and entry 8 checks the release run.
- The ticket's "adapters' settings injected by app.py" has nothing to inject until Epic 2. It isn't testable in this story.
- AC-8 would pass against a `.env.example` that lists only the current fields. AC-1 is what forces the A2 fields to exist.

## Validation (step 5)

- [x] Prerequisites: there are clear criteria (ticket verify), pytest is configured, and the dev env runs
- [x] Every criterion has a stable generated id. No supplied ids collide.
- [x] Every leaf maps to exactly one AC (docstring `AC-n:`), and every AC has exactly one red leaf
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one, and red failures are observed for the expected reason
- [x] No unimplemented setup response is parsed before the criterion assertion
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `dev-story` on entry 2
- [x] No browser sessions were opened. The temp red-check plugin lives in the session scratchpad, not the repo.

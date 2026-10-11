---
title: 'Configuration from ~/.config/language-lab/.env'
type: 'feature'
ticket: '2'
created: '2026-10-10'
status: 'built'
baseline_revision: '5a3bfc15349dae338f5130983060955e8792a8e0'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-1-2.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `Settings` only knows host and port, and nothing reads a `.env`. Every later epic needs the A2 keys loaded once, a Prefix validated per AD-4, and a dev mode that can never write the release Prefix.

**Approach:** Complete `settings.py` with every A2 key, `LANGUAGE_LAB_PUBLIC_HOST` and `LANGUAGE_LAB_DEV`. Add `load_settings()`, which picks `./.env` in dev mode or `~/.config/language-lab/.env` otherwise, and have `main()` call it once and exit cleanly on invalid config. Ship a documented `.env.example`. Make the ATDD scaffolds from 5a3bfc1 pass.

## Boundaries & Constraints

**Always:**
- Implement the field table and `load_settings()` contract in the ATDD checklist (`context`): field names, env keys, types, defaults, `SecretStr` for the two keys, a `NoDecode` list for `OPENROUTER_MODELS` split on commas, trimmed, blanks dropped.
- Every field has a default, so `Settings()` and `Settings(host=..., port=...)` keep working. The `anki_prefix` default is `LanguageLab`, and the host default stays `127.0.0.1` (R-12).
- `ANKI_PREFIX` must match `^[A-Za-z][A-Za-z0-9]*$`. When `dev` is true, `anki_prefix.casefold() == "languagelab"` is refused (Q5, decided 2026-10-10).
- `load_settings()` reads `LANGUAGE_LAB_DEV` from the process env and resolves `Path.cwd()` and `Path.home()` at call time. Process env overrides the file.
- `main()` calls `load_settings()` once. On a `ValidationError` it prints one line per error to stderr, naming the env key and the message, never `input_value`, and exits with code 1 and no traceback.
- Decision (2026-10-10): a missing `.env` (the home file in release, `./.env` in dev) is fatal. `load_settings()` raises a `ConfigError` (a `ValueError` subclass in `settings.py`) naming the path, and `main()` prints `no config at <path>; copy .env.example` to stderr and exits 1. `Settings()` built directly still uses defaults.
- Remove every ATDD skip marker in `tests/unit/test_settings_load.py` and `tests/integration/test_startup_config.py`. Don't weaken any first assertion.

**Never:**
- No new dependencies. No module other than `settings.py` reads `os.environ` or a `.env` (AD-18).
- No adapters, allow-list, or use of `public_host`. Those belong to entry 4 and Epic 2. "Adapters' settings injected by app.py" has nothing to inject yet: `create_app(settings)` stays the seam.
- No `docs/` pages. They belong to entry 9.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Release load | home `.env` with all A2 keys | Settings has every value, `dev=False` | No error expected |
| Unknown keys | `LANGUAGE_LAB_FUTURE_FLAG`, `SOME_OTHER_TOOL_TOKEN` in file | Ignored | No error expected |
| Dev load | `LANGUAGE_LAB_DEV=1`, both files exist | Values from `./.env` only, `dev=True` | No error expected |
| Release ignores cwd | no flag, `./.env` exists | `./.env` not read | No error expected |
| Invalid Prefix | `Language-Lab`, `1Lab`, `Lang Lab`, `""`, `Labé` | Startup aborts | `ValueError` from load; `main()` exits 1, output names `ANKI_PREFIX`, no secret |
| Dev + release Prefix | dev on, `LanguageLab` / `languagelab` / `LANGUAGELAB` | Refused; `LanguageLabDev` accepted | Same as above |
| Models | `a, b ,c`, `""`, `a,,b,` | `["a","b","c"]`, `[]`, `["a","b"]` | No error expected |
| No file | the mode's `.env` is missing (the other may exist) | Startup aborts | `ConfigError` from load; `main()` exits 1 naming the path |

</frozen-after-approval>

## Code Map

- `src/language_lab/settings.py` -- now `Settings(BaseSettings)` with `env_prefix="LANGUAGE_LAB_"`, `extra="ignore"`, host and port. Extend it; keep `env_prefix`, and give the `ANKI_*`, `AZURE_*` and `OPENROUTER_*` fields a string `validation_alias`. Enable init by field name (`validate_by_name=True`) so `Settings(anki_prefix=...)` works. Pass the chosen file with `Settings(_env_file=path)`.
- `src/language_lab/app.py` -- `main()` builds `Settings()`. Switch it to `load_settings()` and handle both errors. `create_app` stays as it is.
- `.env.example` (new, repo root) -- the A2 block, plus `LANGUAGE_LAB_PUBLIC_HOST` and a commented `LANGUAGE_LAB_DEV`, with a comment per key, the `chmod 600` advice, and the dev-mode Prefix rule. `.gitignore` already ignores `.env` and does not match `.env.example`.
- `tests/unit/test_settings_load.py`, `tests/integration/test_startup_config.py` -- red scaffolds to un-skip.
- `tests/support/app_env.py` (`config_values`, `write_dotenv`, `isolated_environ`, `settings_env_names`), `tests/support/startup.py` (`run_language_lab`), `tests/support/fixtures/settings.py` (`settings_factory`, `config_files`, `settings_loader`) -- reuse these and don't change them.
- `tests/api/test_app.py` -- `test_main_prints_url_and_binds_settings` calls `main()` against the real HOME and cwd, so it must use `settings_factory` for isolation. `test_port_in_use_exits_non_zero` must pass `isolated_environ(home)` **and** write a valid home `.env`, or it would pass on the missing-config exit instead of the busy port.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/settings.py` -- fields, Prefix pattern, models validator, after-validator for the dev refusal with a message naming `ANKI_PREFIX`, and `load_settings()` -- AD-4, AD-18
- [x] `src/language_lab/app.py` -- `main()` uses `load_settings()`; on `ConfigError` print its message; on `ValidationError`, print `errors(include_input=False)` as `<KEY>: <msg>` lines to stderr, then `sys.exit(1)` -- R-06
- [x] `.env.example` -- create as mapped -- A2, R-13
- [x] `tests/unit/test_settings_load.py`, `tests/integration/test_startup_config.py` -- remove skips. Add the backlog's P0/P1 cases: invalid Prefix parametrized, dev case variants refused and `LanguageLabDev` accepted, the dev refusal through `main()` exits non-zero with no secret, home-only keys not loaded in dev, release ignores `./.env`, models edge cases, missing file fatal in both modes (via `load_settings()` and `main()`), `repr`/`str` hide secrets, every `.env.example` key maps to a field -- matrix
- [x] `tests/api/test_app.py` -- isolate the two `main()` tests as mapped. Extend the bind test so host and port from a home `.env` reach `uvicorn.run`. Add: `/api/health` and the shell contain no settings value from a sentinel config -- R-06, R-12

**Acceptance Criteria:**
- Given the repo, when `make test-fast` and `make lint` run, then both pass, and no skip marker is left in the two ATDD files.
- Given `LANGUAGE_LAB_DEV=1` and a repo `.env` with `ANKI_PREFIX=LanguageLabDev`, when `uv run language-lab` starts, then it prints the URL and serves.
- Given a home `.env` with `ANKI_PREFIX=Language-Lab` and secret values, when `language-lab` starts, then it exits 1, the output names `ANKI_PREFIX`, and neither secret appears.

## Implementation Notes

- Implemented by a coding subagent from this plan. `settings.py` adds `ConfigError`, `load_settings()`, `config_path()`, and `describe_errors()`. `describe_errors()` maps a field loc to its env key and strips pydantic's "Value error, " prefix, so the dev-refusal line starts with `ANKI_PREFIX must not be…`.
- The dev flag is parsed through `TypeAdapter` over a `TypedDict` keyed `LANGUAGE_LAB_DEV`, so a bad value fails as a `ValidationError` with that key in its loc. `main()` prints it like any other config error.
- Effect of the fatal-missing-file decision: a bare `uv run language-lab` with no `./.env` in dev, or no home `.env` in release, now exits 1 with `no config at <path>; copy .env.example`.
- `tests/README.md` was not updated; the plan doesn't ask for it.
- Matrix audit: every row has a passing test. Release load: AC-1. Unknown keys: AC-2. Dev load: AC-4, AC-5, home-only keys. Release ignores cwd. Invalid Prefix: unit test over 6 values plus the integration test via `main()`. Dev + release Prefix: case variants, `LanguageLabDev` accepted, and via `main()`. Models: AC-7 plus edge cases. No file: unit tests in both modes plus integration via `main()`. `make lint` passes and `make test-fast` gives 56 passed; the subagent also reports e2e 6 passed.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 2, low 1, false 0, maybe-false 0.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `settings.py` `_dev_mode()` | The flag lookup is case-sensitive, but `Settings` is not, so `language_lab_dev=1` loads the release file with `dev=True` | medium | patch | Reproduced: home `.env` loaded, `dev True`. Fixed by a case-insensitive lookup. |
| 2 | `settings.py` `load_settings()` / `app.py` `main()` | An unreadable `.env` raises `PermissionError`, and the user sees a traceback | medium | patch | Reproduced with `chmod 000`: the traceback appears. Fixed: `OSError` becomes `ConfigError` naming the path. |
| 3 | `settings.py` `public_host` vs `.env.example` | An empty `LANGUAGE_LAB_PUBLIC_HOST=` loads as `""`, not `None` | low | patch | Reproduced `public_host ''`. Entry 4 consumes it; the fix is a before-validator, blank → `None`. |

## Design Notes

The dev flag that picks the file comes from the process env. Parse it with the same bool rules as the field (e.g. `TypeAdapter(bool)`), so `LANGUAGE_LAB_DEV=true` and `=1` behave the same, and an invalid value fails as a `ValidationError` too. The refusal uses `self.dev`, so `LANGUAGE_LAB_DEV=1` written inside the home file also refuses the release Prefix, which fails safe.

## Verification

**Commands:**
- `make lint && make test-fast` -- expected: all pass, 0 skipped in the two ATDD files
- `grep -rn "skip" tests/unit/test_settings_load.py tests/integration/test_startup_config.py` -- expected: no output
- In a temp dir with a repo `.env` (`ANKI_PREFIX=LanguageLab`), run `LANGUAGE_LAB_DEV=1 uv run --project <repo> language-lab` -- expected: exit 1 with one `ANKI_PREFIX` line, no traceback

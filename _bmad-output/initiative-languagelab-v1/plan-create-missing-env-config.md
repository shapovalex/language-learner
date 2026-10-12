---
title: 'Create the .env from the template when it is missing, then ask the user to fill it in'
type: 'feature'
ticket: ''
created: '2026-10-12'
status: 'built'
baseline_revision: '88ac3616da4c209efc7dc1daf7d59a358b58ae79'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** On a fresh machine, `language-lab` exits with `no config at <path>; copy .env.example`, but the wheel does not ship `.env.example`, so a release user has to fetch it from the repo and hand-edit it.

**Approach:** When the current mode's `.env` is missing, startup asks for the necessary values in the terminal, creates the file (and its directory) from a template shipped inside the package with those values filled in, and continues starting. Without a terminal it creates the file from the template, says which variables to set, and exits.

**Decisions (2026-10-12):**
- After creating the file: prompt interactively for the necessary variables, write them, keep starting. No TTY → create the template file, print path + variables to set, exit 1.
- Both modes: release creates `~/.config/language-lab/.env`; dev (`LANGUAGE_LAB_DEV=1`) creates `./.env` with `ANKI_PREFIX=LanguageLabDev` so it passes the dev-prefix rule.

## Boundaries & Constraints

**Always:**
- Necessary variables, in prompt order: `AZURE_SPEECH_KEY` (hidden input), `AZURE_SPEECH_REGION`, `OPENROUTER_API_KEY` (hidden input). An empty answer leaves the key empty. Every other key keeps the template's value.
- The template ships inside the `language_lab` package (one source of truth, or a test pinning the repo-root `.env.example` identical to it).
- Prompt first, write after: the file is created only once all answers are in, with exclusive create and mode `0600`; the parent directory is created if missing.
- An existing file, even empty or invalid, is never overwritten or modified, and no prompt is shown.
- No answer or secret value is ever echoed, printed, or logged. The message names the full file path.
- `settings.py` owns rendering and writing the config (AD-18); `app.py` owns the terminal interaction.

**Never:**
- No validation that keys are non-empty when the file already exists.
- No traceback on any path: Ctrl-C/EOF during prompts, unwritable directory, or a value that cannot be written safely.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Release, no file, TTY | `~/.config/language-lab/` absent, user answers | Dir + `.env` created 0600 with answers; server starts | No error |
| Dev, no `./.env`, TTY | `LANGUAGE_LAB_DEV=1` | `./.env` created with answers and `ANKI_PREFIX=LanguageLabDev`; server starts | No error |
| No file, no TTY | stdin not a terminal | Template file created 0600 with empty keys; stderr names path and the three variables | exit 1 |
| File exists | any content | No prompt; read as today; file untouched | Unchanged validation errors |
| Interrupted | Ctrl-C or EOF at a prompt | No file written; one-line message | exit 1, no traceback |
| Unsafe value | answer contains whitespace, quote, `#`, backslash, or newline | Re-ask that variable with a one-line reason | — |
| Cannot create | parent not writable / file appeared meanwhile | `cannot create config at <path>: <strerror>` | exit 1, no traceback |

</frozen-after-approval>

## Code Map

- `src/language_lab/settings.py` -- `config_path(dev)`, `load_settings()` (raises `ConfigError("no config at …; copy .env.example")` at line ~102), `ConfigError`, `RELEASE_PREFIX`. Add the create-from-template step here; reuse `ConfigError` for failures.
- `src/language_lab/app.py:268` `main()` -- catches `ConfigError`/`ValidationError`, prints to stderr, `sys.exit(1)`. The prompt flow goes here, before `load_settings()`.
- `.env.example` (repo root) -- current template, documents every key. Packaged resources load via `importlib.resources.files("language_lab")` (see `_STATIC` in `app.py`); uv_build ships everything under `src/language_lab/`.
- `tests/unit/test_settings_load.py` -- `ENV_EXAMPLE` (line 12) and the two key-coverage tests (lines ~119, ~293); `test_missing_home_file_is_fatal_in_release_mode` / `test_missing_repo_file_is_fatal_in_dev_mode` change meaning. Fixtures `config_files`, `settings_loader` in `tests/support/fixtures/settings.py`.
- `tests/integration/test_startup_config.py` -- `test_missing_config_aborts_startup_naming_the_path` asserts the old message via `run_language_lab`; update it.
- `tests/integration/test_release_wheel.py` + `tests/support/fixtures/release.py` -- wheel smoke under temp HOME; add a check that the wheel creates the file on a bare HOME.
- `README.md` -- "Create the config" (release step 2), dev setup `cp .env.example .env`, and the Configuration paragraph "If the file is missing, the app exits…".

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/env.example` -- move the template here (single source of truth); keep a root `.env.example` only if a test pins it identical -- wheel must ship it.
- [x] `src/language_lab/settings.py` -- add `active_config_path()` (public wrapper of `config_path(_dev_mode())`), `NECESSARY_KEYS` (name, secret flag), `render_config(dev, values) -> str` (template with the given `KEY=` lines replaced; dev sets `ANKI_PREFIX=LanguageLabDev`), `is_safe_value(str) -> bool`, and `create_config(path, text)` (mkdir parents, `O_CREAT|O_EXCL` mode 0o600, `OSError` → `ConfigError`).
- [x] `src/language_lab/app.py` -- in `main()`, before `load_settings()`: if `active_config_path()` is missing, run `_setup_config(path, dev, read_line, read_secret, is_tty)` (injected `input`/`getpass.getpass`/`sys.stdin.isatty` for testing): TTY → prompt, re-ask unsafe values, create, continue; no TTY → create template, print path + variables, exit 1; `KeyboardInterrupt`/`EOFError` → message, exit 1.
- [x] `tests/unit/test_settings_load.py` -- repoint `ENV_EXAMPLE`; keep `load_settings()` missing-file `ConfigError` tests; add `render_config`/`create_config` tests: values placed, dev prefix, 0600, dir created, existing file → `ConfigError` and untouched, unwritable parent → `ConfigError`.
- [x] `tests/unit/test_setup_config.py` (new) -- `_setup_config` with fake input functions covering every I/O matrix row except the wheel run; assert no answer appears in captured output.
- [x] `tests/integration/test_startup_config.py` -- missing config, no TTY (subprocess): file created, exit 1, message names path and the three variables, no traceback.
- [x] `tests/integration/test_release_wheel.py` -- bare HOME: the wheel creates `~/.config/language-lab/.env`.
- [x] `README.md` -- release step 2 and dev setup describe the auto-created file; Configuration paragraph updated.

**Acceptance Criteria:**
- Given a bare HOME and no TTY, when `uvx --from <wheel> language-lab` runs, then `~/.config/language-lab/.env` exists with mode 0600 and the output tells the user to set the three variables in that file.
- Given no config and a terminal, when the user answers the prompts, then the server starts using those values and the secrets never appear on screen.
- Given an existing config file, when the app starts, then the file's bytes and mode are unchanged.

## Implementation Notes

- Root `.env.example` removed (git mv to `src/language_lab/env.example`); the package copy is the single source. `spec-draft.md` still mentions the repo `.env.example` (historical, untouched).
- `is_safe_value` also rejects `$` (python-dotenv interpolates `${VAR}`), backtick, and any non-printable character, beyond the matrix's list. Answers are not stripped: a leading/trailing space is re-asked.
- Added public `is_dev_mode()` in `settings.py` so `app.py` can pass `dev` to `_setup_config` without importing a private helper.
- `load_settings()` missing-file message is now `no config at <path>: not a regular file` (reached only when the path exists but is not a regular file, e.g. a directory or dangling symlink, or when called directly).
- Test subprocess helpers (`run_language_lab`, `run_released_app`) now pass `stdin=DEVNULL` so a developer's terminal never triggers the prompt; new `run_released_until_exit` for the bare-HOME wheel run.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — high 0 / medium 1 / low 3 / false 0 / maybe-false 0

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `load_settings()` "start language-lab in a terminal to create it" shown only when path is a dir/dangling symlink, where `main()` skips setup — advice loops | low | patch | Confirmed: `main()` guards `not exists() and not is_symlink()`, `load_settings()` raises on `not is_file()`. Reword to state the path is not a regular file. |
| `_ask` reason omits backtick, non-printable/Unicode whitespace that `is_safe_value` rejects | low | patch | Confirmed against `_UNSAFE_CHARS` and `isprintable`/`isspace`. Make the reason list every rejected class. |
| No test drives `main()` through the TTY path to a started server with the answered values (AC2) | medium | patch | Confirmed: unit tests call `_setup_config` directly; subprocess helpers force `stdin=DEVNULL`. Add a unit test of `main()` with patched isatty/input/getpass/uvicorn.run. |
| `test_existing_config_is_never_modified` asserts no exit outcome, so "read as today / unchanged validation errors" is unverified | low | patch | Confirmed: no `returncode`/`ANKI_PREFIX` assertion. Add per-case outcome assertions. |

## Design Notes

Use `open(path, "x")` (or `os.open` with `O_CREAT|O_EXCL`, mode 0o600) so a racing second start never clobbers a file, and the mode is set at creation rather than chmod-after-write.

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test-fast` -- expected: all pass
- `uv run pytest tests/integration/test_release_wheel.py` -- expected: all pass

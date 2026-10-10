---
title: 'Tracer: runnable wheel serving the shell'
type: 'feature'
ticket: '1'
created: '2026-10-10'
status: 'built'
baseline_revision: '96b64bdfb53ab414669764d028020c61887fab8d'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repo has no code. Every later entry needs a packaged, runnable app skeleton with pinned dependencies, a composition root, and a client that reaches the API through one fetch caller.

**Approach:** A tracer bullet. Set up a uv-built wheel for `language_lab` with a `language-lab` console script that serves the static shell on 127.0.0.1:8787. The shell loads versioned assets, and `api.js` fetches `GET /api/health` so the page can show the version. Add pytest, ruff, and an empty `tests/fakes/`.

## Boundaries & Constraints

**Always:**
- Python `>=3.14`. Pin every runtime dependency in the architecture Stack exactly: fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.0, pydantic-settings 2.15.0, python-multipart 0.0.32, httpx 0.28.1, av 19.0.1. Pin dev dependencies exactly too: pytest 9.1.1, ruff 0.16.10, pytest-playwright 0.10.0, pytest-cov 7.1.0. Later entries add no dependencies.
- Decision (2026-10-10): the shell HTML response carries `Cache-Control: no-cache` (test-design Q3, R-08). Versioned assets get no special header in this entry.
- Decision (2026-10-10): pytest-cov 7.1.0 is pinned now so a coverage gate stays possible; no gate is configured in this entry.
- `create_app(settings) -> FastAPI` is the only place routes are wired. `Settings` (pydantic-settings) has only `host="127.0.0.1"` and `port=8787` for now. Entry 2 completes it.
- The version has one source, `pyproject.toml`, and is read at runtime through `importlib.metadata`.
- Asset URLs are `/static/<version>/...`, rendered into the shell server-side.
- Any GET outside `/api/*` and `/static/*` returns the shell. Unknown `/api/*` paths return a JSON 404, never the shell.
- `api.js` is the only module that calls `fetch`.
- Static files are packaged inside the wheel.

**Never:**
- Don't add a `.env` load, error envelope, request-id or log middleware, or allow-list. Those belong to entries 2–4.
- Don't add a router, navigation, CSS tokens, fonts, or a Playwright fixture. Those belong to entries 5–7.
- Don't redirect unknown client paths to `/captures`. That redirect belongs to `router.js` (entry 6).
- No CDN, npm, or build step for client code.
- `/api/health` exposes nothing but the version.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Health | `GET /api/health` | 200 `{"version": "<pyproject version>"}` | No error expected |
| Deep client path | `GET /any/deep/path`, `GET /` | 200 `text/html` shell with `Cache-Control: no-cache`, referencing `/static/<version>/...` | No error expected |
| Versioned asset | `GET /static/<version>/api.js` | 200, JavaScript content type | No error expected |
| Unknown API path | `GET /api/nope` | 404 JSON, not the shell | FastAPI default 404 (envelope comes in entry 3) |
| Missing asset | `GET /static/<version>/missing.js` | 404, not the shell | Default 404 |
| Startup | `language-lab` | Prints `http://127.0.0.1:8787/` and serves on that host and port only | Port in use → uvicorn error, non-zero exit |

</frozen-after-approval>

## Code Map

The repository has no application code (only `_bmad*`, `AGENTS.md` (empty), `LICENSE`, and `sequence.md`), so every path below is new. Layout follows the architecture Structural Seed. uv is 0.12.23 locally (Stack says 0.12.24, which is fine), and CPython 3.14.8 is installed. av 19.0.1 ships `cp312-abi3` macOS arm64 wheels, which install on 3.14.

- `pyproject.toml` -- project metadata, version `0.1.0`, pins, `[project.scripts] language-lab = "language_lab.app:main"`, `uv_build` backend, `[dependency-groups] dev`, ruff and pytest config
- `.python-version` -- `3.14`
- `.gitignore` -- add `.venv/`, `dist/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.env` (keep existing lines)
- `src/language_lab/__init__.py` -- `__version__` via `importlib.metadata.version("language-lab")`
- `src/language_lab/settings.py` -- minimal `Settings`
- `src/language_lab/app.py` -- `create_app`, `main`
- `src/language_lab/static/index.html` -- shell template with a `{{VERSION}}` placeholder in asset URLs
- `src/language_lab/static/api.js`, `src/language_lab/static/main.js` -- fetch wrapper and the bootstrap that renders the version
- `tests/__init__.py`, `tests/fakes/__init__.py`, `tests/test_app.py`

## Tasks & Acceptance

**Execution:**
- [x] `pyproject.toml`, `.python-version`, `.gitignore` -- create and extend as mapped. Run `uv lock` -- pins and packaging
- [x] `src/language_lab/__init__.py`, `src/language_lab/settings.py` -- version and `Settings(BaseSettings)` with host and port defaults, no env file -- AD-18 seed
- [x] `src/language_lab/app.py` -- `create_app(settings)`: `GET /api/health`; mount the package `static/` dir at `/static/{version}`; a catch-all GET that returns the shell (rendered once with the version), excluding `api/` and `static/` prefixes so those 404. `main()` builds `Settings()`, prints `LanguageLab running at http://{host}:{port}/`, and runs uvicorn -- AD-13 serving and routing
- [x] `src/language_lab/static/index.html`, `main.js`, `api.js` -- the shell loads `main.js` as a module. `api.js` exports `getHealth()` (and a generic `request` helper). `main.js` renders `LanguageLab v<version>` into the page, or a plain failure message if the call fails -- tracer client path
- [x] `tests/__init__.py`, `tests/fakes/__init__.py` -- empty packages -- harness scaffold
- [x] `tests/test_app.py` -- cover every I/O matrix row except Startup through `fastapi.testclient.TestClient(create_app(Settings()))`. Also assert the defaults are `127.0.0.1:8787`, that the health body has exactly one key, that the shell carries `Cache-Control: no-cache`, and that no `fetch(` appears in static JS outside `api.js` -- matrix and AD-13

**Acceptance Criteria:**
- Given a fresh clone, when `uv build` runs, then `dist/` holds a wheel containing `language_lab/static/index.html`, `api.js`, and `main.js`.
- Given that wheel, when `uvx --from dist/<wheel> language-lab` runs and a browser opens `http://127.0.0.1:8787/any/path`, then the page shows `LanguageLab v0.1.0`, which came from `/api/health`.
- Given the repo, when `uv run pytest` and `uv run ruff check` run, then both pass.

## Implementation Notes

- Build backend pinned as `uv_build>=0.12.23,<0.13` (local uv is 0.12.23).
- `create_app` disables `/docs`, `/redoc`, `/openapi.json` so those paths cannot shadow the shell or leak route info. The catch-all also 404s the bare `api` and `static` paths.
- Static dir is mounted from `importlib.resources.files("language_lab") / "static"`, the same path the shell is read from, so tests and the wheel behave the same.
- Port in use: uvicorn logs the bind error and exits with code 3 (verified).
- Starlette emits a `StarletteDeprecationWarning` that `httpx` with `TestClient` is deprecated in favor of `httpx2`. It is a warning only; no dependency was added because pins are fixed.
- Browser check not automated: Playwright browsers and Google Chrome are not installed locally. `curl` confirmed the API and shell; the HITL browser check is still open.
- Matrix audit: added `test_main_prints_url_and_binds_settings` and `test_port_in_use_exits_non_zero` so the Startup row is covered (16 tests pass).

## Plan Change Log

## Review Triage Log

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `src/language_lab/settings.py` | Bare `HOST`/`PORT` env vars override the bind | high | patch | Reviewer reproduced `HOST=0.0.0.0` → `host='0.0.0.0'`; AD-16 names `LANGUAGE_LAB_HOST`, so `env_prefix="LANGUAGE_LAB_"` is settled by architecture. |
| 2 | `tests/test_app.py` | Tests depend on ambient host/port env; port-in-use test hangs under `HOST=0.0.0.0` | medium | patch | Reproduced as 3/16 failures with `HOST=0.0.0.0`; fixed by isolating `LANGUAGE_LAB_*` env in tests. |
| 3 | `src/language_lab/app.py` `main()` | URL printed before uvicorn binds | low | reject | Real but only misleads on an already-failing start, and the bind error follows immediately; the fix needs a lifespan hook. |
| 4 | `src/language_lab/app.py` catch-all | Non-GET to unknown `/api/*` gives 405; `HEAD /` gives 405 | low | reject | Response is still JSON and not the shell; the intent and matrix specify GET; entry 3's error envelope revisits error handling; the fix adds routes. |
| 5 | static mount | Raw `index.html` template served at `/static/<v>/index.html` | low | reject | Nothing links to it; the fix means moving the template out of the served directory. |
| 6 | `src/language_lab/static/api.js` `request()` | Spreading a `Headers` instance drops its headers | low | patch | `{...new Headers()}` is `{}`; normalizing with `new Headers()` is a direct correction in the shared helper. |
| 7 | diff | `uv.lock` missing from the change | false | reject | `uv.lock` exists in the tree and is committed with the change; it was only left out of the review diff to keep it readable. |
| 8 | AC 2 | Browser acceptance criterion not verified | false | reject | Not a code defect: the plan marks it as a HITL manual check for presentation. |

## Design Notes

To keep the catch-all from swallowing API and static 404s, register it last and have it return a 404 when the path starts with `api/` or `static/`. Read `index.html` with `importlib.resources` and replace `{{VERSION}}` once in `create_app`, so tests and the wheel take the same path.

## Verification

**Commands:**
- `uv run ruff check && uv run pytest` -- expected: all pass
- `uv build && unzip -l dist/*.whl | grep static/` -- expected: the three static files are listed
- `uvx --from dist/language_lab-0.1.0-py3-none-any.whl language-lab` in the background, then `curl -s 127.0.0.1:8787/api/health` and `curl -s 127.0.0.1:8787/any/path` -- expected: the version JSON, then the shell HTML with versioned URLs

**Manual checks (if no CLI):**
- HITL: open `http://127.0.0.1:8787/any/path` in a browser and see `LanguageLab v0.1.0`.


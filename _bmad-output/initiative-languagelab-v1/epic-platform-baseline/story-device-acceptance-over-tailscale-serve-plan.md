---
title: 'Device acceptance over Tailscale Serve'
type: 'feature'
ticket: '10'
created: '2026-10-13'
status: 'in-progress'
baseline_revision: 'c95ba4a902ee50a3368d93676fcb6442c5967691'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing yet proves the released wheel works on real devices: the Tailscale fixtures behind the allow-list tests are synthetic (R-05), WebKit-on-iOS behaviour is unverified (R-09), and LAN unreachability is untested (R-12). The epic's Done-when 1 and 2 (AC1, AC2 reach) rest on this run.

**Approach:** Give the user a runbook to follow on the Mac Mini and the three devices, run it, record the results, and fix or ticket every finding.

## Boundaries & Constraints

**Always:**
- The run uses the released wheel that contains the recorder (`v0.2.1`, see the 2026-10-13 amendment below), started exactly as `docs/install.md` and `docs/remote-access.md` say. A doc step that fails or misleads is a finding.
- The runbook covers every clause of the ticket's verify, each as a step with the exact command or action and the expected result: HTTPS shell in a secure context on iPhone Safari, iPad Safari and a desktop browser; `/captures`, `/en/items`, `/en/pronunciation`, `/fr/items`, `/fr/pronunciation`, `/setup` by nav and by direct URL; a non-GET `/api` from the desktop browser over Tailscale is not `forbidden_origin`; one with another Origin is; `<LAN IP>:8787` and `<LAN IP>:8765` are unreachable from another device.
- It also carries the manual checks earlier stories handed to entry 10: both startup lines, the Menu sheet and safe-area insets on iPhone, iOS swipe-back between destinations.
- Each step gets a recorded result (pass, fail, or not run with the reason), per device where it applies.
- Every finding is fixed in this story or appended to `deferred-work.md`. A fix under `src/` is verified by `make test` and `make test-webkit`, and noted as needing a new release to reach the Mac Mini.
- The repo is public: no real tailnet name, machine name, login, or tailnet IP is committed. Use `mac-mini.tail1234.ts.net` in fixtures and `mac-mini.tailnet-name.ts.net` in docs.
- Decision (2026-10-13): the real Serve headers are captured by a stdlib-only recorder, run on the Mac Mini on port 8787 while the app is stopped. It serves one page with a button that POSTs, writes the headers Serve forwarded in the fixture's shape, and sanitises `tailscale status --json` from stdin. It keeps every header name and replaces the tailnet name, logins, display names and IPs with the fixture placeholders. Both synthetic fixtures are replaced with its output.
- Decision (2026-10-13, amended by the user after the first implementation pass): the Mac Mini runs wheels through `uvx` only and nothing is cloned there. The recorder therefore ships in the wheel as `language_lab.tools.record_tailscale_fixtures` with its own console script, `language-lab-record-fixtures`, and writes its files to the current folder. This replaces the earlier `scripts/` location and "nothing ships in the wheel". The run needs a release that contains it.
- Decision (2026-10-13): on iPhone and iPad the secure context is shown by the recorder's page, which prints `window.isSecureContext` at the same HTTPS origin as the shell. The desktop also checks the real shell in its console.

**Never:**
- No echo or debug route in the app (`app.py`); the recorder is a separate command.
- No write to a ticket file. No new dependency. No LAN bind, login, or CORS.
- No claim that a step passed without the user's reported result.

</frozen-after-approval>

## Code Map

- `docs/install.md`, `docs/remote-access.md` -- what the user follows. Edit only to fix a finding; `tests/unit/test_docs_consistency.py` guards them (placeholder tailnet name, FR-4 headings, asset URL).
- `src/language_lab/app.py` -- `AllowListMiddleware` runs before routing, so `POST /api/health` gives `405` with code `not_found` from an allowed Origin and `403 forbidden_origin` from a foreign one. No write route exists in the release; the runbook uses this. `main()` prints `LanguageLab running at …` and `On your tailnet: https://…/`.
- `src/language_lab/static/router.js` `ROUTES` -- the six paths above; an unknown path redirects to `/captures`. No screen calls `setDirty` yet, so the dirty swipe-back check (R-03) cannot be run on a device; log it in `deferred-work.md` for the first epic with a dirty screen.
- `tests/fixtures/tailscale-serve-headers.json`, `tailscale-status.json`, `tests/fixtures/README.md` -- synthetic; shape `{request, upstream, headers}` read by `serve_headers()`. The README has a "Synthetic until recorded (R-05)" section to update.
- `tests/support/hosts.py` -- `TAILNET_HOST = "mac-mini.tail1234.ts.net"`; keep.
- `tests/api/test_host_origin_allow_list.py`, `tests/unit/test_tailscale_discovery.py` -- consume the fixtures; must pass unchanged on real recordings.
- `scripts/check_release_tag.py`, `tests/integration/test_release_tag.py`, `tests/support/release.py` -- the pattern for a stdlib script and its subprocess test.
- `_bmad-output/test-artifacts/` -- home for the runbook and results.
- This machine is a MacBook Pro without Tailscale. Every device step is the user's.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/acceptance/device-acceptance-1-10.md` -- write the runbook: Mac Mini setup from the docs, per-device checks, desktop Origin checks (`fetch` in the console, `curl -X POST -H 'Origin: https://evil.example'`), LAN probes with `curl -m 5` (AnkiConnect probe with Anki running), a results table, a findings list -- ticket verify, R-05, R-09, R-12
- [x] `src/language_lab/tools/record_tailscale_fixtures.py`, `pyproject.toml` `[project.scripts]` -- the recorder: `serve` (page showing `window.isSecureContext` and a POST button; writes the sanitised headers file) and `status` (stdin to sanitised status JSON); binds `127.0.0.1` only -- R-05, AC2
- [x] `tests/integration/test_record_tailscale_fixtures.py`, `tests/support/` helper -- sanitising removes a real tailnet name, login, display name and IPs and keeps header names; the output loads through `serve_headers()` and passes discovery -- R-05
- [ ] HITL: the user releases `v0.2.1` from this branch's work, runs the runbook, and reports results, findings and the two recorded files
- [x] `tests/fixtures/*.json`, `tests/fixtures/README.md` -- replace with the sanitised recordings; rewrite the synthetic note as how they were recorded -- R-05
- [ ] Findings -- fix each (docs, `src/`, tests) or append it to `_bmad-output/initiative-languagelab-v1/deferred-work.md`; add the R-03 dirty swipe-back entry
- [ ] `_bmad-output/test-artifacts/acceptance/device-acceptance-1-10.md` -- fill in results and the disposition of each finding

**Acceptance Criteria:**
- Given the filled-in runbook, when a reader checks it against the ticket's verify, then every clause has a recorded result on each device it applies to.
- Given the findings list, when each entry is read, then it names a commit in this story or a `deferred-work.md` entry.
- Given the repo after the story, when `make lint` and `make test` run, then both pass.

## Implementation Notes

- Implemented directly in the planning session, without a coding subagent.
- The recorder is deny-by-default: a header value is kept only for the ten headers that say how Serve and the browser address the app (`host`, `x-forwarded-host`, `x-forwarded-proto`, `origin`, `referer`, `sec-fetch-*`, `content-type`, `content-length`); every other value becomes `redacted`. In the status JSON only booleans, nulls, `Version`, `BackendState` and `OS` are kept as received. Keys are kept.
- `tests/support/hosts.py` `serve_headers()` now drops `content-length` and takes an optional path. A real recording carries the recorded body's length, which would break a replay with a different body.
- New `tests/support/recorder.py` runs the script as the runbook does (`serve --port 0`, `status` on stdin).
- The runbook's expected responses for `POST /api/health` (405 `not_found`, 403 `forbidden_origin`) were checked against the app in-process.
- The R-03 dirty swipe-back entry is in `deferred-work.md`.
- After the user's amendment the recorder moved from `scripts/` into the package (`language_lab.tools`, console script `language-lab-record-fixtures`), and was run from a locally built wheel through `uvx`. `tests/unit/test_docs_consistency.py` picked the single console script by unpacking; it now picks the one that targets `language_lab.app:main`.
- The version is not bumped here; the release bump is its own change, as for 0.2.0, and it must update the asset URL in the docs.
- 2026-10-14: the user recorded both fixtures on the Mac Mini with 0.2.1. Serve keeps the tailnet name in `Host` and sends the same `X-Forwarded-Host`; it also sends `content-length`, which `serve_headers()` already drops. The allow-list tests pass unchanged on the recordings.
- 2026-10-14: the user postponed reporting the per-step results (satisfied with how it works; will report problems later). The runbook marks those steps "not run", and a deferred-work entry tracks recording them. No findings were reported, so none were fixed or ticketed.
- Still open from the HITL task: the device run, the two recordings, and the findings.

## Plan Change Log

## Review Triage Log

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass
- `grep -rnE '[a-z0-9-]+\.ts\.net' tests/fixtures docs _bmad-output/test-artifacts/acceptance | grep -vE 'tail1234|tailnet-name'` -- expected: no output

**Manual checks (if no CLI):**
- The results table in the runbook has no empty cell.

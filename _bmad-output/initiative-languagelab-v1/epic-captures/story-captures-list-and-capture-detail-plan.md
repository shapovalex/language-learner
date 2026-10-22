---
title: 'Captures list and Capture detail'
type: 'feature'
ticket: '2'
created: '2026-10-22'
status: 'built'
baseline_revision: '0a1119b20f2a0e09b9529345cd87bdc045ac1ec0'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-3-2.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Saved Captures can't be seen. There is no way to list Captures or open one, in the AnkiStore, the API or the Captures screen.

**Approach:** Add `list_captures` and `get_capture` (port, adapter, fake), `GET /api/captures` and `GET /api/captures/{captureId}`, a `/captures/<captureId>` route, and the list and detail on the Captures screen. Phone and iPad portrait show them as separate screens. From 1024px they show as two panes. Make the 19 red-phase ATDD cases from commit 0a1119b pass.

## Boundaries & Constraints

**Always:**
- Reads hold the Anki lock once and go through `client.invoke`. They are not gated (AD-19).
- The only query is `note_query(manifest, "<Prefix> Capture")`. The CaptureId is matched in Python and never appears in a query (AD-4).
- Every field is decoded through the codec. Anki ids stay in the adapter.
- Sort newest first by `created_at`, never by note id. Equal times have a deterministic order.
- Times show in the browser's local time zone, in 24-hour form with `en-US` month names. The copy follows the checklist's decisions.
- Moving between `/captures` and `/captures/<id>` keeps the Captures screen mounted, so unsaved compose text survives without an alert.

**Never:**
- No Make an Item pane (epic-capture-to-item), no Delete (entry 3), no search.
- No error messages built from upstream text (AD-15).
- No changes to guard.py, query.py or setup_gate.py.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List | Captures under the Prefix and another Prefix, plus other notes | `{captures:[...]}` with only this Prefix's Captures, decoded, newest first | — |
| Empty scope | `findNotes` returns `[]` | `[]`, no `notesInfo` sent | — |
| Deleted meanwhile | A `{}` entry from `notesInfo` | Skipped | — |
| One Capture | A known CaptureId, plain or in editor markup | 200 `{captureId, text, createdAt}` | — |
| Unknown / malformed id | An unknown UUIDv4, or `capture-1` | 404 `not_found` from the Capture route; a malformed id never reaches the store | Envelope only |
| Anki down / malformed reply | Unreachable, or a bad `CreatedAt` | 503 `anki_unavailable` | — |
| Detail not in Anki (UI) | GET answers 404 | "This Capture isn't in Anki." and "‹ Captures"; on desktop the list stays with nothing selected | — |
| List load fails (UI) | GET answers an error | Inline `role="alert"` with the envelope's message and Try again, which reloads the list | — |

</frozen-after-approval>

## Code Map

- `adapters/anki/store.py`:
  - `list_captures()`: one lock hold. Factor a `_capture_infos(query)` helper out of `_find_capture`, holding its `findNotes`, `notesInfo`, length check, `{}` skip and dict check. `list_captures` decodes each entry with `_stored_capture(_field(info, _CAPTURE_ID).strip(), info)` and sorts on `(created_at, capture_id)` with `reverse=True`.
  - `get_capture(id)`: `_find_capture` under the lock, raising `AppError(NOT_FOUND)` on None.
  - Update the module docstring.
- `ports/anki_store.py`: add both methods with docstrings, and update the use-case list.
- `tests/fakes/anki_store.py`: the busy and available checks, `list_captures` sorted as the adapter sorts, and `get_capture` raising `not_found`. Update the docstring.
- `tests/unit/test_anki_store_port.py`: add both names to the method set.
- `features/captures/service.py`: `list()` and `get(capture_id)`.
- `features/captures/routes.py`:
  - Add a `_body(capture)` helper and use it in POST too.
  - `GET ""` → `{"captures": [...]}`.
  - `GET "/{capture_id}"`: when the id doesn't fullmatch `_UUID4`, raise `AppError(NOT_FOUND)` before calling the store.
- `app.py`: add `ErrorCode.NOT_FOUND: 404` to `_APP_ERROR_STATUS`, near line 118.
- `static/api.js`: `listCaptures()` and `getCapture(id)` (encode the id).
- `static/router.js`:
  - Add the route `/^\/captures\/([^/]+)$/` → `"captures"` with `{captureId}`.
  - Same-screen navigation: `mount` may return `{unmount, update}` instead of a function. Track the mounted screen name and its update function.
    - In `render()`, when the route's name equals the mounted one and it has `update`: set `currentPath`, call `update(params)`, and return. Don't clear dirty and don't remount.
    - `go` and `onPopState` skip the dirty ask when the target stays on that screen.
  - Function returns keep working for the other screens.
- `static/screens/captures.js`: keep the compose code. Add the following around it:
  - The layout: `.captures-layout`, holding a left pane (heading, compose card, list section) and a detail pane. The root class `captures-detail-open` says when a Capture is open.
  - The list section: a header with two spans, "Newest first" (narrow) and "N Captures · newest first" (wide, "1 Capture"). It also holds the skeleton (`role="status"`, "Loading Captures…", Setup's skeleton markup), the empty `<p>` "No Captures yet.", the load-error alert, and `<ul aria-label="Captures">` of `<li><a class="list-row capture-row" href="/captures/<id>">` with the text and a time `<span>`. The open row has `aria-current="page"`.
  - The detail pane:
    - With no Capture open, the hint "Choose a Capture to see it here." (wide only).
    - Otherwise the back link "‹ Captures" (narrow only), then an `<article>` with the text and "Captured …", or the not-found `<p>`.
    - Fetch it with `getCapture`, guarded by a token.
  - On a successful Save, prepend the returned Capture and drop any entry with the same id.
  - Time helpers: `rowTime(iso, now)` and `detailTime`, comparing local calendar dates with `new Date()`. Use `Intl.DateTimeFormat("en-US", {hour:"2-digit", minute:"2-digit", hourCycle:"h23"})` and `{month:"short", day:"numeric"[, year:"numeric"]}`.
- `static/css/studio.css`:
  - Below 1024px, `.captures-detail-open` hides the left pane, and without it the detail pane is hidden. Hide `.wide-only` here.
  - From 1024px, a two-pane grid (left at least 320px, up to about 420px), and `.narrow-only` hidden.
  - Rows wrap long text (`overflow-wrap:anywhere`). Style the time in `--color-ink-muted`, and give the article a card surface.
- Don't change the tests, `tests/support/*` or the shell catch-all (`app.py:352` already serves `/captures/<id>`).

## Tasks & Acceptance

**Execution:**
- [x] Port, adapter, fake and port unit test. Then un-skip `tests/integration/test_anki_capture_reads.py`, covering AC-1 to AC-4.
- [x] Service, routes and `app.py`. Then un-skip `tests/api/test_captures_read.py`, covering AC-5 to AC-7.
- [x] Add secondary cases:
  - Integration: an empty scope sends no notesInfo, a `{}` entry is skipped, a malformed CreatedAt is `anki_unavailable`, and a `needs_setup` gate still lists.
  - API: 503 on both routes with `available=False`.
- [x] `api.js`, `router.js`, `captures.js` and `studio.css`. Then un-skip `tests/e2e/test_captures_list.py`, covering AC-8 to AC-16.
- [x] Add E2E secondaries:
  - Desktop: typed compose text survives selecting a row, with no alert.
  - iPad portrait uses the phone layout.
  - At `viewports.ALL` there is no horizontal scroll.

**Acceptance Criteria:**
- Given the 19 ATDD cases and the added cases, when they run un-skipped, then all pass. The 3.1 compose tests still pass.
- Given the full suite, when `make test`, `uv run ruff check` and `uv run ruff format --check` run, then all are clean.

## Implementation Notes

- `mount` in captures.js returns its unmount function with an `update` property, not a `{unmount, update}` object. The story 1.6 contract test (`test_navigation.py::test_screen_module_mounts_and_unmounts`) requires a function return. The router accepts both shapes and reads `update` from either.
- The router's same-screen path bumps `renderToken`, so a stale module import can't mount over it. `mountedName` and `updateScreen` are cleared on every unmount.
- `/captures/<id>` decodes the segment with a guarded `decodeURIComponent`, so a malformed `%` keeps the raw text instead of throwing.
- Detail: a Capture already in the list shows at once while `getCapture` refreshes it. A non-`not_found` failure shows an inline alert with the envelope's message and Try again.
- Saves made while the list is still loading are merged in when it arrives (`list.saved`).
- Below 1024px, opening a Capture moves focus to the back link, and coming back moves it to that Capture's row. Both elements were hidden by the layout change.
- Extra secondaries beyond the plan: equal-CreatedAt ordering and Anki-down reads (integration), `capture-1` never reaching an unreachable store (API), and on the phone a browser back that keeps the compose text, iPad landscape two panes, the desktop not-found leaving nothing selected, a list load failure with Try again, and no hint on the phone (E2E).

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — high 0 · medium 0 · low 4 · false 0 · maybe-false 0

| # | Finding | Verdict | Route | Evidence |
|---|---------|---------|-------|----------|
| 1 | `CaptureService.list` shadows the builtin, so its `list[Capture]` annotation resolves to the method on Python 3.14 | low | patch | Reproduced: `inspect.get_annotations(CaptureService.list)` raises `TypeError: 'function' object is not subscriptable`. Nothing reads it today; the fix is a direct rename |
| 2 | The router's same-screen branch returns before consuming `pendingFlash`, so a flash within Captures is lost and later shows on another screen | low | patch | `render()` returns at `updateScreen(...)` before `pendingFlash`/`flashBanner` handling; no caller passes a flash yet (grep), but EXPERIENCE.md "Saved from a Capture" plans it. The fix moves existing handling, adding no branch |
| 3 | The list shows Captures whose CaptureId was hand-edited in Anki to a non-UUIDv4 (or empty), and their detail reads "This Capture isn't in Anki." | low | reject | Real but needs a user to hand-edit a managed CaptureId field in Anki. The fix adds filtering or validation branches to the adapter or the route |
| 4 | Checklist secondaries not added: `create_app` wiring for both GETs, detail strings beyond "today", AC-14 at phone width, no full reload on desktop row click | low | patch | Checked: none of these is in the three test files. Adding test cases only, no code surface |

## Design Notes

The checklist listed one secondary case: an unsaved-compose alert when a row opens on the phone. It is replaced by keeping the screen mounted. The text is hidden on the detail screen but never lost, so no alert is needed, and the router's guard still covers leaving for another screen. The checklist's risk section asked for exactly this.

## Verification

**Commands:**
- `uv run pytest tests/integration/test_anki_capture_reads.py tests/api/test_captures_read.py tests/e2e/test_captures_list.py tests/e2e/test_captures_compose.py`. Expected: all pass.
- `make test`. Expected: green.
- `uv run ruff check && uv run ruff format --check`. Expected: clean.

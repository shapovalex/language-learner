---
title: 'Delete a Capture after confirmation'
type: 'feature'
ticket: '3'
created: '2026-10-22'
status: 'built'
baseline_revision: 'f62963c9f7c3d5b31d894fd32afdb1a4ce59307a'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-3-3.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A Capture can't be deleted. There is no Delete in the AnkiStore, the API, or Capture detail (FR-13).

**Approach:** Add `delete_capture` (port, adapter, fake), `DELETE /api/captures/{captureId}`, and a reusable destructive confirmation dialog in the router, opened from "Delete Capture" in Capture detail. Make the 18 red-phase ATDD cases from commit f62963c pass, following the checklist's decisions and defaults.

## Boundaries & Constraints

**Always:**
- One lock hold. The only query is `note_query(manifest, "<Prefix> Capture")`; the CaptureId is matched in Python on the decoded, stripped field and never sent (AD-4). Every matching note id goes in one `deleteNotes`, through `client.invoke`, so the guard and the setup gate apply (AD-19).
- No match: no write, return `None` (a retried delete succeeds).
- Dialog copy: title "Delete this Capture?", body "This removes the Capture from Anki. Items you made from it stay.", Delete permanently (destructive) then Cancel (secondary). Focus starts on Cancel, Tab stays on the two buttons, Esc and a forced close are Cancel, and focus returns to the trigger.
- While the DELETE is in flight the dialog stays open, both buttons disabled, labels kept, and Esc does nothing.
- The confirmation is generic (title, body, confirm label, trigger, async action), so Item delete reuses it.
- After success, navigate to `/captures` as a same-screen update, so compose text survives.

**Never:**
- No change to the unsaved alert's behavior (`#unsaved-alert`, story 1.7 tests stay green).
- No error text built from upstream messages (AD-15). No Try again on the delete alert.
- No changes to guard.py, query.py or setup_gate.py. The ATDD tests' bodies change only by un-skipping them. Decision (2026-10-22, human): shared test helpers may be fixed where the ATDD tests can't pass otherwise (`tests/support/network.py`: `route.fallback()`), and secondary tests may extend their files' helpers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Delete | Capture present (plain or editor markup) | That note and card gone; others and another Prefix's stay; 204 | — |
| Already gone | No Capture holds the id | `None`, no write; 204 | — |
| Gated | Not `ready`, Capture present | Note kept | `setup_required`, 409 |
| Gated, nothing to delete | Not `ready`, id absent | `None` | — |
| Malformed id | `capture-1` | 404 `not_found`, store never called | Envelope only |
| Anki down | Unreachable | Nothing deleted | 503 `anki_unavailable` |
| UI failure | DELETE answers `anki_unavailable` | Dialog closes, Capture stays, inline alert "Not deleted — Anki isn't reachable" / "Make sure Anki Desktop is open on the Mac mini, then try again." | Other codes: "Not deleted" + envelope message; network: "LanguageLab could not reach the server." |

</frozen-after-approval>

## Code Map

- `ports/anki_store.py`: `delete_capture(capture_id) -> None` with a docstring; extend the module's use-case list.
- `adapters/anki/store.py`: `delete_capture` reuses `_capture_infos`. Read `noteId` from each matching entry (non-bool int, else `ANKI_UNAVAILABLE`), then one `deleteNotes(notes=[...])`. Update the module docstring.
- `tests/fakes/anki_store.py`: `delete_capture` raises busy/unavailable like the others, then `captures.pop(id, None)`. Update the docstring.
- `tests/unit/test_anki_store_port.py`: add `delete_capture` to the exact method set (~line 70) and to the module docstring.
- `features/captures/service.py`: `delete(capture_id)`.
- `features/captures/routes.py`: `@router.delete("/{capture_id}", status_code=204)` returning `Response(status_code=204)`; same `_UUID4` check as GET. `app.py` needs no change (404 and 409 are mapped).
- `static/api.js`: `deleteCapture(id)` → `request(..., {method: "DELETE"})` (204 → `null`).
- `static/index.html`: a sibling `<dialog class="alert-dialog" id="confirm-dialog" role="alertdialog" aria-labelledby aria-describedby>` with the trash icon disc (S-Delete), title, body, and Delete permanently / Cancel buttons.
- `static/router.js`: export `confirmDestructive({title, body, confirmLabel, trigger, action})` → Promise<boolean>. Reuse `cycleFocus`. `action` is async; the dialog stays busy until it settles, then closes, focuses the trigger when connected and visible, and resolves true (or rethrows the failure for the caller). Cancel resolves false. `onPopState` cancels an open, idle confirm. Update the header comment.
- `static/screens/captures.js`: in `renderDetail` "shown"/loaded state, a header row with the "Delete Capture" button (`button-destructive-text`) and, on failure, the inline alert after the article. On success, drop the Capture from `list.captures` and `list.saved`, `navigate("/captures")`, then focus the "Captures" `h1` (`tabindex="-1"`). Clear the delete error on `show()`.
- `static/css/studio.css`: `.button-destructive-text` (danger text, no fill, 44px), `.alert-dialog-icon` (48px `danger-soft` disc), and the detail action placement (phone: header beside the back link; desktop: after the "Captured …" line).

## Tasks & Acceptance

**Execution:**
- [ ] Port, adapter, fake, port unit test. Un-skip `tests/integration/test_anki_capture_delete.py` (AC-1–AC-3).
- [ ] Service and route. Un-skip `tests/api/test_captures_delete.py` (AC-4, AC-5).
- [ ] Integration secondaries: gated with nothing to delete succeeds; a `{}` entry is skipped; a malformed `noteId` is `anki_unavailable`. API: GET after DELETE is 404.
- [ ] `index.html`, `router.js`, `api.js`, `captures.js`, `studio.css`. Un-skip `tests/e2e/test_captures_delete.py` (AC-6–AC-12).
- [ ] E2E secondaries: Cancel returns focus to Delete Capture and reopening works; compose text survives a delete with no unsaved alert and focus lands on the heading; a second press while busy sends one DELETE; `anki_busy` shows "Not deleted" + message; no Delete Capture on "This Capture isn't in Anki."; the dialog fits `viewports.ALL` without horizontal scroll.

**Acceptance Criteria:**
- Given the 18 ATDD cases and the added cases, when run un-skipped, then all pass, and the 3.1, 3.2 and unsaved-alert E2E tests still pass.
- Given the full suite, when `make test`, `uv run ruff check` and `uv run ruff format --check` run, then all are clean.

## Implementation Notes

- Implemented directly in the session (no subagent), from the plan.
- `tests/support/network.py` changed despite the plan's "tests only un-skipped" scope. The method-filtered stubs (`_fulfill_json`, `HeldRoute`) passed other methods on with `route.continue_()`, which goes straight to the network and skips earlier handlers. With a DELETE stub registered before the GET stubs, the DELETE reached the live server, so AC-11 and AC-12 failed. They now use `route.fallback()`, which still reaches the server when no other handler matches. Every earlier E2E test still passes.
- The router's `confirmDestructive` keeps the dialog up while busy: Esc is ignored, and a close the browser forces reopens it until the action settles. A browser back cancels an idle dialog.
- Delete Capture shows only at `status === "shown"`, not while a Capture from the list is still being re-read.
- After a failed delete the alert re-renders the detail, so focus moves to the new Delete Capture button.
- Desktop placement uses flex `order` on the detail pane: the action row, with the back link hidden, comes after the card, and the delete alert after it.
- Added beyond the plan: API `setup_required` 409 for DELETE (the matrix row), a network-failure alert, and Esc ignored while busy.
- Verified after the review patches: `make test` passed (772 tests), and the delete and unsaved-alert E2E files pass in WebKit (78 tests). Before them, `make test` passed with 768 tests. The delete, list and unsaved-alert E2E files pass in WebKit (99 tests). `ruff check` and `ruff format --check` are clean.

## Plan Change Log

- Pass 1, finding 3 (intent_gap). The frozen Never forbade any test change beyond un-skipping, which conflicted with AC-11 and AC-12 as written. The human accepted the `tests/support/network.py` fix, and the Never now allows helper fixes. The code already matched the amended intent, so no re-derivation was needed. KEEP: the `route.fallback()` helper fix and the sibling `#confirm-dialog` design.

## Review Triage Log

### Pass 1 (quick) — high 0 · medium 0 · low 4 · false 0 · maybe-false 0

| # | Finding | Verdict | Route | Evidence |
|---|---------|---------|-------|----------|
| 1 | The desktop "Delete Capture" sits below the card. S-CapturesDesk puts it inside the card, right of the text and time | low | patch | Checked against mockup lines 52–58. Fixed: a narrow-only button in the header and a wide-only one in the card. The `order` hack is gone. Test: `test_on_desktop_delete_capture_sits_in_the_card` |
| 2 | The E2E secondary "a second press while busy sends one DELETE" is missing | low | patch | Fixed: added `test_a_second_press_while_busy_sends_no_second_delete` |
| 3 | `tests/support/network.py` changed (`continue_` → `fallback`), against the frozen Never "No changes to … the tests beyond un-skipping them" | low | intent_gap | Real deviation. Without it, AC-11 and AC-12 can't pass unless the test bodies change, which the same rule forbids. Resolved: the human accepted the helper fix, and the frozen Never was amended |
| 4 | A browser back while the DELETE is in flight changes the route under the busy dialog. A failure then shows no alert, and a success leaves focus on `<body>` | low | patch | Traced: `onPopState` → `cancelConfirm` (busy, no-op) → `render()` → `update` → `show(null)`; `onDelete`'s catch returns on `open.id !== id`. Fixed: `onPopState` puts the route back while the confirmation is busy. Test: `test_a_browser_back_while_the_delete_is_in_flight_keeps_the_capture_open` |

## Design Notes

A sibling dialog rather than generalizing `#unsaved-alert`: the unsaved alert shares `pendingAnswer` across concurrent leaves and has its own forced-close race handling, which a destructive confirm doesn't need. Sharing only `cycleFocus` keeps story 1.7's behavior untouched, as the checklist's risk section advised.

## Verification

**Commands:**
- `uv run pytest tests/integration/test_anki_capture_delete.py tests/api/test_captures_delete.py tests/e2e/test_captures_delete.py tests/e2e/test_captures_list.py tests/e2e/test_captures_compose.py tests/e2e/test_unsaved_alert.py` -- expected: all pass.
- `make test` -- expected: green.
- `uv run ruff check && uv run ruff format --check` -- expected: clean.

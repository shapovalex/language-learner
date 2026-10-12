---
title: 'Unsaved-changes alert and flash in the router'
type: 'feature'
ticket: '7'
created: '2026-10-11'
status: 'built'
baseline_revision: 'b4035265f93f15810a69c60e93db118ac9b37d5c'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-1-7.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A screen with an unsaved Draft, edits, or Preview can be left by a pill, a Menu row, a back link, or browser back with no warning, and a screen has no way to hand a one-shot message (the post-Save banner) to the next screen. Later epics need `setDirty`, `confirmLeave`, and `navigate(path, { flash })` from the router (AD-13).

**Approach:** Extend `router.js` with the dirty state, one router-owned unsaved alert dialog that guards every leave path, `confirmLeave()`, `beforeunload` while dirty, and a flash rendered after the next mount. Then turn the 11 red-phase ATDD scaffolds (49 cases) green. The checklist's "Implementation contract" section is the binding selector and behavior contract.

## Boundaries & Constraints

**Always:**
- Follow the checklist contract exactly: named exports `setDirty(state)`, `confirmLeave() → Promise<boolean>`, `navigate(path, { flash })`; one `role="alertdialog"` labelled by "Discard unsaved changes?" and described by its body; buttons "Discard" then "Keep editing"; hidden when closed; focus on Keep editing on open; Esc = Keep editing.
- Body text: `kind: "draft"` → `This Draft isn't saved.`; any other kind → `{count} unsaved changes to “{target}”`, singular `change` when count is 1, typographic quotes.
- While dirty, every in-app link click, every `navigate()` call, and browser back goes through the alert. Keep editing/Esc leaves screen and URL unchanged (browser back: the router restores the dirty screen's URL). Discard clears the dirty state and continues to the target (browser back lands on the previous entry).
- `setDirty(null)`, Discard, and every completed navigation clear the dirty state. `beforeunload` is listened to only while dirty.
- The flash is a `role="status"` element inside `main`, added after the target screen mounts and removed on the next navigation. A flash on a navigation cancelled by Keep editing is dropped.
- Clean navigation behaves exactly as in story 1.6 (`test_navigation.py`, `test_menu_sheet.py` stay green on Chromium and WebKit).
- Styles follow DESIGN.md: Alert dialog unsaved variant (centered `surface` `card-lg` card over `scrim`, no icon disc, muted body, Destructive "Discard" then Secondary "Keep editing", full width, stacked, in-alert height ≥ `--space-target-min`) and `success-banner` (`accent-soft`, `on-accent-soft`, `banner` type, no dismiss). Use existing tokens; don't edit `tokens.css`.

**Never:**
- No test-only hook or placeholder markup in `src/` (the tests inject the back link and import `router.js` themselves).
- No server change, no new dependencies, no build step.
- Don't weaken a scaffold's first assertion. No `RED_PHASE` marker remains.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Back while dirty, Keep editing | `/captures` → `/en/items`, dirty, browser back | URL back to `/en/items`, no extra back-press needed later | No error expected |
| Back while dirty, Discard | same, then Discard | lands on `/captures`, clean | No error expected |
| confirmLeave when clean | not dirty | resolves `true`, no alert | No error expected |
| Second leave while alert open | alert showing, `confirmLeave()` again | same pending answer, still one alert | No error expected |
| Flash then cancelled leave | dirty, `navigate(p, {flash})`, Keep editing | no navigation, flash never shown | Dropped |

</frozen-after-approval>

## Code Map

- `src/language_lab/static/router.js` -- add module state (`dirty`, pending answer, pending flash, `currentPath`), `setDirty`, `confirmLeave`, the alert (built in `start()` or present in `index.html`), make `navigate(path, options)` async and guarded, guard the `popstate` handler, clear dirty + remove old flash in `render()`, add the flash after `screen.mount(...)` (only for the latest `renderToken`). `onLinkClick` already funnels every in-app link (pills, Menu rows, any `main` link) into `navigate()` and already closes the Menu first — reuse it, don't add per-link handlers. Keep the same-path early return before the guard.
- `src/language_lab/static/index.html` -- optional home for the alert markup (next to `#menu-sheet`); keep `{{VERSION}}` URLs.
- `src/language_lab/static/css/studio.css` -- append `.alert-dialog` (card, title in dialog-title type, muted body, stacked buttons, `.button-destructive`, `.button-secondary`) and `.success-banner`. Note `.scrim` is `display:none` at ≥600px; the alert needs a backdrop at every width (use `::backdrop` or its own layer), above `.app-header` (z-index 3).
- `tests/e2e/test_unsaved_alert.py`, `tests/e2e/test_flash.py` -- remove `RED_PHASE` and every `@RED_PHASE`, drop the "Skipped until…" docstring sentence.
- `tests/support/unsaved.py`, `tests/support/navigation.py` -- helpers the scaffolds use; don't edit.
- `src/language_lab/app.py`, `tokens.css`, `screens/*.js` -- don't edit.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/static/router.js` -- dirty state, `setDirty`, `beforeunload`, alert open/answer, `confirmLeave`, guarded `navigate` and `popstate`, flash in `render()` -- AC-1–AC-11
- [x] `src/language_lab/static/index.html` (if markup lives there) and `src/language_lab/static/css/studio.css` -- alert dialog and success banner styles -- AC-2, AC-9
- [x] `tests/e2e/test_unsaved_alert.py`, `tests/e2e/test_flash.py` -- un-skip in the checklist's order (AC-1 → AC-6 → AC-2 → AC-3 → AC-4 → AC-10 → AC-5 → AC-11 → AC-7 → AC-8 → AC-9), watching each go red then green
- [x] `tests/e2e/test_unsaved_alert.py` -- add matrix tests: back+Keep editing then Discard via a second back reaches `/captures` in one step (no duplicate entry); a flash on a cancelled `navigate` never appears; Tab stays within the alert

**Acceptance Criteria:**
- Given the repo, when `make lint`, `make test`, and `make test-webkit` run, then all pass with 0 skipped and no `RED_PHASE` remains.
- Given the alert is open at any width, when the user presses Tab repeatedly, then focus stays on Discard / Keep editing and never reaches the page behind.
- Given the alert closes by Keep editing, when focus settles, then focus is back on the control that started the leave (the pill, the Menu button, or the back link), never inside the hidden dialog.

## Implementation Notes

- The alert is a native `<dialog>` in `index.html` (next to `#menu-sheet`), opened with `showModal()`; its backdrop is `::backdrop` in `--color-scrim` (with a literal fallback for browsers where `::backdrop` doesn't inherit custom properties yet).
- The answer settles synchronously in `answerAlert()` (buttons, Esc via `cancel`), not on the queued `close` event. Two races found while greening: resolving on `close` let a back pressed right after Keep editing reuse the stale pending answer; and the stale `close` event then dismissed the reopened alert. The `close` listener now only answers a close the browser forces (`!dialog.open`).
- Focus is trapped with an explicit Tab / Shift+Tab cycle (any modifiers, for WebKit's Alt+Tab), and Keep editing focuses the control that started the leave (the link, or the Menu button for a Menu row).
- While the alert is open, a further browser back is undone (re-push) and the open leave stands; of several `navigate()` calls awaiting one alert, only the latest proceeds on Discard.
- Added tests: Tab containment at three widths, focus return (pill, Menu button, back link), back + Keep editing then back + Discard reaches `/captures` in one step, second `confirmLeave()` shares the pending answer, flash dropped on a cancelled `navigate`.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 0, low 6, false 1, maybe-false 0.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `router.js` `onPopState` | Browser forward while dirty re-pushes after the forward target, so a later back goes to the forward entry | low | reject | Reviewer reproduced it. No unsaved data is lost because the alert still asks. It needs a forward step from a dirty screen, which is rare. Forward is P2 in the checklist backlog and outside the intent's leave paths, and the fix needs history-state indexing (a new branch and new state). |
| 2 | `router.js` `onPopState` + `go()` | A back-raised alert and a `navigate()` called meanwhile both act on one Discard (two renders, ends on /captures) | low | patch | Reproduced by the reviewer. It is only reachable programmatically, because the modal makes the page inert. Fix: the popstate leave bumps `leaveSeq` and only goes back if it is still the latest leave. |
| 3 | `router.js` `render()` | `setDirty(null)` plus `navigate()` while a `confirmLeave()` alert is open renders under the stale alert | low | reject | Needs a screen to clear dirty and navigate programmatically while a modal it opened is up. No screen does this. The fix adds a guard that ties the alert to the render. |
| 4 | `router.js` `setDirty()` | The body text doesn't refresh if the state changes while the alert is open | low | reject | The page is inert under the modal, so no user input can change the count. Only a programmatic change could, which no screen makes. The fix adds a branch. |
| 5 | `test_unsaved_alert.py` focus-return test | Likely passes on Chromium without `trigger.focus()` (native dialog restores focus) | low | reject | Test strength only. The WebKit run (R-09) exercises the explicit focus return, where clicked links don't take focus. |
| 6 | `studio.css` `.alert-dialog` | `max-width: 420px` is a literal | low | reject | No dialog-width token exists in `tokens.css` or DESIGN.md. Cosmetic. |
| 7 | `router.js` `showFlash()` | The banner sits above the per-Language segmented control | false | reject | The success banner is only used on Captures (EXPERIENCE "Saved from a Capture"), which has no Language nav. Top of `main` is the checklist decision recorded with the user. |

## Design Notes

**Dialog element.** Recommended: a native `<dialog class="alert-dialog" role="alertdialog" aria-labelledby aria-describedby>` opened with `showModal()`. It is hidden when closed, makes the rest of the page inert (focus containment), restores focus on close, and draws `::backdrop` with `--color-scrim` at every width. Handle its `cancel` event (Esc) as Keep editing with `preventDefault()` and then `close()` yourself, so one code path answers.

**Browser back.** On `popstate` while dirty: immediately `history.pushState(null, "", currentPath)` (this truncates the forward entry, so no duplicate), then ask. Keep editing: done. Discard: clear dirty, then `history.back()`; that `popstate` is now clean and renders normally.

```js
export function confirmLeave() {
  if (!dirty) return Promise.resolve(true);
  pendingAnswer ??= openAlert().finally(() => (pendingAnswer = null)); // Discard → setDirty(null), true
  return pendingAnswer;
}
```

**Flash order.** `navigate` stores the flash only after the guard passes; `render()` removes any old banner first and prepends the new one to `main` after mounting, so a stale render (token mismatch) never shows it.

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass, 0 skipped
- `make test-webkit` -- expected: all pass (R-09)
- `grep -rn RED_PHASE tests` -- expected: no matches

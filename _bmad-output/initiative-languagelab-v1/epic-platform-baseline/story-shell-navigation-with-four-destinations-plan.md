---
title: 'Shell navigation with four destinations'
type: 'feature'
ticket: '6'
created: '2026-10-11'
status: 'built'
baseline_revision: '04fe92977aa1b8a383c9a4b3aa9ff321b29a2edc'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-1-6.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The shell is one `<main>` that prints the server version. Users can't move between Captures, English, French, and Setup, and later epics have no router or screen contract (AD-13) to build on.

**Approach:** Add `router.js` with History API routing for the six destinations, a header with pills on tablet and desktop and a Menu bottom sheet on phone, a per-Language Items / Pronunciation nav, and four empty screen modules. Then turn the 12 red-phase ATDD scaffolds green. The ATDD checklist's "Implementation contract" section is the binding selector and behavior contract.

## Boundaries & Constraints

**Always:**
- Follow the checklist contract exactly: landmark names, link order and targets, headings, `aria-current="page"`, the Menu button's `aria-expanded`, the dialog named "Menu", and the screen files `screens/{captures,items,pronunciation,setup}.js` with `mount(root, params) → unmount` (`params.lang` is `"en"` or `"fr"`).
- In-app link clicks use `history.pushState` with no document load. `popstate` re-renders. A click on the current path pushes nothing. Modified clicks (Cmd, Ctrl, Shift, middle button) go to the browser. `/` and unknown paths go to `/captures` by `replaceState`.
- The router unmounts the previous screen before it mounts the next. Setup ignores a `/api/health` response that arrives after unmount.
- The Menu sheet: focus goes to the current area's row, Tab and Shift+Tab cycle through the rows (match `key === "Tab"`, whatever the modifiers, because WebKit uses Alt+Tab), and Esc, a scrim tap, the Menu button, or choosing a row closes it and returns focus to Menu. The Menu button sits above the scrim.
- Styles use the DESIGN.md components (`nav-pill`, `nav-pill-active`, `segmented-control` navigation use, `menu-sheet`, `list-row`, `list-row-selected`, scrim) through the existing tokens. Every target is at least `--space-target-min`.
- Only `api.js` calls `fetch`.

**Never:**
- No `setDirty`, `confirmLeave`, unsaved alert, `beforeunload`, or flash. Those are entry 7.
- No server change. No new dependencies, no npm, no build step.
- Screen bodies stay empty beyond their `h1`. Setup also shows the version line.
- Don't weaken a scaffold's first assertion.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Direct load | `GET /fr/pronunciation` | French pill current, Pronunciation section current, `h1` "French Pronunciation" | No error expected |
| Unknown path | `GET /de/items` or `/` | URL replaced with `/captures`, no extra history entry | No error expected |
| Same-path click | Click "Captures" on `/captures` | No new history entry | No error expected |
| Setup offline | `/api/health` fails | "LanguageLab could not reach the server." in Setup | Caught in the screen |
| Late response | Leave Setup before health resolves | Nothing is written into the unmounted root | Guarded by a flag |

</frozen-after-approval>

## Code Map

- `src/language_lab/static/index.html` -- add the header (wordmark "LanguageLab", `nav[aria-label=Main]` with four links, a "Menu" button with `aria-expanded="false"` and `aria-controls`), a hidden scrim, a hidden `div[role=dialog][aria-modal=true]` labelled by its "Menu" `h2` with the four row links, and keep `<main id="app">`, now empty. Keep the `{{VERSION}}` asset URLs.
- `src/language_lab/static/main.js` -- replace the version write with `start()` from `router.js`. The version moves to the Setup screen.
- `src/language_lab/static/router.js` (new) -- route table, `start()`, `navigate(path)`, a delegated click handler on `document` for `a[href^="/"]` that skips `/api/` and `/static/`, `popstate`, `aria-current` on Main nav and Menu rows, the Language nav, and the Menu sheet behavior. Export `navigate` so entry 7 can extend it to `navigate(path, { flash })`.
- `src/language_lab/static/screens/*.js` (new) -- four modules. Each one renders exactly one `h1`, and `unmount` calls `root.replaceChildren()`. `setup.js` imports `getHealth` from `../api.js`.
- `src/language_lab/static/css/studio.css` -- append the shell and nav component styles below the base styles, and update its header comment, which says no component styles. Keep `tokens.css` unchanged, because `tests/support/design_tokens.py` compares it with DESIGN.md.
- `src/language_lab/app.py` -- already serves the shell for every non-`/api` GET and mounts all of `static/`. Don't edit it.
- `tests/e2e/test_navigation.py`, `tests/e2e/test_menu_sheet.py` -- remove the `RED_PHASE` definition and the `@RED_PHASE` lines, and drop the "Skipped until…" sentence from each module docstring.
- `tests/support/navigation.py`, `tests/support/keys.py` -- helpers the scaffolds use. Don't edit them.
- `tests/e2e/test_shell.py`, `tests/e2e/test_studio_styles.py` -- already adjusted to pass after this story. They load `/setup`, and the focus test prepends its probe.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/static/screens/{captures,items,pronunciation,setup}.js` -- the four screen modules, with headings from the contract -- AC-6, AC-12
- [x] `src/language_lab/static/router.js` -- routing, link interception, `aria-current`, the Language nav, and the Menu sheet with its focus trap -- AC-1, AC-4, AC-5, AC-7–AC-11
- [x] `src/language_lab/static/index.html`, `src/language_lab/static/main.js` -- the header and sheet markup, and the router boot -- AC-2, AC-3
- [x] `src/language_lab/static/css/studio.css` -- pills, segmented control, Menu sheet and scrim, and the 600px breakpoint -- AC-2, AC-3
- [x] `tests/e2e/test_navigation.py`, `tests/e2e/test_menu_sheet.py` -- un-skip in the checklist's suggested order (AC-6 → … → AC-10), watching each go red and then green

**Acceptance Criteria:**
- Given the repo, when `make lint`, `make test`, and `make test-webkit` run, then all pass and no `RED_PHASE` marker remains.
- Given 600px or wider, when the shell renders, then exactly one of the pill row and the Menu button is visible, never both and never neither.
- Given the phone Menu sheet is open, when Tab is pressed on the last row, then focus wraps to the first row and never reaches the page behind.

## Implementation Notes

- Segments in the Language nav are 44px tall (`--space-target-min`), not DESIGN.md's 40px, to meet the "every target ≥ target-min" constraint.
- The `.list-row` trailing chevron is drawn with borders and `content: ""` so it adds nothing to the row's accessible name, which the tests match exactly.
- While the sheet is open, `<main>` is `inert`. When the viewport crosses 600px upward, the sheet closes through `matchMedia`.
- Red was observed with src stashed (34 failed), and green afterwards. A throwaway probe, since deleted, also checked these on Chromium and WebKit: one of pills or Menu visible at 599, 600 and 601px; Shift+Tab wraps and Tab never leaves the sheet; a same-path click pushes nothing; `/nowhere` leaves no history entry; a late `/api/health` doesn't write into an unmounted Setup.

- Matrix audit added three tests to `tests/e2e/test_navigation.py`: `test_redirect_leaves_no_history_entry`, `test_same_path_click_pushes_no_history_entry`, and `test_setup_ignores_health_after_unmount`. The last one checks the status paragraph, so removing the `mounted` guard makes it fail (verified by mutation). The Setup offline row is covered by `tests/e2e/test_shell.py::test_shows_message_when_api_fails`.
- Results: `make lint` passes, `make test` 167 passed with 0 skipped, `make test-webkit` 95 passed, and no `RED_PHASE` remains.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 3, low 3, false 1, maybe-false 0.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `tests/e2e/test_navigation.py` `test_redirect_leaves_no_history_entry` | The test passes even if the fallback used `pushState` | medium | patch | With `pushState`, history would be /nowhere → /captures → /setup, and one back still lands on /captures. Rewritten to start in-app and dispatch `popstate`, so a pushed /nowhere would bounce back to /captures instead of reaching /setup. |
| 2 | `router.js` `render()` | A failed screen import is unhandled and leaves `main` empty with no message | medium | patch | `navigate()` and `popstate` call `render()` without a catch. A stale versioned asset after a server upgrade 404s the import. Patched: the error is caught and an alert is rendered. |
| 3 | `studio.css` `:focus-visible` | The focus ring is invisible on the accent-filled current pill and the accent-bordered current Menu row | medium | patch | There is no `outline-offset`, so the 2px accent outline merges with the accent fill or border. `openMenu()` focuses exactly that row, which breaks the a11y floor. Added `outline-offset: 2px`. |
| 4 | `router.js` `matchMedia` handler and `closeMenu()` | Crossing 600px with the sheet open drops focus to `body` | low | reject | Real: the Menu button is `display: none` at that width. It takes a rotation while the sheet is open, which is rare. The fix needs a new branch to pick a focus target. |
| 5 | `studio.css` `@media (min-width: 600px)` | Desktop uses the tablet gutter (28px instead of 24px) | low | reject | Real, but 4px and cosmetic. The fix needs a desktop breakpoint, which DESIGN.md doesn't define (its layout is intrinsic). |
| 6 | `studio.css` `.main-nav` | The pill gap is `--space-3` (8px), but DESIGN.md says `{spacing.2}` (6px) | low | patch | DESIGN.md Layout says "Chip and pill groups use {spacing.2} gaps". One-token correction. |
| 7 | `router.js` `navigate()` with a Menu row | Same-path row tap focus order on WebKit | false | reject | The reviewer traced it and found focus returns to Menu as the contract requires. No bad outcome. |

## Design Notes

**Layout.** The breakpoint is 600px (`@media (min-width: 600px)`). Below it the Menu button shows and the pill row hides. At 600px and up it's the reverse. The phone header shows the wordmark at the left and Menu at the right. Screen titles in the phone header come with later screen entries.

**Language nav placement.** The router renders `nav[aria-label=English|French]` at the top of `<main>`, above a screen container that it owns, at every width. EXPERIENCE puts it in the header on iPad. The tests accept either place, and moving it later is CSS and markup only. The router renders it, not the screens, so the screens' `mount` and `unmount` stay pure and the AC-6 detached-mount check sees only the `h1`.

**Router shape.**

```js
const ROUTES = [
  [/^\/captures$/, "captures", () => ({})],
  [/^\/(en|fr)\/items$/, "items", (m) => ({ lang: m[1] })],
  [/^\/(en|fr)\/pronunciation$/, "pronunciation", (m) => ({ lang: m[1] })],
  [/^\/setup$/, "setup", () => ({})],
];
// render(path): match, or replaceState("/captures"); unmount the previous screen;
// update aria-current; mount the next screen with a dynamic import("./screens/<name>.js")
```

Guard against a stale render: if a second navigation starts while a dynamic import is pending, only the latest render mounts.

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass, 0 skipped
- `make test-webkit` -- expected: all pass (R-09)
- `grep -rn RED_PHASE tests` -- expected: no matches

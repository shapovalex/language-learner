---
runScope: 'story'
runKey: 'story-1-6'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-11'
storyId: '1.6'
storyKey: '1-6'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml (entry 6)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-1-6.md'
generatedTestFiles:
  - 'tests/e2e/test_navigation.py'
  - 'tests/e2e/test_menu_sheet.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (navigation model, Navigation and overlays, a11y floor, Responsive)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md (Navigation components)'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-13)'
  - '_bmad-output/test-artifacts/test-design/test-design-epic-1.md'
  - 'pyproject.toml'
  - 'Makefile'
  - 'src/language_lab/app.py'
  - 'src/language_lab/static/index.html'
  - 'src/language_lab/static/main.js'
  - 'tests/README.md'
  - 'tests/e2e/conftest.py'
  - 'tests/e2e/test_shell.py'
  - 'tests/e2e/test_studio_styles.py'
  - 'tests/e2e/test_api_client.py'
  - 'tests/support/viewports.py'
  - 'tests/support/dom.py'
  - 'tests/support/network.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'router.js routes /captures, /en/items, /en/pronunciation, /fr/items, /fr/pronunciation and /setup with the History API (no document reload)' }
  - { id: 'AC-2', idSource: 'generated', text: 'The header shows nav pills on tablet and desktop' }
  - { id: 'AC-3', idSource: 'generated', text: 'The phone shows a Menu bottom sheet instead of pills' }
  - { id: 'AC-4', idSource: 'generated', text: 'Each Language has an Items / Pronunciation segmented control that changes route' }
  - { id: 'AC-5', idSource: 'generated', text: 'aria-current marks the active area and the active Language section' }
  - { id: 'AC-6', idSource: 'generated', text: 'One empty screen module per destination, using mount(root, params) -> unmount' }
  - { id: 'AC-7', idSource: 'generated', text: 'At 390, 820 and 1280px every destination is reachable by nav' }
  - { id: 'AC-8', idSource: 'generated', text: 'At 390, 820 and 1280px every destination is reachable by direct URL load' }
  - { id: 'AC-9', idSource: 'generated', text: 'At 390, 820 and 1280px every destination is reachable by browser back' }
  - { id: 'AC-10', idSource: 'generated', text: 'The Menu sheet traps focus and returns it to Menu on close' }
  - { id: 'AC-11', idSource: 'generated', text: 'An unknown client path, and /, redirect to /captures in router.js (epic decision; test-design Q4, decided 2026-10-11)' }
  - { id: 'AC-12', idSource: 'generated', text: 'The server version from /api/health shows on the Setup screen, not in the shell (decided 2026-10-11)' }
---

# ATDD Checklist: Story 1.6, Shell navigation with four destinations

## Run context

- **Story source:** epic-platform-baseline `tickets.toml` entry 6. There is no story file, so the criteria come from the ticket's description (AC-1 to AC-6) and `verify` (AC-7 to AC-10) in source order, plus two criteria from decisions taken with the user in this run (AC-11, AC-12). Ids AC-1 to AC-12 are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The ticket's `verify` is a Playwright check, so every criterion here runs through pytest-playwright (dev-only, NFR-11), as stories 1.1, 1.3 and 1.5 did.
- **Test design:** `test-design-epic-1.md`. P1 rows: every destination reachable by nav, direct load and back with aria-current correct (one test per width, looping over destinations); phone Menu sheet `role=dialog` labelled "Menu", focus to the current row and trapped, Esc / scrim / Menu close and return focus (also under WebKit). P2 row: an unknown client path redirects to `/captures` (Q4). Linked risk R-09 (Chromium-only automation), mitigated by `make test-webkit` on tag runs. R-03 (leave paths while dirty) belongs to entry 7.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node.
- **Affected components:** `src/language_lab/static/router.js` (new), `src/language_lab/static/screens/*.js` (new), `src/language_lab/static/main.js` (boots the router), `src/language_lab/static/index.html` (header, Main nav, Menu button and sheet), `src/language_lab/static/css/` (pill row vs Menu by width, sheet). The server is unchanged: it already serves the shell for every non-`/api` GET.
- **Existing tests this story would break.** `tests/e2e/test_shell.py` and `open_shell()` in `test_studio_styles.py` expect `main` to read exactly "LanguageLab v…" on `/` and `/captures`. `test_keyboard_focus_shows_accent_ring` expects the first Tab from `body` to reach its probe, which the nav links will take. They are adjusted in this run so that they pass both before and after the story (see Fixture and support changes).

### Decisions taken with the user (2026-10-11)

| Question | Decision |
| --- | --- |
| Where the server version renders once screens mount | **On the Setup screen.** "LanguageLab v…" and the "could not reach the server" message live there. DESIGN.md rejects global status bars. |
| Unknown client path (test-design Q4) and `/` | **`router.js`**, which owns the route table. An unknown path or `/` is replaced (`history.replaceState`) with `/captures`. The server stays a catch-all. |
| Menu button while the sheet is open | **It stays above the scrim**, carries `aria-expanded`, and toggles the sheet closed. The Tab trap cycles through the sheet's rows only. |
| Selector contract | **Accepted as proposed:** see Implementation contract. |

## Generation mode (step 2)

AI generation. The stack is `backend`, so step 2 skips recording. The navigation UI doesn't exist yet, so there's nothing to record; the selectors come from the a11y floor (roles and accessible names) and the agreed contract.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | E2E | P1 | Desktop: load `/captures`, mark the document, click the Main nav link "Setup" | URL is `/setup` and the document marker survives (no reload) |
| AC-2 | E2E | P1 | Tablet and desktop: load `/captures` | Main nav links read Captures · English · French · Setup |
| AC-3 | E2E | P1 | Phone: load `/captures`, open Menu, choose "French" | a "Menu" button is visible |
| AC-4 | E2E | P1 | Desktop, per Language: load `/<lang>/items`, choose "Pronunciation" in the Language nav | the Language nav links read Items · Pronunciation |
| AC-5 | E2E | P1 | Desktop: direct-load each of the six destinations | exactly one Main nav link has `aria-current="page"`, and it's the destination's area |
| AC-6 | E2E | P2 | Import each screen module in the page and mount it on a detached element | mount renders the screen's `h1`, returns a function, and unmount empties the root |
| AC-7 | E2E | P1 | Per width: from `/captures`, reach every destination by nav (pill or Menu, then the Language nav) | URL and `h1` match each destination |
| AC-8 | E2E | P1 | Per width: `goto` each destination | its `h1` shows, and the URL is unchanged |
| AC-9 | E2E | P1 | Per width: visit every destination by nav, then go back through them | each back step shows the previous destination's URL and `h1` |
| AC-10 | E2E | P1 | Phone, on `/fr/pronunciation`, per close path (Esc, scrim, Menu) | focus moves to the "French" row |
| AC-11 | E2E | P2 | `goto` `/`, `/nowhere`, `/de/items` | the URL becomes `/captures` |
| AC-12 | E2E | P1 | Load `/captures`, then `/setup` | no "LanguageLab v…" text in `main` on Captures |

- **No duplicate levels.** AC-2 and AC-3 own the layout per width; AC-7 to AC-9 own reachability; AC-5 owns `aria-current`; AC-10 owns focus. AC-7 and AC-9 share one nav helper and assert only URL and heading.
- **Red reasons that come from an action.** AC-1, AC-7 and AC-9 click a nav link that doesn't exist yet, so their red failure is the action timing out on that link rather than an assertion. There's no criterion-free way to reach the transition before the UI exists. AC-12 waits for the Captures heading (unasserted setup) before the absence assertion; asserting absence without that wait would pass vacuously while `main.js` is still fetching.
- **AC-6 runs in the browser,** because there's no Node to run the modules (NFR-11). It imports the real module through its versioned URL, as `test_api_client.py` does for `api.js`.
- **AC-11** checks the URL first. Whether the redirect adds a history entry (`replaceState` vs `pushState`) is in the backlog, because `history.length` after a first `goto` differs between Chromium and WebKit.
- **WebKit (R-09).** Every leaf runs under WebKit through `make test-webkit` on tag runs. Keyboard steps use `Alt+Tab` there, since WebKit's Tab skips links.

## TDD Red Phase (Current)

✅ Red-phase scaffolds generated: **12 leaves (one per criterion), 34 cases, all `@RED_PHASE` (`pytest.mark.skip`)**. Execution was sequential: every criterion is E2E, so there was no API worker.

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/e2e/test_navigation.py` | E2E | 10 (30): AC-1, AC-2, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-11, AC-12 |
| `tests/e2e/test_menu_sheet.py` | E2E | 2 (4): AC-3, AC-10 |

Red-phase failure reasons, observed on Chromium with the skip markers stripped (34 failed):

- AC-1: `Locator.click: Timeout` on Main nav link "Setup" (no nav yet)
- AC-2: `Locator expected to have text ['Captures', 'English', 'French', 'Setup']`, actual `[]`
- AC-3: `Locator expected to be visible`, no "Menu" button
- AC-4: `Locator expected to have text ['Items', 'Pronunciation']`, actual `[]`
- AC-5: `Locator expected to have text ['<area>']`, actual `[]` (no `aria-current`), for all six destinations
- AC-6: `assert {'imported': False} == {...}`, no `static/screens/*.js`
- AC-7, AC-9: `Locator.click: Timeout` on Main nav link "Captures", inside `go_by_nav`
- AC-8: `Locator expected to have text 'Captures'`, no `h1` in `main` (aria snapshot: `main: LanguageLab v0.1.0`)
- AC-10: `Locator.click: Timeout` on the "Menu" button
- AC-11: `Page URL expected to be …/captures`, actual `/`, `/nowhere`, `/de/items`
- AC-12: `Locator.wait_for: Timeout` on the Captures heading (the unasserted setup; see Test strategy)

**Green feasibility, checked and reverted.** A throwaway stand-in (a 90-line `router.js`, four screen modules, header and sheet markup in `index.html`, a media query at 600px) turned all 34 cases green on **Chromium and WebKit**, together with the rest of the E2E suite (89 passed). Two mutations of it were then caught by the intended leaves: links doing full reloads failed AC-1 (`assert None == '<mark>'`), and removing the Tab trap failed all three AC-10 cases. All stand-in files were removed, and `src/` is unchanged.

With the scaffolds skipped, the whole suite stays green (130 passed, 34 skipped). `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P1 | `test_nav_links_route_without_reloading` | URL is `/setup`; then the document marker survives; then the Setup `h1` |
| AC-2 | P1 | `test_header_shows_pills_on_tablet_and_desktop` [tablet, desktop] | Main nav links are Captures · English · French · Setup; then Main nav visible and Menu hidden |
| AC-3 | P1 | `test_phone_menu_sheet_lists_areas_and_navigates` | a "Menu" button is visible; then Main nav hidden; the sheet lists the four areas with Captures current; "French" goes to `/fr/items` and closes the sheet |
| AC-4 | P1 | `test_language_nav_switches_section` [en, fr] | the Language nav has Items · Pronunciation; then each one routes and renders its `h1` |
| AC-5 | P1 | `test_aria_current_marks_area_and_section` [6 destinations] | exactly one Main nav link is current, the destination's area; then exactly one Language nav link is current, its section |
| AC-6 | P2 | `test_screen_module_mounts_and_unmounts` [6 screens] | one dict: imported, `h1` text, `mount` returns a function, unmount empties the root |
| AC-7 | P1 | `test_every_destination_reachable_by_nav` [phone, tablet, desktop] | URL and `h1` for each destination in turn, starting from `/setup` |
| AC-8 | P1 | `test_every_destination_loads_directly` [phone, tablet, desktop] | URL unchanged and `h1` for each destination |
| AC-9 | P1 | `test_browser_back_returns_through_destinations` [phone, tablet, desktop] | after each `go_back`, the previous destination's URL and `h1` |
| AC-10 | P1 | `test_menu_sheet_traps_and_returns_focus` [esc, scrim, menu-button] | the current area's row ("French") is focused on open; then two Tabs wrap to "Captures"; the close path hides the sheet, focuses Menu, sets `aria-expanded="false"`, and keeps the URL |
| AC-11 | P2 | `test_root_and_unknown_paths_redirect_to_captures` [`/`, `/nowhere`, `/de/items`] | URL becomes `/captures`; then the Captures `h1` |
| AC-12 | P1 | `test_server_version_shows_on_setup_only` | no "LanguageLab v…" in `main` on Captures; then it's visible on Setup |

## Implementation contract the tests encode

- **Main nav:** `<nav aria-label="Main">` with four links, in order Captures · English · French · Setup, pointing at `/captures`, `/en/items`, `/fr/items`, `/setup`. It's visible at 820 and 1280px and hidden at 390px. The tests don't pin the breakpoint itself (the stand-in used 600px).
- **Menu (phone):** a `<button>` named exactly "Menu" with `aria-expanded`, visible at 390px and hidden at 820 and 1280px. It opens an element with `role="dialog"` named "Menu" that holds the same four links (`aria-current="page"` on the current area), sitting at the bottom of the viewport over a scrim. The button stays above the scrim and toggles the sheet. On open, focus goes to the current area's row. Tab and Shift+Tab cycle through the rows. Esc, a tap on the scrim just above the sheet, or the Menu button closes it and returns focus to Menu. Choosing a row navigates and closes it.
- **Language nav:** `<nav aria-label="English">` or `"French"` on that Language's screens (anywhere inside `main`, or in the header on tablet; the tests find it by role and name at any width), with links Items · Pronunciation and `aria-current="page"` on the active one.
- **`aria-current="page"`** on the active area's Main nav link for both of its sections, and on no other Main nav link.
- **Screens:** `static/screens/{captures,items,pronunciation,setup}.js`, each exporting `mount(root, params)`, which renders exactly one `h1` into `root` and returns an `unmount()` that leaves `root` empty. `items` and `pronunciation` take `params.lang` (`"en"` or `"fr"`). Headings: Captures · English Items · French Items · English Pronunciation · French Pronunciation · Setup. Routed screens render inside `<main>`.
- **router.js:** in-app links are handled with `history.pushState`, with no document load, and `popstate` re-renders. Clicking a link to the current path must not push a duplicate entry. `/` and any unmatched path are replaced (`replaceState`) with `/captures`.
- **Setup screen:** renders "LanguageLab v{version}" from `/api/health` through `api.js`, or "LanguageLab could not reach the server." on failure. No other screen shows the version, and the shell no longer writes it into `main`.
- **Server:** unchanged. It already serves the shell for every non-`/api` GET (story 1.1).

## Fixture and support changes (made in this run)

- `tests/support/navigation.py` (new): `Destination` and the six `DESTINATIONS`, `AREAS`, `SECTIONS`, `LANDING_SECTION`; locators `main_nav()`, `language_nav()`, `menu_button()`, `menu_sheet()`, `screen_heading()`; `path_pattern()`; `go_by_nav()`, which uses a pill or the Menu sheet by width, clicks only the Language nav when already in that Language (one history entry per destination), and waits for the URL; `MARK_DOCUMENT` / `READ_MARK` for the no-reload check.
- `tests/support/keys.py` (new): `tab()` / `shift_tab()` per browser (WebKit's Tab skips links). `test_studio_styles.py` now uses it in place of its local `TAB_KEY`.
- `tests/support/dom.py`: `prepend_to_body()`.
- **Existing tests adjusted so that they pass before and after this story:**
  - `tests/e2e/test_shell.py`: both tests load `/setup` and look for the version or failure text inside `main`, instead of matching `main`'s whole text.
  - `tests/e2e/test_studio_styles.py`: `open_shell()` loads `/setup` the same way. `test_keyboard_focus_shows_accent_ring` prepends its probe, so the first Tab reaches it ahead of the nav links.
- There are no new fixtures and no Playwright Utils merged-fixtures (N/A, Python).

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` line.
2. Run it, for example `uv run pytest tests/e2e/test_navigation.py -k loads_directly` or `uv run pytest tests/e2e/test_menu_sheet.py`.
3. Watch it fail for the reason listed above, implement, and watch it pass.
4. If it fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes: no `RED_PHASE` markers remain in the two files, and `make test`, `make test-webkit` (R-09) and `make lint` pass.

Suggested order: AC-6 → AC-8 → AC-11 → AC-12 → AC-2 → AC-1 → AC-5 → AC-4 → AC-7 → AC-9 → AC-3 → AC-10.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-11 | The redirect adds no history entry: after `goto("/nowhere")` and one in-app nav, `go_back` lands on `/captures`, not `/nowhere` | P2 |
| AC-1 | Same-path click pushes no duplicate entry (click "Captures" on `/captures`, then back leaves the app's previous destination) | P2 |
| AC-1 | Modified clicks (Cmd/Ctrl/middle click) and external links are left to the browser | P3 |
| AC-5 | `aria-current` on the Menu sheet rows for every destination at phone width (AC-3 checks Captures only) | P2 |
| AC-10 | Shift+Tab from the first row wraps to the last; focus can't reach the page behind the sheet | P2 |
| AC-10 | Choosing a row moves focus somewhere sensible (the new screen's `h1` or `main`), not `body` | P3 |
| AC-6 | Navigating away calls the previous screen's `unmount` (a spy screen or a counter exposed in test builds); Setup's late `/api/health` response doesn't write into an unmounted root | P2 |
| AC-7 | The pills meet `{spacing.target-min}` (44px) and use the DESIGN.md `nav-pill` / `nav-pill-active` styles | P3 |
| AC-2/3 | A width between phone and tablet (for example 600px) shows exactly one of pills or Menu, never both or neither | P3 |
| R-09 | Every leaf above under WebKit on tag runs; already covered by `make test-webkit` once green | P1 |
| - | Manual: iPhone and iPad Safari reach every destination by nav and direct URL (test design, entry 10) | P1 (manual) |

## Open items

- **AC-6 pins file names.** `static/screens/{captures,items,pronunciation,setup}.js` with `params.lang` is the reading taken here of "one empty screen module per destination". If the developer prefers six modules (`en-items.js`, …), change `SCREEN_MODULES` in `test_navigation.py`. The behavior checked stays the same.
- **Red reasons that come from actions.** AC-1, AC-7, AC-9 and AC-10 go red on a click timeout, and AC-12 on its unasserted heading wait, because the controls they drive don't exist yet. They were checked green against the stand-in, so the assertions behind them are reachable and meaningful.
- **Entry 7 builds on this.** `go_by_nav()` and the destination table are meant for the unsaved-changes leave-path matrix (R-03). Entry 7 also needs the `dirty_screen` hook from the test design.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (ticket description and verify, plus two decisions recorded with the user), pytest-playwright is configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-12), and no supplied ids collide
- [x] Every new leaf maps to exactly one AC (docstring `AC-n:`), and every AC has exactly one red leaf
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one, or the documented action that reaches it; each red failure was observed for the expected reason
- [x] No unimplemented setup response is parsed before the criterion assertion
- [x] The adjusted existing tests pass today and passed against the stand-in
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `bmad-build` on entry 6
- [x] No CLI browser sessions were opened. The unskip plugin and the stand-in backup live in the session scratchpad, not the repo

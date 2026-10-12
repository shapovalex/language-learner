---
runScope: 'story'
runKey: 'story-1-7'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-11'
storyId: '1.7'
storyKey: '1-7'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml (entry 7)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-1-7.md'
generatedTestFiles:
  - 'tests/e2e/test_unsaved_alert.py'
  - 'tests/e2e/test_flash.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-13 Router, Crossing screens)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (Alert dialog, Unsaved changes, Success banner, a11y floor)'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md (Alert dialog unsaved-changes variant, Success banner)'
  - '_bmad-output/test-artifacts/test-design/test-design-epic-1.md'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-1-6.md'
  - 'pyproject.toml'
  - 'Makefile'
  - 'src/language_lab/static/router.js'
  - 'src/language_lab/static/index.html'
  - 'src/language_lab/static/main.js'
  - 'src/language_lab/static/screens/*.js'
  - 'tests/README.md'
  - 'tests/e2e/conftest.py'
  - 'tests/e2e/test_menu_sheet.py'
  - 'tests/e2e/test_api_client.py'
  - 'tests/support/navigation.py'
  - 'tests/support/keys.py'
  - 'tests/support/dom.py'
  - 'tests/support/viewports.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'router.setDirty(null | {kind, count, target}) sets and clears the dirty state; after setDirty(null) leaving asks nothing' }
  - { id: 'AC-2', idSource: 'generated', text: 'A single unsaved alert dialog: role=alertdialog with a labelled title and description' }
  - { id: 'AC-3', idSource: 'generated', text: 'Both body variants: "This Draft isn''t saved." for a Draft, "{count} unsaved change(s) to “{target}”" otherwise' }
  - { id: 'AC-4', idSource: 'generated', text: 'Focus starts on Keep editing when the alert opens' }
  - { id: 'AC-5', idSource: 'generated', text: 'Esc cancels the alert: the screen and URL stay' }
  - { id: 'AC-6', idSource: 'generated', text: 'While dirty, the alert intercepts pills, Menu rows, back links and browser back' }
  - { id: 'AC-7', idSource: 'generated', text: 'router.confirmLeave() resolves true on Discard (or when clean) and false on Keep editing' }
  - { id: 'AC-8', idSource: 'generated', text: 'beforeunload is registered only while dirty' }
  - { id: 'AC-9', idSource: 'generated', text: 'navigate(path, { flash }) shows a one-shot message that is gone after the next navigation' }
  - { id: 'AC-10', idSource: 'generated', text: 'Keep editing stays on the screen with the URL unchanged (browser back included)' }
  - { id: 'AC-11', idSource: 'generated', text: 'Discard navigates to where the leave path was going' }
---

# ATDD Checklist: Story 1.7, Unsaved-changes alert and flash in the router

## Run context

- **Story source:** epic-platform-baseline `tickets.toml` entry 7. There is no story file. AC-1 to AC-9 come from the ticket's description in source order. AC-10 and AC-11 are the two `verify` clauses the description doesn't already state ("Keep editing stays", "Discard navigates"). The `verify` clauses that repeat the description (leave paths, confirmLeave, flash) map to AC-6, AC-7 and AC-9. All ids are generated.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The ticket's `verify` is a Playwright check, so every criterion runs through pytest-playwright (dev-only, NFR-11), as in stories 1.5 and 1.6.
- **Test design:** `test-design-epic-1.md`. P1 rows (R-03, score 6): the unsaved alert on every leave path (pill, Menu row, back link, browser back) × {Keep editing, Discard, Esc}, focus on Keep editing, browser back leaving the URL unchanged on Keep editing; `confirmLeave()` true/false; both body variants; `role=alertdialog` labelled; `beforeunload` only while dirty (`page.on('dialog')`); flash once. R-09: also run under WebKit (`make test-webkit`). Test data: a `dirty_screen` hook to call `router.setDirty` from Playwright.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node.
- **Affected components:** `src/language_lab/static/router.js` (`setDirty`, `confirmLeave`, `navigate(path, { flash })`, the leave guard on link clicks and `popstate`, `beforeunload`), the alert dialog and flash banner markup (`index.html` or built by `router.js`), and `static/css/` (alert card over scrim, success banner). The server is unchanged.
- **Existing tests:** none break. Clean navigation behaves as in story 1.6, so `test_navigation.py` and `test_menu_sheet.py` stay green.

### Decisions taken with the user (2026-10-11)

| Question | Decision |
| --- | --- |
| Back links, before any screen has one | **The test injects one** into `main` (`<a class="back-link" href="/captures">‹ Captures</a>`). `router.js` intercepts every in-app link through one click handler, so this exercises the real leave path, and `src/` gains no placeholder markup. |
| Who renders the flash | **`router.js`**: a `role="status"` success banner at the top of `main` after the next screen mounts, removed on the next navigation. |
| `kind` values and body text | `{kind: "draft"}` → "This Draft isn't saved." Any other kind (`"edits"`, `"preview"`) → "{count} unsaved changes to “{target}”", or "1 unsaved change to “{target}”". The title is always "Discard unsaved changes?". |
| `confirmLeave()` | Clean: resolves `true` with no dialog. Dirty: shows the alert; Discard clears the dirty state and resolves `true`, and Keep editing or Esc resolves `false`. The router also clears the dirty state on every completed navigation. |
| The `dirty_screen` hook | **No test-only code in `src/`.** The test imports the real `router.js` through its versioned URL (same module instance as `main.js`, as `test_api_client.py` does for `api.js`) and calls `setDirty`, `confirmLeave` and `navigate`. |

## Generation mode (step 2)

AI generation. The stack is `backend`, so step 2 skips recording. The alert and flash don't exist yet, so there's nothing to record. Selectors come from the a11y floor (roles and accessible names) and the agreed contract.

## Test strategy (step 3)

All criteria are E2E, because the router only runs in the browser and there's no Node (NFR-11). Each criterion has one leaf. The leave-path matrix is a parameter, not extra leaves.

**Leave paths (the R-03 matrix).** The dirty screen is English Items, reached by nav from Captures so that browser back has somewhere to go. Each width uses the paths a user has there:

| Width | Paths (target) |
| --- | --- |
| phone 390 | Menu row "Setup" (`/setup`), back link (`/captures`), browser back (`/captures`) |
| tablet 820 | pill "Setup", back link, browser back |
| desktop 1280 | pill "Setup", back link, browser back |

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | E2E | P1 | Desktop: dirty, then `setDirty(null)`, then click pill "Setup" | URL becomes `/setup` |
| AC-2 | E2E | P1 | Desktop: dirty (edits), click pill "Setup" | one `alertdialog` named "Discard unsaved changes?" |
| AC-3 | E2E | P1 | Desktop, per variant (draft, edits ×2, edits ×1, preview ×1): dirty, click pill | the alert's accessible description is the exact body text |
| AC-4 | E2E | P1 | Desktop: dirty, click pill | "Keep editing" is focused |
| AC-5 | E2E | P1 | Per leave path (9): dirty, leave, press Esc | alert hidden, then URL still `/en/items` |
| AC-6 | E2E | P1 | Per leave path (9): dirty, leave | the alert is visible |
| AC-7 | E2E | P1 | Desktop, per case (clean, discard, keep-editing): call `confirmLeave()` and answer | the resolved value |
| AC-8 | E2E | P1 | Desktop, dirty and clean: close the page with `run_before_unload` | dialog types seen: `["beforeunload"]` dirty, `[]` clean |
| AC-9 | E2E | P1 | Desktop: `navigate("/setup", { flash })`, then nav to Captures, then back to Setup | a `status` in `main` reads the flash |
| AC-10 | E2E | P1 | Per leave path (9): dirty, leave, Keep editing | alert hidden, then URL still `/en/items` and the English Items heading |
| AC-11 | E2E | P1 | Per leave path (9): dirty, leave, Discard | URL is the path's target |

- **No duplicate levels.** AC-6 owns "the alert shows" per path, and AC-5, AC-10 and AC-11 own what each answer does. They pass through the alert as unasserted setup (a click on its button), so a missing alert fails them as an action timeout on the button rather than as a duplicate assertion. AC-2, AC-3 and AC-4 own the dialog's semantics, text and focus on one path, because the dialog is a single router-owned element whatever the path.
- **Red reasons that come from an action.** AC-1, AC-7 and AC-9 call `setDirty`, `confirmLeave` or `navigate(…, { flash })` from the page. Before the story, the first two throw `TypeError: … is not a function`, and the flash option is ignored. AC-5, AC-10 and AC-11 also throw on `setDirty` first. There's no criterion-free way to reach these transitions before the API exists.
- **AC-1 vs. vacuous passes.** Today any pill click navigates, so AC-1's URL assertion would pass vacuously if the setup didn't fail. It's red only because `setDirty` is missing. Once green, it's meaningful: a `setDirty(null)` that doesn't clear makes the alert block the click.
- **Browser back** must restore `/en/items` on Keep editing and Esc (the router re-pushes the URL `popstate` already moved), and land on `/captures` on Discard.
- **AC-8** closes the page with `run_before_unload=True` and accepts any dialog, so both cases end with the page closed and assert the list of dialog types it saw. Chromium only shows `beforeunload` after a user gesture, and the setup has one (the nav click to English Items).
- **WebKit (R-09).** Every leaf runs under WebKit through `make test-webkit` on tag runs.

## TDD Red Phase (Current)

✅ Red-phase scaffolds generated: **11 leaves (one per criterion), 49 cases, all `@RED_PHASE` (`pytest.mark.skip`)**. Execution was sequential: every criterion is E2E, so there was no API worker.

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/e2e/test_unsaved_alert.py` | E2E | 10 (48): AC-1 to AC-8, AC-10, AC-11 |
| `tests/e2e/test_flash.py` | E2E | 1 (1): AC-9 |

Red-phase failure reasons, observed on Chromium with the skip markers stripped (49 failed):

- AC-1 to AC-8, AC-10, AC-11 (48 cases): `Page.evaluate: TypeError: (intermediate value).setDirty is not a function`, from `open_dirty_screen()` or `set_dirty()`. `setDirty` is the first piece of the story every one of them needs, so this is an action red (see Test strategy). Once `setDirty` exists, each one reaches its own first assertion.
- AC-9: `Locator expected to have text 'Saved “jump to conclusions” to Anki. …'`, element not found. `navigate()` ignores `{ flash }` today.

**Green feasibility, checked and reverted.** A throwaway stand-in in `router.js` (about 90 added lines: `setDirty` with `beforeunload`, a `role=alertdialog` built in `start()`, `confirmLeave()`, `navigate()` awaiting it, `popstate` re-pushing `currentPath` while dirty and calling `history.back()` on Discard, dirty cleared in `render()`, and the flash as a `role=status` prepended to `main`) turned all 49 cases green on **Chromium and WebKit**, together with the rest of the E2E suite (193 passed). Four mutations of it were caught by the intended leaves:

| Mutation | Caught by |
| --- | --- |
| `popstate` doesn't re-push the URL | the 12 browser-back cases of AC-5, AC-6, AC-10, AC-11 |
| Discard and `render()` don't clear the dirty state | AC-7 `discard`, and all 9 cases of AC-11 |
| `beforeunload` listener never removed | AC-8 `clean` |
| The flash isn't removed on the next render | AC-9 |

The stand-in was removed, and `src/` is unchanged. With the scaffolds skipped, the whole suite stays green (167 passed, 49 skipped). `ruff check` and `ruff format --check` pass.

**Found while checking WebKit.** `page.close(run_before_unload=True)` never closes a page served by the app under WebKit, with or without a `beforeunload` listener. So AC-8 uses `page.reload()`, which shows the prompt on both browsers while dirty and none when clean.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P1 | `test_set_dirty_null_lets_leave_without_alert` | URL is `/setup`; then no alert; then the Setup `h1` |
| AC-2 | P1 | `test_alert_is_one_labelled_alertdialog` | exactly one `alertdialog` named "Discard unsaved changes?"; then exactly one alertdialog at all; its accessible description; buttons Discard · Keep editing |
| AC-3 | P1 | `test_alert_body_names_what_is_lost` [draft, edits-2, edits-1, preview-1] | the accessible description is the exact body |
| AC-4 | P1 | `test_alert_focuses_keep_editing` | Keep editing is focused |
| AC-5 | P1 | `test_escape_cancels_the_leave` [9 leave paths] | alert hidden after Esc; then URL and `h1` still English Items |
| AC-6 | P1 | `test_every_leave_path_raises_the_alert` [9 leave paths] | alert visible; then URL still `/en/items` |
| AC-7 | P1 | `test_confirm_leave_resolves_with_the_answer` [clean, discard, keep-editing] | the resolved value; then no alert, URL unchanged, and the Setup pill leads to `/setup` (clean, discard) or stays (keep-editing) |
| AC-8 | P1 | `test_beforeunload_only_while_dirty` [dirty, clean] | dialog types seen on reload: `["beforeunload"]` or `[]` |
| AC-9 | P1 | `test_flash_shows_once_then_goes` | a `status` in `main` reads the flash; then the Setup `h1`; gone on Captures; still gone back on Setup |
| AC-10 | P1 | `test_keep_editing_stays_on_the_screen` [9 leave paths] | alert hidden; then URL and `h1` still English Items; the same leave raises exactly one alert again |
| AC-11 | P1 | `test_discard_continues_the_leave` [9 leave paths] | URL is the path's target; then no alert, the target's `h1`, and a further nav to French Items asks nothing |

## Implementation contract the tests encode

- **Exports from `router.js`:** `setDirty(state)` with `state` = `null` or `{kind, count, target}`; `confirmLeave()` → `Promise<boolean>`; `navigate(path, { flash })`, where `flash` is optional. The tests import the module from `/static/<version>/router.js`, so these must be named exports of the module `main.js` starts.
- **The alert:** one element with `role="alertdialog"`, named by its title "Discard unsaved changes?" (`aria-labelledby`) and described by its body (`aria-describedby`). Two buttons in this order: "Discard", then "Keep editing". Hidden (not just transparent) when closed. Focus goes to Keep editing on open. Esc answers Keep editing.
- **Body text:** `kind: "draft"` → `This Draft isn't saved.` Any other kind → `{count} unsaved changes to “{target}”`, with `change` when `count` is 1. The quotes are typographic (U+201C, U+201D).
- **Leave paths while dirty:** any in-app link click (Main nav pill, Menu sheet row, a back link anywhere in `main`), any `navigate()` call, and browser back. On Keep editing or Esc, the screen and URL are unchanged: for browser back, the router puts the dirty screen's URL back. On Discard, the leave continues to its target (browser back lands on the previous entry), and the dirty state is cleared.
- **Clearing:** `setDirty(null)`, Discard (from a leave or from `confirmLeave()`), and every completed navigation clear the dirty state.
- **`confirmLeave()`:** clean → `true` with no alert. Dirty → the alert; Discard → `true`, Keep editing or Esc → `false`. It never navigates.
- **`beforeunload`:** a listener that prompts while dirty only (registered in `setDirty`, removed on clear).
- **Flash:** `navigate(path, { flash })` renders the message after the target screen mounts, as a `role="status"` element inside `main` (DESIGN `success-banner`, no dismiss control). The next navigation removes it, and it never comes back.
- **Server:** unchanged.

## Fixture and support changes (made in this run)

- `tests/support/unsaved.py` (new): `ROUTER_JS`; `set_dirty()`, `navigate()`, `start_confirm_leave()` / `confirm_leave_result()`, which call the real router from the page; `unsaved_alert()`, `discard_button()`, `keep_editing_button()`; `DRAFT`, `EDITS`, `TARGET`, `ALERT_TITLE`; `open_dirty_screen()` (Captures, then English Items by nav, then `setDirty`); `reload_collecting_dialogs()`; and `LEAVE_PATHS`, the nine width × path cases with their targets. The back-link path injects `<a class="back-link" href="/captures">‹ Captures</a>` into `main` (idempotent).
- `tests/README.md`: lists `unsaved.py` under support.
- Existing tests: no changes. There are no new fixtures and no Playwright Utils merged-fixtures (N/A, Python).

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` line (or the module's `RED_PHASE` marker use on that test).
2. Run it, for example `uv run pytest tests/e2e/test_unsaved_alert.py -k set_dirty_null` or `uv run pytest tests/e2e/test_flash.py`.
3. Watch it fail for the reason listed above, implement, and watch it pass.
4. If it fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes: no `RED_PHASE` markers remain in the two files, and `make test`, `make test-webkit` (R-09) and `make lint` pass.

Suggested order: AC-1 (`setDirty`) → AC-6 → AC-2 → AC-3 → AC-4 → AC-10 → AC-5 → AC-11 → AC-7 → AC-8 → AC-9.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-2 | Focus is trapped in the alert (Tab and Shift+Tab cycle Discard ↔ Keep editing); `main` and the header are inert behind it | P1 |
| AC-10 | Keep editing returns focus to the control that started the leave (the pill, the Menu button, the back link) | P2 |
| AC-6 | `navigate(path)` called by a screen while dirty raises the alert (the programmatic leave path) | P2 |
| AC-6 | Browser forward while dirty is guarded the same way as back | P2 |
| AC-10 | After Keep editing on browser back, history isn't left with a duplicate entry that makes the next back a no-op | P2 |
| AC-11 | Discard from the phone Menu row leaves the Menu sheet closed and the scrim gone | P2 |
| AC-9 | A flash on a `navigate()` blocked by Keep editing is dropped, not shown on a later screen | P2 |
| AC-9 | The banner uses DESIGN `success-banner` (accent-soft row, check icon) | P3 |
| AC-3 | Visual: the unsaved variant has no icon disc and no chips; Discard is Destructive, Keep editing Secondary, full width and stacked | P3 |
| R-09 | Every leaf above under WebKit on tag runs; already covered by `make test-webkit` once green | P1 |
| R-03 | Manual: iOS swipe-back and bfcache on iPhone and iPad Safari (entry 10) | P1 (manual) |

## Open items

- **Most leaves go red on `setDirty` first.** 48 of the 49 cases fail in setup with `setDirty is not a function` until AC-1's export lands, so their own first assertions show only after that. They were checked green and mutation-tested against the stand-in, so the assertions behind the setup are reachable and meaningful.
- **AC-1 is vacuous without the setup failing.** Today any pill click navigates. Once `setDirty` exists, AC-1 is meaningful: a `setDirty(null)` that doesn't clear makes the alert block the click.
- **The back link is injected.** When the first detail screen ships a real back link (Epic 4 or 5), add a case for it to the leave-path matrix there.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (ticket description and verify, plus decisions recorded with the user), pytest-playwright is configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-11), and no supplied ids collide
- [x] Every new leaf maps to exactly one AC (docstring `AC-n:`), and every AC has exactly one red leaf
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one; where an action fails first (`setDirty`), that is documented and each red failure was observed
- [x] No unimplemented setup response is parsed before the criterion assertion
- [x] Existing tests are unchanged and pass
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `bmad-build` on entry 7
- [x] No CLI browser sessions were opened. The unskip plugin, the probe scripts and the `router.js` backups live in the session scratchpad, not the repo

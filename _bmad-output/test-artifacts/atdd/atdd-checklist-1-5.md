---
runScope: 'story'
runKey: 'story-1-5'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-11'
storyId: '1.5'
storyKey: '1-5'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml (entry 5)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-1-5.md'
generatedTestFiles:
  - 'tests/unit/test_studio_assets.py'
  - 'tests/api/test_shell_styles.py'
  - 'tests/e2e/test_studio_styles.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-platform-baseline/epic-platform-baseline.md'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md'
  - '_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md (a11y floor, safe areas)'
  - '_bmad-output/test-artifacts/test-design/test-design-epic-1.md'
  - 'pyproject.toml'
  - 'src/language_lab/app.py'
  - 'src/language_lab/static/index.html'
  - 'src/language_lab/static/main.js'
  - 'tests/conftest.py'
  - 'tests/README.md'
  - 'tests/e2e/conftest.py'
  - 'tests/e2e/test_shell.py'
  - 'tests/e2e/test_api_client.py'
  - 'tests/support/network.py'
  - 'tests/support/viewports.py'
  - 'tests/support/live_server.py'
  - 'tests/support/fixtures/live_server.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'static/css holds the DESIGN.md Studio tokens (colors, spacing, radius, type scale)' }
  - { id: 'AC-2', idSource: 'generated', text: 'Base styles give a visible focus ring' }
  - { id: 'AC-3', idSource: 'generated', text: 'Base styles set inputs at 16px or more' }
  - { id: 'AC-4', idSource: 'generated', text: 'Base styles respect safe areas' }
  - { id: 'AC-5', idSource: 'generated', text: 'Figtree is vendored with its license under static/vendor/' }
  - { id: 'AC-6', idSource: 'generated', text: 'The shell loads Figtree, and Figtree is applied' }
  - { id: 'AC-7', idSource: 'generated', text: 'pytest-playwright (dev-only) is set up with a live-server fixture in tests/e2e/conftest.py that later entries reuse' }
  - { id: 'AC-8', idSource: 'generated', text: 'Every request the served shell makes goes to the app, none to an external host' }
---

# ATDD Checklist: Story 1.5, Studio styles and vendored Figtree

## Run context

- **Story source:** epic-platform-baseline `tickets.toml` entry 5. There is no story file, so the criteria come from the ticket's description and `verify` in source order, with generated ids AC-1 to AC-8.
- **Stack:** `backend` by detection (pyproject, pytest, no `package.json`). The ticket's own `verify` is a Playwright check, so the browser criteria use pytest-playwright (dev-only, NFR-11), as stories 1.1 and 1.3 did.
- **Test design:** `test-design-epic-1.md`. P2 rows: Figtree applied and no external request; focus ring on Tab; input font-size ≥16px. P3 rows: token values match DESIGN.md (parse and compare); safe-area insets (manual, entry 10). No high risk is linked.
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, and NFR-11 rules out Node.
- **Affected components:** `src/language_lab/static/css/` (new), `src/language_lab/static/vendor/figtree/` (new), `src/language_lab/static/index.html` (stylesheet link, `viewport-fit=cover`).
- **Execution:** sequential. There was a single worker for every level; the suite is small and Python-only.
- **AC-7 is already met.** Framework setup (commit `17e9b99`) added pytest-playwright, `live_server` (`tests/support/fixtures/live_server.py`) and the `base_url` override in `tests/e2e/conftest.py`. The smoke test `test_live_server_answers_on_its_settings_port` covers it.

### Decisions taken with the user (2026-10-11)

| Question | Decision |
| --- | --- |
| Custom-property naming | **Prefixed by group**, mapped 1:1 from the DESIGN.md front matter: `--color-<name>`, `--space-<name>`, `--radius-<name>` (from `rounded`), and per typography role `--font-size-<role>`, `--font-weight-<role>`, plus `--line-height-<role>` and `--letter-spacing-<role>` where DESIGN.md sets them. |

## Generation mode (step 2)

AI generation. The stack is `backend`, so there's no recording. The browser checks read computed styles, `document.fonts` and the request log through pytest-playwright, with no selectors to record.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Unit | P3 | Parse the DESIGN.md front matter and every `:root` custom property in `static/css/*.css` | no expected token name is missing |
| AC-2 | E2E | P2 | A button appended to the served shell, focused with Tab | its outline is `solid`, `2px`, accent `rgb(90, 69, 200)` |
| AC-3 | E2E | P2 | A text input, a textarea and a select appended to the shell at phone width | none has a computed font-size below 16px |
| AC-4 | API | P3 | GET the shell and the stylesheets it links | the viewport meta has `viewport-fit=cover` |
| AC-5 | Unit | P2 | List `static/vendor/figtree/` in the package | it holds at least one `.woff2` |
| AC-6 | E2E | P2 | Load the shell, wait for the version text and `document.fonts.ready` | a Figtree face has loaded (fonts load only when rendered text uses them) |
| AC-7 | E2E (existing) | smoke | `test_live_server_answers_on_its_settings_port` | already green, so no red leaf |
| AC-8 | E2E | P2 | Record every request with its resource type while the shell loads and its fonts settle | a `stylesheet` and a `font` request were made |

- **No duplicate levels.** AC-6 asserts that the font renders, and AC-8 asserts where requests go.
- **AC-8 and the existing P2 test.** `test_requests_stay_on_app_origin` already asserts "nothing off-origin", but it passes vacuously while the shell loads no CSS or font. The AC-8 leaf asserts first that those requests exist. Once it's green, the old test is redundant (see the backlog).
- **AC-6's first assertion** is "a Figtree face loaded", not the computed `font-family`. The CSS can name Figtree while the file 404s and the fallback renders. The computed family and the four weights (400/500/600/700) follow in the same leaf. They work for a variable font and for one file per weight.
- **AC-4** stays at API level. Chromium can't emulate safe-area insets, so the leaf checks the two things that make them work on iOS: `viewport-fit=cover` and `env(safe-area-inset-*)` in the CSS. The device check remains manual (entry 10, P3).
- **AC-2 and AC-3 append test-only controls** to `document.body`, because the shell has no focusable element or field yet. They append to `body`, not `#app`, which `main.js` rewrites.
- **AC-7 has no red leaf.** It can't fail before implementation, because it's already implemented. This is a recorded exception to "one red leaf per criterion".

## TDD Red Phase (Current)

✅ Red-phase scaffolds generated: **7 leaves (one per criterion except AC-7), all `@pytest.mark.skip`**. Each one was checked to fail for the expected reason with its skip marker stripped.

| File | Level | Leaves |
| --- | --- | --- |
| `tests/unit/test_studio_assets.py` | Unit | 2 (AC-1, AC-5) |
| `tests/api/test_shell_styles.py` | API | 1 (AC-4) |
| `tests/e2e/test_studio_styles.py` | E2E | 4 (AC-2, AC-3, AC-6, AC-8) |

Red-phase failure reasons, observed with the skip markers stripped:

- AC-1: `assert ['--color-accent', …] == []`. All 111 expected tokens are missing, because `static/css/` doesn't exist.
- AC-2: `{'outlineStyle': 'auto', 'outlineWidth': '1px', 'outlineColor': 'rgb(0, 95, 204)'} != FOCUS_RING`. That's Chromium's default ring.
- AC-3: `{'Input probe': 13.3333, 'Select probe': 13.3333, 'Textarea probe': 13.3333} == {}`
- AC-4: `assert 'viewport-fit=cover' in ['width=device-width', 'initial-scale=1']`
- AC-5: `assert [] != []`. There are no `.woff2` files under `static/vendor/figtree/`.
- AC-6: `assert 0 > 0`. No Figtree face has loaded.
- AC-8: `{'font', 'stylesheet'} <= {'document', 'fetch', 'script'}`

**Green feasibility, checked and reverted.** A throwaway `tokens.css` (generated from DESIGN.md), a `base.css` and two lines in `index.html` turned AC-1, AC-2, AC-3, AC-4 and AC-6 green. The stand-in used `@font-face { src: local("Helvetica") }`. AC-5 and AC-8 stayed red, as they should, because no vendored `.woff2` was fetched. So AC-6 alone can't prove the font is vendored; AC-8's `font` request from the app origin is what proves it. All throwaway files were removed, and `src/` is unchanged.

With the scaffolds skipped, the whole suite stays green (89 passed, 7 skipped). `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P3 | `test_css_declares_every_design_md_token` | no expected token is missing; then every value matches DESIGN.md (case- and quote-insensitive) |
| AC-2 | P2 | `test_keyboard_focus_shows_accent_ring` | outline `solid` / `2px` / `rgb(90, 69, 200)` on a Tab-focused button |
| AC-3 | P2 | `test_form_fields_use_at_least_16px_text` | no input, textarea or select below 16px at 390px width |
| AC-4 | P3 | `test_shell_and_styles_respect_safe_areas` | `viewport-fit=cover`; then the linked CSS (and its `@import`s) uses `env(safe-area-inset-{top,right,bottom,left}` |
| AC-5 | P2 | `test_figtree_is_vendored_with_its_license` | at least one `.woff2` in `static/vendor/figtree/`; then `OFL.txt` exists and names the SIL Open Font License |
| AC-6 | P2 | `test_shell_renders_in_vendored_figtree` | a Figtree face loaded through rendering; then `main`'s computed family starts with Figtree; then weights 400/500/600/700 all load |
| AC-7 | smoke | `test_live_server_answers_on_its_settings_port` (existing, green) | already met by framework setup, so no red leaf |
| AC-8 | P2 | `test_styles_and_fonts_come_from_the_app` | a `stylesheet` and a `font` request were made; then no request left `base_url` |

AC-2's `expect(probe).to_be_focused()` comes before the criterion assertion. It's setup that already passes today (Tab from `body` reaches the only focusable element), so it can't change the first failure.

## Implementation contract the tests encode

- **`src/language_lab/static/css/*.css`**: any file layout works. The AC-1 test reads every custom property in every `.css` file there. It expects the 111 properties derived from the DESIGN.md front matter: `--color-*` (29), `--space-*` (22), `--radius-*` (12), and per typography role `--font-size-*` and `--font-weight-*`, plus `--line-height-*` and `--letter-spacing-*` for the roles that set them. `fontFamily` isn't a token. Values compare case-insensitively without quotes, so `#5A45C8` matches `#5a45c8` and `700` matches `'700'`. The test reads DESIGN.md itself, so a token added there later turns the test red until the CSS follows.
- **`index.html`**: the viewport meta gains `viewport-fit=cover`, and it gets at least one `<link rel="stylesheet">` under the versioned `/static/{{VERSION}}/` prefix. `@import` between sheets is followed by the AC-4 test.
- **Base styles**: `:focus-visible` gets `outline: 2px solid var(--color-accent)` (computed `rgb(90, 69, 200)`). `input`, `textarea` and `select` get `font-size` ≥ 16px. Safe-area padding uses all four `env(safe-area-inset-*)` sides. `body` (or at least `main`) uses `font-family: Figtree, system-ui, sans-serif`.
- **`static/vendor/figtree/`**: one or more `.woff2` files and `OFL.txt`. Either a variable font (`font-weight: 400 700`) or one file per weight passes AC-6, provided 400, 500, 600 and 700 each resolve to a loaded Figtree face. There's no Google Fonts URL anywhere (AC-8).
- **Packaging**: the wheel must carry `css/` and `vendor/`. `uv_build` includes the whole package dir today. The built-wheel smoke test (P0, entry 8) checks this end to end.

## Fixture and support changes (made in this run)

- `tests/support/design_tokens.py` (new): `load_front_matter()`, a parser for DESIGN.md's YAML subset, since no YAML dependency ships; `expected_custom_properties()`; `css_custom_properties()`; `normalize()`.
- `tests/support/shell.py` (new): `parse_shell()`, `viewport_directives()`, `fetch_stylesheets()`.
- `tests/support/dom.py` (new): `append_to_body()`, `computed_style()`, `px()`, `settle_fonts()`.
- `tests/support/network.py`: `Resource` and `record_resources()`.
- `tests/README.md`: the layout table lists the new helpers.
- There are no new fixtures and no Playwright Utils merged-fixtures (N/A, Python).

## Next Steps (Task-by-Task Activation)

1. Pick a task. Remove its `@RED_PHASE` line.
2. Run it, for example `uv run pytest tests/unit/test_studio_assets.py` or `uv run pytest tests/e2e/test_studio_styles.py -k figtree`.
3. Watch it fail for the reason listed above, implement, and watch it pass.
4. If it fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes: no `RED_PHASE` markers remain in the three files, and `make test` and `make lint` pass.

Suggested order: AC-1 → AC-4 → AC-2 → AC-3 → AC-5 → AC-6 → AC-8.

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-8 | Delete `test_requests_stay_on_app_origin` in `tests/e2e/test_shell.py`. The AC-8 leaf subsumes it and isn't vacuous. | P2 |
| AC-8 | Every `/static/` request uses the versioned prefix `/static/{__version__}/` (cache busting for the CSS and fonts) | P2 |
| AC-2 | Focus ring on a link and a text field too (parametrize); a field's border also switches to `accent` on focus (DESIGN.md text-field `borderFocus`) | P2 |
| AC-2 | No ring on mouse click (`:focus-visible`, not `:focus`) | P3 |
| AC-3 | `input[type=search]`, `type=number` and `contenteditable` also ≥16px | P3 |
| AC-6 | The same check under WebKit on tag runs (iPhone/iPad proxy, R-09). It's already covered by `make test-webkit` once green. | P2 |
| AC-6 | Cyrillic text falls back to `system-ui` without a failed request (DESIGN.md: Figtree ships Latin only) | P3 |
| AC-5 | The built wheel contains `static/vendor/figtree/*.woff2` and `OFL.txt` (fold into entry 8's wheel smoke test) | P1 (entry 8) |
| AC-4 | Manual: safe-area insets on iPhone, notch and home bar (test design P3, entry 10) | P3 (manual) |
| AC-1 | `--font-family-*` token if the developer adds one (DESIGN.md has a single family, so it isn't required) | - |

## Open items

- **AC-1 reads a planning artifact.** The token test parses `_bmad-output/.../DESIGN.md` from the repo, as the test design asks ("parse-and-compare"). If DESIGN.md moves, update `DESIGN_MD` in `tests/support/design_tokens.py`.
- **AC-7 has no red leaf.** It was implemented by framework setup before this story. That's a deliberate exception to "one red leaf per criterion".
- **The test design's "live_server port registered in the allow-list"** belongs to entry 4, not here. The fixture already passes its port through settings (R-14).

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (ticket description and verify), pytest and pytest-playwright are configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-8), and no supplied ids collide
- [x] Every new leaf maps to exactly one AC (docstring `AC-n:`). Every AC except AC-7 (already met, recorded) has exactly one red leaf
- [x] Every scaffold is skipped with a reason, and none uses placeholder assertions
- [x] The first assertion is the criterion-defining one, and each red failure was observed for the expected reason
- [x] No unimplemented setup response is parsed before the criterion assertion. AC-4 parses the shell, which exists today, and fetches stylesheets only after the first assertion.
- [x] Story handoff: there's no story file to link, so this checklist is the handoff for `bmad-build` on entry 5
- [x] No CLI browser sessions were opened. The temp red-check plugin lives in the session scratchpad, not the repo.

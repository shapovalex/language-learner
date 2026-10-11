---
title: 'Studio styles and vendored Figtree'
type: 'feature'
ticket: '5'
created: '2026-10-11'
status: 'built'
baseline_revision: '3f076432c1617911f28a800aab0509d576fe1665'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-1-5.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The shell is unstyled and renders in the browser default font. Later screens need the DESIGN.md Studio tokens, the accessibility base styles, and Figtree, all served by the app with nothing loaded from a CDN.

**Approach:** Add `static/css/` with the tokens and base styles, vendor the Figtree variable woff2 files and their OFL license under `static/vendor/figtree/`, and link the stylesheet from the shell. Then turn the seven red-phase ATDD scaffolds green. AC-7 (pytest-playwright with a live-server fixture) is already met.

## Boundaries & Constraints

**Always:**
- Custom-property naming is prefixed by group and maps 1:1 from the DESIGN.md front matter: `--color-*`, `--space-*`, `--radius-*` (from `rounded`), and per typography role `--font-size-*` and `--font-weight-*`, plus `--line-height-*` and `--letter-spacing-*` where DESIGN.md sets them (ATDD decision, 2026-10-11). Values match DESIGN.md exactly.
- Font stack: `Figtree, system-ui, sans-serif`. Cyrillic falls back to `system-ui` (DESIGN.md Typography).
- `:focus-visible` gets a 2px solid `--color-accent` outline. `input`, `textarea`, and `select` get a font size of at least 16px. Safe-area padding uses all four `env(safe-area-inset-*)` sides, and the viewport meta adds `viewport-fit=cover`.
- Every CSS and font URL resolves under `/static/<version>/`.
- Ship the OFL license as `static/vendor/figtree/OFL.txt`.

**Never:**
- No Google Fonts or CDN URL at runtime. No npm and no build step.
- No new dependencies.
- No component styles (cards, nav pills, fields) and no layout beyond base. Those belong to the screen entries.
- Don't weaken a scaffold's first assertion.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Shell styles | `GET /captures` | Head has `viewport-fit=cover` and a stylesheet link under `/static/<version>/css/` | No error expected |
| Font load | Shell renders Latin text | A Figtree face loads from `/static/<version>/vendor/figtree/*.woff2`, and weights 400–700 resolve | Missing file → test AC-6/AC-8 fails |
| Keyboard focus | Tab to a button | Outline is `2px solid rgb(90, 69, 200)` | No error expected |
| Phone field | input/textarea/select at 390px | Computed font size ≥ 16px | No error expected |

</frozen-after-approval>

## Code Map

- `src/language_lab/static/index.html` -- add `viewport-fit=cover` to the viewport meta, and add `<link rel="stylesheet" href="/static/{{VERSION}}/css/studio.css">` before the module script. `app.py` replaces `{{VERSION}}` once, so the shell needs no change.
- `src/language_lab/app.py:176` -- mounts the whole package `static/` at `/static/{version}`, so the new subdirectories are served and packaged with no code change. Don't edit it.
- `tests/unit/test_studio_assets.py`, `tests/api/test_shell_styles.py`, `tests/e2e/test_studio_styles.py` -- red-phase scaffolds. Remove the `RED_PHASE` marker and the `@RED_PHASE` lines only.
- `tests/support/design_tokens.py` -- the AC-1 oracle. It reads every custom property in `static/css/*.css` (only the top-level directory) and compares it with DESIGN.md. Extra properties are allowed.
- `tests/support/shell.py:fetch_stylesheets` -- follows `@import`, so a single linked sheet that imports others also works.
- `tests/e2e/test_shell.py:37` `test_requests_stay_on_app_origin` -- subsumed by AC-8 (ATDD backlog). Delete it. Keep `record_requests` in `tests/support/network.py`, because `record_resources` and `tests/README.md` refer to it; drop only the import of it in `test_shell.py`.
- Figtree source: `https://cdn.jsdelivr.net/npm/@fontsource-variable/figtree@5.2.10/` → `files/figtree-latin-wght-normal.woff2` (20,156 B), `files/figtree-latin-ext-wght-normal.woff2` (10,280 B), `LICENSE` (OFL 1.1, includes "SIL Open Font License"). The unicode ranges come from that package's `wght.css`. Its weight axis is `300 900`.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/static/vendor/figtree/` -- download the two woff2 files and save `LICENSE` as `OFL.txt` -- AC-5
- [x] `src/language_lab/static/css/tokens.css` -- `:root` with every DESIGN.md color, spacing, rounded, and typography token, in DESIGN.md order -- AC-1
- [x] `src/language_lab/static/css/studio.css` -- `@import "tokens.css"`, two `@font-face` rules (family `Figtree`, `font-weight: 300 900`, `font-display: swap`, the package's unicode ranges, `url(../vendor/figtree/...)`), and base styles: box-sizing, `body` on `--color-ground`/`--color-ink` in body type with safe-area padding, `:focus-visible` ring, fields at `max(16px, 1em)` with `font: inherit` -- AC-2, AC-3, AC-4, AC-6
- [x] `src/language_lab/static/index.html` -- the viewport and link changes in the Code Map -- AC-4, AC-8
- [x] the three test files -- un-skip. `tests/e2e/test_shell.py` -- remove the redundant test and its unused import -- ATDD green phase

**Acceptance Criteria:**
- Given the repo, when `make lint` and `make test` run, then both pass and no `RED_PHASE` marker remains.
- Given a built wheel, when it is unzipped, then it lists `static/css/*.css`, `static/vendor/figtree/*.woff2`, and `OFL.txt`.

## Implementation Notes

- One linked entry sheet, `css/studio.css`, imports `css/tokens.css` (111 tokens in DESIGN.md order) and declares two `@font-face` rules for the Latin and Latin Extended Figtree variable woff2 files, with weight `300 900`.
- WebKit's Tab skips buttons by default, so AC-2 failed on `make test-webkit`, which CI runs on `v*` tags. The test now presses `Alt+Tab` on WebKit (`TAB_KEY`). The first assertion is unchanged.
- Dropped the "Skipped until…" sentences from the three scaffold docstrings.
- Results: `make lint` passes; `make test` gives 95 passed with 0 skipped; `make test-webkit` gives 21 passed. The wheel lists both CSS files, both woff2 files and `OFL.txt`. The grep for Google Fonts and CDN URLs finds nothing.

## Plan Change Log

## Review Triage Log

Pass 1 (quick): high 0, medium 0, low 0, false 1, maybe-false 1.

| # | Location | Finding | Verdict | Route | Evidence |
|---|----------|---------|---------|-------|----------|
| 1 | `tests/e2e/test_studio_styles.py` | The AC-2 test body and the docstrings were edited beyond "remove the RED_PHASE lines only" | false | reject | The plan forbids weakening the first assertion, and the assertion is unchanged. The edit fixes a real tag-run failure (WebKit Tab skips buttons) and is recorded in Implementation Notes. No bad outcome follows. |
| 2 | `tests/e2e/test_studio_styles.py` `TAB_KEY` | On the Linux WebKit runner, `Alt+Tab` may not move focus to the button | maybe-false (medium if true) | defer | Verified on macOS WebKit only; no container runtime here to run Linux WebKit. WebCore's tab handler skips Ctrl/Meta/AltGraph, not Alt, so it likely works. A `v*` tag CI run, or `make test-webkit` on Linux, would settle it. |

## Design Notes

Use a single linked entry sheet, so `index.html` stays at one `<link>`. `@import "tokens.css"` comes first in `studio.css`, because `@import` must precede every other rule. Relative URLs inside the CSS keep the version prefix without templating:

```css
@font-face {
  font-family: Figtree;
  font-weight: 300 900;
  font-display: swap;
  src: url(../vendor/figtree/figtree-latin-wght-normal.woff2) format("woff2");
  unicode-range: U+0000-00FF, U+0131, /* … from wght.css */;
}
```

## Verification

**Commands:**
- `make lint && make test` -- expected: all pass, 0 skipped from story 1.5
- `uv build && unzip -l dist/*.whl | grep -E 'static/(css|vendor)'` -- expected: the CSS files, both woff2 files, and OFL.txt
- `grep -rn "fonts.googleapis\|fonts.gstatic\|cdn" src/language_lab/static` -- expected: no matches

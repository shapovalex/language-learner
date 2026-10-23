---
title: 'Card templates and acceptance on the released wheel'
type: 'feature'
ticket: '4'
created: '2026-10-23'
status: 'done'
baseline_revision: '6d4becc665a77dc94ee00ba8833cf4cf694091f8'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Understand, Produce and Write templates and `cards.css` are working placeholders. AC15 (FR-21) needs the agreed fronts, backs, hints and audio placement in the Studio palette. Epic 4's Done-when 1–5 also rest on real Anki, AnkiMobile and iOS Safari, which only the Mac Mini, iPhone and iPad have. So do the deferred R-03 Draft check, the `decode_field` blank-line question, the `read_leftovers` timing and the hand-built `changeDeck`/`updateNoteFields`/`cardsInfo` replies.

**Approach:**
1. Rewrite the six Study template pairs and `cards.css` in the Studio palette, and pin FR-21/AD-10 in pytest. Setup then offers a templates Repair on an existing collection.
2. After merge, the user cuts the release and runs a step-by-step runbook on the Mac Mini with `ANKI_PREFIX=LanguageLabDev`.
3. Results go into the acceptance file, recorded replies become fixtures, and every finding is fixed or ticketed.

## Boundaries & Constraints

**Always:**
- Templates read only declared, non-hidden fields:
  - `Russian` (primary) is on the Produce/Write fronts and on every back.
  - `RussianAlternatives` is on backs only, and is printed, never parsed (no `<script>` in any template).
  - Every back shows every shown field (the existing test).
- Audio placement (FR-21):
  - Understand may play it on the front.
  - Produce and Write fronts carry no `Audio`. Their backs carry it once.
  - An empty `Audio` renders no player.
  - No IPA anywhere.
- Write keeps `{{type:Target}}` on front and back. The comparison is advisory; Anki's own Rating buttons stay.
- CSS uses the Studio tokens from DESIGN.md: `ground` `#FFF8F1`, `surface` `#FFFFFF`, `ink` `#221E2E`, `ink-muted` `#5C5669`, `accent` `#5A45C8`, `accent-soft` `#ECE8FB`, `surface-sunken` `#F0EAE2`, `border` `#E2DACF`.
  - The font is Figtree with a system fallback; the font is not embedded.
  - A `.nightMode` override keeps text readable, since Anki's night mode may override the colors (spec Assumptions).
  - Existing class names (`.prompt`, `.hint`, `.meta`, `.note`, `.example`) keep working, so Capture and Pronounce still render.
- The runbook follows `captures-acceptance-3-4.md`: a header block, `WHEEL`/`ac()` helpers, lettered Do/Expect tables, CI evidence, Results, Findings.
  - It uses the released wheel with entries 1–4 (`v0.6.0`, cut by the user), release mode, and `ANKI_PREFIX=LanguageLabDev`, reached over Tailscale Serve.
  - Every verify clause is a step: DW1–DW5, the templates Repair, a test clip stored in Anki (`LanguageLabDev_`-named) shown in Desktop and AnkiMobile, R-03 on the dirty Draft editor (iPhone and iPad), a `notesInfo` of a Hint edited with blank lines, the `/api/setup/plan` timing with real cards, and real `changeDeck`/`updateNoteFields`/`cardsInfo` replies.
- No step is marked pass without the user's reported result.
  Decision (2026-10-23, human): the user reported the whole run as passing ("everything looks ok") with no pastes and closed the story; the `decode_field`, `read_leftovers` and reply-fixture checks move to `deferred-work.md`. Each finding names a commit in this story or a `deferred-work.md` entry.
- The repo is public: no tailnet name, login, account, address, or non-`LanguageLabDev` resource is committed.

**Never:**
- No change to the Pronounce or Capture markup, field lists, note-type names, ords, or the setup diff/apply code.
- No new dependency, route or console script, and no JavaScript in templates.
- No write to a ticket file. Nothing is written under the `LanguageLab` Prefix. No `LANGUAGE_LAB_DEV` on the Mac Mini, and no clone or repo script there: only `uvx`, `curl` and `say`.

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/templates/{vocabulary,sentence}-{understand,produce,write}-{front,back}.html` -- the 12 files to rewrite.
  - Vocabulary shown fields: Target, Russian, RussianAlternatives, Hint, PartOfSpeech, Grammar, Example, ExampleRussian, Mnemonic, Audio. Sentence: Target, Russian, RussianAlternatives, Hint, Note, Audio.
  - Leave `*-pronounce-*` and `capture-*` alone.
- `src/language_lab/adapters/anki/templates/cards.css` -- shared by all five note types (`manifest.py:174`).
- `adapters/anki/setup_diff.py:77` `_templates_differ` compares the text exactly, so any file change yields a REPAIR TEMPLATES row per note type, and `setup_apply.py:97` applies it. No code change is needed.
- `tests/unit/test_anki_manifest.py:228` `test_card_templates_and_css_come_from_template_files_and_render_only_shown_fields` and `_field_refs` -- they already cover unknown, hidden and all-shown-on-back fields. Extend them; don't loosen any assertion.
- `tests/unit/test_setup_plan.py` -- check that a stale-template model still yields REPAIR (likely already covered).
- `tests/support/anki_state.py:24-27`, `tests/integration/test_anki_item_save.py:22-25` -- "hand-built … story 4.4's acceptance run checks them". Replace this note once the replies are recorded.
- `tests/support/anki_connect.py` `anki_fixture(name)` -- `{"request","response"}` fixtures in `tests/fixtures/anki/`. `tests/fixtures/README.md` gets an "Epic 4 acceptance" section.
- Copy for runbook steps:
  - `static/screens/captures.js` and `make-item.js`: Make an Item pane, "Generate Draft", "Write it myself", "Save to Anki", the duplicate sheet buttons.
  - `static/screens/item-detail.js`.
  - `router.js` `describeLoss` for Draft, and `index.html` `#unsaved-alert`.
- API for curl steps: `POST /api/drafts/generate`, `POST /api/items/{lang}` (Save, a retry with the same `itemId` updates), `GET /api/items/{lang}/duplicates`, `GET /api/setup/plan`. Non-GET needs `-H 'Origin: http://127.0.0.1:8787'`.
- `_bmad-output/initiative-languagelab-v1/deferred-work.md` lines 8, 17, 21, 27 -- the R-03, decode_field and read_leftovers entries. Record their outcome in the acceptance file.
- This machine has no Anki or iOS device; every device step is the user's.

## Tasks & Acceptance

**Execution:**
- [x] The 12 Study template files -- rewrite them per Design Notes -- FR-21, AD-10
- [x] `templates/cards.css` -- Studio styles, the `.nightMode` override, and the old classes kept -- spec FR-21
- [x] `tests/unit/test_anki_manifest.py` -- add a test pinning AD-10/FR-21: the Produce/Write fronts read `Russian` and never `RussianAlternatives`/`Audio`; the Understand front reads `Audio`; each Study back renders `Audio` once (FrontSide counted); no template contains `<script` or `ipa` (case-insensitive); `cards.css` holds the Studio hexes and `.nightMode` -- the ticket's pytest verify
- [x] `_bmad-output/test-artifacts/acceptance/capture-to-item-acceptance-4-4.md` -- the runbook:
  - A: release `v0.6.0` and helpers.
  - B: start, health, Setup lists templates Repair for the five note types; apply.
  - C: one Capture → an English Vocabulary (Generate Draft: Example removable, no Mnemonic) and a French Sentence; four cards each in the right decks; independent schedules (answer one in Desktop, the others unchanged); Generation context absent from `notesInfo` (DW1, DW2, DW5).
  - D: the duplicate sheet, Open existing → Item detail, Cancel, other Language not shown (DW3).
  - E: a retried Save via curl with the same `itemId` → no new note (DW5).
  - F: a test clip `say` → `storeMediaFile` + `updateNoteFields` Audio on the Vocabulary note; check every Card face in Desktop and AnkiMobile after Sync; the Sentence has no player (DW4).
  - G: R-03 on the Draft editor.
  - H: Hint with blank lines → `notesInfo` paste.
  - I: `time curl /api/setup/plan`.
  - J: record `changeDeck`/`updateNoteFields`/`cardsInfo`.
  - Then CI evidence, Results, Findings.
- [x] HITL: the user merges, cuts `v0.6.0`, runs the runbook, and reports each result with pastes (reported as a group, no pastes)
- [ ] (deferred: no replies pasted) `tests/fixtures/anki/{changeDeck,updateNoteFields,cardsInfo}.json`, `tests/fixtures/README.md`, `tests/integration/test_anki_item_save.py`, `tests/support/anki_state.py` -- write the recorded exchanges, test that the simulator answers the same shape, and replace the hand-built notes -- verify "fixtures against real replies"
- [x] Findings -- fix each, or append it to `deferred-work.md`. Fill in Results and the deferred outcomes.

**Acceptance Criteria:**
- Given the new templates, when `pytest tests/unit/test_anki_manifest.py` runs, then it passes and fails if a Produce/Write front reads `RussianAlternatives` or `Audio`.
- Given a collection set up from v0.5.0 templates, when the Setup plan is computed, then each of the five note types has a templates Repair row (an existing or new `test_setup_plan.py` case).
- Given the filled-in runbook, when checked against the ticket's verify, then DW1–5, R-03 and the `read_leftovers` timing each have a recorded result and cite the CI tests behind them.
- Given the repo after the story, when `make lint` and `make test` run, then both pass and no committed file holds a private name.

## Implementation Notes

- Templates: every Study face is an `.ll-card` with an overline; Audio is wrapped in `{{#Audio}}…{{/Audio}}` so an empty field renders no player. ExampleRussian without Example still shows through a `{{^Example}}{{#ExampleRussian}}` branch. Write back repeats Russian + Hint instead of `{{FrontSide}}`.
- The v0.5.0 Repair AC is a new `v0.5.0-templates` case in `tests/integration/test_anki_setup_preview.py` (the real diff lives there, not in `tests/unit/test_setup_plan.py`): the old CSS on all five note types plus the old Understand fronts yield exactly five REPAIR TEMPLATES rows.
- Runbook written with every Result `not run`; the fixtures, `anki_state.py`/`test_anki_item_save.py` notes, Findings and deferred outcomes wait for the user's run (HITL).

## Plan Change Log

## Review Triage Log

**Pass 1 (quick, 2026-10-23):** high 0, medium 2, low 5, false 1, maybe-false 0.

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1 | Runbook F3 can't show Example, Example in Russian or Mnemonic: Clear (C3) empties both Example fields and no Mnemonic is generated | medium | patch | Confirmed: `make-item.js` Clear loops over `example` and `exampleRussian`. Fixed: F2 also writes Example, ExampleRussian and Mnemonic, F3 checks the panel and the ExampleRussian-only branch, and C3's Expect names both fields. |
| 2 | Runbook F4 can't show the Sentence Hint, Alternatives or Note: C6 fills only Russian meaning | medium | patch | Confirmed in C6. Fixed: C6 fills Alternatives, Hint and Note, and F4 expects them. |
| 3 | G6 compares the English Sentence query with no baseline | low | patch | Confirmed: B3 queried only `$VQ`/`$SQ`. Fixed: B3 records the English Sentence ids. |
| 4 | DW2's retry and model-order clauses have no runbook step | low | patch | Confirmed. Fixed: Results says these clauses are proved in CI only and cites the tests. |
| 5 | The `v0.5.0-templates` case uses invented strings, not v0.5.0's | low | patch | Confirmed against `git show v0.5.0:…/cards.css`. Fixed: the case uses the exact v0.5.0 text. |
| 6 | An empty chips div adds an 8px gap on Vocabulary backs | low | patch | Confirmed: `<div class="chips">` sits outside any section. Fixed: `.chips:empty { display: none; }`. |
| 7 | The Produce/Write backs don't show Russian in `.russian` 20px 700 | false | reject | On these cards Russian is the prompt, shown in `.prompt` above the answer rule. The answer is the Target in `.target` inside its own card below `<hr id="answer">`, so the prompt and the answer don't look alike. |
| 8 | The type box border is 1px, but DESIGN.md's `border-input` is a 2px outline | low | patch | Confirmed at `DESIGN.md:475`. Fixed: 2px. |

Verification after the patches: `make test` 959 passed; `make lint` clean.

## Design Notes

**Layout.** Every face is a centered column on `ground`, holding one white `.ll-card` (24px radius, 1px `border`):
- Front: an overline (`Understand` / `Produce` / `Write`, 12px 700 `ink-muted`), then the prompt (`.prompt`, 30px 600 `ink`), then Hint (`.hint`, muted).
- Back, after `<hr id="answer">`:
  - Target, then Audio.
  - `Russian` in 20px 700.
  - Alternatives in muted 15px.
  - PartOfSpeech/Grammar as `accent-soft` chips.
  - Example over ExampleRussian in a `surface-sunken` panel.
  - Mnemonic or Note under a small label.

**Write back without `{{FrontSide}}`.** It repeats Russian + Hint, then `{{type:Target}}`. This avoids relying on how Anki renders a type box inside FrontSide. The existing test already accepts explicit fields.

```html
<!-- vocabulary-produce-front.html -->
<div class="ll-card">
  <div class="overline">Produce</div>
  <div class="prompt">{{Russian}}</div>
  {{#Hint}}<div class="hint">{{Hint}}</div>{{/Hint}}
</div>
```

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test` -- expected: all pass, including the new template test

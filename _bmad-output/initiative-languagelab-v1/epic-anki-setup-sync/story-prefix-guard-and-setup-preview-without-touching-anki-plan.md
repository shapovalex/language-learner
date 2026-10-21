---
title: 'Prefix guard and Setup preview without touching Anki'
type: 'feature'
ticket: '6'
created: '2026-10-21'
status: 'built'
baseline_revision: '886e92aa0a637a2b77673f950b7d3fded8e8bc48'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-6.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing stops the Anki adapter writing outside the Prefix (AD-4, NFR-1), and Setup can't show what it would change (FR-6, AD-3); the 13 red-phase ATDD leaves for story 2.6 are skipped.

**Approach:** Add `domain/setup.py` (plan types, `plan_hash`), `adapters/anki/query.py`, `adapters/anki/guard.py` wired into `AnkiConnectClient.invoke`, `AnkiStore.setup_preview()` (read + diff under one lock hold), `GET /api/setup/plan`, and the Setup screen's change list. The ATDD checklist's "Defaults taken without a question" and "Implementation contract" are the spec for names, item rules and the API body.

## Boundaries & Constraints

**Always:**
- The guard fails closed: an action not in its read allowlist or its known-write table raises `PrefixViolation` before any request; `multi` is checked per inner action. Without a guard the client sends reads only.
- "Under the Prefix" = deck `== P` or `startswith(P + "::")`; note type `startswith(P + " ")`. Write targets must be exact manifest names, never prefix matches.
- Id-targeted writes send only their lookups (`notesInfo`/`cardsInfo`/`getDeckConfig`) unless every target is managed; name-targeted writes send no lookup.
- `PrefixViolation` carries no target name (AD-15) and surfaces as the existing 500 `internal_error`.
- The preview sends reads only, under one `AnkiLock.hold()`; Repair never covers deck options other than the three bury flags and preset assignment (FR-8).
- `plan_hash` depends on the items as a set; unmanaged entries are outside it.
- Screen copy exactly as the E2E constants (EXPERIENCE.md, S-Setup mockup); rows read-only.

**Never:**
- No Apply button, apply endpoint, writes, migrations or opt-in repairs (entries 7, 9, 11).
- No non-managed notes in `unmanaged` (OQ-6, entry 11). No guard on v1 Sync.
- Do not weaken any ATDD first assertion; do not edit `tests/support/anki_state.py` reply shapes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty Prefix | stock Anki | 39 Create items (28 deck, 5 noteType, 5 templates, 1 preset) | None |
| Set-up Prefix | `managed_collection` (± user deck options, ± a set-up `LanguageLabDev`) | no items | None |
| Template/CSS drift | changed, missing or extra card template, or CSS | one `repair templates <type>` | None |
| Field drift | field added, removed or reordered | one `migrate noteType <type>` | None |
| Preset drift | bury flag on, or an existing preset deck not on `<P>` | one `repair preset <P>` | None |
| No `<P>` preset on any existing preset deck | — | `create preset <P>` | None |
| Unknown deck / note type under P | `P::Old stuff`, `P Spanish Vocabulary` | `unmanaged` entries; `PArchive` ignored | None |
| Out-of-Prefix write | `createDeck LanguageLabDev::Study` from `LanguageLab` | `PrefixViolation`, nothing sent | raised |
| Anki down / busy during preview | — | `GET /api/setup/plan` 503 envelope; screen shows inline alert in place of the list | AppError handler |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/client.py` -- `AnkiConnectClient.__init__` gains `guard: PrefixGuard | None = None`; `invoke` awaits the guard check (lookups via a private unguarded `_invoke_raw`) before `_post`. `invoke_v1` unchanged.
- `src/language_lab/adapters/anki/store.py` -- `__init__(..., *, manifest: Manifest | None = None, ...)` keeps existing callers working; add `setup_preview()`. Reuse `self._lock.hold()` like `reachable`.
- `src/language_lab/adapters/anki/manifest.py` -- `Manifest` (`decks`, `note_types[].fields/templates/css`, `preset.decks`, `preset.bury_flags` dotted paths). Read only; don't change.
- `src/language_lab/ports/anki_store.py`, `tests/fakes/anki_store.py` -- add `setup_preview() -> SetupPreview`; fake takes `preview: SetupPreview | None = None`, raises `anki_busy` when `busy`, `anki_unavailable` when not `available`.
- `src/language_lab/features/setup/{service,routes}.py` -- `SetupService.plan()` returns the camelCase body; `GET /plan` in `setup_router`. Follow the `Readiness` TypedDict style.
- `src/language_lab/app.py:270-273,312` -- build `manifest = build_manifest(settings.anki_prefix)` once; client `guard=PrefixGuard(manifest)`, store `manifest=manifest`.
- `src/language_lab/static/api.js` -- `getPlan()`. `static/screens/setup.js` -- plan section after the readiness card, then footer, then the version line. `static/css/studio.css` -- `change-row`, `chip-accent`, `info-callout` per DESIGN.md (tokens already in `tokens.css`).
- Constraint from `tests/e2e/test_navigation.py` `LATE_HEALTH`: `getHealth()` must stay the last fetch started by `mount`, and nothing rendered before the version line may be a `<p>` until data arrives.
- The live server and base-url E2E use `FakeAnkiStore()` → empty preview → callout; existing readiness E2E alert counts stay valid.
- Tests to un-skip and hoist imports: `tests/integration/test_anki_prefix_guard.py`, `tests/integration/test_anki_setup_preview.py`, `tests/unit/test_anki_query.py`, `tests/unit/test_setup_plan.py`, `tests/unit/test_anki_store_port.py` (drop the 2.1 exact-set assertion `{"reachable","sync"}`), `tests/api/test_setup_plan.py`, `tests/e2e/test_setup_preview.py`.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/domain/setup.py` -- `PlanAction`, `ResourceKind`, frozen `PlanItem`, `Unmanaged`, `SetupPreview(items=(), unmanaged=())`, `plan_hash` (sha256 of the sorted `[action, kind, name]` list as JSON) -- AC-7.
- [x] `src/language_lab/adapters/anki/query.py` -- `deck_query`, `note_query`: exact membership in the manifest, else `ValueError` -- AC-3.
- [x] `src/language_lab/adapters/anki/guard.py` + `client.py` -- `PrefixViolation`, `READS`, `PrefixGuard.check(action, params, lookup)` per the checklist's name- and id-targeted tables (plus `modelTemplate*`/`modelField*` writes by `modelName`, `unsuspend` like `suspend`); AD-7 regex `^<P>_<uuid4>_[0-9a-f]{12}\.mp3$` -- AC-1, AC-2.
- [x] `src/language_lab/adapters/anki/setup_diff.py` -- pure `diff(manifest, state) -> SetupPreview` over an `AnkiState` (deck names, model names, per-model fields/templates/css, per-existing-preset-deck config); items ordered deck, noteType, templates, preset -- AC-6, AC-8.
- [x] `store.py`, `ports/anki_store.py`, `tests/fakes/anki_store.py` -- `setup_preview()` reading via `multi` (`deckNames`, `modelNames`; then `modelFieldNames`/`modelTemplates`/`modelStyling` per existing managed type; `getDeckConfig` per existing preset deck), children sent with `version: 6` -- AC-4, AC-5.
- [x] `features/setup/*`, `app.py` -- route and wiring -- AC-9.
- [x] `static/api.js`, `static/screens/setup.js`, `static/css/studio.css` -- grouped rows (kind then action order, chip "Create 28", names as muted detail), "Nothing to change" callout, "Not managed by LanguageLab" list, two-line footer with the plan's Prefix, inline alert on plan error -- AC-10…AC-13.
- [x] The seven ATDD files -- remove `RED_PHASE`/`SETUP_RED_PHASE`, hoist imports; add backlog P1 cases: mixed plan renders kind-then-action order (E2E), `setup_preview` `anki_busy` → 503 (API), composed app's client rejects an out-of-Prefix write (integration).

**Acceptance Criteria:**
- Given the 27 ATDD cases un-skipped, when `make test` runs, then all pass with no story 2.6 `RED_PHASE` left and nothing else regresses.
- Given `create_app(settings)` with the real adapter, when its client is asked for `createDeck` outside the Prefix, then `PrefixViolation` is raised and no request leaves.
- Given `make lint`, then ruff check and format are clean.

## Implementation Notes

- Unguarded client: `guard.check_read_only` (reads in `READS`, and `multi` of reads) runs when no guard is given; the guard's lookups go through the private `_invoke_raw`.
- `changeDeck` checks its target deck before the `cardsInfo` lookup, so a bad deck sends nothing. Id lists must be non-empty lists of ints.
- Any `modelField*`/`modelTemplate*` action not in `READS` is treated as a write by `modelName` (so e.g. `modelFieldsOnTemplates` is allowed only for manifest note types).
- `setup_preview()` sends two `multi` reads: `deckNames`+`modelNames`, then per existing managed type `modelFieldNames`/`modelTemplates`/`modelStyling` and `getDeckConfig` per existing preset deck. Malformed replies are `anki_unavailable`. Without `manifest=` it raises `RuntimeError`.
- Story 2.1 port test keeps a subset check (`{"reachable","sync"} <= port`); the AC-4 leaf holds the exact set.
- Backlog added: composed-app guard probe (integration, also proves an allowed write passes, so read-only default can't fake it), plan 503 busy/unavailable (API), mixed-plan ordering and plan-error inline alert (E2E).
- Footer renders with the plan (it needs the plan's Prefix); on plan error only the alert shows.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 1, medium 2, low 2, false 0, maybe-false 0. All five patched by the implementer; `make test` 472 passed, `make lint` clean.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `deleteDecks` of a managed parent (`["LanguageLab"]`) passes, and Anki deletes unmanaged subdecks with it | high | patch | `manifest.decks` includes the root and parents; Anki deletes subdecks. Removed `deleteDecks` from the name-targeted writes (fails closed); REJECTED case added. |
| `addNote`/`updateNoteFields` `audio`/`video`/`picture` filenames skip the AD-7 check | medium | patch | AnkiConnect stores those files as media; the guard read only model/deck/id. `_require_note_media` checks each `filename` before any lookup; REJECTED case added. |
| Two existing preset decks on two different `<Prefix>`-named configs preview nothing | medium | patch | `_preset_item` compared names only. Repair when the `<Prefix>` configs don't share one `id`; `two-prefix-presets` case added. |
| An unhashable `multi` inner action raises `TypeError`, not `PrefixViolation` | low | patch | `action in READS` ran before the `str` check. Moved the check first in `check` and `check_read_only`. |
| Non-string template `Front`/`Back` becomes a Repair instead of `anki_unavailable` | low | patch | `_model_state` checked fields and css only. Both sides now required to be `str`. |

## Design Notes

- Preset rule: collect `getDeckConfig` of each preset deck that exists. None named `<P>` → Create preset. Otherwise Repair if any such deck's config isn't named `<P>`, or a `<P>` config's bury flag (dotted path from `BURY_FLAGS`, missing counts as differing) differs. Missing decks never imply a preset item.
- Templates: compare `{card name: (Front, Back)}` from `modelTemplates` with the manifest's, plus `modelStyling().css`, exact text.
- `saveDeckConfig` lookup: `getDeckConfig(deck=manifest.preset.decks[0])`; allow only if it is a dict named `<P>`, its `id` equals the config's `id`, and the config's `name` is `<P>`.

## Verification

**Commands:**
- `make test` -- expected: all pass, 0 skipped among the 2.6 files
- `make lint` -- expected: clean
- `grep -rn "RED_PHASE" tests/integration/test_anki_prefix_guard.py tests/integration/test_anki_setup_preview.py tests/unit/test_anki_query.py tests/unit/test_setup_plan.py tests/unit/test_anki_store_port.py tests/api/test_setup_plan.py tests/e2e/test_setup_preview.py` -- expected: no output

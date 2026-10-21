---
title: 'Opt-in repairs for leftovers'
type: 'feature'
ticket: '11'
created: '2026-10-21'
status: 'built'
baseline_revision: 'f7486eab366f29f9ee3d7c3c8bc7ecf11b9a16a5'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-11.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Setup can't see or fix leftovers under the Prefix: orphan media, managed cards in the wrong deck for their ord, and unsuspended Capture cards (CAP-2, epic decision 2026-10-14); the 13 red-phase ATDD leaves (15 cases) for story 2.11 are skipped.

**Approach:** The preview's reads also read the manifest note types' cards and the Prefix's media, and `diff` offers each leftover as an opt-in Repair row (`SetupPreview.repairs`), one per resource, unchecked. Only rows the user checks (by key) enter the plan and its hash; the server re-plans on each toggle (`GET /api/setup/plan?repair=<key>`), and apply takes `{planHash, repairs}`, re-hashes and runs one guarded write per checked row. The ATDD checklist's "Decisions" and "Defaults taken without a question" are the spec for names, wire keys and copy.

## Boundaries & Constraints

**Always:**
- `items`, the SetupState and the gate depend on required items only: leftovers never gate feature writes (AD-19).
- `PlanItem.key` is a property `f"{kind}:{name}"`; `detail` is excluded from equality and the hash.
- Hash on apply: `plan_hash((*items, *checked))`, `checked` = fresh `repairs` whose key is in the requested set (a repeated key counts once; a key no longer offered drops out, so the hash differs → `plan_changed` before any write).
- Repairs run last (after Create/Repair/Migrate), under the same lock hold, each one write through `invoke_setup`; an `AppError` doesn't end the run; a `PrefixViolation` propagates.
- Only manifest note types' cards are read (exact `note_query`); media only by `getMediaFilesNames` pattern `<Prefix>_*` plus full AD-7 match (the guard's regex, shared, not copied).
- A card whose ord the manifest note type doesn't declare is not offered (template removal isn't this story).

**Never:** no write in preview or plan reads; no repair row for non-manifest note types or unmanaged decks; no new guard write kinds; no change to `items` order, `requiresFullSync` or `fullSyncRequired`; no weakening of any ATDD first assertion.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Leftovers only | set-up Anki, one of each kind | 3 unchecked `repairs`, `items` empty, `ready` | None |
| Orphan media | AD-7 name, no `[sound:name]` in any decoded Audio | `orphanMedia:<name>` row | None |
| Referenced / other Prefix / wrong case | in Audio (editor markup too), `LanguageLabDev_…`, case-changed | no row | None |
| Misplaced card | deck ≠ `card_deck(type, ord)`, `Default` included | `misplacedCard:<id>`, detail `noteType, card, deck, expectedDeck` | None |
| Unsuspended Capture card | `queue` ≠ -1 | `unsuspendedCard:<id>`, detail `noteType, card, deck` | None |
| Apply, nothing checked | unchecked hash, `repairs=[]` | no write | None |
| Apply one checked | checked hash + its key | exactly `deleteMediaFile` / `changeDeck` / `suspend` | failed write → discrepancy |
| Checked under unchecked hash | | nothing written | `409 plan_changed` |

</frozen-after-approval>

## Code Map

- `domain/setup.py` -- `ResourceKind.ORPHAN_MEDIA/MISPLACED_CARD/UNSUSPENDED_CARD`; `PlanItem.detail: Mapping[str, str] = field(default_factory=dict, compare=False, hash=False)`, `key` property; `SetupPreview.repairs: tuple[PlanItem, ...] = ()`. `plan_hash` unchanged.
- `adapters/anki/guard.py` -- extract the AD-7 regex into a module function (e.g. `media_pattern(prefix)`) reused by `PrefixGuard` and the diff.
- `adapters/anki/setup_diff.py` -- `AnkiState` gains `cards: tuple[CardState, ...]` (id, model, ord, deck, suspended), `media: frozenset[str]`, `audio: frozenset[str]` (names referenced by managed notes' decoded `Audio`, `\[sound:([^\]]+)\]`). `diff` builds `repairs` in order orphanMedia (sorted by name), misplacedCard, unsuspendedCard (by card id). Card name for `detail["card"]` from the manifest template whose `ord` matches. Capture type = manifest note type with `language is None`. Update the module docstring.
- `adapters/anki/setup_gate.py` -- `read_note_versions` also collects the referenced audio names from the same `notesInfo` (return both, or a small result type); `read_preview` adds one `multi` of `findCards` per present manifest type plus `getMediaFilesNames`, then one `cardsInfo` when cards exist (skip `{}`), validating shapes (`AppError(ANKI_UNAVAILABLE)` otherwise). `compute_state` untouched.
- `adapters/anki/setup_apply.py` -- `run_repairs(invoke, items)`: per row `deleteMediaFile(filename=)`, `changeDeck(cards=[id], deck=expectedDeck)`, `suspend(cards=[id])`; failures swallowed like `_write`. Docstring: drop "entry 11" note's future tense where relevant.
- `adapters/anki/store.py`, `ports/anki_store.py`, `tests/fakes/anki_store.py` -- `setup_apply(plan_hash, repairs: Collection[str] = ())` per the Always rules; return the full fresh preview (its `repairs` are all still-offered rows). Fake hashes `items` + offered rows in `repairs`.
- `features/setup/service.py`, `routes.py` -- `RepairRow` TypedDict-ish (`key, action, kind, name, checked` + detail keys); `Plan.repairs`; `plan(repairs=())` with `planHash` over items + checked; `apply(plan_hash, repairs=())` → `_apply` uses the same hash in its `applicable` check and passes `repairs` to the store; `_result` discrepancies = `items` + verified repairs whose key was checked (`requiresFullSync` false), `verified` = none. Routes: `repair: list[str] = Query([])` on GET plan; `ApplyRequest.repairs: list[str] = []`.
- `static/api.js` -- `getPlan(repairs = [])` (repeated `repair` params), `applySetup(planHash, repairs = [])` sends `{planHash, repairs}`.
- `static/screens/setup.js`, `static/css/studio.css` -- "Optional repairs" card after the change list/callout and before Not managed: heading id + `aria-labelledby` list, hint "Nothing here changes unless you check it.", one `<li>` per row with a `<label>` checkbox and the checklist copy. Checked keys kept in state; a toggle re-reads the plan with them (drop a stale answer by sequence number), keeping checks still offered. Apply shows when `items.length > 0` or any key checked; posts the re-read `planHash` + keys. `plan_changed` re-read keeps still-offered checks. `DISCREPANCY_KINDS`/`EXPECTED_FOUND` gain the three repair kinds (default copy).

## Tasks & Acceptance

**Execution:**
- [x] Domain, guard regex, diff, gate reads, `run_repairs`, store, port, fake -- AC-1..3, 6, 8..11, 13.
- [x] Integration tests whose replays assert exact read sequences or lack `findCards`/`cardsInfo`/`getMediaFilesNames` (`test_anki_setup_preview.py`, `test_anki_setup_state.py`, `test_anki_setup_apply.py`, …) -- update for the new reads without weakening their assertions.
- [x] Service, routes, `app.py` if needed -- AC-4, 7, 13; add `"repairs": []` to whole-body tests in `tests/api/test_setup_plan.py` (and any other).
- [x] `api.js`, `setup.js`, `studio.css` -- AC-5, 12.
- [x] Three ATDD files -- remove `RED_PHASE`, hoist in-body names; add the checklist's "Secondary branches" as P1 tests (unit: `key`/`detail` don't change `plan_hash`; integration: two `[sound:]` tags, case-changed name, misplaced Capture card, card in a vanished deck, misplaced+unsuspended gives two rows, failing `suspend` → discrepancy, orphan vanished before apply → `plan_changed`; API: no leftovers → `repairs: []`, repeated key once; E2E: uncheck re-reads without the key, Apply hidden with nothing checked and no items).

**Acceptance Criteria:**
- Given the 15 story 2.11 cases un-skipped, when `make test` runs, then all pass, no 2.11 `RED_PHASE` remains, and nothing regresses.
- Given `make lint`, then ruff check and format are clean.

## Implementation Notes

- `read_note_versions` returns `NoteReads(versions, audio)`; the new `read_leftovers` sends the `findCards` + `getMediaFilesNames` multi and one `cardsInfo` (skipped when there are no cards; `{}` entries dropped). No existing replay asserted an exact read sequence that broke, so no integration test needed rewriting.
- Wire-shape tests that compared whole bodies gained `"repairs": []` (`tests/api/test_setup_plan.py`, the two apply POST bodies in `tests/e2e/test_setup_apply.py`); `test_setup_plan.py` (unit) lists the three new `ResourceKind`s; the port test pins `setup_apply(plan_hash, repairs: Collection[str] = ())`.
- Screen: Apply is disabled while a toggle's re-plan is in flight, so it always posts the hash read with the current checks; checks reset after a finished run. "Run Setup again" after discrepancies re-applies the items only (the result's `planHash` is items-only), so a failed repair needs re-checking.
- The "Optional repairs" card is hidden under `newer_schema` (apply refuses it anyway).

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 5, false 0, maybe-false 0. Four patched by the implementer, one deferred, two rejected.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| "Run Setup again" after a failed checked repair reports verified though nothing was retried | medium | patch | `_result.planHash` covers `items` only and the screen posts `repairs: []`, so a run whose only discrepancy is a failed `suspend` retries nothing and `_checked(verification, [])` is empty → `verified: true`. Fix: hash covers items + still-checked rows; retry posts the repair discrepancies' keys. |
| The gate's on-demand state compute runs the leftover reads, so they can refuse or slow feature writes | medium | patch | `SetupGate.check` → `read_preview` → `read_leftovers` (a `cardsInfo` of every managed card, the cardsInfo shape unverified on real Anki); none of it changes the state. Fix: `read_preview(leftovers=False)` from the gate only. |
| `read_leftovers` de-duplicates card ids in a list (quadratic) under the lock | low | patch | Direct correction: a card has one note type, so the `findCards` results can't overlap; concatenate. |
| `checked` comment says "in plan order" while `toggle` appends | low | patch | Comment corrected. |
| One `cardsInfo` of every managed card on each preview and each checkbox toggle grows with the collection | low | defer | The server re-plan per toggle is the user's decision (2026-10-21); bounding it needs a design (cache, or narrower reads). Logged in deferred-work.md. |
| A toggle's failed re-plan replaces the plan with an error and nothing recovers it | low | rejected | Same as the existing initial-plan error path; Anki down on a click is rare and a reload recovers; the fix adds a retry branch. |
| An AD-7 file referenced only by a non-managed note is offered as orphan media | low | rejected | Needs a user to paste a managed `[sound:]` tag into a non-managed note; the guard limits reads to manifest note types, so covering it needs unscoped note reads (AD-4). The row is opt-in and names the file. |

## Verification

**Commands:**
- `make test` -- expected: all pass
- `make lint` -- expected: clean
- `grep -rn "RED_PHASE" tests/integration/test_anki_setup_repairs.py tests/api/test_setup_repairs.py tests/e2e/test_setup_repairs.py` -- expected: no output

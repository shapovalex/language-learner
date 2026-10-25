---
title: 'Fix Reference audio Save failing because Anki lowercases media names'
type: 'bugfix'
ticket: ''
created: '2026-10-25'
status: 'built'
baseline_revision: 'da2526dc971a461a9fa4e7741e7ea729fc6c026b'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** On real Anki, every Save that carries Reference audio fails with "Not saved — Anki isn't reachable". AnkiConnect `storeMediaFile` lowercases the filename: on the Mac mini, a request for `LanguageLabDev_<id>_<hash>.mp3` answered `languagelabdev_<id>_<hash>.mp3`. `save_item` treats any answer other than the requested name as `ANKI_UNAVAILABLE`. Spike 2.2 already saw this, and also saw `getMediaFilesNames` match its pattern case-sensitively. The replay and the fake echo the name unchanged, so the tests missed it.

**Approach:** Make managed media names lowercase from the start, as spike 2.2 recommended: `<prefix lowercased>_<ItemId>_<sha256[:12]>.mp3`. Anki then stores the name unchanged. Every place that builds, matches or lists managed media then uses that one lowercase form. Amend AD-7 to match.

## Boundaries & Constraints

**Always:**
- One source for the lowercase form: `domain/audio.py::media_name` and `guard.py::media_pattern` both lowercase the Prefix. Every other site, including the `getMediaFilesNames` patterns, uses these two functions or the same lowercased Prefix.
- Save still checks the `storeMediaFile` answer. It accepts the answer only when it equals the requested (lowercase) name, so a real rename by Anki still fails safely.
- Media whose names carry the Prefix's original case is never managed. The guard keeps refusing to delete it (fail closed).
- Lowercase leftovers from failed v0.8.0 Saves already match the new pattern. Setup offers them as `orphanMedia`, and Item delete removes them.
- Replay test doubles answer `storeMediaFile` the way real Anki does: with the lowercased name.
- User decision (2026-10-25): acceptance is simple and UI only. Do it through LanguageLab and Anki Desktop / AnkiMobile screens, with no AnkiConnect or `/api` requests.

**Never:** Rename existing mixed-case media; no such file was ever saved successfully. No changes to the schema, templates, endpoints or UI copy. No case-insensitive matching (it would widen the guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Save replace | Draft or Item with an accepted clip, Prefix `LanguageLabDev` | Media `languagelabdev_<id>_<hash>.mp3` stored; Audio field `[sound:<that name>]`; Save 200 | — |
| Rename | `storeMediaFile` answers any other name | `anki_unavailable`; no note write | Leftover is a Setup repair |
| Read | Detail, then `/api/media/<name>` | Detail `audio` is the lowercase name; bytes served | Mixed-case name: 404 |
| Supersede/remove | Item with a lowercase clip | Old clip deleted after the note write | As before (AD-6) |
| Delete Item | Lowercase clips, including v0.8.0 leftovers | All `languagelabdev_<id>_*` removed | As before |
| Setup | Unreferenced lowercase clip | Offered as `orphanMedia`; Apply deletes it | Mixed-case: not offered |
| Isolation | Prefixes `LanguageLab` and `LanguageLabDev` | Neither lists, serves or deletes the other's media | Guard refuses |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/audio.py::media_name` (L73): lowercase the Prefix here.
- `src/language_lab/adapters/anki/guard.py::media_pattern` (L50): the AD-7 regex. Lowercase the Prefix. It is used by the guard (L114, `storeMediaFile`/`deleteMediaFile`/`retrieveMediaFile`), `setup_diff.py::_repairs` (L102), and `store.py::_audio_name` (L162), `get_media` (L410) and `delete_item` (L492).
- `src/language_lab/adapters/anki/store.py::save_item` (L363–371): keep the `result != name` check. Once the name is lowercase it passes on real Anki. `delete_item` stem (L488: `f"{manifest.prefix}_{item_id}_"`): lowercase it.
- `src/language_lab/adapters/anki/setup_gate.py::read_leftovers` (L217): the `getMediaFilesNames` pattern `f"{manifest.prefix}_*"`. Lowercase it (case-sensitive match, spike 2.2).
- `tests/support/audio.py::store_media` (~L85): answer with `name.lower()` and store under that name, like real Anki. `tests/support/anki_state.py::media_name` (L159), `tests/support/item_delete.py::media_names` (L39), `tests/fakes/anki_store.py` (L185): follow the new name.
- Name expectations: `tests/unit/test_audio_domain.py`, `tests/integration/{test_anki_setup_repairs,test_anki_item_delete,test_anki_prefix_guard}.py`, `tests/api/{test_reference_audio,test_items_delete}.py`.
- Evidence: `_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md` L82. `tests/fixtures/anki/storeMediaFile.json` is the recorded lowercasing reply. AD-7 is at `architecture-languagelab/architecture-languagelab.md` L121–126.

## Tasks & Acceptance

**Execution:**
- [x] `domain/audio.py`, `adapters/anki/guard.py`, `adapters/anki/store.py`, `adapters/anki/setup_gate.py`: produce, match and list the lowercase form, per the Code Map.
- [x] `tests/support/audio.py` and the helpers and fake named in the Code Map: replay answers the lowercased name. Add a replay test that loads `tests/fixtures/anki/storeMediaFile.json`'s lowercasing behaviour and proves a mixed-case Prefix Save succeeds. Observe it fail first, before the fix.
- [x] Tests for each Matrix row: rename → `anki_unavailable` with no note write; a mixed-case name gets a 404 and is not offered by Setup; lowercase v0.8.0 leftovers are offered by Setup and removed by Item delete; the two Prefixes stay isolated. Update the existing name expectations.
- [x] `architecture-languagelab.md` AD-7 Naming: `<prefix lowercased>_<ItemId>_<sha256[:12]>.mp3`, citing spike 2.2.

**Acceptance Criteria:**
- Given Prefix `LanguageLabDev` and a replay that lowercases like real Anki, when a Draft and then an existing Item save new audio, then both Saves succeed, and playback, replacement cleanup, removal and Item delete all work.
- Given the full suite, when it runs, then it passes with no skips.

## Review Triage Log

Pass 1 (quick, 2026-10-25): high 0, medium 0, low 3, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| AD-6 Delete Item row still uses the old case, `<Prefix>_<ItemId>_*` | low | patch | It contradicts the amended AD-7 and `store.py` L489. Lowercase the row. |
| Prefixes differing only by case now share media names | low | reject | Not reachable in practice: it needs two installs with case-only different Prefixes on one Anki profile. Anki deck names are already case-insensitive, so such Prefixes collide on decks before media. The fix would add Prefix-uniqueness enforcement. |
| Setup mixed-case test is dropped at listing, never reaching `_repairs`' fullmatch | low | patch | The replay's `fnmatchcase` filters the name out first. Make the listing return it regardless of the pattern, as the Item delete test does. |

After the patches, verification on my side: `make test` 1190 passed; `make test-webkit` 641 passed; `make lint` and `git diff --check` clean. Nothing deferred.

## Verification

**Commands:**
- `make test`, `make test-webkit`, `make lint`, `git diff --check`: expected clean.

**Manual checks (UI only, on the next patch release with `ANKI_PREFIX=LanguageLabDev`):**
- On the phone, make a Draft, Preview, Use preview, Save to Anki: the Saved banner appears. In Anki Desktop Browse the Audio field reads `[sound:languagelabdev_…mp3]` and the card plays it. Open the Item, Regenerate, Use preview, Save, then Remove audio, Save, then Delete. After each step, Tools → Check Media lists no unused `languagelabdev_` file.
- Open Setup: any lowercase leftovers from failed v0.8.0 Saves are offered as media repairs. Apply clears them from Check Media.

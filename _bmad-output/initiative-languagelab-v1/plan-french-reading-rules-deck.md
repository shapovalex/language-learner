---
title: 'French Reading Rules deck, created and filled by Setup'
type: 'feature'
ticket: ''
created: '2026-10-29'
status: 'built'
baseline_revision: 'da6b547a0571a861d3e5aa9ceea23007c8f12d1b'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/initiative-languagelab-v1/plan-french-reading-rules-deck-content.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The user wants an Anki deck for French reading rules: the front shows a letter combination, the back its phonetic transcription and several example words, each with audio they can play. They want Setup to create it; the app needs no screens to manage it.

**Approach:** Add a managed note type `<Prefix> French Reading Rule` (one card, "Read") and deck `<Prefix>::Study::French::Reading Rules` to the manifest, plus the 46 curated rules and their pre-generated fr-CA MP3s as package data. Setup's plan offers one Create row per rule whose note is missing. Apply stores each word's audio and adds the note, so the change list, verification and repairs all work for the new rows.

## Boundaries & Constraints

**Always:**
- Content comes from the context file, one rule per row, in that order, with exactly 3 examples each. Every rule carries a fixed lowercase UUIDv4 `id` (its `RuleId`), unique.
- Audio is bundled in the wheel, generated once at dev time with Azure `fr-CA-SylvieNeural` by a repo script. Setup never calls Azure. The host runs only the wheel (uvx), never repo scripts.
- Media names follow AD-7 unchanged: `media_name(prefix, rule.id, bytes)`. The Prefix guard and `media_pattern` stay as they are.
- Every Anki write goes through the existing guarded Setup `invoke`. A failed write doesn't end the run; verification reports it.
- Field values go through `encode_field`. Audio fields hold `[sound:<name>]` exactly as Save Item stores them.
- Reading-rule notes carry `SchemaVersion` = the manifest's. `SCHEMA_VERSION` stays 1: the change adds a note type, not fields.
- Missing reading-rule notes never make the SetupState `needs_setup`. Deleting a rule in Anki must not block feature writes.

**Never:**
- No reading-rule screens, routes or API in the app, and no editing, updating or deleting of existing rule notes (Create only).
- No change to `cards.css` or the existing templates: that would make every existing install repair its templates.
- No per-word IPA, no Russian, and no Pronounce card for reading rules.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh or upgraded install | Note type, deck and rule notes absent | Plan shows Create rows for the deck, the note type, its templates and 46 "French reading rules". Apply leaves 46 notes, each with one card in the Reading Rules deck and 3 stored MP3s. Verify says "Nothing to change". | None expected |
| Already set up | All 46 rule notes present (matched by decoded `RuleId`) | No reading-rule rows; state `ready` | None expected |
| User deleted one rule note | 45 present | One Create row offered; state stays `ready`; feature writes still pass the gate | None expected |
| Rule card moved by hand | Card outside the Reading Rules deck | Offered as a `misplacedCard` repair, as for Item cards | None expected |
| A rule note's media | Present and referenced in `ExampleNAudio` | Never offered as `orphanMedia` | None expected |
| `storeMediaFile` fails for one word | AnkiConnect error | That rule's `addNote` is skipped; the other rules go on; verify lists it as a discrepancy and the next plan offers it again | Run continues (`try_write`) |
| A rule note has another card ord's card | n/a, one template | Only ord 0 exists | n/a |

</intent-contract>

## Code Map

- `src/language_lab/adapters/anki/manifest.py` -- the one source of names. Add the note type (fields `Combination, Transcription, Note, Example1, Example1Audio, Example2, Example2Audio, Example3, Example3Audio, RuleId, SchemaVersion`; `RuleId` hidden), its template `Read` ord 0 from `templates/reading-rule-read-{front,back}.html`, the deck (29 decks, after `…::Study::French::Sentences::Write`, so it lands on the preset via `preset_decks`). `NoteType` gains `deck: str | None = None`; `card_deck` returns it first. Set `language=Language.FR, category=None` so `item_note_type` never returns it and the Capture checks (`language is None`) still mean Capture only. Expose the rules (`Manifest.reading_rules`) and the note type name. Update the module docstring counts.
- `src/language_lab/domain/reading_rules.py` (new) -- frozen `ReadingRule(id, key, combination, transcription, note, examples: tuple[Example(word, audio: bytes)…])` and a loader of package data `language_lab/data/french_reading_rules/rules.json` + `audio/<key>-<n>.mp3`, cached, validating 3 examples each, unique ids/keys/combinations, and `validate_mp3`.
- `src/language_lab/domain/setup.py` -- add `ResourceKind.READING_RULE = "readingRule"` (name = the rule's combination).
- `src/language_lab/adapters/anki/setup_gate.py` -- `read_note_versions` also returns the decoded `RuleId`s of reading-rule notes; `_sounds` reads `Audio` and `Example1..3Audio`; `compute_state` ignores `READING_RULE` items for `needs_setup`; `read_preview` passes the rule ids into `AnkiState`.
- `src/language_lab/adapters/anki/setup_diff.py` -- `AnkiState.reading_rules: frozenset[str]` (stored RuleIds); `diff` appends one `CREATE READING_RULE` item per missing rule, in data order, last in `items`. Update the docstring.
- `src/language_lab/adapters/anki/setup_apply.py` -- after the preset step, for each planned rule: `storeMediaFile` (base64) for each example, then `addNote` (`allowDuplicate: true`, deck from `card_deck(model, 0)`, fields encoded, `RuleId`, `SchemaVersion`). Skip the note if any store didn't answer its name. Update the docstring.
- `src/language_lab/static/screens/setup.js` -- `KINDS` gains `["readingRule", "French reading rules"]` after preset; `DISCREPANCY_KINDS.readingRule = "Reading rule"`; `EXPECTED_FOUND["create:readingRule"] = "Expected this reading rule's note; found none."`.
- `scripts/generate_reading_rules_audio.py` (new) -- dev tool: `LANGUAGE_LAB_DEV=1 uv run python scripts/generate_reading_rules_audio.py`; loads settings, synthesizes every example with `AzureSpeech.synthesize("fr-CA", "fr-CA-SylvieNeural", word)`, writes the MP3s and `audio/index.json` (`{file: word}`), removes stale files.
- `tests/support/anki_state.py` -- `apply_manifest` must also add every rule note (fields as Setup stores them), its card and its media, so `managed_collection` stays "nothing to change". Answer `storeMediaFile` with `writes=True` (adds to `media`, returns the filename).
- Reuse: `media_name` (`domain/audio.py`), `encode_field`/`decode_field` (`codec.py`), `try_write`, `note_query`, `_stored_value` (`setup_gate.py`). Look at `store.save_item` for the store/addNote shapes.
- Don't touch: `guard.py`, `cards.css`, existing templates, `SCHEMA_VERSION`, migrations.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/data/french_reading_rules/rules.json` -- the 46 rules from the context file, each with a new fixed UUIDv4 `id` -- the content.
- [x] `scripts/generate_reading_rules_audio.py` -- write it and run it once to generate `audio/*.mp3` and `index.json` (the dev `.env` holds Azure keys) -- bundled audio.
- [x] `src/language_lab/domain/reading_rules.py` -- loader and types -- one reader for the package data.
- [x] `src/language_lab/adapters/anki/templates/reading-rule-read-front.html`, `…-back.html` -- front: overline "Reading rule", `.prompt` `{{Combination}}`. Back: `{{FrontSide}}`, `<hr id="answer">`, `.russian.transcription` `{{Transcription}}`, `{{#Note}}.hint{{/Note}}`, a `.panel` with one `.example` row per `{{#ExampleN}}` holding the word and `{{ExampleNAudio}}`. Existing classes only.
- [x] `manifest.py`, `domain/setup.py`, `setup_gate.py`, `setup_diff.py`, `setup_apply.py` -- as in the Code Map.
- [x] `src/language_lab/static/screens/setup.js` -- copy for the new kind.
- [x] Tests: update the counts and expectations that change (`tests/unit/test_anki_manifest.py` 28→29 decks and the note-type list, setup preview/apply/state/repairs integration tests, `tests/e2e/test_setup_preview.py`, the wheel test that lists package data). Add unit tests for the loader (3 examples, unique ids/keys/combinations, every MP3 valid, `index.json` words match `rules.json`, no stray files) and diff/state tests for the matrix rows; an integration test that applies on a stock collection and verifies the 46 notes, cards and media; and a wheel test that the data ships.
- [x] `docs/anki.md`, `docs/setup.md` -- say Setup creates and fills `<Prefix>::Study::French::Reading Rules`, recreates any rule note you delete (suspend a card instead), and doesn't update existing ones. `docs/development.md` -- the regenerate command.

**Acceptance Criteria:**
- Given a stock Anki, when the user opens Setup, then "What will change in Anki" shows a "French reading rules · ou, ou + vowel, …" row with "Create 46", and the Decks row includes `<Prefix>::Study::French::Reading Rules`.
- Given that plan applied, when the user studies `<Prefix>::Study::French::Reading Rules` in Anki, then each card's front shows only the combination, and its back shows the transcription, any note, and three words, each with its own play button that plays that word.
- Given Setup applied, when Setup is opened again, then it shows "Nothing to change." and no orphan-media or misplaced-card repair for the rule notes.
- Given one rule note deleted in Anki, when the user saves an Item, then the save succeeds, and Setup offers "Create 1" for that rule.

## Implementation Notes

- `Manifest` gained `reading_rule_note_type` and `reading_rules`; the note type is last in `note_types`, so existing orders hold.
- Test support: `apply_manifest`/`managed_collection` seed the 46 rule notes by default; feature tests that compare a collection's exact notes, cards or media (captures/items delete, audio save/lifecycle, media case, item reads, reference audio) now use `reading_rules=False` (the "user deleted every rule" state, still `ready`). Coexistence is covered by `test_deleting_an_item_leaves_every_reading_rule_note_and_its_media`.
- Migration tests now expect a Migrate `notes` row for `<Prefix> French Reading Rule` at a future SchemaVersion: the seeded notes are at the manifest's version and migrate like any managed note.
- The wheel listing grep counts 142: the 140 files plus 2 directory entries.
- Bundled audio is 1.6 MB (138 MP3s at 48 kbit/s), not ~1 MB.
- Risk, not fixed (out of scope): Delete Item's absent-note media cleanup deletes `<prefix>_<ItemId>_*`; an ItemId equal to a rule id would remove that rule's media. The app never sends rule ids as ItemIds.

## Plan Change Log

## Review Triage Log

### 2026-10-29 — Review pass
- verdicts: 2 findings — high 0, medium 1, low 1, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` A deleted rule's 3 MP3s were offered as `orphanMedia`; Create re-stores them under the same deterministic names and `run_repairs` then deleted them, leaving the recreated note silent — fixed in `setup_diff.py`: `_repairs` skips media names that a rule Create row of the same diff stores; covered by `test_a_deleted_rules_media_is_never_offered_as_orphan_and_survives_every_repair`.
  - `[low]` `[patch]` With the rule note type's fields edited (e.g. `RuleId` removed), every apply added 46 more notes without a RuleId — fixed in `setup_diff.py`: no rule Create rows while that note type exists with fields other than the manifest's (its Migrate row still shows); covered by `test_a_rule_note_type_with_other_fields_gets_no_rule_row_and_apply_adds_no_rule_note`. Low: it needs a hand edit of a managed note type.

## Design Notes

Why bundled audio and not Setup-time synthesis: Setup stays Anki-only and fast (138 TTS calls would hold the Anki lock or need a new Speech dependency in Setup), works without Azure, and produces the same audio every time. Cost: about 1 MB of MP3 in the wheel.

Why `READING_RULE` rows don't gate writes: the gate protects the schema features write to. A missing seed note threatens nothing, and gating on it would lock the app whenever the user deletes a rule they don't want.

Store sketch (apply, per planned rule):

```python
names = []
for n, ex in enumerate(rule.examples, 1):
    name = media_name(prefix, rule.id, ex.audio)
    if await try_write(invoke, "storeMediaFile", filename=name, data=b64(ex.audio)) != name:
        break
    names.append(name)
else:
    await try_write(invoke, "addNote", note={...})
```

## Verification

**Commands:**
- `make lint` -- expected: clean
- `make test-fast` -- expected: all pass except the known `tests/unit/test_studio_assets.py::test_css_declares_every_design_md_token` (fails on the baseline: commit da6b547 deleted the DESIGN.md it reads)
- `uv run pytest -n auto --dist loadgroup -m e2e -k setup` -- expected: pass
- `uv build && unzip -l dist/language_lab-*.whl | grep french_reading_rules | wc -l` -- expected: 140 (rules.json, index.json, 138 MP3s)

## Auto Run Result

Status: built

**Summary:** Setup now creates `<Prefix> French Reading Rule` (one "Read" card) and `<Prefix>::Study::French::Reading Rules`, and seeds 46 French reading rules: front = letter combination; back = IPA transcription, an optional note, and three example words, each with its own bundled fr-CA (Azure `fr-CA-SylvieNeural`) audio play button. There are no app screens for it. Missing rule notes never block feature writes.

**Files changed:**
- `src/language_lab/data/french_reading_rules/` — `rules.json` (46 rules, fixed UUIDv4 ids), `audio/` (138 MP3s plus `index.json`).
- `src/language_lab/domain/reading_rules.py` — validated loader of the package data.
- `scripts/generate_reading_rules_audio.py` — dev-time audio generator (Azure).
- `src/language_lab/adapters/anki/manifest.py` — the note type, its deck, `NoteType.deck`, `Manifest.reading_rules`.
- `src/language_lab/adapters/anki/templates/reading-rule-read-{front,back}.html` — the card, using existing CSS classes only.
- `src/language_lab/domain/setup.py` — `ResourceKind.READING_RULE`.
- `src/language_lab/adapters/anki/setup_diff.py` — rule Create rows; no orphan rows for media a Create re-stores; no rule rows while the note type's fields differ.
- `src/language_lab/adapters/anki/setup_gate.py` — reads RuleIds and example audio fields; rule rows don't make the state `needs_setup`.
- `src/language_lab/adapters/anki/setup_apply.py` — stores audio, then adds each rule note.
- `src/language_lab/static/screens/setup.js` — row and discrepancy copy.
- `docs/anki.md`, `docs/setup.md`, `docs/development.md`, `docs/README.md` — the deck, its Setup behavior, the regenerate command.
- Tests: the new `tests/unit/test_reading_rules.py` and `tests/integration/test_anki_setup_reading_rules.py`, a wheel data test, and updated count and row expectations across the setup and feature tests and `tests/support/anki_state.py`.

**Review:** one quick pass. 2 patches applied (1 medium, 1 low), 0 deferred, 0 rejected.

**Follow-up review recommended:** false (one medium patched; no high).

**Verification:** `make lint` is clean. `make test-fast`: 1042 passed, 1 failed; the failure is the baseline one, `test_css_declares_every_design_md_token`, which reads the DESIGN.md that da6b547 deleted. `-m e2e -k setup`: 37 passed. The full e2e suite passed once before the review patches. The wheel ships all 140 data files (the grep counts 142 with directory entries).

**Residual risks:** Not yet checked in a real Anki: playback and layout of the cards were only verified in the in-memory collection. Delete Item's media cleanup for an absent note matches `<prefix>_<ItemId>_*`, so an ItemId equal to a rule id would delete that rule's audio; the app never sends one. The wheel is 1.6 MB larger.

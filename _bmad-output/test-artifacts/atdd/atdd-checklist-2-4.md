---
runScope: 'story'
runKey: 'story-2-4'
workflowStatus: 'completed'
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04-generate-tests', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-10-21'
storyId: '2.4'
storyKey: '2-4'
storyFile: ''
storySource: '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml (entry 4)'
atddChecklistPath: '_bmad-output/test-artifacts/atdd/atdd-checklist-2-4.md'
generatedTestFiles:
  - 'tests/unit/test_anki_manifest.py'
  - 'tests/unit/test_anki_codec.py'
  - 'tests/integration/test_anki_templates_wheel.py'
inputDocuments:
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/tickets.toml'
  - '_bmad-output/initiative-languagelab-v1/epic-anki-setup-sync/epic-anki-setup-sync.md'
  - '_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-1, AD-3, AD-4, AD-7, AD-9, AD-10, AD-19, Consistency Conventions)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md (FR-6, FR-8, FR-20, FR-21)'
  - '_bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md (A3)'
  - '_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md (Q5, reply shapes)'
  - '_bmad-output/test-artifacts/atdd/atdd-checklist-2-10.md (format and conventions)'
  - 'No test design for epic 2: test-design/test-design-epic-2.md, test-design-qa.md and test-design-architecture.md are absent, here and at the legacy root'
  - 'pyproject.toml'
  - 'src/language_lab/settings.py (PREFIX_PATTERN, RELEASE_PREFIX, DEV_PREFIX)'
  - 'src/language_lab/adapters/anki/{__init__,client,lock,store}.py'
  - 'tests/README.md, tests/conftest.py'
  - 'tests/fixtures/anki/getDeckConfig.json, createModel.json, modelTemplates.json'
  - 'tests/support/{anki_connect,release}.py, tests/support/fixtures/release.py'
  - 'tests/integration/test_release_wheel.py'
  - 'bmod-tea/knowledge: data-factories.md, component-tdd.md, test-quality.md, test-healing-patterns.md, test-levels-framework.md, test-priorities-matrix.md, ci-burn-in.md'
acceptanceCriteria:
  - { id: 'AC-1', idSource: 'generated', text: 'adapters/anki/manifest.py derives every name (note types, decks, preset) from ANKI_PREFIX, and the names for LanguageLab and LanguageLabDev never overlap' }
  - { id: 'AC-2', idSource: 'generated', text: 'The manifest declares the five note types with the A3/AD-10 fields, including hidden ItemId/CaptureId and SchemaVersion, and Russian plus RussianAlternatives' }
  - { id: 'AC-3', idSource: 'generated', text: 'Each Item note type has four card templates and the Capture note type one' }
  - { id: 'AC-4', idSource: 'generated', text: 'The manifest maps card ord 0-3 to Exercise (Understand, Produce, Write, Pronounce) and to its deck' }
  - { id: 'AC-5', idSource: 'generated', text: 'The manifest declares the 28-deck tree' }
  - { id: 'AC-6', idSource: 'generated', text: 'The manifest declares the <Prefix> preset with its three sibling-burying flags off' }
  - { id: 'AC-7', idSource: 'generated', text: 'The manifest declares the current SchemaVersion' }
  - { id: 'AC-8', idSource: 'generated', text: 'Working front/back templates and CSS live as files under adapters/anki/templates/, and the manifest reads them from there' }
  - { id: 'AC-9', idSource: 'generated', text: 'The template files are packaged in the built wheel' }
  - { id: 'AC-10', idSource: 'generated', text: 'codec write escapes only & < > and turns \n into <br> (AD-9), so a domain value round-trips through write then read' }
  - { id: 'AC-11', idSource: 'generated', text: 'codec read maps <br> and block tags to \n, strips other tags, unescapes, and turns NBSP into a space (AD-9)' }
  - { id: 'AC-12', idSource: 'generated', text: 'RussianAlternatives are joined and split with ", " in the codec (AD-10)' }
---

# ATDD Checklist: Story 2.4, Managed manifest, template files, and field codec

## Run context

- **Story source:** epic-anki-setup-sync `tickets.toml`, entry 4. There is no story file. AC-1 to AC-12 come from the ticket's description, in source order, with the verify clauses folded in: "LanguageLab vs LanguageLabDev never overlap" into AC-1, "four card templates per Item note type and one for Capture" into AC-3, "present in the built wheel" into AC-9, and the codec round-trips into AC-10 (domain values) and AC-11 (Anki-editor content). All ids are generated.
- **Stack:** `backend` (pyproject, pytest, no `package.json`). The story has no UI and no HTTP surface, so there are no E2E or API leaves.
- **Test design:** none for epic 2. Priorities follow the ticket's risk (medium), NFR-1 (Prefix boundary), FR-8/AC7 (no sibling burying), FR-20 (cards in the right deck) and AD-9 (field content integrity).
- **Playwright Utils / Pact.js Utils:** N/A. Both are TypeScript-only, NFR-11 rules out Node, and there are no contract artifacts.
- **Affected components:**
  - New: `domain/catalog.py` (Language, Category, Exercise), `adapters/anki/manifest.py`, `adapters/anki/codec.py`, `adapters/anki/templates/` (HTML and CSS files).
  - Changed: none in `src/`. Tests: `tests/support/release.py` gains `run_python_from_wheel()`.
  - Packaging: none expected. `uv_build` already ships every file under `src/language_lab/`, so the templates go in the wheel without a `pyproject.toml` change (checked with the stand-ins).

### Decisions taken with the user (2026-10-21)

| Question | Decision |
| --- | --- |
| Which field comes first in each note type (Anki's sort field and duplicate key; changing it later is a migration)? | **Target/Text first.** Vocabulary: `Target, Russian, RussianAlternatives, Hint, PartOfSpeech, Grammar, Example, ExampleRussian, Mnemonic, Audio, ItemId, SchemaVersion`. Sentence: `Target, Russian, RussianAlternatives, Hint, Note, Audio, ItemId, SchemaVersion`. Capture: `Text, CreatedAt, CaptureId, SchemaVersion`. A3 lists the same fields with the ids first; only the order differs. |

### Defaults taken without a question

- **Names** follow A3 with the Prefix in place of `LanguageLab`: note types `<P> Capture`, `<P> English Vocabulary`, `<P> English Sentence`, `<P> French Vocabulary`, `<P> French Sentence`; decks `<P>`, `<P>::Captures`, `<P>::Study::<English|French>::<Vocabulary|Sentences>::<Understand|Produce|Write>`, `<P>::Pronunciation::<English|French>::<Vocabulary|Sentences>` and their parents; preset `<P>`.
- **Card template names** are the Exercise names `Understand`, `Produce`, `Write`, `Pronounce` (ord 0 to 3); the Capture template is `Capture`.
- **"Hidden"** means no card template renders the field. Anki has no hidden-field flag that `createModel` sets.
- **Bury flags** are the spike's Q5 keys as dotted paths into the deck config: `new.bury`, `rev.bury`, `buryInterdayLearning`, each `False`.
- **The preset is assigned to 26 decks:** every deck in the Study and Pronunciation branches, branch roots included (AD-3: "every managed Study and Pronunciation deck"). The root and `Captures` keep Anki's default.
- **SchemaVersion starts at `1`**, an `int`.
- **Shared enums** go in a new `domain/catalog.py`: `Language` (`en`, `fr`), `Category` (`vocabulary`, `sentence`), `Exercise` (`understand`, `produce`, `write`, `pronounce`), per the Consistency Conventions. `domain/items.py` stays the Items epic's (AD-11).
- **Codec read, block tags:** an opening or closing `div`, `p`, `li`, `ul`, `ol`, `h1`-`h6`, `blockquote` or `pre` tag is a line boundary. Adjacent boundaries collapse to one `\n`, and a boundary at the start or end of the field adds nothing. Each `<br>` (any case, `<br/>`, `<br />`) is always exactly one `\n`. Tag names match case-insensitively.
- **Codec write** leaves `"`, `'` and NBSP alone (AD-9: escape only `& < >`).
- **Alternatives split** tolerates edits made in Anki: it splits on `,`, strips each part and drops empty parts. Join is always `", ".join(...)`. Splitting runs on decoded text, after `decode_field`.

## Generation mode (step 2)

AI generation. The stack is `backend`, so recording is skipped. Execution is **sequential**, written in this session, with no subagents.

## Test strategy (step 3)

| AC | Level | Priority | Primary scenario | First (criterion-defining) assertion |
| --- | --- | --- | --- | --- |
| AC-1 | Unit | P0 | Build the manifest for `Zq`, then for `LanguageLab` and `LanguageLabDev` | every name of the `Zq` manifest is `Zq`, or starts with `Zq ` or `Zq::` |
| AC-2 | Unit | P1 | Build for `LanguageLab`; read each note type's fields | note type names equal the five A3 names, in order |
| AC-3 | Unit | P1 | Count and name each note type's templates | template count per note type is 4 for each Item type and 1 for Capture |
| AC-4 | Unit | P0 | `card_deck(note_type, ord)` for every Item type and ord 0-3, and Capture ord 0 | the full `(note type, ord) -> deck` mapping equals the expected 17 entries |
| AC-5 | Unit | P1 | Read `manifest.decks` | the sorted deck names equal the expected 28 |
| AC-6 | Unit | P0 | Read `manifest.preset` | `bury_flags == {"new.bury": False, "rev.bury": False, "buryInterdayLearning": False}` |
| AC-7 | Unit | P2 | Read `manifest.schema_version` for two Prefixes | `schema_version == 1` |
| AC-8 | Unit | P1 | Compare each template's front, back and CSS with the files under `templates/`, then lint the field references | every front, back and CSS text is the exact content of a file under `adapters/anki/templates/` |
| AC-9 | Integration | P1 | Build the wheel (`release_wheel`), list it, then import the manifest from the installed wheel | every file under the source `templates/` is in the wheel at the same path |
| AC-10 | Unit | P0 | `encode_field(value)` over a table of domain values | `encode_field(value) == stored` |
| AC-11 | Unit | P0 | `decode_field(stored)` over a table of Anki-written content | `decode_field(stored) == value` |
| AC-12 | Unit | P1 | Join, split, then split Anki-edited strings | `join_alternatives(["à la carte", "menu"]) == "à la carte, menu"` |

- **One leaf per criterion.** AC-10 and AC-11 are parametrized tables in one leaf each.
- **Red-phase imports.** The modules under test are imported in each leaf's body, so collection stays green while they're missing. Hoist the imports when green.
- **No duplicate coverage.** Names, structure and the codec are pure data and functions, so they're covered at Unit. Only packaging needs the built wheel (Integration).
- **Negative paths at high risk.** AC-1 checks disjointness of the two real Prefixes, including a `LanguageLab` deck search scope never covering a `LanguageLabDev` deck. AC-8 checks that no template renders a hidden field and that no front shows `RussianAlternatives` or (on Produce/Write) `Audio`. AC-10/AC-11 include markup-looking text, double escapes and entities.

## TDD Red Phase (Current)

Scaffolds generated: **12 leaves, 35 cases, all `@RED_PHASE` (`pytest.mark.skip`)**.

| File | Level | Leaves (cases) |
| --- | --- | --- |
| `tests/unit/test_anki_manifest.py` | Unit | 8 (8): AC-1 to AC-8 |
| `tests/unit/test_anki_codec.py` | Unit | 3 (26): AC-10 (9), AC-11 (16), AC-12 (1) |
| `tests/integration/test_anki_templates_wheel.py` | Integration | 1 (1): AC-9 |

Observed with the skip markers stripped (a scratchpad plugin, not committed): **35 failed**.

- 26 cases: `ModuleNotFoundError: No module named 'language_lab.adapters.anki.codec'`, raised in the test body.
- 9 cases: `ModuleNotFoundError: No module named 'language_lab.adapters.anki.manifest'`, raised in the test body.

**Green feasibility, checked and removed.** Throwaway stand-ins turned all **35 of 35** cases green:

- `domain/catalog.py`, `adapters/anki/codec.py` (regex block/br handling, `html.unescape`), `adapters/anki/manifest.py` (frozen dataclasses, templates read through `importlib.resources`)
- 19 files under `adapters/anki/templates/`: `cards.css`, `capture-{front,back}.html`, `<category>-<exercise>-{front,back}.html`
- The wheel built by `uv build` carried all 19 with no `pyproject.toml` change, and the manifest imported from the installed wheel matched the source one.

Each mutation below was caught:

| Mutation | Caught by |
| --- | --- |
| Write also escapes `"` | AC-10 `quotes-left-alone` |
| NBSP character kept on read | AC-11 `nbsp-char`, `nbsp-entity` |
| Consecutive `<br>` collapsed | AC-11 `blank-line` |
| Block tags stripped instead of becoming newlines | AC-11 `editor-div-line`, `editor-div-lines`, `paragraphs`, `list` |
| No unescape on read | AC-11 (4 rows), AC-10 (3 round-trip rows) |
| Strict `", "` split | AC-12 |
| A Pronunciation deck hardcodes `LanguageLab` | AC-1 |
| ord 3 sent to a Study deck | AC-4 |
| Preset also on the root deck | AC-6 |
| One bury flag missing | AC-6 |
| `ItemId` first | AC-2 |
| `ItemId` not hidden | AC-2, AC-8 |
| SchemaVersion 2 | AC-7 |
| No Pronounce template | AC-3, AC-4, AC-8 |
| CSS inline instead of from a file | AC-8 |
| A back renders `{{ItemId}}` | AC-8 |
| `RussianAlternatives` on a Produce front | AC-8 |
| `Audio` on a Write front | AC-8 |
| A Vocabulary back drops `Mnemonic` | AC-8 |
| `wheel-exclude` drops the templates | AC-9 |

The stand-ins were deleted (the four new source paths removed, `pyproject.toml` restored and compared). With the scaffolds skipped, the suite stays green (**395 passed, 35 skipped**), and `ruff check` and `ruff format --check` pass.

## Acceptance Criteria Coverage

| AC | Priority | Test | First assertion, then the rest |
| --- | --- | --- | --- |
| AC-1 | P0 | `test_every_manifest_name_derives_from_the_prefix_and_prefixes_never_overlap` | every `Zq` name is `Zq`, `Zq …` or `Zq::…`; then no `LanguageLab` text in them; release and dev name sets disjoint; neither Prefix's `deck:` scope covers the other's decks; `manifest.prefix` |
| AC-2 | P1 | `test_manifest_declares_five_note_types_with_their_fields` | the five names in A3 order; then each field tuple (Target/Text first); hidden sets `{ItemId, SchemaVersion}` / `{CaptureId, SchemaVersion}` |
| AC-3 | P1 | `test_item_note_types_have_four_card_templates_and_capture_one` | template counts 4/4/4/4/1; then `(ord, name)` is `(0, Capture)` and `(0..3, Understand..Pronounce)` |
| AC-4 | P0 | `test_card_ord_maps_to_its_exercise_and_deck` | the 17-entry `(note type, ord) -> deck` map; then every target deck is declared; `EXERCISE_BY_ORD` |
| AC-5 | P1 | `test_manifest_declares_the_28_deck_tree` | sorted decks equal the 28 expected; then no duplicates; parents listed before children |
| AC-6 | P0 | `test_preset_turns_off_the_three_bury_flags_on_every_study_and_pronunciation_deck` | `bury_flags` equals the three keys, all `False`; then preset name is the Prefix; each dotted key names a bool in the recorded `getDeckConfig`; preset decks are exactly the 26 Study and Pronunciation decks |
| AC-7 | P2 | `test_manifest_declares_the_current_schema_version` | `schema_version == 1`; then `SCHEMA_VERSION == 1`; same for the dev Prefix |
| AC-8 | P1 | `test_card_templates_and_css_come_from_template_files_and_render_only_shown_fields` | no front, back or CSS text that isn't a file under `templates/`; then per template: only declared fields, no hidden field, a non-empty front, each Item back shows every non-hidden field (with `{{FrontSide}}`), no `RussianAlternatives` on a front; Understand front has Target and no Russian; Produce front has Russian and no Target or Audio; Write front and back have `{{type:Target}}`, the front Russian and no Audio; Pronounce front has Target; Capture front has Text |
| AC-9 | P1 | `test_template_files_ship_in_the_built_wheel` | every source template file is in the wheel; then same bytes; the manifest imported from the installed wheel (not `src/`) declares the same template and CSS texts |
| AC-10 | P0 | `test_write_escapes_only_amp_lt_gt_and_turns_newlines_into_br` [plain, accents-and-apostrophe, quotes-left-alone, escapes, markup-looking-text, entity-looking-text, newlines, trailing-newline, empty] | `encode_field(value) == stored`; then `decode_field(encode_field(value)) == value` |
| AC-11 | P0 | `test_read_turns_anki_markup_into_plain_text` [br, br-spellings, blank-line, editor-div-line, editor-div-lines, paragraphs, list, inline-tags-stripped, styled-span, unescape, entities, double-escaped-once, nbsp-entity, nbsp-char, our-own-write, empty] | `decode_field(stored) == value` |
| AC-12 | P1 | `test_russian_alternatives_are_joined_and_split_with_comma_space` | `join_alternatives(["à la carte", "menu"]) == "à la carte, menu"`; then split back; one and zero alternatives; four Anki-edited strings split leniently |

## Implementation contract the tests encode

- **`domain/catalog.py`:** `Language(StrEnum)` `EN="en"`, `FR="fr"`; `Category(StrEnum)` `VOCABULARY="vocabulary"`, `SENTENCE="sentence"`; `Exercise(StrEnum)` `UNDERSTAND`, `PRODUCE`, `WRITE`, `PRONOUNCE` with lowercase values. The tests import only `Exercise`; the others follow the Consistency Conventions for later entries.
- **`adapters/anki/manifest.py`:**
  - `SCHEMA_VERSION = 1`.
  - `EXERCISE_BY_ORD: Mapping[int, Exercise]` = `{0: UNDERSTAND, 1: PRODUCE, 2: WRITE, 3: PRONOUNCE}`.
  - `build_manifest(prefix: str) -> Manifest`, with:
    - `.prefix: str`, `.schema_version: int`
    - `.note_types: tuple[NoteType, ...]` in the order Capture, English Vocabulary, English Sentence, French Vocabulary, French Sentence
    - `NoteType`: `.name`, `.fields: tuple[Field, ...]` (`Field.name`, `Field.hidden`), `.templates: tuple[CardTemplate, ...]` in ord order (`.name`, `.ord`, `.front`, `.back`), `.css`
    - `.decks: tuple[str, ...]`, 28 full names, each parent before its children
    - `.preset`: `.name == prefix`, `.bury_flags == {"new.bury": False, "rev.bury": False, "buryInterdayLearning": False}`, `.decks` the 26 Study and Pronunciation decks
    - `.card_deck(note_type_name: str, ord: int) -> str`
  - Template and CSS texts are the exact contents of files under `adapters/anki/templates/`, read as package data (`importlib.resources`), not inline strings. Any file layout works; the tests compare texts, not paths.
- **Templates** (working, not final; epic-capture-to-item owns the final markup, AD-3 Deferred):
  - Fronts: Understand shows Target (Audio allowed) and not Russian. Produce shows Russian, not Target or Audio. Write shows Russian and `{{type:Target}}`, not Audio. Pronounce shows Target. Capture shows Text.
  - Backs: each Item back shows every non-hidden field, directly or through `{{FrontSide}}`. Write's back repeats `{{type:Target}}`.
  - No template references `ItemId`, `CaptureId` or `SchemaVersion`, or a field its note type lacks. `RussianAlternatives` never appears on a front.
- **`adapters/anki/codec.py`:** `encode_field(value: str) -> str`, `decode_field(stored: str) -> str`, `join_alternatives(alternatives: list[str]) -> str`, `split_alternatives(stored: str) -> list[str]`, with the rules under "Defaults taken without a question".
- **Packaging:** the template files ship in the wheel. `uv_build` does that today with no configuration.

## Fixture and support changes (made in this run)

- `tests/support/release.py`: `run_python_from_wheel(wheel, code, *, cwd)` runs `uv run --no-project --python <this python> --with <wheel> python -c <code>` outside the repo and returns stdout.
- `tests/README.md`: the new helper.

## Next Steps (Task-by-Task Activation)

1. Pick a task and remove its `@RED_PHASE` line.
2. Run it, e.g. `uv run pytest tests/unit/test_anki_codec.py`.
3. Watch it fail for the reason above, implement, and watch it pass. Then hoist its in-body imports.
4. If a test fails unexpectedly, fix the implementation (feature bug) or the test (test bug). Don't weaken the first assertion.
5. Before the story closes:
   - No `RED_PHASE` markers remain in the three files.
   - `make test` and `make lint` pass.

Suggested order:

1. `codec.py` (AC-10, AC-11, AC-12). It has no dependencies.
2. `domain/catalog.py` and the manifest's names, decks, mapping, preset and version (AC-1, AC-2, AC-4, AC-5, AC-6, AC-7).
3. Template files and loading (AC-3, AC-8), then packaging (AC-9).

## Green-phase automation backlog (secondary branches, not scaffolded)

| AC | Add once green | Priority |
| --- | --- | --- |
| AC-1 | `build_manifest` rejects a Prefix that fails `PREFIX_PATTERN` (a name with a space, `::` or a quote) with `ValueError`, even though settings checks it first | P2 |
| AC-4 | `card_deck` raises for an unknown note type or an ord outside the type's templates | P2 |
| AC-10 | `\r\n` from a client is stored as one `<br>`, not `\r<br>` | P2 |
| AC-11 | Anki's empty-line markup (`a<div><br></div>b`) and `<br>` next to a block tag read as the user typed them; record the rule once seen in real fields | P2 |
| AC-11 | Reading strips `<img>`, `[sound:…]` stays as text in non-Audio fields, and comments (`<!-- -->`) go | P3 |
| AC-12 | A read Item gets `russianAlternatives` from `split_alternatives(decode_field(raw))`, and a Save writes `encode_field(join_alternatives(...))` (lands with the adapter reads/writes in entries 6 and 8 and epic 4) | P1 |
| AD-9 | No module outside `adapters/anki/codec.py` calls `html.escape`/`html.unescape` or replaces `<br>` (a source scan) | P3 |
| AC-8 | Rendering each Item template with a sample note through a minimal mustache pass leaves no `{{` behind and shows no audio markup when `Audio` is empty (FR-21) | P3 |

## Open items

- **Template visuals are placeholders on purpose.** Epic-capture-to-item writes the final markup and CSS as a template-only change with no SchemaVersion bump (epic decision 2026-10-08). The AC-8 rules are the floor those templates must keep.
- **Block-tag reading is a default, not a recording.** The spike recorded no Anki-editor field content. If real fields show other shapes (`<div><br></div>` empty lines), add rows to AC-11 from a recorded `notesInfo`.
- **The preset on branch-root decks** (`Study`, `Pronunciation`, per Language and Category) is a reading of AD-3. If entry 6 or 7 finds that assigning a preset to a parent deck changes what the user sees when studying it, narrow `preset.decks` and AC-6's 26.
- **`saveDeckConfig` returned `false`** in the spike (Q5). This entry only declares the flags; entry 6/7 must prove a working save before relying on it.

## Validation (step 5)

- [x] Prerequisites: the criteria are clear (the ticket description and verify, A3, AD-3/AD-9/AD-10, the spike's Q5 keys, and the field-order decision recorded with the user), pytest is configured, and the dev env runs
- [x] Every criterion has a stable generated id (AC-1 to AC-12), with no collisions
- [x] Every leaf's docstring carries exactly one `AC-n`, and each criterion has exactly one red-phase leaf (12 leaves)
- [x] Every scaffold is skipped with a reason naming what re-enables it, and none has placeholder assertions
- [x] The first assertion is the criterion-defining one. The stand-in run showed each leaf reaching it, and the mutation table shows each failing on its own branch
- [x] No unimplemented setup result is parsed before the criterion assertion (AC-9 builds the wheel through the existing fixture and asserts on the file list first)
- [x] No state transitions in this story; the round trip (write then read) is exercised in AC-10
- [x] Existing tests are unchanged in behavior and pass (395 passed, 35 skipped). `ruff check` and `ruff format --check` are clean
- [x] Story handoff: there's no story file, so this checklist is the handoff for `bmad-build` on entry 4
- [x] No browser sessions were opened. The unskip plugin and stand-in copies are in the session scratchpad, and the stand-ins were removed from the tree

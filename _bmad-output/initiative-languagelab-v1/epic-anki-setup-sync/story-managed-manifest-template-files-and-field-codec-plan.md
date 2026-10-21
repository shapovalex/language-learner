---
title: 'Managed manifest, template files, and field codec'
type: 'feature'
ticket: '4'
created: '2026-10-21'
status: 'built'
baseline_revision: '54b70fd7fd6bba7eccf24b8a855e1542533f39bf'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-2-4.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Setup (entries 6–9) and every feature need one source of Anki names and structure (AD-3) and one codec for field content (AD-9, AD-10); neither exists, so the 12 red-phase ATDD leaves for story 2.4 are skipped.

**Approach:** Add `domain/catalog.py` (shared enums), `adapters/anki/manifest.py` (pure, Prefix-derived declaration with templates and CSS read as package data), 19 working template files under `adapters/anki/templates/`, and `adapters/anki/codec.py`; un-skip the ATDD leaves and make them green.

## Boundaries & Constraints

**Always:**
- Every name derives from the `prefix` argument; nothing hardcodes `LanguageLab`.
- Field order is Target/Text first (decided with the user 2026-10-21, see the ATDD checklist); `ItemId`/`CaptureId` and `SchemaVersion` are hidden = no template references them.
- Template and CSS texts are read from files via `importlib.resources`, never inline strings.
- Codec write escapes only `& < >` and maps `\n` → `<br>`; read follows the block-tag/`<br>` rules in the ATDD checklist ("Defaults taken without a question").
- Shared enums use the Consistency Conventions values (`en`/`fr`, `vocabulary`/`sentence`, lowercase Exercise).

**Never:**
- No AnkiConnect calls, no Setup diff/apply, no port changes (entries 6–9).
- No final template visuals (epic-capture-to-item); templates are working placeholders.
- No `domain/items.py` (AD-11, Items epic). No `pyproject.toml` change unless the wheel test proves it necessary.
- Do not weaken any ATDD first assertion.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Prefix names | `build_manifest("LanguageLabDev")` | every name is the Prefix, `<P> …` or `<P>::…`; disjoint from `LanguageLab` | No error expected |
| Card routing | `card_deck("<P> French Sentence", 3)` | `<P>::Pronunciation::French::Sentences` | unknown type/ord → `KeyError`/`ValueError` |
| Bad Prefix | `build_manifest("Bad Prefix")` | rejected | `ValueError` (PREFIX_PATTERN) |
| Codec write | `"a < b\nc"` | `"a &lt; b<br>c"`, quotes and NBSP untouched | No error expected |
| Codec read | `"<div>one</div><div>two</div>"`, `a&nbsp;b`, `&amp;lt;` | `"one\ntwo"`, `"a b"`, `"&lt;"` | No error expected |
| Alternatives | `" a ,  b , "` split | `["a", "b"]`; join always `", "` | No error expected |

</frozen-after-approval>

## Code Map

- `tests/unit/test_anki_manifest.py`, `tests/unit/test_anki_codec.py`, `tests/integration/test_anki_templates_wheel.py` -- red-phase leaves (AC-1…AC-12); remove `RED_PHASE` markers and hoist in-body imports once green. The checklist's "Implementation contract" section is the API to satisfy.
- `src/language_lab/settings.py:24` -- `PREFIX_PATTERN`; reuse for the manifest's Prefix check.
- `src/language_lab/domain/sync.py` -- style reference: short module docstring, `StrEnum`, `@dataclass(frozen=True)`.
- `src/language_lab/adapters/anki/__init__.py` -- adapter package; `templates/` lands beside it (uv_build ships all package files).
- `tests/fixtures/anki/getDeckConfig.json` -- recorded config the bury-flag paths are checked against; do not edit.
- `tests/support/release.py` -- `run_python_from_wheel()` already added by ATDD; do not change.
- `tests/README.md` -- update only if a new test helper is added.

## Tasks & Acceptance

**Execution:**
- [x] `src/language_lab/adapters/anki/codec.py` -- `encode_field`, `decode_field`, `join_alternatives`, `split_alternatives` per AD-9/AD-10 and the checklist rules; `\r\n` normalized to one `<br>` -- the only field conversion (AD-9).
- [x] `src/language_lab/domain/catalog.py` -- `Language`, `Category`, `Exercise` `StrEnum`s -- shared vocabulary for later entries.
- [x] `src/language_lab/adapters/anki/templates/` -- `cards.css`, `capture-{front,back}.html`, `<vocabulary|sentence>-<understand|produce|write|pronounce>-{front,back}.html` (19 files) meeting the checklist's template rules (fronts, backs with `{{FrontSide}}`, `{{type:Target}}` on Write, `Audio` only where allowed, `RussianAlternatives` back only) -- working templates.
- [x] `src/language_lab/adapters/anki/manifest.py` -- `SCHEMA_VERSION = 1`, `EXERCISE_BY_ORD`, frozen dataclasses `Field`, `CardTemplate`, `NoteType`, `Preset`, `Manifest` (with `card_deck`), `build_manifest(prefix)` validating `PREFIX_PATTERN`; decks parents-first (28); preset on the 26 Study/Pronunciation decks with `new.bury`, `rev.bury`, `buryInterdayLearning` all `False` -- AD-3 single source.
- [x] the three ATDD test files -- un-skip, hoist imports; add P2 cases for bad Prefix, unknown `card_deck` input, and `\r\n` write -- green-phase backlog items that cost one assert each.

**Acceptance Criteria:**
- Given the scaffolds un-skipped, when `make test-fast` runs, then all 35 story cases pass and nothing else regresses.
- Given a wheel built by `uv build`, when the integration test imports the manifest from it, then its template and CSS texts equal the source ones.
- Given `make lint`, then ruff check and format pass with no `RED_PHASE` left in the three files.

## Implementation Notes

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — high 0, medium 0, low 5 (3 patched, 2 rejected), false 0, maybe-false 1 (deferred)

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1 | `decode_field("a<div><br></div>b")` gives `a\n\n\nb` | maybe-false (medium if true) | defer | Whether the Anki editor in use writes `<div><br></div>` is unrecorded (recent editors write `<br>`); the checklist already parks it as a P2 backlog item pending a recorded `notesInfo`. |
| 2 | Raw `\n` in stored HTML kept as line breaks; edge boundary ignores surrounding whitespace | low | reject | Neither our encoder nor the Anki editor writes raw newlines; only hand-imported HTML would, and the fix needs whitespace-collapsing rules beyond a direct correction. |
| 3 | `encode_field` leaves a lone `\r` | low | patch | Direct correction: normalize lone `\r` to `\n`; test extended. |
| 4 | `Manifest`/`Preset` unhashable (`MappingProxyType` field) | low | reject | No caller hashes them; fixing needs a field-level hash override, more than a direct correction. |
| 5 | `ExampleRussian` hidden when `Example` empty on vocabulary backs | low | patch | Own `{{#ExampleRussian}}` section. |
| 6 | Unguarded `PartOfSpeech`/`Grammar` meta div renders empty | low | patch | Section guards like the other optional fields. |

## Design Notes

Templates are keyed by Category and Exercise, not Language, so English and French note types share files. `card_deck` derives from the note type's Language/Category: ords 0–2 → `<P>::Study::<Lang>::<Plural>::<Exercise title>`, ord 3 → `<P>::Pronunciation::<Lang>::<Plural>`, Capture → `<P>::Captures`. Codec read sketch: normalize `\r\n`; `<br\s*/?>` → `\n`; runs of block open/close tags → one boundary, dropped at field start/end; strip remaining tags; `html.unescape`; NBSP → space.

## Verification

**Commands:**
- `uv run pytest tests/unit/test_anki_manifest.py tests/unit/test_anki_codec.py tests/integration/test_anki_templates_wheel.py` -- expected: all pass, none skipped
- `make test-fast` -- expected: green
- `make lint` -- expected: clean

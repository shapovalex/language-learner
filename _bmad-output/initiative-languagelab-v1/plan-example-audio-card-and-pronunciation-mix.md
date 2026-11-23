---
title: 'Example card with example audio, and a new/due mix in Pronunciation'
type: 'feature'
ticket: ''
created: '2026-11-23'
status: 'built'
baseline_revision: '7347bbdc190390474eec0acafaa7ab7d6a821df0'
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

**Problem:** (1) A Vocabulary Item's `Example`/`ExampleRussian` only appear on the backs of other cards; there is no card that asks the learner to produce the example sentence, and no audio for it. (2) The Pronunciation screen always shows due Cards before new ones, so after rating one new Card that Card (now in learning, `is:due`) comes back first and the session never mixes in the other new Cards.

**Approach:** (1) Add an `ExampleAudio` field and a fifth card template, Example (front `ExampleRussian`, back `Example` + its audio), to the two Vocabulary note types via a SchemaVersion 2 migration; make example audio at Save, and offer a backfill that adds it to existing Vocabulary notes. (2) When both due and new Cards exist, choose the next Pronunciation Card's kind at random.

**Decisions (2026-11-23):**
- Mix: when both kinds exist, the next Card's kind is random, weighted by the due:new counts, and the first Card of that kind is shown. The Card just rated is never shown again straight away while another Card exists.
- The new card is named "Example" and goes in `Study::<Language>::Vocabulary::Example`.
- An Example card exists only once its note has example audio.
- Backfill: a button on the Items screen for each Language. It uses the saved Voice, works in batches and shows progress.
- When a Save changes the Example text (or ExampleAudio is empty), the example audio is remade automatically with the Draft's Voice.

## Boundaries & Constraints

**Always:** Existing card templates (ords 0-3), their files and the Sentence note types stay byte-identical. Every Anki write goes through the guarded, gated client; Anki names come from the manifest only (AD-3, AD-4). Example media uses the AD-7 media name and is cleaned up like `Audio`. The migration only adds a field and a template, which is append-only and never deletes cards or notes.

**Never:** Changing Sentence note types. Changing the FSRS/ease mapping or Anki's own scheduling. Storing session state on the server.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mix | queue has `d` due and `n` new Cards | first due Card with probability d/(d+n), else first new Card | n/a |
| Just rated | the Card just rated is still at the head of its kind and another Card exists | a different Card is shown | n/a |
| One kind | only due or only new Cards | first Card of that kind, as today | n/a |
| Save with example | Vocabulary Save, Example + ExampleRussian non-blank, Voice chosen | ExampleAudio stored and the Example card is in its Study deck | TTS failure: Item saves without example audio, inline warning |
| Example edited | stored Example differs from the saved one | new example audio, old media deleted | as above |
| Backfill | Vocabulary notes with Example + ExampleRussian and empty ExampleAudio | each gets audio and an Example card in its deck; progress shown | a failed note is counted and skipped; rerun picks it up |

</frozen-after-approval>

## Code Map

- `src/language_lab/adapters/anki/manifest.py` -- `SCHEMA_VERSION=1`, `_FIELDS`, `EXERCISE_BY_ORD`, `STUDY_ORDS`, `_item_templates`, `_decks`, `card_deck`. Add ord 4 (Example) for Vocabulary only; new deck per Vocabulary branch; `ExampleAudio` appended to Vocabulary fields (after `SchemaVersion`, since `modelFieldAdd` appends).
- `src/language_lab/domain/catalog.py` -- `Exercise` enum: add `EXAMPLE`.
- `src/language_lab/adapters/anki/templates/` -- new `vocabulary-example-{front,back}.html`; do not touch existing files.
- `src/language_lab/adapters/anki/migrations.py` -- `build_migrations` returns `()`; add `Migration(1, (AddField(<Lang> Vocabulary, "ExampleAudio"),…))`. The template is added by the existing templates Repair (`setup_apply.repair_templates` → `modelTemplateAdd`).
- `src/language_lab/adapters/anki/setup_gate.py` -- `_AUDIO_FIELDS`: add `ExampleAudio` so orphan media detection sees it.
- `src/language_lab/adapters/anki/store.py` -- `save_item` (l.414): store example media and set `ExampleAudio`, move ord 4 card to its deck after add *and* after update (Anki generates it in an existing card's deck); `delete_item` media cleanup already covers `<prefix>_<itemId>_*`. `pronunciation_queue` (l.581): carry `is_new` per card. New `add_example_audio(language, voice_synth, limit)` for the backfill.
- `src/language_lab/ports/anki_store.py`, `tests/fakes/anki_store.py` -- port/fake for new store methods.
- `src/language_lab/domain/pronunciation.py` -- `PronounceCard` gains `is_new` (wire `isNew`).
- `src/language_lab/features/items/routes.py`, `service.py` -- Save intent gains optional `exampleVoice`; service synthesizes via `AudioService.preview`-style voice validation (`features/audio/service.py`) when needed. New backfill route `POST /api/items/{lang}/example-audio`.
- `src/language_lab/static/screens/make-item.js` (`referenceAudio`, l.680) -- send the chosen Voice as `exampleVoice`; `static/api.js` (`saveItem` l.189); `static/screens/items.js` -- backfill button + progress.
- `src/language_lab/static/screens/pronunciation.js` (l.416, 477) -- pick next Card by alternation instead of `cards[0]`.
- `tests/support/anki_state.py` -- fake collection: generate a card for a template only when its front's required fields are non-empty; generate missing cards on `updateNoteFields` and `modelTemplateAdd`, in the deck of the note's first card (Anki's behaviour).
- Tests to extend: `tests/unit/test_anki_manifest.py` (asserts `SCHEMA_VERSION == 1`, ord map), `tests/integration/test_anki_migrations.py`, `test_anki_item_save.py`, `test_anki_pronunciation.py`, `tests/e2e/test_pronunciation_review.py`.

## Tasks & Acceptance

**Execution:**
- [ ] `domain/catalog.py`, `adapters/anki/manifest.py`, new templates -- Example exercise, ord 4, deck, `ExampleAudio` field, SCHEMA_VERSION 2 -- the managed shape.
- [ ] `adapters/anki/migrations.py`, `setup_gate.py` -- v1→v2 AddField; audio field scan -- upgrades existing collections through Setup.
- [ ] `adapters/anki/store.py`, `ports/anki_store.py`, `tests/fakes/anki_store.py` -- example media on Save, ord 4 deck placement, backfill batch, `is_new` on queue cards.
- [ ] `features/items/{routes,service}.py`, `app.py` wiring -- `exampleVoice` on Save, backfill route returning `{done, failed, remaining}`.
- [ ] `static/api.js`, `screens/make-item.js`, `screens/items.js` -- send Voice; backfill control looping batches with progress.
- [ ] `domain/pronunciation.py`, `static/screens/pronunciation.js` -- `isNew` on the wire; weighted random pick + skip-just-rated, with the random source injectable for e2e tests (e.g. a `?seed`/test hook or a stubbed `Math.random` via Playwright `add_init_script`).
- [ ] `tests/support/anki_state.py` + unit/integration/e2e tests for every I/O matrix row and the migration.

**Acceptance Criteria:**
- Given a collection at SchemaVersion 1, when Setup is previewed and applied, then both Vocabulary note types gain `ExampleAudio` and an Example template, every managed note is at SchemaVersion 2, and ords 0-3 templates are unchanged.
- Given 5 new Pronounce Cards, when the learner rates the first Good (it becomes due), then the next Card shown is never that same Card, and with the random source stubbed to pick "new" a new Card is shown while the chip reads "1 due · 4 new".
- Given a Vocabulary Item with Example and ExampleRussian and no ExampleAudio, when the Items screen backfill runs, then the note gains ExampleAudio and one Example card in `Study::<Language>::Vocabulary::Example`, and the progress count reaches zero remaining.
- Given a Sentence Item, when saved, then no example audio is requested and its note is unchanged in shape.

## Implementation Notes

- Setup's apply adds migration fields before the plan's Create and Repair items and stamps SchemaVersion after them, because Anki refuses a template that names a missing field (`run_migrations` was split into `add_fields` and `stamp_versions`).
- The backfill is a candidates read plus one guarded write per Item (`store_example_audio`), so speech never holds the Anki lock.
- Saving with a blank Example or ExampleRussian clears `ExampleAudio`.
- The Example card's back shows only Example and its audio. The manifest test's "every back shows the whole note" check was relaxed for ord 4.
- Simulated, not verified against real Anki: a template naming a missing field is refused, and a generated card lands in the deck of the note's first card.

## Plan Change Log

## Review Triage Log

Quick review, pass 1: 2 medium, 3 low patched; 3 rejected (1 false, 2 low).

- medium (patch): editing the Example with no new audio (synthesis failed or no Voice) left the old clip in `ExampleAudio` for good; the next Save and the backfill both skip it (`has_example_audio`). Fix: empty it and delete the old clip.
- medium (patch): emptying `ExampleAudio` left the ord 4 card with an empty front in its Study deck. Fix: suspend it when emptied, and unsuspend it when audio is written again.
- low (patch): the backfill counted "not written" (Item gone, edited, or given audio concurrently) as failed, which inflated the client's `skip` and could skip a pending Item. Fix: only a synthesis or MP3 failure counts as failed.
- low (patch): the inner `current` helper in `pronunciation.js` l.258 shadowed the outer `current` Card. Fix: renamed it.
- low (patch): the `Item` docstring said example audio is set only by `get_item`. Fix: corrected.
- false (rejected): "every re-read draws again and can discard an Attempt". Every non-initial `load()` follows a Rating, an exclude or a `not_found`, and each of those already replaces the Card on screen. A stale `justRated` after an exclude only leaves out a card rated earlier, which does no harm.
- low (rejected): a Save on a SchemaVersion 1 collection synthesizes before `SETUP_REQUIRED`. This is rare (the gate blocks after Setup is needed), and the fix would add a pre-check guard.
- low (rejected): the named test files `test_anki_migrations.py` and `test_anki_item_save.py` weren't extended. The same coverage is in `test_anki_example_audio.py` (production migration, v1→v2 apply, Save paths), so there's no gap.

## Design Notes

Card existence: Anki only creates a card whose front renders non-empty, so the Example front is wrapped in `{{#ExampleAudio}}{{#ExampleRussian}}…{{/ExampleRussian}}{{/ExampleAudio}}`. Adding the template creates no cards; a card appears exactly when our Save/backfill writes `ExampleAudio`, and that same code moves it to its deck.

Pronunciation mix lives in the client because each Rating re-reads the queue and the server keeps no session (AD-17). The screen keeps the cardId it just rated. It drops that card from the candidates when others exist, picks a kind weighted by the remaining due:new counts, and shows that kind's first card.

## Verification

**Commands:**
- `uv run pytest -q` -- expected: all pass
- `uv run ruff check src tests && uv run ruff format --check src tests` -- expected: clean

**Manual checks:**
- Run Setup against a real Anki copy and confirm that the plan shows Migrate + templates Repair for the two Vocabulary note types only.

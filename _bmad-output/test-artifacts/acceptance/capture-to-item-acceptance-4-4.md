# Capture to Item acceptance on the released wheel (story 4.4)

The manual run that proves the released LanguageLab turns a Capture into Items in a real Anki
collection on the Mac Mini, used from the iPhone and iPad over Tailscale. It covers
epic-capture-to-item Done-when 1 to 5 (DW1–DW5) and the Setup templates Repair that story 4.4's
new card templates bring. It also settles four deferred checks in `deferred-work.md`: the
unsaved-changes alert on the Draft editor on iOS Safari (R-03), how `decode_field` reads a field
edited with blank lines, the cost of the Setup preview's `read_leftovers` with real cards, and
the real AnkiConnect replies to `changeDeck`, `updateNoteFields` and `cardsInfo`, which the tests
have so far hand-built.

- **Release under test:** `v0.6.0`, the first release with entries 1 to 4 of the epic
- **Prefix under test:** `LanguageLabDev`, set as an environment override. Never `LanguageLab`.
- **Mode:** release (no `LANGUAGE_LAB_DEV`)
- **Run on:** _(date of the run)_
- **Devices:** Mac Mini (host, with Anki Desktop, AnkiConnect and Tailscale Serve), iPhone
  Safari and AnkiMobile, iPad Safari, desktop browser on another computer

On the Mac Mini use only `uvx`, `curl`, `say` and the shell's own tools: no clone, no repository
script.

This repository is public. Do not write your real tailnet name, machine name, login, AnkiWeb
account or any address in this file, and do not paste AnkiConnect output that names decks or
note types outside `LanguageLabDev`. Write `<tailnet>` where a name would appear.

Record each step in [Results](#results) as **pass**, **fail**, or **not run** with the reason.
Paste the replies the steps ask for: a step reported without its paste stays unchecked against
the tests. Anything that fails, surprises you, or that the docs got wrong goes in
[Findings](#findings).

## A. Release and the Mac Mini

On the development machine:

| Step | Do | Expect |
| --- | --- | --- |
| A1 | From a clean checkout of `main` with entries 1 to 4 merged: `scripts/cut_release.sh 0.6.0`. | It ends with `Released v0.6.0. Wheel:` and the URL `https://github.com/shapovalex/language-learner/releases/download/v0.6.0/language_lab-0.6.0-py3-none-any.whl`. |

On the Mac Mini, with Anki Desktop open on the profile story 3.4 used (its `LanguageLabDev`
Prefix set up from v0.5.0), AnkiConnect installed, the profile logged in to AnkiWeb, and the
OpenRouter key and models in your LanguageLab config ([docs/configuration.md](../../../docs/configuration.md)).
In the terminal you will use for the whole run, set:

```sh
WHEEL=https://github.com/shapovalex/language-learner/releases/download/v0.6.0/language_lab-0.6.0-py3-none-any.whl
ac() { curl -s http://127.0.0.1:8765 -d "{\"action\":\"$1\",\"version\":6${2:+,\"params\":$2}}"; echo; }
VQ='{"query":"note:\"LanguageLabDev English Vocabulary\""}'
SQ='{"query":"note:\"LanguageLabDev French Sentence\""}'
ESQ='{"query":"note:\"LanguageLabDev English Sentence\""}'
APP=http://127.0.0.1:8787
```

`ac findNotes "$VQ"` then lists the ids of every `LanguageLabDev English Vocabulary` note, and
`$SQ` those of `LanguageLabDev French Sentence`, and `$ESQ` those of `LanguageLabDev English Sentence`. Anki ids are creation times in milliseconds, so
the largest id is the newest note.

| Step | Do | Expect |
| --- | --- | --- |
| A2 | `env \| grep LANGUAGE_LAB_DEV; echo "exit=$?"` | No variable printed, `exit=1`. If it is set, `unset LANGUAGE_LAB_DEV`. |
| A3 | `tailscale serve status` (see [docs/remote-access.md](../../../docs/remote-access.md)) | HTTPS on `<tailnet>` proxied to `http://127.0.0.1:8787`. |

## B. Start the release and repair the templates

| Step | Do | Expect |
| --- | --- | --- |
| B1 | `ANKI_PREFIX=LanguageLabDev uvx --from "$WHEEL" language-lab` | `LanguageLab running at http://127.0.0.1:8787/`, `On your tailnet: https://<tailnet>/`, then `Sync with AnkiWeb: ok`. |
| B2 | In a second terminal (set the six lines above there too): `curl -s $APP/api/health` | `{"version":"0.6.0"}` |
| B3 | `ac findNotes "$VQ"`, `ac findNotes "$SQ"` and `ac findNotes "$ESQ"` | `{"result": [...], "error": null}` each. Note the ids each lists (usually none). |
| B4 | Open `/setup` in the desktop browser. | Five rows "Repair", "Card templates and CSS", one per note type: `LanguageLabDev Capture`, `LanguageLabDev English Vocabulary`, `LanguageLabDev English Sentence`, `LanguageLabDev French Vocabulary`, `LanguageLabDev French Sentence`. Each explains "Expected LanguageLab's card templates and CSS; found different ones." No other row, unless an earlier run left one (then note it). |
| B5 | Click "Apply setup" and wait. | "Setup applied and verified", "Decks, note types, templates and deck options match what LanguageLab expects." If it also says a full sync is required, follow it ([docs/setup.md](../../../docs/setup.md)) and note it under Findings. |
| B6 | Reload `/setup`. | "Nothing to change." |
| B7 | In Anki Desktop, Tools › Manage Note Types › `LanguageLabDev English Vocabulary` › Cards. | The Understand, Produce and Write templates start with `<div class="ll-card">` and an `overline` line; the Styling tab starts with `/* Studio styles for the managed note types`. Pronounce is unchanged. |

Leave the app running; parts C to J use it.

## C. One Capture, two Items, four Cards each (DW1, DW2, DW5)

| Step | Do | Expect |
| --- | --- | --- |
| C1 | On the iPhone, with Tailscale connected, open `https://<tailnet>/captures` and save the Capture `jump to conclusions`. Tap it. | Capture detail with the Make an Item pane: Text ("Use as is" / "Custom value"), Language, Category, "Generation context · optional · used once, never saved", "Generate Draft" and "Write it myself". |
| C2 | Keep "Use as is", choose English and Vocabulary, type the Generation context `zebrafinch`, tap "Generate Draft". | "Writing your Draft…", then the Draft editor with "Draft — not saved yet" and `jump to conclusions` as Target. Russian meaning, Example and Example in Russian are filled; Mnemonic is empty. |
| C3 | Tap "Clear" on Example. Tap "Save to Anki". | Example and Example in Russian are both empty before Save. After Save, back on the same Capture with "Saved “jump to conclusions” to Anki. Make another Item from this Capture, or delete it." |
| C4 | `ac findNotes "$VQ"`, set `VNID` to the largest id, then `ac notesInfo "{\"notes\":[$VNID]}"` | One more id than B3. Target `jump to conclusions`; Example empty; Mnemonic empty; ItemId a lowercase UUID; SchemaVersion `1`. Paste the reply. |
| C5 | `ac findNotes '{"query":"\"deck:LanguageLabDev\" zebrafinch"}'`, and read the app's terminal lines for C2. | `{"result": [], "error": null}`: the Generation context is in no note. No log line holds `zebrafinch` (DW5). |
| C6 | On the same Capture: "Custom value" `Ne tirons pas de conclusions hâtives.`, French, Sentence, "Write it myself". Fill Russian meaning `Не будем делать поспешных выводов.`, Alternatives `Не будем спешить с выводами.`, Hint `polite, spoken`, Note `hâtif means hasty`, and save. | Back on the same Capture with the "Saved …" banner. |
| C7 | `ac findNotes "$SQ"`, set `SNID` to the largest id. | One more id than B3. |
| C8 | For each note: `ac findCards "{\"query\":\"nid:$VNID\"}"`, then `ac cardsInfo '{"cards":[<the four ids>]}' \| tr ',' '\n' \| grep -E '"(ord\|deckName\|queue\|reps\|due)"'`. The same with `$SNID`. | Exactly four cards each. Vocabulary: ord 0 `LanguageLabDev::Study::English::Vocabulary::Understand`, 1 `…::Produce`, 2 `…::Write`, 3 `LanguageLabDev::Pronunciation::English::Vocabulary`. Sentence: the same under `French::Sentences`. All `queue` 0 (new), `reps` 0. |
| C9 | In Anki Desktop, study `LanguageLabDev::Study::English::Vocabulary::Understand` and answer the one card "Good". Repeat C8 for `$VNID`. | Only the ord 0 card changed (`reps` 1, a new `queue`/`due`); ords 1 to 3 are as in C8: independent schedules (DW1). |

## D. The duplicate sheet (DW3)

| Step | Do | Expect |
| --- | --- | --- |
| D1 | On the iPhone, on the same Capture: "Use as is", English, Vocabulary, "Write it myself". Fill Russian meaning `торопиться` and tap "Save to Anki". | A sheet at the bottom: "Possible duplicate · English · Vocabulary", "You already have an Item with this text", one match `jump to conclusions` with its Russian meaning, "Nothing has been saved yet. You can still create a second Item.", "Open existing", "Cancel", "Create anyway". |
| D2 | Tap "Cancel". | The sheet closes; the Draft editor keeps `торопиться`. `ac findNotes "$VQ"` lists the same ids as C4. |
| D3 | Tap "Save to Anki" again, then "Open existing". | The alert "Discard unsaved changes?", "This Draft isn't saved." Tap "Discard": the Item detail at `/en/items/<ItemId>`, view-only, with the C4 values (Russian meaning, Alternatives, Part of speech, …). |
| D4 | `curl -s "$APP/api/items/fr/duplicates?category=vocabulary&target=jump%20to%20conclusions"`, the same with `en` and `category=sentence`, then with `en` and `category=vocabulary`. | `{"matches":[]}` twice: the other Language or Category is not shown. The last lists one match with the C4 ItemId. |

## E. A retried Save updates (DW5)

| Step | Do | Expect |
| --- | --- | --- |
| E1 | `ITEM=$(curl -s "$APP/api/items/en/duplicates?category=vocabulary&target=jump%20to%20conclusions" \| sed -e 's/^{"matches":\[\(.*\)\]}$/\1/' -e 's/}$/,"audio":"keep"}/'); echo "$ITEM"` | One JSON object: the C4 `itemId`, `"category":"vocabulary"`, the fields, and `"audio":"keep"` last. |
| E2 | `curl -s -i -X POST $APP/api/items/en -H "Origin: $APP" --form-string "item=$ITEM"` | `HTTP/1.1 200` and `{"itemId":"<the C4 ItemId>"}`. |
| E3 | `ac findNotes "$VQ"`; repeat C8 for `$VNID`. | The same ids as C4: no second note. The same four cards, decks and C9 schedule. |

## F. A test clip on every Card face (DW4)

| Step | Do | Expect |
| --- | --- | --- |
| F1 | `CLIP="$TMPDIR/LanguageLabDev_acceptance.m4a"; say -o "$CLIP" --file-format=m4af --data-format=aac "jump to conclusions"; ac storeMediaFile "{\"filename\":\"LanguageLabDev_acceptance.m4a\",\"data\":\"$(base64 -i "$CLIP")\"}"` | `{"result": "LanguageLabDev_acceptance.m4a", "error": null}` |
| F2 | Set the Audio and fill every optional field, so each face has something to show: `ac updateNoteFields "{\"note\":{\"id\":$VNID,\"fields\":{\"Audio\":\"[sound:LanguageLabDev_acceptance.m4a]\",\"RussianAlternatives\":\"спешить с выводами\",\"Hint\":\"idiom\",\"PartOfSpeech\":\"verb phrase\",\"Grammar\":\"jump to a conclusion\",\"Example\":\"Don't jump to conclusions.\",\"ExampleRussian\":\"Не делай поспешных выводов.\",\"Mnemonic\":\"a leap over the facts\"}}}"` | Paste. Docs say `{"result": null, "error": null}` (part J). |
| F3 | In Anki Desktop, Browse, search `"note:LanguageLabDev English Vocabulary"`, select the note, and Preview each card, front then back. | Studio look: a white card with rounded corners on a warm background, an overline (Understand / Produce / Write). Understand front: Target and one audio player; its back adds Russian meaning (bold), Alternatives, Hint, Part of speech and Grammar as chips, Example over Example in Russian in a grey panel, Mnemonic under its "Mnemonic" label, and no second player. Produce and Write fronts: Russian meaning and Hint, no player (Write adds the type box). Their backs: Target (Write: the typed comparison) and one player. No IPA. Pronounce as before. |
| F4 | Empty the Example only: `ac updateNoteFields "{\"note\":{\"id\":$VNID,\"fields\":{\"Example\":\"\"}}}"`. Preview the Understand, Produce and Write backs again. | The grey panel still shows, holding only `Не делай поспешных выводов.`; everything else as F3. |
| F5 | The same as F3 for `"note:LanguageLabDev French Sentence"`. | The same layout. Produce and Write fronts: Russian meaning and the Hint `polite, spoken`. Backs: Alternatives `Не будем спешить с выводами.` and `hâtif means hasty` under its "Note" label (Understand back: also the Hint). No audio player on any face (empty Audio). |
| F6 | Turn on night mode in Anki Desktop (Preferences › Appearance) and look at one front and one back. | Text stays readable. Turn it back if you like. |
| F7 | Sync Anki Desktop, then sync AnkiMobile on the iPhone. Browse to the two notes in AnkiMobile and look at each card's front and back; play the clip. | As F3 to F5; the clip plays where F3 shows a player. AnkiMobile may play it on its own as the face opens. |

## G. Unsaved Draft on iOS: swipe back and return from background (R-03)

Do G1 to G6 on the iPhone, then again on the iPad.

| Step | Do | Expect |
| --- | --- | --- |
| G1 | Open the `jump to conclusions` Capture, choose English and Sentence, tap "Write it myself". | The Draft editor, at an address ending `/new`. |
| G2 | Swipe right from the left edge of the screen. | "Discard unsaved changes?" with "This Draft isn't saved.", "Discard" and "Keep editing". The address still ends `/new`. |
| G3 | Tap "Keep editing". | The alert closes; the Draft editor is still there. |
| G4 | Type `rester` in Russian meaning. Switch to another app for at least a minute, then return to Safari. | Still the Draft editor with `rester`, no reload. |
| G5 | Swipe back again. | The alert again. Tap "Discard": the Capture detail, no Draft. |
| G6 | `ac findNotes "$VQ"` and `ac findNotes "$ESQ"` | `$VQ`: the same ids as E3. `$ESQ`: the same ids as B3. No note made by G1 to G5. |

If Safari reloads in G4 (a blank flash, the Draft gone), record a fail with what you saw.

## H. A Hint edited with blank lines (`decode_field`)

| Step | Do | Expect |
| --- | --- | --- |
| H1 | In Anki Desktop, Browse, the French Sentence note: replace the Hint with `line one`, press Enter twice, type `line two`. Close the editor. | Saved. |
| H2 | `ac notesInfo "{\"notes\":[$SNID]}"` | Paste the Hint value exactly (for example `line one<div><br></div><div>line two</div>`). |
| H3 | `curl -s "$APP/api/items/fr/<the Sentence ItemId from H2>"` | Paste the `hint` value. One blank line between the two lines (`line one\n\nline two`) is what the deferred entry asks for; three newlines is the open question. |

## I. Setup preview timing with real cards (`read_leftovers`)

| Step | Do | Expect |
| --- | --- | --- |
| I1 | `ac findCards '{"query":"deck:LanguageLabDev"}' \| tr ',' '\n' \| grep -c '[0-9]'` | The number of cards under the Prefix (at least 9). |
| I2 | Three times: `time curl -s -o /dev/null -w '%{http_code}\n' $APP/api/setup/plan` | `200` each, and the `real` times; paste them. Far under the 15 s Anki lock wait. |

## J. Record the real `changeDeck`, `updateNoteFields` and `cardsInfo` replies

The tests' fake Anki answers these from AnkiConnect's docs. Paste each request and reply exactly;
they become `tests/fixtures/anki/` exchanges.

| Step | Do | Expect |
| --- | --- | --- |
| J1 | `ac findCards "{\"query\":\"nid:$VNID\"}"`, set `UCID` to the ord 0 card from C8, then `ac changeDeck "{\"cards\":[$UCID],\"deck\":\"LanguageLabDev::Study::English::Vocabulary::Understand\"}"` (the deck it is already in) | Paste. Docs say `{"result": null, "error": null}`. |
| J2 | The F2 reply. | Pasted at F2. |
| J3 | `ac cardsInfo "{\"cards\":[$UCID]}"` | Paste the whole reply (it holds only `LanguageLabDev` names and the acceptance text). |

Everything this run made is in the dev Prefix; leave it or delete it as you like.

## CI evidence

These tests back each Done-when on every CI run, against the fake Anki, the fake OpenRouter and
the recorded fixtures. Until part J's replies are recorded, the fake's `changeDeck`,
`updateNoteFields` and `cardsInfo` replies are hand-built from AnkiConnect's docs.

| Done-when | Entry | Test |
| --- | --- | --- |
| 1: one note, four Cards in their decks | 1 | `tests/integration/test_anki_item_save.py::test_a_new_item_id_makes_one_note_with_four_cards_in_their_decks`, `tests/unit/test_anki_manifest.py::test_card_ord_maps_to_its_exercise_and_deck` |
| 1: Vocabulary and Sentence from one Capture, back to it | 1 | `tests/e2e/test_make_an_item.py::test_a_vocabulary_and_a_sentence_item_are_saved_from_one_capture` |
| 1: independent schedules (no burying) | epic-anki-setup-sync | `tests/unit/test_anki_manifest.py::test_preset_turns_off_the_three_bury_flags_on_every_study_and_pronunciation_deck` |
| 2: strict schema, one retry, then `llm_invalid_output` | 2 | `tests/integration/test_openrouter_llm.py::test_an_invalid_reply_is_retried_once_then_llm_invalid_output`, `::test_a_valid_retry_is_the_generated_draft`, `tests/unit/test_draft_generation_domain.py::test_strict_json_schema_follows_the_strict_rules` |
| 2: removable example, never a mnemonic | 2 | `tests/unit/test_draft_generation_domain.py::test_each_category_generates_its_item_fields_less_target_and_mnemonic`, `tests/e2e/test_generate_draft.py::test_clear_removes_the_example_before_save` |
| 2: model order through `.env` alone | 2 | `tests/unit/test_settings_load.py::test_openrouter_models_parse_in_order`, `tests/integration/test_openrouter_llm.py::test_generate_asks_openrouter_with_the_configured_models_and_a_strict_schema` |
| 3: duplicate sheet, Open existing, Cancel, Create anyway | 3 | `tests/e2e/test_duplicate_warning.py::test_a_match_opens_the_duplicate_sheet_and_nothing_is_saved`, `::test_cancel_keeps_the_draft_and_an_edited_target_is_checked_again`, `::test_open_existing_asks_about_the_draft_then_opens_the_match`, `::test_create_anyway_saves_the_draft_and_returns_to_the_capture`, `tests/e2e/test_item_detail.py::test_item_detail_shows_the_items_values_view_only` |
| 3: other Language or Category not shown | 3 | `tests/api/test_items_read.py::test_a_target_that_differs_or_another_language_or_category_is_no_match` |
| 4: fronts, backs, hints and audio placement | 4 | `tests/unit/test_anki_manifest.py::test_card_templates_and_css_come_from_template_files_and_render_only_shown_fields`, `::test_study_templates_place_russian_and_audio_per_fr21_and_css_uses_the_studio_tokens` |
| 4: Setup repairs templates from v0.5.0 | 4 | `tests/integration/test_anki_setup_preview.py::test_preview_diffs_the_manifest_into_create_repair_and_migrate_items[v0.5.0-templates]` |
| 5: Generation context never persisted | 2 | `tests/api/test_drafts_generate.py::test_the_generation_context_reaches_the_model_and_nothing_else`, `tests/e2e/test_generate_draft.py::test_the_generation_context_stays_in_the_screens_memory`, `::test_the_generation_context_is_used_once` |
| 5: a retried Save updates | 1 | `tests/integration/test_anki_item_save.py::test_a_retried_save_with_the_same_item_id_updates_that_note`, `tests/api/test_items_save.py::test_a_retried_save_with_the_same_item_id_replaces_the_content`, `tests/e2e/test_make_an_item.py::test_a_failed_save_keeps_the_draft_and_a_retry_sends_the_same_item_id` |
| R-03: leaving the Draft asks first | 1 | `tests/e2e/test_make_an_item.py::test_leaving_the_draft_editor_raises_the_unsaved_draft_alert` (browser back in WebKit, not a real iOS swipe) |

Run on 2026-10-23 at the story's baseline plus its changes:
`uv run pytest -q tests/integration/test_anki_item_save.py tests/integration/test_openrouter_llm.py tests/integration/test_anki_setup_preview.py tests/unit/test_anki_manifest.py tests/unit/test_draft_generation_domain.py tests/unit/test_settings_load.py tests/api/test_items_read.py tests/api/test_items_save.py tests/api/test_drafts_generate.py tests/e2e/test_make_an_item.py tests/e2e/test_generate_draft.py tests/e2e/test_duplicate_warning.py tests/e2e/test_item_detail.py`
gave `237 passed`.

## Results

A step marked "not run" has no recorded result. It is not a pass.

| Step | Result | Notes |
| --- | --- | --- |
| A1 release `v0.6.0` | not run | Waiting for the user's run. |
| A2 no `LANGUAGE_LAB_DEV` | not run | Waiting for the user's run. |
| A3 Tailscale Serve to 8787 | not run | Waiting for the user's run. |
| B1 starts, tailnet line, Sync ok | not run | Waiting for the user's run. |
| B2 health `0.6.0` | not run | Waiting for the user's run. |
| B3 Item notes before | not run | Waiting for the user's run. |
| B4 five templates Repair rows | not run | Waiting for the user's run. |
| B5 Apply setup verified | not run | Waiting for the user's run. |
| B6 Nothing to change | not run | Waiting for the user's run. |
| B7 new templates in Anki | not run | Waiting for the user's run. |
| C1 Make an Item pane | not run | Waiting for the user's run. |
| C2 Generate Draft, no Mnemonic | not run | Waiting for the user's run. |
| C3 Example cleared, saved | not run | Waiting for the user's run. |
| C4 Vocabulary note | not run | Waiting for the user's run. |
| C5 Generation context absent | not run | Waiting for the user's run. |
| C6 French Sentence saved | not run | Waiting for the user's run. |
| C7 Sentence note | not run | Waiting for the user's run. |
| C8 four cards each in their decks | not run | Waiting for the user's run. |
| C9 independent schedules | not run | Waiting for the user's run. |
| D1 duplicate sheet | not run | Waiting for the user's run. |
| D2 Cancel keeps the Draft | not run | Waiting for the user's run. |
| D3 Open existing → Item detail | not run | Waiting for the user's run. |
| D4 other Language or Category not shown | not run | Waiting for the user's run. |
| E1 the stored Item as a Save | not run | Waiting for the user's run. |
| E2 retried Save `200` | not run | Waiting for the user's run. |
| E3 no second note | not run | Waiting for the user's run. |
| F1 clip stored | not run | Waiting for the user's run. |
| F2 Audio and optional fields set | not run | Waiting for the user's run. |
| F3 Vocabulary faces in Desktop | not run | Waiting for the user's run. |
| F4 Example in Russian alone in the panel | not run | Waiting for the user's run. |
| F5 Sentence faces, no player | not run | Waiting for the user's run. |
| F6 night mode readable | not run | Waiting for the user's run. |
| F7 AnkiMobile after Sync | not run | Waiting for the user's run. |
| G1–G6 iPhone | not run | Waiting for the user's run. |
| G1–G6 iPad | not run | Waiting for the user's run. |
| H1 Hint with blank lines | not run | Waiting for the user's run. |
| H2 `notesInfo` Hint value | not run | Waiting for the user's run. |
| H3 Item read Hint value | not run | Waiting for the user's run. |
| I1 cards under the Prefix | not run | Waiting for the user's run. |
| I2 `/api/setup/plan` timings | not run | Waiting for the user's run. |
| J1 `changeDeck` reply | not run | Waiting for the user's run. |
| J2 `updateNoteFields` reply | not run | Waiting for the user's run. |
| J3 `cardsInfo` reply | not run | Waiting for the user's run. |
| DW2 one retry then `llm_invalid_output`; model order through `.env` | CI only | No device step: proved in CI by `tests/integration/test_openrouter_llm.py::test_an_invalid_reply_is_retried_once_then_llm_invalid_output`, `::test_a_valid_retry_is_the_generated_draft`, `::test_generate_asks_openrouter_with_the_configured_models_and_a_strict_schema` and `tests/unit/test_settings_load.py::test_openrouter_models_parse_in_order` (see [CI evidence](#ci-evidence)). C2–C4 cover the rest of DW2 on the device. |

**Deferred outcomes** (filled in after the run):

- R-03 on the Draft editor (`deferred-work.md`, story 1.10 entry): _pending G1–G6._
- `decode_field` and blank lines (story 2.4 entry): _pending H2–H3._
- `read_leftovers` cost (stories 2.11 and 2.13 entries): _pending I1–I2._
- Hand-built `changeDeck`, `updateNoteFields`, `cardsInfo` replies (`tests/support/anki_state.py`, `tests/integration/test_anki_item_save.py`): _pending J1–J3._

## Findings

| # | Step | What happened | Disposition |
| --- | --- | --- | --- |

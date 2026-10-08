# LanguageLab Specification

Status: approved product design; implementation has not started.

## Purpose

LanguageLab is a personal language-learning web application that uses Anki as its only persistent learning store. It streamlines capture and note creation, generates four independently scheduled exercises for every learning item, and adds pronunciation reviews backed by Anki scheduling.

The first milestones are:

- English: progress from B2 toward C1.
- French: reach A1.

The long-term target for both languages is C2, but advanced exercise design is outside the initial scope. Russian remains the translation language for the initial version.

Target pronunciation locales are `en-US` and `fr-CA`.

## Product boundaries

LanguageLab is a single-user, online-only application. It has:

- no user accounts;
- no application database;
- no offline mode or PWA requirement;
- no native mobile application;
- no analytics, goals, streaks, or pronunciation history;
- no study-capacity or backlog management;
- no migration of existing Anki notes;
- no OCR, URL, browser-selection, image, or audio capture;
- no automatic pronunciation rating;
- no exact reproduction of Anki's native card queue.

Anki is authoritative for captures, approved learning content, cards, media references, review history, and scheduling. LanguageLab owns only runtime state and configuration outside Anki.

## Runtime architecture

### Backend

- Python with FastAPI.
- Packaged as a versioned Python wheel with the `language-lab` console entry point.
- Run manually in a terminal on the Mac Mini:

  ```bash
  uvx --from /path/to/language_lab-1.2.3-py3-none-any.whl language-lab
  ```

- No Docker or `launchd` service.
- The terminal process remains attached for the lifetime of the application.
- Operational logs go to stdout/stderr only.
- Logs include operational errors and request IDs, but exclude captured text, generated content, API payloads, and audio.

### Frontend

- Responsive HTML and CSS with vanilla JavaScript.
- Served by FastAPI from assets packaged in the wheel.
- No frontend framework or Node runtime is required on the Mac Mini.
- Browser local storage persists only the last selected Azure voice for each locale.

### Network access

- AnkiConnect remains on its default localhost endpoint, `127.0.0.1:8765`.
- LanguageLab binds to localhost on a different configurable port; the default is `127.0.0.1:8787`.
- Tailscale Serve exposes LanguageLab through a private HTTPS tailnet URL for Safari and desktop browsers.
- Neither LanguageLab nor AnkiConnect binds directly to the LAN or public network.
- The setup documentation provides the one-time Tailscale Serve command.
- Startup prints the local URL and, when discoverable, the private Tailscale URL.
- The user opens the browser manually.

Tailscale HTTPS is required because mobile browser microphone capture requires a secure context. The application is available only while the Mac Mini, terminal process, Anki Desktop, Tailscale, and internet connection are available.

## Configuration

Runtime configuration lives outside the disposable `uvx` environment:

```text
~/.config/language-lab/.env
```

The repository includes a documented `.env.example`. It covers at least:

```dotenv
LANGUAGE_LAB_HOST=127.0.0.1
LANGUAGE_LAB_PORT=8787
ANKI_CONNECT_URL=http://127.0.0.1:8765
ANKI_PREFIX=LanguageLab

AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=

OPENROUTER_API_KEY=
OPENROUTER_MODELS=openai/gpt-5.6-luna,google/gemini-3.5-flash-lite,anthropic/claude-sonnet-4.6
```

The OpenRouter model IDs are examples, not permanent recommendations. Every configured model must support strict JSON Schema output and should be evaluated with representative English/French/Russian fixtures.

AnkiConnect remains keyless and localhost-only. Browser code never calls AnkiConnect directly; every call goes through the local Python backend. The setup documentation notes that any local process can control a keyless AnkiConnect instance.

## Navigation

The application exposes these primary areas:

```text
Captures
English
  Items
  Pronunciation
French
  Items
  Pronunciation
Setup
```

Captures and Setup are shared. Item management and pronunciation review have separate English and French tabs.

## Anki ownership boundary

LanguageLab may create, update, repair, and delete resources only under the configured prefix, which defaults to `LanguageLab`. There are no pre-existing user notes inside that boundary.

The application owns:

- managed deck structure;
- managed note types and fields;
- card templates and CSS;
- card-to-deck mappings;
- schema-version migrations;
- managed media files.

The user may edit managed note field values in either Anki or LanguageLab, but does not manually edit managed schemas or templates.

LanguageLab reads the current Anki value when opening an item. Saves use last-write-wins semantics; race-conflict detection is not required.

## Anki structure

### Note types

LanguageLab creates five managed note types:

1. `LanguageLab Capture`
2. `LanguageLab English Vocabulary`
3. `LanguageLab English Sentence`
4. `LanguageLab French Vocabulary`
5. `LanguageLab French Sentence`

Vocabulary includes individual words and multiword phrases. Sentences use a separate note type.

### Capture fields

- `Text`
- `CreatedAt`
- hidden `SchemaVersion`

A capture generates a card in the Captures deck. The card is immediately suspended and never enters study.

### Vocabulary fields

- hidden stable `ItemId`
- `Target`
- `Russian`, containing one primary contextual meaning and optional short alternatives
- optional `Hint`
- optional `PartOfSpeech`
- optional `Grammar`
- optional `Example`
- optional `ExampleRussian`
- optional user-written `Mnemonic`
- `Audio`
- hidden `SchemaVersion`

Phrases may leave word-specific fields such as `PartOfSpeech` empty.

### Sentence fields

- hidden stable `ItemId`
- `Target`
- `Russian`, containing one primary contextual meaning and optional short alternatives
- optional `Hint`
- optional `Note`
- `Audio`
- hidden `SchemaVersion`

No note type contains IPA or Azure voice metadata.

### Decks

The managed hierarchy separates ordinary Anki study from app-only pronunciation cards:

```text
LanguageLab
├── Captures
├── Study
│   ├── English
│   │   ├── Vocabulary
│   │   │   ├── Understand
│   │   │   ├── Produce
│   │   │   └── Write
│   │   └── Sentences
│   │       ├── Understand
│   │       ├── Produce
│   │       └── Write
│   └── French
│       ├── Vocabulary
│       │   ├── Understand
│       │   ├── Produce
│       │   └── Write
│       └── Sentences
│           ├── Understand
│           ├── Produce
│           └── Write
└── Pronunciation
    ├── English
    │   ├── Vocabulary
    │   └── Sentences
    └── French
        ├── Vocabulary
        └── Sentences
```

The configured prefix replaces `LanguageLab` when customized.

Sibling burying is disabled for managed Study decks so cards created from the same note can progress independently. Other scheduling options and daily limits remain user-controlled.

## Exercise model

Every approved Vocabulary or Sentence note immediately generates all four cards. Exercises cannot be disabled per item.

| Exercise | Front | Expected action | Review surface |
| --- | --- | --- | --- |
| Understand | Target-language text; optional audio button | Recall Russian meaning | Anki |
| Produce | Primary Russian meaning and optional hint | Recall the target-language text | Anki |
| Write | Primary Russian meaning and optional hint | Type the target-language text | Anki |
| Pronounce | Visible target-language text; optional audio button | Speak the text | LanguageLab |

The back of an Anki card shows the correct target text and Russian meaning, applicable grammar, optional example, optional mnemonic, and reference audio according to these rules:

- Understand may offer audio on the front.
- Produce reveals audio only after the answer.
- Write reveals audio only after submission or answer reveal.
- Pronounce permits reference audio before the first attempt and before every retry.

Typing comparison is advisory. The user still selects Anki's Again/Hard/Good/Easy rating.

Each exercise is a distinct Anki card with an independent schedule. Ordinary Anki clients own Understand, Produce, and Write reviews. LanguageLab exclusively owns Pronounce reviews.

## Capture workflow

Capture input is text only.

1. The user creates and saves a capture.
2. LanguageLab writes a Capture note to Anki and suspends its card.
3. The user opens the capture.
4. The user chooses either **Use as is** or supplies a custom value.
5. The user selects English or French and Vocabulary or Sentence.
6. The selected/custom value must already be in the target language.
7. The user may provide transient generation context, such as a source sentence or intended meaning.
8. LanguageLab generates an editable draft.
9. The user presses Save to create the managed note, four cards, and approved media.
10. LanguageLab returns to the same capture.
11. The user may create another item from it or permanently delete it.

Generation context is not saved unless the user copies it into a persisted field such as Hint or Example.

## Duplicate handling

Before creating an item, LanguageLab normalizes case and surrounding punctuation and searches for matching target text within the same language and note category.

When matches exist, the user can:

- open an existing item;
- cancel creation;
- create the new item anyway.

Creation is never blocked absolutely because identical spelling may represent a different meaning.

## Draft generation with OpenRouter

LanguageLab uses OpenRouter's Chat Completions API with:

- an ordered model list from `OPENROUTER_MODELS`;
- strict JSON Schema structured output;
- `provider.require_parameters=true`;
- local Pydantic validation;
- OpenRouter's default privacy and provider-routing behavior.

Vocabulary and Sentence use separate response schemas.

Generation produces:

- one contextually relevant primary Russian meaning;
- a short list of relevant alternatives when useful;
- applicable grammatical metadata;
- one Vocabulary example and Russian example translation by default.

It does not produce dictionary dumps or mnemonics. Vocabulary drafts provide a Clear button for the generated example.

If local schema validation fails, LanguageLab retries generation once. A second failure displays an error and leaves Anki unchanged. A schema-valid result remains a draft: the user may edit it, and nothing is persisted until Save.

## Content editing and regeneration

The Items tabs support search, open, edit, regenerate, and delete.

All content mutations use a preview-and-save boundary:

- New items remain drafts until Save.
- Manual edits remain local to the form until Save.
- Regenerated translations, examples, notes, or audio appear beside the current value.
- The current Anki value remains unchanged until Save.
- Saving audio writes the exact previewed bytes to Anki media.
- Superseded managed audio is removed only after the new note value has been saved successfully.

Deletion is permanent. LanguageLab shows an explicit confirmation naming the item and affected cards. Confirmation deletes the Anki note, all generated cards, their review histories, and managed audio. There is no archive or application trash.

## Azure reference audio

The backend obtains the current Azure voice catalog and filters it by the item's locale:

- `en-US` for English;
- `fr-CA` for French.

The UI displays the available voices. Preview synthesizes temporary audio through the backend so Azure credentials never reach the browser. Save stores the previewed MP3 in Anki media and updates the note's `Audio` field.

The last selected voice is stored separately for each locale in that browser's local storage. It is not stored in Anki. Changing the browser's default voice does not regenerate existing audio; regeneration is an explicit preview-and-save operation.

## Pronunciation review

Azure Pronunciation Assessment is the only pronunciation provider in the initial version.

### Review flow

1. LanguageLab fetches a new or due Pronunciation card from the selected language branch.
2. It displays the target text.
3. The user may play reference audio before recording.
4. The browser records one attempt and sends it to the backend.
5. The backend normalizes the browser recording into an Azure-supported audio format and submits a scripted assessment with the target as reference text.
6. The UI displays Azure's available feedback.
7. The user may replay reference audio and retry without limit.
8. The user clicks Again, Hard, Good, or Easy.
9. The rating is immediately submitted through AnkiConnect to Anki's scheduler.
10. After successful scheduling, LanguageLab fetches the next card.

The rating button itself is the explicit commit action; it does not require a separate Save button.

### Feedback limits

For `en-US`, show Azure's available overall, word, phoneme, and supported prosody feedback.

For `fr-CA`, show only the overall, word, and phoneme-position feedback Azure actually provides. The UI must not claim to identify a named incorrect French sound. The initial version uses no Speechace, SPPAS, custom phonemizer, or IPA overlay.

Azure scores never choose an Anki rating. The user always decides the rating.

### Ephemeral data

Recordings, Azure responses, attempts, and scores exist only for the active review interaction. After a rating succeeds or the user abandons the review, they are discarded. LanguageLab stores no pronunciation history.

## Scheduling and synchronization

LanguageLab uses AnkiConnect scheduler operations rather than implementing FSRS or legacy Anki scheduling.

The pronunciation queue is intentionally simple:

- include new and due Pronunciation cards;
- use application-defined simple ordering;
- do not reproduce Anki's exact daily limits, sibling behavior, or native ordering.

The scheduler transition and resulting interval remain authoritative because the selected rating is submitted to Anki itself.

Synchronization runs:

- at LanguageLab startup;
- every five minutes while the process is running;
- before a pronunciation session;
- after a pronunciation session;
- during graceful shutdown.

Sync failures are written to the terminal and retried at the next opportunity. They do not block normal work. If Anki Desktop or AnkiConnect is unavailable, Anki-backed actions show a visible error.

No synchronization occurs while the terminal process is stopped.

## Setup and repair

The user manually installs and runs Anki Desktop and AnkiConnect. LanguageLab's Setup area then:

1. Checks AnkiConnect availability.
2. Checks Azure and OpenRouter configuration.
3. Shows the configured Anki prefix.
4. Previews the decks, note types, fields, templates, CSS, and options it will create or repair.
5. Applies setup only after Save/confirmation.
6. Verifies that the expected managed structure exists afterward.

Setup and repair operations are idempotent. Structural migrations are schema-versioned and remain inside the configured prefix.

## Failure semantics

- OpenRouter failure leaves the draft/capture unchanged and displays an error.
- Azure TTS failure leaves the current audio unchanged and displays an error.
- Azure pronunciation failure leaves the Anki card unanswered and allows retry or exit.
- AnkiConnect failure blocks the requested Anki-backed action and displays an error.
- Anki sync failure is non-blocking and is retried later.
- Failed Save operations never delete or replace the prior Anki field or media value.

## Acceptance criteria

The initial version is complete when every criterion below passes.

1. A versioned wheel starts successfully on the Mac Mini through the documented `uvx --from ... language-lab` command and loads configuration from `~/.config/language-lab/.env`.
2. An iPhone, iPad, and desktop browser can reach LanguageLab over private Tailscale HTTPS and grant microphone permission.
3. Setup against an empty prefix creates the five note types and complete managed deck hierarchy, and a second setup run makes no unintended changes.
4. A text capture created from a remote browser is stored as a suspended Capture note in Anki.
5. One capture can create multiple approved learning items before the capture is deleted.
6. Saving one English or French Vocabulary/Sentence draft creates one note and exactly four cards in the correct decks.
7. All four cards have independent Anki schedules, and managed Study decks do not bury siblings.
8. Duplicate detection offers Open existing, Cancel, and Create anyway for normalized matches.
9. OpenRouter produces locally validated Vocabulary and Sentence drafts; malformed output cannot be saved accidentally.
10. Generated Vocabulary drafts include a removable example and never generate a mnemonic.
11. Editing through LanguageLab updates the existing Anki note without replacing its cards or review histories.
12. Editing a managed field directly in Anki is visible when the item is next opened in LanguageLab.
13. Audio preview does not change Anki; Save writes the exact previewed MP3, and regeneration preserves the old audio until Save succeeds.
14. The last selected `en-US` and `fr-CA` voices persist independently in browser local storage.
15. Understand, Produce, and Write cards display the agreed prompts, backs, hints, and audio placement in AnkiMobile and Anki Desktop.
16. Pronunciation review permits reference playback, recording, Azure feedback, and unlimited retries without changing Anki.
17. Clicking a pronunciation ease rating answers only that Pronunciation card through Anki's scheduler and loads the next card.
18. Azure output never automatically selects an ease rating or claims unsupported named French-sound diagnosis.
19. Recordings and assessment responses are absent after the active pronunciation interaction ends.
20. Startup, five-minute, pronunciation-session, and graceful-shutdown synchronization attempts occur while LanguageLab is running; failures remain non-blocking.
21. Permanent deletion removes the note, its four cards and review histories, and managed audio after explicit confirmation.
22. LanguageLab never creates, edits, or deletes Anki resources outside its configured prefix.

## External references

- [AnkiConnect API](https://git.sr.ht/~foosoft/anki-connect/tree/master/item/README.md)
- [Anki media](https://docs.ankiweb.net/media.html)
- [Anki deck options and scheduling](https://docs.ankiweb.net/deck-options.html)
- [Azure Pronunciation Assessment](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment)
- [Azure Speech language and voice support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)
- [Azure Text to Speech REST API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
- [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [OpenRouter model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks)
- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)
- [uv tool execution](https://docs.astral.sh/uv/concepts/tools/)

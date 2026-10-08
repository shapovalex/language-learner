---
title: LanguageLab PRD — Addendum
created: 2026-10-08
updated: 2026-10-08
---

# LanguageLab PRD: Addendum

These technical decisions are already approved in `spec-draft.md`. They are binding input for architecture but sit outside the PRD's capability narrative. FR and NFR references point to `prd-languagelab.md`.

## A1. Runtime Architecture

**Backend**
- Python with FastAPI.
- Packaged as a versioned Python wheel with a `language-lab` console entry point.
- Run manually in a terminal on the Mac Mini (FR-1):
  ```bash
  uvx --from /path/to/language_lab-1.2.3-py3-none-any.whl language-lab
  ```
- No Docker and no `launchd` service. The process stays attached to the terminal.
- Logs go to stdout/stderr only and contain operational errors and request IDs, never content (NFR-7, NFR-9).

**Frontend**
- Responsive HTML/CSS with vanilla JavaScript, served by FastAPI from assets packaged inside the wheel.
- No frontend framework and no Node runtime on the Mac Mini (NFR-11).
- Browser local storage holds only the last selected Azure Voice per locale (FR-29).

**Network** (FR-2, NFR-5)
- AnkiConnect runs on its default `127.0.0.1:8765`.
- LanguageLab binds to localhost on a configurable port, default `127.0.0.1:8787`.
- Tailscale Serve exposes LanguageLab at a private HTTPS tailnet URL.
- Rationale: mobile browser microphone capture requires a secure context, so HTTPS through Tailscale is mandatory.
- Startup prints the local URL and the Tailscale URL when it can be discovered.

## A2. Configuration

Location: `~/.config/language-lab/.env`, outside the disposable `uvx` environment. The repo ships a documented `.env.example` with at least these keys:

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

- The model IDs are examples, not permanent recommendations. Every configured model must support strict JSON Schema output. Before a model is configured, it should be evaluated with representative English/French/Russian fixtures, as documented (FR-4).
- AnkiConnect stays keyless and localhost-only. The browser never calls it directly (NFR-6). Setup docs note that any local process can control a keyless AnkiConnect (FR-4).

## A3. Anki Data Model

### Note types (FR-6)

1. `LanguageLab Capture`
2. `LanguageLab English Vocabulary`
3. `LanguageLab English Sentence`
4. `LanguageLab French Vocabulary`
5. `LanguageLab French Sentence`

Vocabulary covers single words and multiword phrases. Sentences have their own note type. The configured Prefix (`ANKI_PREFIX`) replaces `LanguageLab` everywhere.

### Fields

**Capture**
- `Text`
- `CreatedAt`
- hidden `SchemaVersion`

A Capture generates one card in the Captures deck. The card is suspended immediately and never enters study (FR-9).

**Vocabulary**
- hidden stable `ItemId`
- `Target`
- `Russian`: one primary contextual meaning plus optional short alternatives
- optional `Hint`
- optional `PartOfSpeech`: may be empty for phrases
- optional `Grammar`
- optional `Example`
- optional `ExampleRussian`
- optional user-written `Mnemonic`: never generated
- optional `Audio`
- hidden `SchemaVersion`

**Sentence**
- hidden stable `ItemId`
- `Target`
- `Russian`: one primary contextual meaning plus optional short alternatives
- optional `Hint`
- optional `Note`
- optional `Audio`
- hidden `SchemaVersion`

No note type contains IPA or Azure Voice metadata.

### Ownership

LanguageLab owns the deck structure, note types and fields, card templates and CSS, card-to-deck mappings, schema-version migrations and managed media. The user may edit field values in Anki or LanguageLab but does not edit schemas or templates by hand. Concurrent edits are resolved last-write-wins (FR-23).

### Deck hierarchy

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

- Sibling burying is disabled for managed Study decks. Other options and daily limits are left to the user (FR-8).
- Pronounce Cards sit in a separate branch so that studying `<Prefix>::Study` in Anki clients excludes them, while Anki still schedules them. This is a user convention, not an enforced limit: studying the `<Prefix>` root would surface them (FR-4).

## A4. Draft Generation: OpenRouter

- OpenRouter Chat Completions API.
- Ordered model list from `OPENROUTER_MODELS`, using OpenRouter model fallbacks (FR-17).
- Strict JSON Schema structured output, with `provider.require_parameters=true` so routing only reaches providers that honour the schema.
- Local Pydantic validation of every response. On failure, retry once, then show an error (FR-16).
- Separate response schemas for Vocabulary and Sentence (FR-14, FR-15).
- OpenRouter's default privacy and provider-routing behavior applies (NFR-8).

## A5. Azure Speech

**Text to speech** (FR-26 to FR-28)
- The backend fetches the current voice catalog and filters it by locale: `en-US` for English, `fr-CA` for French.
- Preview audio is synthesized through the backend and returned as MP3. Save writes those exact bytes to Anki media and updates `Audio`.
- Superseded managed audio is deleted only after the note update succeeds.

**Pronunciation Assessment** (FR-31 to FR-35)
- Scripted assessment, with the Target text as the reference text.
- The backend converts the browser recording into an Azure-supported audio format before submitting it.
- `en-US`: overall, word, phoneme and supported prosody feedback.
- `fr-CA`: overall, word and phoneme-position feedback only.
- No Speechace, SPPAS, custom phonemizer or IPA overlay in v1.

## A6. Scheduling and Sync via AnkiConnect

- Pronounce Ratings are submitted through AnkiConnect scheduler operations, so Anki's transition and resulting interval are authoritative. LanguageLab implements neither FSRS nor legacy scheduling.
- The pronunciation queue is assembled from new and due cards in the Pronunciation branch with simple app-defined ordering (FR-30).
- Sync is triggered through AnkiConnect at startup, every 5 minutes, before and after each Pronunciation session, and on graceful shutdown (FR-36).

## A7. External References

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

---
title: LanguageLab PRD
status: final
created: 2026-10-08
updated: 2026-10-08
---

# PRD: LanguageLab

## 0. Document Purpose

This PRD defines v1 of LanguageLab. Downstream BMad workflows (architecture, UX, epics/tickets) build on it. It restates the approved product design in `spec-draft.md` as grouped features with globally numbered FRs (FR-1…FR-N), cross-cutting NFRs, and a v1 acceptance gate. Vocabulary is anchored in the §3 Glossary. Inferred points that the user has since confirmed are listed in §11. Technical decisions that are settled but are not product capabilities (runtime stack, packaging, configuration keys, Anki note-type fields and deck tree, OpenRouter/Azure call parameters) live in `addendum.md`, which is binding input for architecture.

## 1. Vision

LanguageLab is a personal language-learning web app that keeps Anki as its only persistent learning store. It makes the slow parts of building a good deck fast. Text is captured from any device. Each capture becomes a reviewed, AI-drafted learning item, and every item automatically gets four independently scheduled exercises: understand, produce, write and pronounce.

Anki stays the source of truth for content, cards, media, review history and scheduling. LanguageLab adds what Anki lacks: assisted note creation, consistent card design, reference audio from Azure voices, and a pronunciation review loop. In that loop, Azure Assessment feedback informs the learner, who still chooses the Rating, and Anki's own scheduler applies it.

The first milestones are English from B2 toward C1 and French to A1, with Russian as the translation language. The long-term target for both languages is C2, but v1 deliberately does not include advanced exercise design for upper levels.

## 2. Target User

LanguageLab has exactly one user, its builder (Oleksii). They are a Russian-speaking learner who already uses Anki and studies on iPhone, iPad and desktop.

### 2.1 Jobs To Be Done

- **Functional:** Turn a word, phrase or sentence I meet into a high-quality Anki item quickly, without hand-writing translations, grammar notes and examples.
- **Functional:** Practice speaking every item I learn, get objective feedback on my pronunciation, and still have it scheduled by Anki's spaced repetition.
- **Contextual:** Capture on whichever device I'm holding, and process captures later when I have time.
- **Emotional:** Trust that my Anki collection, built up over years, is never damaged by a tool I'm experimenting with.

### 2.2 Non-Users (v1)

Other learners, multiple accounts, teachers and shared decks are out of scope. LanguageLab is not a general-purpose Anki front-end.

### 2.3 Key User Journeys

- **UJ-1. Oleksii captures a phrase on the go.** Oleksii reads an English article on an iPhone and meets "to hedge one's bets". They open the private LanguageLab URL in Safari, type the phrase into Captures and save. The Capture is now a suspended note in Anki and will never show up in study. **Edge case:** if Anki Desktop is closed on the Mac Mini, the save shows a visible error and nothing is lost silently.
- **UJ-2. Oleksii turns a capture into learning items.** At the desktop, Oleksii opens the Capture and chooses **Use as is** with English → Vocabulary. They paste the source sentence as generation context, and LanguageLab returns an editable Draft: the primary Russian meaning, short alternatives, grammar, and an example with its translation. Oleksii trims an alternative and adds a mnemonic. Next they open the English Voice list, preview two voices, keep one and press Save. Anki now holds one note with four cards. LanguageLab returns to the same Capture, where Oleksii creates a second Item (the sentence itself, as English → Sentence) and then deletes the Capture. **Edge case:** if a normalized match already exists, Oleksii is offered Open existing, Cancel or Create anyway.
- **UJ-3. Oleksii practices pronunciation on the iPad.** Oleksii opens French → Pronunciation. LanguageLab syncs and then shows the first new or due Pronounce card. Oleksii plays the Reference audio, records an Attempt and sees Azure's overall, word and phoneme-position feedback. They replay the reference, retry twice, then choose Good. Anki schedules the card and the next one loads. Leaving the tab triggers a Sync, and nothing from the Attempts is kept.
- **UJ-4. Oleksii studies the other three exercises in AnkiMobile.** On the commute, Oleksii reviews Understand, Produce and Write cards in AnkiMobile. These cards come from LanguageLab's managed decks and follow the agreed prompt/back/audio rules. Siblings from the same note are not buried, so each exercise progresses on its own schedule.
- **UJ-5. Oleksii fixes an item.** Oleksii notices a weak translation while reviewing in Anki and corrects it there. Later, they open the Item in LanguageLab and see the corrected value. They regenerate the example, compare it with the current one, also regenerate the audio with a different voice, and save. Cards and review history are preserved, and the old audio file is removed only after the save succeeds.
- **UJ-6. Oleksii sets up LanguageLab for the first time.** With Anki Desktop and AnkiConnect running, Oleksii starts LanguageLab from the terminal with the documented command and opens the printed Tailscale URL. Setup reports AnkiConnect, Azure and OpenRouter status and previews the decks, note types, templates and options it will create. Oleksii confirms, and setup verifies the result. Running setup again later changes nothing.

## 3. Glossary

- **Anki** — Anki Desktop on the Mac Mini, reached through AnkiConnect. It is the authoritative store for all learning data.
- **Prefix** — The configured top-level name (default `LanguageLab`) that bounds every resource LanguageLab manages in Anki.
- **Managed resource** — Any deck, note type, field, card template, CSS, deck option or media file under the Prefix that LanguageLab created. LanguageLab owns its structure. The user may edit managed field values, but not schemas or templates.
- **Language** — English (locale `en-US`) or French (locale `fr-CA`). In v1 the translation language is always Russian.
- **Category** — Vocabulary (single words and multiword phrases) or Sentence.
- **Capture** — A piece of raw text saved for later processing. It is stored as a Capture note whose card is permanently suspended. One Capture can produce zero or more Items.
- **Generation context** — Transient text, such as a source sentence or intended meaning, that guides Draft generation. It is never persisted.
- **Draft** — An unsaved, editable proposal for an Item's field values, produced by generation or edited by hand. Nothing in a Draft reaches Anki until Save.
- **Item** — A saved Vocabulary or Sentence note for one Language. It has exactly four Cards, one per Exercise.
- **Target text** — The Item's target-language word, phrase or sentence.
- **Russian meaning** — One primary contextual Russian meaning plus optional short alternatives.
- **Hint** — Optional short disambiguating text shown on the front of Produce and Write Cards.
- **Mnemonic** — Optional memory aid on Vocabulary Items. Only the user writes it; generation never fills it.
- **Note field** — The optional grammar/usage `Note` field on Sentence Items. Not to be confused with the Anki note that stores an Item.
- **Exercise** — One of four review types: **Understand**, **Produce**, **Write**, **Pronounce**.
- **Card** — The Anki card for one Exercise of one Item. Each Card has an independent schedule.
- **Study decks** — Managed decks under `<Prefix>::Study` holding Understand, Produce and Write Cards (the **Study Cards**). They are reviewed in ordinary Anki clients.
- **Pronunciation decks** — Managed decks under `<Prefix>::Pronunciation` holding Pronounce Cards. They are reviewed only in LanguageLab. This is a usage convention: the user studies `<Prefix>::Study` in Anki clients, never the `<Prefix>` root (see FR-4).
- **Reference audio** — The optional MP3 synthesized by an Azure voice for an Item's Target text and stored in Anki media. An Item may have none.
- **Voice** — An Azure neural voice available for the Item's locale.
- **Preview** — Temporary content (regenerated text or audio) shown next to the current value and not yet saved.
- **Save** — The explicit commit that writes a Draft or Preview to Anki.
- **Attempt** — One recording of the user speaking the Target text during a pronunciation review.
- **Assessment** — Azure Pronunciation Assessment feedback for one Attempt.
- **Rating** — Again, Hard, Good or Easy, chosen by the user and submitted to Anki's scheduler.
- **Pronunciation session** — A run of pronunciation reviews within one Language's Pronunciation tab. It starts when the user opens the tab and ends when they leave it or the queue is empty.
- **Sync** — An Anki synchronization with AnkiWeb, triggered by LanguageLab through AnkiConnect.
- **Setup** — The idempotent create/repair/migrate operation for all Managed resources.

## 4. Features

### 4.1 Access, Runtime and Navigation

**Description:** The user starts LanguageLab manually on the Mac Mini and reaches it from iPhone, iPad and desktop browsers over a private Tailscale HTTPS URL. HTTPS is a hard requirement because mobile browsers allow microphone capture only in a secure context. The app is available only while the Mac Mini, the LanguageLab process, Anki Desktop, Tailscale and the internet connection are all up. Realizes UJ-1, UJ-6.

#### FR-1: Manual start with a single documented command

The user can start a specific released version of LanguageLab with one documented terminal command. Configuration is loaded from a user config file that lives outside the disposable runtime environment.

**Consequences (testable):**
- The documented command starts a versioned release on the Mac Mini, and configuration is read from `~/.config/language-lab/.env`.
- Startup prints the local URL and, when it can be discovered, the private Tailscale URL.
- The process stays attached to the terminal for its whole lifetime. The user opens the browser manually.

**Out of Scope:** background services, auto-start, auto-opening a browser.

#### FR-2: Private remote access from phone, tablet and desktop

The user can reach LanguageLab from iPhone Safari, iPad Safari and desktop browsers via a private tailnet HTTPS URL and grant microphone permission.

**Consequences (testable):**
- iPhone, iPad and a desktop browser load LanguageLab over Tailscale HTTPS and can grant microphone access.
- Neither LanguageLab nor AnkiConnect is reachable directly from the LAN or the public internet.

#### FR-3: Primary navigation

The user can move between these primary areas: **Captures**, **English** (Items, Pronunciation), **French** (Items, Pronunciation) and **Setup**.

**Consequences (testable):**
- Captures and Setup are shared across Languages. Items and Pronunciation exist separately for English and French.
- The layout is usable at phone, tablet and desktop widths.

#### FR-4: Setup documentation

The user has documentation covering first-time installation and configuration.

**Consequences (testable):**
- A documented `.env.example` lists every configuration key with an explanation.
- The docs give the one-time Tailscale Serve command.
- The docs warn that any local process can control a keyless AnkiConnect instance.
- The docs tell the user to study `<Prefix>::Study` in Anki clients and never the `<Prefix>` root, so Pronounce Cards stay LanguageLab-only.
- The docs recommend making an Anki backup before running Setup or a migration.
- The docs describe evaluating a model against a representative English/French/Russian fixture set before adding it to, or reordering, the configured model list.

### 4.2 Setup and Repair

**Description:** The user installs and runs Anki Desktop and AnkiConnect manually. LanguageLab's Setup area then checks readiness and previews every Managed resource it will create or repair. Changes are applied only after confirmation, and the result is verified. The full managed structure (five note types and the deck hierarchy) is specified in `addendum.md` §A3. Realizes UJ-6.

#### FR-5: Readiness check

The user can see whether AnkiConnect is reachable, whether Azure and OpenRouter are configured, and which Prefix is in effect.

**Consequences (testable):**
- Each check reports pass/fail on its own. A failure names the missing or unreachable dependency.

#### FR-6: Setup preview and confirmed apply

The user can preview the decks, note types, fields, templates, CSS and deck options that Setup will create or repair, and apply them only after confirming.

**Consequences (testable):**
- Before confirmation, Anki is unchanged.
- Running Setup against an empty Prefix creates the five managed note types and the complete managed deck hierarchy.
- After applying, Setup verifies that the expected structure exists and reports any discrepancy.
- A second Setup run makes no unintended changes (idempotent).

#### FR-7: Schema-versioned migration

LanguageLab can migrate Managed resources from an older schema version to the current one.

**Consequences (testable):**
- Every managed note records its schema version.
- Migrations stay inside the Prefix, are idempotent, and are previewed and confirmed like any other Setup run. Migrations never run automatically at startup.

#### FR-8: Independent scheduling of sibling Cards

Setup configures the managed Study decks so that Cards from the same note are not buried.

**Consequences (testable):**
- Managed Study decks have sibling burying disabled.
- All other scheduling options and daily limits remain under the user's control. Setup does not overwrite them on repair.

### 4.3 Captures

**Description:** Capture input is text only. A Capture is a holding area: it is stored in Anki but never studied, and it can spawn several Items before it is deleted. Realizes UJ-1, UJ-2.

#### FR-9: Create a Capture

The user can save a text Capture from any connected browser.

**Consequences (testable):**
- Saving creates a Capture note in Anki recording the text and its creation time. The note's card is suspended immediately and never enters study.
- If Anki is unavailable, the user sees a visible error and no Capture is reported as saved.

#### FR-10: Browse and open Captures

The user can list existing Captures and open one.

**Consequences (testable):**
- Captures are listed newest first, with their text and creation time.
- v1 has no Capture search.

#### FR-11: Start an Item from a Capture

From an open Capture, the user can start a new Item. The user chooses **Use as is** or enters a custom value, picks a Language and a Category, and may add Generation context.

**Consequences (testable):**
- The chosen or custom value must already be in the target Language. LanguageLab does not translate it.
- Generation context is never persisted unless the user copies it into a persisted field such as Hint or Example.

#### FR-12: Multiple Items per Capture

After an Item is saved, LanguageLab returns to the same Capture so the user can create more Items from it.

**Consequences (testable):**
- One Capture can create multiple saved Items before the Capture is deleted.

#### FR-13: Delete a Capture

The user can permanently delete a Capture.

**Consequences (testable):**
- Deleting a Capture removes its Capture note and card from Anki. Items created from it are unaffected.
- Deletion requires confirmation, using the same pattern as Item deletion.

### 4.4 Draft Generation

**Description:** For a new Item, LanguageLab asks an LLM (via OpenRouter) for a concise, contextually relevant Draft. Each output is validated against a strict schema for its Category. Invalid output never reaches the user as a Draft and can never be saved. Model choice is an ordered, configurable fallback list. Call parameters are in `addendum.md` §A4. Realizes UJ-2.

#### FR-14: Generate a Vocabulary Draft

The user can generate a Draft for a Vocabulary Item from its Target text and optional Generation context.

**Consequences (testable):**
- The Draft contains one contextually relevant primary Russian meaning, a short list of alternatives when useful, and applicable grammatical metadata (part of speech and grammar notes where relevant; phrases may leave word-specific fields empty).
- The Draft contains one example sentence with its Russian translation by default. The user can remove it with a Clear action.
- Generation never produces a mnemonic or a dictionary dump.

#### FR-15: Generate a Sentence Draft

The user can generate a Draft for a Sentence Item from its Target text and optional Generation context.

**Consequences (testable):**
- The Draft fills the Russian meaning (one contextually relevant primary meaning, plus optional short alternatives), an optional Hint and an optional Note field on applicable grammar or usage.
- Generation does not produce an example, a mnemonic or a dictionary dump.

#### FR-16: Validated output with one retry

LanguageLab accepts only generated output that passes local schema validation for the Item's Category.

**Consequences (testable):**
- If validation fails, LanguageLab retries generation once.
- If the retry also fails, the user sees an error. The Capture and Anki are unchanged.
- Malformed output cannot be saved accidentally.

#### FR-17: Configurable model fallback

LanguageLab tries the configured LLM models in order when generating.

**Consequences (testable):**
- The model list and its order come from configuration only. Changing it needs no code change.

**Notes:** Generation quality beyond schema validity is gated by the user, who reviews and approves every Draft at Save. Before a model is configured, it is evaluated against fixtures as documented (FR-4).

#### FR-18: Edit a Draft before Save

The user can edit every Draft field before saving, including the user-only Mnemonic field.

**Consequences (testable):**
- Edits stay local to the form until Save.
- Nothing is written to Anki until Save.

### 4.5 Duplicate Handling

**Description:** The same spelling can carry a different meaning, so duplicates are surfaced but never blocked. Realizes UJ-2.

#### FR-19: Duplicate warning before creation

Before creating an Item, LanguageLab looks for existing Items with matching Target text in the same Language and Category. Case and surrounding punctuation are ignored when matching.

**Consequences (testable):**
- When matches exist, the user can **Open existing**, **Cancel** or **Create anyway**.
- Creation is never blocked outright.
- Matches in the other Language or Category are not reported.

### 4.6 Items and Cards

**Description:** Saving a Draft creates one Item note with exactly four Cards. Exercises cannot be disabled per Item. LanguageLab defines the card presentation for the three Anki-reviewed Exercises. Field lists and deck placement are in `addendum.md` §A3. Realizes UJ-2, UJ-4, UJ-5.

| Exercise | Front | Expected action | Review surface |
| --- | --- | --- | --- |
| Understand | Target text; optional audio button | Recall the Russian meaning | Anki |
| Produce | Primary Russian meaning and optional Hint | Recall the Target text | Anki |
| Write | Primary Russian meaning and optional Hint | Type the Target text | Anki |
| Pronounce | Target text (visible); optional audio button | Speak the Target text | LanguageLab |

#### FR-20: Save an Item with four Cards

The user can save a Draft as an Item.

**Consequences (testable):**
- Saving creates one note and exactly four Cards, each in its correct managed deck for its Language, Category and Exercise.
- If the user previewed and kept Reference audio, it is written to Anki media and linked from the note. Reference audio is optional, and an Item can be saved without it.
- Each Card has an independent Anki schedule.

#### FR-21: Anki card presentation

Understand, Produce and Write Cards render the agreed prompts and backs in AnkiMobile and Anki Desktop.

**Consequences (testable):**
- The back shows the Target text, the Russian meaning, applicable grammar, the optional example (with translation), the optional Mnemonic and the Reference audio when present.
- When an Item has no Reference audio, no audio button is rendered.
- Understand may offer audio on the front. Produce reveals audio only after the answer is shown. Write reveals audio only after submission or answer reveal.
- Typing comparison on Write is advisory. The user still selects the Rating.
- No Card shows IPA or Voice metadata.

#### FR-22: Search and open Items

The user can search Items within a Language and open one. Search matches the Target text and the Russian meaning across both Categories.

**Consequences (testable):**
- Opening an Item reads its current values from Anki, so an edit made directly in Anki is visible the next time the Item is opened.

#### FR-23: Edit an Item

The user can edit an Item's field values and save them.

**Consequences (testable):**
- Saving updates the existing note in place without replacing its Cards or review history.
- Saves are last-write-wins. Detecting conflicts between Anki edits and LanguageLab edits is not required.
- If the user changes the Target text, LanguageLab reruns the duplicate check (FR-19) before Save. If the Item has Reference audio, LanguageLab warns that it no longer matches the text and offers to regenerate it.

#### FR-24: Regenerate content with side-by-side Preview

The user can regenerate the Russian meaning, the example (Vocabulary), the Note field (Sentence) or the Reference audio of an existing Item and compare each Preview with the current value.

**Consequences (testable):**
- The current Anki value is unchanged until Save.
- Discarding a Preview leaves the Item unchanged.

#### FR-25: Delete an Item

The user can permanently delete an Item after an explicit confirmation that names the Item and the Cards affected.

**Consequences (testable):**
- Confirming deletes the note, all four Cards, their review histories and the Item's managed Reference audio.
- There is no archive, trash or undo.

### 4.7 Reference Audio

**Description:** Reference audio is synthesized by Azure voices for the Item's locale. It is previewed before it is stored, and the exact previewed bytes are what Anki receives. Realizes UJ-2, UJ-5.

#### FR-26: Choose a Voice for the locale

The user can choose from the Voices currently available for the Item's locale (`en-US` for English, `fr-CA` for French).

**Consequences (testable):**
- The Voice list reflects Azure's current catalog filtered to the locale.

#### FR-27: Preview audio without changing Anki

The user can synthesize and play a temporary audio Preview.

**Consequences (testable):**
- Previewing does not change Anki.
- Azure credentials never reach the browser.

#### FR-28: Save previewed audio

The user can save a previewed audio clip as the Item's Reference audio.

**Consequences (testable):**
- Save stores the exact previewed MP3 in Anki media and updates the Item's audio field.
- Superseded managed audio is removed only after the new value saves successfully. If Save fails, the previous audio stays in place.

#### FR-29: Remember the last Voice per locale

Each browser remembers the last selected Voice for each locale on its own.

**Consequences (testable):**
- The `en-US` and `fr-CA` selections persist independently in browser local storage and are not stored in Anki.
- Changing the selected Voice never regenerates existing audio. Regeneration is always an explicit Preview and Save.

### 4.8 Pronunciation Review

**Description:** LanguageLab is the only surface that reviews Pronounce Cards. Azure Pronunciation Assessment is the only provider in v1. Feedback informs the user, but the user always chooses the Rating, and Anki's scheduler applies it. Realizes UJ-3.

#### FR-30: Pronunciation queue

The user can review new and due Pronounce Cards for the selected Language.

**Consequences (testable):**
- The queue contains only new and due Pronounce Cards from that Language's Pronunciation decks.
- LanguageLab defines a simple order: due cards first (oldest due first), then new cards in creation order. Anki's exact daily limits, sibling behavior and native ordering are not reproduced.
- When the queue is empty, the user sees an empty-state message.

#### FR-31: Reference playback and recording

For the current Card, the user sees the Target text, can play the Reference audio (when present) before the first Attempt and before every retry, and can record an Attempt in the browser.

**Consequences (testable):**
- If the Item has no Reference audio, there is no playback control, and recording and assessment still work.
- An Attempt is recorded in the browser and submitted for Assessment without leaving the review screen.

#### FR-32: Pronunciation feedback

The user sees Azure's Assessment for each Attempt, scored against the Target text as the reference text.

**Consequences (testable):**
- For `en-US`: Azure's available overall, word, phoneme and supported prosody feedback is shown.
- For `fr-CA`: only the overall, word and phoneme-position feedback Azure actually provides is shown. The UI never claims to identify a named incorrect French sound.
- If Assessment fails, the Card stays unanswered and the user can retry or exit.

#### FR-33: Unlimited retries without side effects

The user can retry any number of times.

**Consequences (testable):**
- Attempts and Assessments never change Anki.

#### FR-34: Rate and advance

The user commits a review by clicking Again, Hard, Good or Easy.

**Consequences (testable):**
- The Rating is submitted straight away to Anki's scheduler for that Pronounce Card only. No separate Save is needed.
- After Anki confirms the answer, the next Card loads. If submission fails, the user sees an error and the Card stays current and unanswered.
- Assessment scores never choose or pre-select a Rating.

#### FR-35: Ephemeral pronunciation data

Recordings, Assessment responses, Attempts and scores exist only for the active review.

**Consequences (testable):**
- After a Rating succeeds or the review is abandoned, the related recordings and Assessment responses are gone from the browser and the server.
- No pronunciation history is stored anywhere.

### 4.9 Synchronization

**Description:** LanguageLab keeps AnkiWeb current so reviews done on other devices and reviews done in LanguageLab converge. Scheduling itself is always Anki's. LanguageLab never implements FSRS or legacy scheduling. Realizes UJ-3, UJ-4.

#### FR-36: Sync triggers

LanguageLab triggers a Sync at startup, every five minutes while running, before and after each Pronunciation session, and during graceful shutdown.

**Consequences (testable):**
- Each trigger results in a Sync attempt while the process runs. No Sync happens while it is stopped.
- Sync failures are written to the terminal, retried at the next trigger, and never block normal work.

## 5. Cross-Cutting NFRs

### 5.1 Anki Ownership Boundary and Data Safety

- **NFR-1 (Boundary):** LanguageLab never creates, edits or deletes Anki resources outside the configured Prefix. Inside the Prefix there are no pre-existing user notes.
- **NFR-2 (Authority):** Anki is authoritative for Captures, Items, Cards, media references, review history and scheduling. LanguageLab has no application database. It owns only runtime state, configuration, and the per-browser Voice preference.
- **NFR-3 (No lossy failures):** A failed Save never deletes or replaces the prior Anki field or media value.
- **NFR-4 (Preview-and-Save):** All content changes go through an explicit Save. The only other commits are Capture Save, Setup confirmation, deletion confirmation and Rating clicks.

### 5.2 Failure Semantics

| Failure | Behavior |
| --- | --- |
| OpenRouter | Draft and Capture unchanged; error shown |
| Azure TTS | Current audio unchanged; error shown |
| Azure Pronunciation Assessment | Card stays unanswered; retry or exit allowed |
| AnkiConnect / Anki Desktop unavailable | Requested Anki-backed action blocked; visible error |
| Sync | Non-blocking; logged to terminal; retried at next trigger |

### 5.3 Privacy and Security

- **NFR-5:** Every service binds only to localhost. Remote access goes exclusively through Tailscale Serve over HTTPS.
- **NFR-6:** The browser never calls AnkiConnect, Azure or OpenRouter directly. Every call goes through the LanguageLab backend, and credentials never reach the browser.
- **NFR-7:** Operational logs never contain captured text, generated content, API payloads or audio.
- **NFR-8:** OpenRouter is used with its default privacy and provider-routing behavior.

### 5.4 Observability

- **NFR-9:** Operational logs go only to stdout/stderr and include operational errors and request IDs.

### 5.5 Platform

- **NFR-10:** Responsive web UI for iPhone Safari, iPad Safari and current desktop browsers. No native app, PWA or offline mode.
- **NFR-11:** The Mac Mini needs no frontend build toolchain at runtime (details in `addendum.md` §A1).

## 6. Non-Goals (Explicit)

- Not multi-user: no accounts and no sharing.
- No application database, offline mode, PWA or native mobile app.
- No analytics, goals, streaks or pronunciation history.
- No study-capacity or backlog management.
- No migration or import of existing Anki notes into LanguageLab.
- No OCR, URL, browser-selection, image or audio capture. Capture is text only.
- No automatic pronunciation rating and no Rating suggestions.
- No exact reproduction of Anki's native card queue.
- No custom scheduling algorithm. Anki schedules everything.
- No IPA, phonemizer, Speechace, SPPAS or named-French-sound diagnosis.

## 7. MVP Scope

### 7.1 In Scope

- English (`en-US`) and French (`fr-CA`) with Russian as the translation language.
- Text Capture, AI-drafted Vocabulary and Sentence Items, duplicate handling, editing, regeneration and deletion.
- Four Exercises per Item. Understand, Produce and Write are reviewed in Anki; Pronounce is reviewed in LanguageLab with Azure Assessment.
- Azure Reference audio with Voice selection.
- Setup/repair/migration of Managed resources.
- Periodic and event-driven Sync.

### 7.2 Out of Scope for v1

- Advanced exercise design for the C1–C2 range (the long-term target). Deferred until the B2→C1 and A1 milestones show what is needed.
- Additional languages, locales or translation languages.
- Pronunciation providers other than Azure.
- Disabling Exercises per Item.
- Conflict detection between edits in Anki and edits in LanguageLab.

## 8. Success Metrics

This is a personal tool with no in-app analytics. Success is judged by the release gate and by sustained use, observed through Anki's own data.

- **SM-1 (release gate):** All v1 acceptance criteria in §9 pass, and every FR's testable consequences hold. §9 lists the user-facing headline checks; FR consequences cover the rest.
- **SM-2 (adoption):** Most new learning Items for English and French are created through LanguageLab rather than by hand in Anki, measured from Anki note-type counts. There is no numeric target; it is reviewed informally after one month of use. Validates FR-11–FR-20.
- **SM-3 (pronunciation habit):** Pronounce Cards are reviewed regularly enough that they don't fall far behind the Study Cards, measured from Anki deck stats. Validates FR-30–FR-34.
- **SM-C1 (counter-metric):** Item count. Don't optimize for volume of Items created. Concise, contextually correct Items are the goal. Counterbalances SM-2.
- **SM-C2 (counter-metric):** Azure pronunciation scores. Don't chase scores or feed them into Ratings. They are feedback, not a target. Counterbalances SM-3.

## 9. v1 Acceptance Criteria

v1 is complete when every criterion passes.

1. A versioned wheel starts on the Mac Mini through the documented `uvx --from ... language-lab` command and loads `~/.config/language-lab/.env`. (FR-1)
2. iPhone, iPad and a desktop browser reach LanguageLab over private Tailscale HTTPS and grant microphone permission. (FR-2)
3. Setup against an empty Prefix creates the five note types and the complete managed deck hierarchy, and a second run makes no unintended changes. (FR-6)
4. A text Capture created from a remote browser is stored as a suspended Capture note. (FR-9)
5. One Capture can create multiple Items before it is deleted. (FR-12, FR-13)
6. Saving an English or French Vocabulary/Sentence Draft creates one note and exactly four Cards in the correct decks. (FR-20)
7. All four Cards have independent schedules, and managed Study decks do not bury siblings. (FR-8, FR-20)
8. Duplicate detection offers Open existing, Cancel and Create anyway for normalized matches. (FR-19)
9. OpenRouter produces locally validated Vocabulary and Sentence Drafts, and malformed output cannot be saved accidentally. (FR-14–FR-16)
10. Generated Vocabulary Drafts include a removable example and never generate a mnemonic. (FR-14)
11. Editing through LanguageLab updates the existing note without replacing its Cards or review histories. (FR-23)
12. A managed field edited directly in Anki is visible when the Item is next opened in LanguageLab. (FR-22)
13. Audio Preview does not change Anki. Save writes the exact previewed MP3, and regeneration keeps the old audio until Save succeeds. (FR-27, FR-28)
14. The last selected `en-US` and `fr-CA` Voices persist independently in browser local storage. (FR-29)
15. Understand, Produce and Write Cards show the agreed prompts, backs, hints and audio placement in AnkiMobile and Anki Desktop. (FR-21)
16. Pronunciation review allows reference playback, recording, Azure feedback and unlimited retries without changing Anki. (FR-31–FR-33)
17. Clicking a Rating answers only that Pronounce Card through Anki's scheduler and loads the next Card. (FR-34)
18. Azure output never selects a Rating automatically and never claims an unsupported named French-sound diagnosis. (FR-32, FR-34)
19. Recordings and Assessment responses are gone once the active pronunciation review ends. (FR-35)
20. Startup, five-minute, Pronunciation-session and graceful-shutdown Sync attempts happen while LanguageLab runs, and failures don't block anything. (FR-36)
21. Permanent deletion removes the note, its four Cards and review histories, and its managed audio, after explicit confirmation. (FR-25)
22. LanguageLab never creates, edits or deletes Anki resources outside its configured Prefix. (NFR-1)

## 10. Open Questions

1. Should there be a maximum Attempt recording length? Azure scripted assessment has per-request duration limits, so the FR-31 recording UI may need to stop automatically. Architecture decides once it has confirmed Azure's limits. `[non-blocking; architecture]`
2. Should Captures support search or filtering once the backlog grows? v1 assumes a simple list. `[non-blocking]`
3. Are there spending guardrails for OpenRouter and Azure usage, or is provider-side billing enough? `[non-blocking]`
4. Should the Pronunciation queue cap new Pronounce Cards per session? v1 shows all new and due cards. `[non-blocking; revisit if the queue feels overwhelming]`
5. Exact duplicate normalization: how are inner whitespace, apostrophe variants and diacritics treated? Case and surrounding punctuation are already ignored. `[non-blocking; architecture]`
6. If unexpected, non-managed notes or decks already exist under the Prefix, should Setup report them and leave them alone? `[non-blocking; architecture]`

## 11. Confirmed Assumptions

*These were inferred while drafting and then confirmed by the user on 2026-10-08. They are now stated inline as requirements:*

- §3 Glossary: a Pronunciation session starts when the user opens a Language's Pronunciation tab and ends when they leave it or the queue is empty.
- §4.2 FR-7: schema migrations run through the Setup preview/confirm flow, not automatically at startup.
- §4.2 FR-8: Setup repair leaves user-changed scheduling options untouched.
- §4.3 FR-10: Captures are listed newest first, with no search in v1.
- §4.3 FR-13: Capture deletion uses the same confirmation pattern as Item deletion.
- §4.4 FR-15: Sentence generation fills the Russian meaning, optional Hint and optional Note, and generates no example.
- §4.6 FR-20: Reference audio is optional (decided at review).
- §4.6 FR-23: an edit to the Target text triggers a duplicate re-check and a stale-audio warning (decided at review).
- §3 Glossary / §4.1 FR-4: Pronounce Cards stay LanguageLab-only by usage convention (decided at review).
- §4.6 FR-22: Item search matches Target text and Russian meaning across both Categories.
- §4.8 FR-30: Pronunciation queue order is due before new, oldest due first, then new cards in creation order.
- §8 SM-2: adoption has no numeric target and is reviewed informally after one month.

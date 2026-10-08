# LanguageLab — UX Source Extract

Sources:
- PRD = `_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md`
- ADD = `_bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md`
- SPEC = `spec-draft.md`

Extraction only. Nothing here is invented; every item cites its source. Where sources disagree, the disagreement is flagged.

---

## 1. Glossary terms (verbatim, PRD §3)

Use these terms exactly in UX copy and specs.

- **Anki**: Anki Desktop on the Mac Mini, reached through AnkiConnect. The authoritative store.
- **Prefix**: configured top-level name (default `LanguageLab`).
- **Managed resource**: deck, note type, field, card template, CSS, deck option or media file under the Prefix. The user may edit field values but not schemas or templates.
- **Language**: English (`en-US`) or French (`fr-CA`). The translation language is always Russian.
- **Category**: Vocabulary (single words and multiword phrases) or Sentence.
- **Capture**: raw text saved for later processing. Stored as a Capture note with a permanently suspended card. Produces zero or more Items.
- **Generation context**: transient text, such as a source sentence or intended meaning. Never persisted.
- **Draft**: unsaved, editable proposal for an Item's field values. Nothing reaches Anki until Save.
- **Item**: saved Vocabulary or Sentence note. It has exactly four Cards.
- **Target text**: the Item's target-language word, phrase or sentence.
- **Russian meaning**: one primary contextual Russian meaning plus optional short alternatives.
- **Hint**: optional short disambiguating text shown on the front of Produce and Write Cards.
- **Mnemonic**: optional memory aid on Vocabulary Items. User-written only; never generated.
- **Note field**: optional grammar/usage `Note` on Sentence Items. Not the same as an Anki note.
- **Exercise**: **Understand**, **Produce**, **Write**, **Pronounce**.
- **Card**: the Anki card for one Exercise of one Item. Each Card has an independent schedule.
- **Study decks** / **Study Cards**: `<Prefix>::Study`, which holds Understand, Produce and Write. Reviewed in Anki clients.
- **Pronunciation decks**: `<Prefix>::Pronunciation`, which holds Pronounce Cards. Reviewed only in LanguageLab.
- **Reference audio**: optional Azure-synthesized MP3 of the Target text, stored in Anki media.
- **Voice**: Azure neural voice for the Item's locale.
- **Preview**: temporary content (regenerated text or audio) shown next to the current value and not yet saved.
- **Save**: the explicit commit that writes a Draft or Preview to Anki.
- **Attempt**: one recording of the user speaking the Target text.
- **Assessment**: Azure Pronunciation Assessment feedback for one Attempt.
- **Rating**: Again, Hard, Good or Easy, chosen by the user.
- **Pronunciation session**: starts when the user opens a Language's Pronunciation tab. Ends when they leave it or the queue is empty.
- **Sync**: Anki synchronization with AnkiWeb, triggered through AnkiConnect.
- **Setup**: idempotent create/repair/migrate operation for all Managed resources.

Fixed UI labels named in the sources:
- **Use as is** (FR-11; SPEC Capture workflow)
- **Open existing**, **Cancel**, **Create anyway** (FR-19)
- **Clear**, for the example (FR-14; SPEC "Clear button")
- **Again / Hard / Good / Easy** (FR-34)
- **Save** (NFR-4)
- Navigation labels **Captures**, **English**, **French**, **Items**, **Pronunciation**, **Setup** (FR-3)

Field names from ADD §A3: Capture `Text`, `CreatedAt`. Vocabulary `Target`, `Russian`, `Hint`, `PartOfSpeech`, `Grammar`, `Example`, `ExampleRussian`, `Mnemonic`, `Audio`. Sentence `Target`, `Russian`, `Hint`, `Note`, `Audio`. The hidden fields `ItemId` and `SchemaVersion` are not user-facing.

---

## 2. Form factors & platform

- One user (Oleksii), a Russian-speaking learner who studies on **iPhone, iPad and desktop** (PRD §2).
- Browsers: **iPhone Safari, iPad Safari and current desktop browsers** (FR-2, NFR-10).
- Responsive web UI. The layout must be usable at phone, tablet and desktop widths (FR-3, NFR-10).
- **No native app, no PWA, no offline mode** (NFR-10, §6; SPEC Product boundaries).
- Built with vanilla HTML/CSS/JS and no frontend framework, served by FastAPI. No Node on the Mac Mini (ADD §A1, NFR-11). This limits UI component complexity.
- Access is through a private Tailscale HTTPS URL. HTTPS is required for mobile microphone access (FR-2, ADD §A1).
- The browser must be able to grant microphone permission (FR-2, AC-2).
- Browser local storage holds **only** the last Voice per locale (FR-29, ADD §A1).
- The app is reachable only while the Mac Mini, the LanguageLab process, Anki Desktop, Tailscale and the internet are all up (PRD §4.1; SPEC Network access).
- The UI language (English or Russian) is **not stated** in any source. Content languages are English, French and Russian.
- Accessibility requirements: **none stated** in any source.

---

## 3. Stated needs / capabilities by feature

### 3.1 Access, Runtime, Navigation (PRD §4.1)
- FR-1: manual start with one terminal command. Startup prints the local URL and the Tailscale URL. The user opens the browser manually. There is no auto-start.
- FR-2: reachable from iPhone, iPad and desktop over Tailscale HTTPS; microphone permission can be granted.
- FR-3: primary areas are **Captures**, **English** (Items, Pronunciation), **French** (Items, Pronunciation) and **Setup**. Captures and Setup are shared across Languages. Usable at phone, tablet and desktop widths.
- FR-4: documentation (outside the app UI): `.env.example`, the Tailscale Serve command, a keyless AnkiConnect warning, "study `<Prefix>::Study`, never the root", a backup recommendation, and model evaluation.

### 3.2 Setup and Repair (PRD §4.2)
- FR-5: readiness check shows AnkiConnect reachable, Azure configured, OpenRouter configured, and the Prefix in effect. Each check has its own pass/fail. A failure names the dependency.
- FR-6: preview the decks, note types, fields, templates, CSS and deck options that will be created or repaired. Apply only after confirmation. Anki is unchanged before confirmation. Verification runs after apply and reports discrepancies. Setup is idempotent.
- FR-7: schema-versioned migrations use the same preview/confirm flow and never run automatically at startup.
- FR-8: Setup disables sibling burying on Study decks and does not overwrite user scheduling options on repair.

### 3.3 Captures (PRD §4.3)
- FR-9: save a text Capture from any browser. The card is suspended immediately. If Anki is unavailable, show a visible error and do not report the Capture as saved.
- FR-10: list Captures newest first, showing text and creation time. **No search in v1.**
- FR-11: from an open Capture, start an Item. Choose **Use as is** or enter a custom value, pick a Language and a Category, and optionally add Generation context. The value must already be in the target Language (no translation). Generation context is not persisted.
- FR-12: after an Item is saved, return to the same Capture.
- FR-13: permanently delete a Capture with confirmation, using the same pattern as Item deletion. Items created from it are unaffected.

### 3.4 Draft Generation (PRD §4.4)
- FR-14: a Vocabulary Draft contains a primary Russian meaning, short alternatives when useful, and grammar metadata (part of speech and grammar notes; phrases may leave word fields empty). It has one example with a Russian translation by default, removable with **Clear**. There is no mnemonic and no dictionary dump.
- FR-15: a Sentence Draft contains the Russian meaning (primary plus optional alternatives), an optional Hint and an optional Note field. There is no example and no mnemonic.
- FR-16: output is schema-validated with one automatic retry. A second failure shows an error, and the Capture and Anki are unchanged. Malformed output cannot be saved.
- FR-17: an ordered model fallback list, set in configuration only. **No UI.**
- FR-18: every Draft field is editable, including Mnemonic. Edits stay local until Save.
- Note (FR-17): the user gates quality by reviewing every Draft at Save.

### 3.5 Duplicate Handling (PRD §4.5)
- FR-19: before creation, match Target text within the same Language and Category, ignoring case and surrounding punctuation. Options are **Open existing / Cancel / Create anyway**. Creation is never blocked. Matches from the other Language or Category are not shown.

### 3.6 Items and Cards (PRD §4.6)
- Exercise table (PRD §4.6, SPEC Exercise model): Understand front = Target text + optional audio. Produce/Write front = primary Russian meaning + optional Hint. Pronounce front = Target text (visible) + optional audio and is reviewed in LanguageLab.
- FR-20: Save creates one note and four Cards. Reference audio is optional.
- FR-21 (Anki card design, rendered in AnkiMobile and Desktop): the back shows Target, Russian meaning, grammar, optional example with translation, optional Mnemonic and audio. No audio button appears without audio. Audio placement: Understand may show it on the front; Produce shows it after the answer; Write shows it after submission or reveal. The Write typing comparison is advisory. **No IPA or Voice metadata** on any Card.
- FR-22: search Items within a Language, matching Target text and Russian meaning across both Categories. Opening an Item reads fresh values from Anki.
- FR-23: edit and save in place, last-write-wins. Changing the Target text reruns the duplicate check. If audio exists, warn that it no longer matches and offer to regenerate it.
- FR-24: regenerate the Russian meaning, the example (Vocabulary), the Note field (Sentence) or the Reference audio. The **Preview appears side by side with the current value.** Discarding leaves the Item unchanged.
- FR-25: permanent delete after a confirmation that **names the Item and the Cards affected**. No archive, trash or undo.

### 3.7 Reference Audio (PRD §4.7)
- FR-26: Voice list = Azure's current catalog filtered to `en-US` or `fr-CA`.
- FR-27: synthesize and play a temporary Preview. Anki is not changed.
- FR-28: Save stores the exact previewed MP3. Old audio is removed only after a successful save.
- FR-29: the last Voice per locale is remembered per browser. Changing the Voice never regenerates existing audio.
- UJ-2: "open the English Voice list, preview two voices, keep one" (comparing several voices is implied).

### 3.8 Pronunciation Review (PRD §4.8)
- FR-30: the queue holds new and due Pronounce Cards for the Language: due first (oldest first), then new cards in creation order. Show an **empty-state message** when the queue is empty.
- FR-31: show the Target text. Play Reference audio (when present) before the first Attempt and before each retry. Record in the browser and submit without leaving the screen. With no audio, there is no playback control, but recording still works.
- FR-32: `en-US` shows overall, word, phoneme and supported prosody feedback. `fr-CA` shows only overall, word and phoneme-position feedback, and **never claims a named incorrect French sound**. If the Assessment fails, the Card stays unanswered and the user can retry or exit.
- FR-33: unlimited retries. Attempts never change Anki.
- FR-34: Again/Hard/Good/Easy commits immediately, with no separate Save. The next Card loads after Anki confirms. If submission fails, show an error and keep the Card current. **Scores never choose or pre-select a Rating.**
- FR-35: recordings, Assessments and scores are ephemeral, with no history.

### 3.9 Synchronization (PRD §4.9)
- FR-36: Sync runs at startup, every 5 minutes, before and after each Pronunciation session, and on shutdown. Failures go to the terminal only and are non-blocking. **No in-app Sync UI is stated.**

---

## 4. Implied surfaces / screens

Derived from FR-3 navigation and the features above. The groupings are inferred; the screen names follow the source terms.

1. **Global navigation / shell**: Captures · English (Items, Pronunciation) · French (Items, Pronunciation) · Setup (FR-3). Must work at phone, tablet and desktop widths.
2. **Captures list + new Capture input**: text entry and Save; list newest first with text and creation time (FR-9, FR-10; UJ-1 "type the phrase into Captures and save").
3. **Capture detail**: shows the Capture text and offers Start Item and Delete Capture (FR-11, FR-12, FR-13).
4. **New Item setup (from Capture)**: Use as is / custom value; Language picker; Category picker; Generation context field (FR-11).
5. **Draft editor**: Vocabulary and Sentence variants with editable fields (FR-14, FR-15, FR-18), the Clear action on the example (FR-14), a Voice picker with audio Preview (FR-26, FR-27), and Save (FR-20). This is a likely place for a generation in-progress or error state (FR-16).
6. **Duplicate warning**: dialog or panel with Open existing / Cancel / Create anyway (FR-19, FR-23).
7. **Items list/search (per Language)**: search across Target and Russian meaning, both Categories (FR-22).
8. **Item detail/edit**: edit fields, regenerate with a side-by-side Preview (FR-24), audio regenerate and Voice choice (FR-26–FR-28), stale-audio warning (FR-23), Delete (FR-25).
9. **Delete confirmation** (shared pattern for Item and Capture): names the Item and the Cards affected (FR-25, FR-13).
10. **Pronunciation review (per Language)**: Target text, Reference audio play, record Attempt, Assessment feedback, retry, the four Rating buttons, and an empty state (FR-30–FR-35).
11. **Setup**: readiness checks (FR-5), Prefix display, preview of resources, Confirm/apply, verification result (FR-6), migration preview (FR-7).
12. **Out-of-app surfaces** (not LanguageLab UI, but UX-relevant): Anki card templates and CSS for Understand, Produce and Write in AnkiMobile and Desktop (FR-21), terminal output at startup and for Sync errors (FR-1, FR-36), and setup docs (FR-4).

---

## 5. Flows described

- **UJ-1 / FR-9: Capture on the go** (iPhone Safari). Open URL → Captures → type → Save → suspended note. Edge case: Anki is closed, so a visible error appears and nothing is lost silently.
- **UJ-2 / SPEC Capture workflow steps 1–11: Capture → Item(s)**. Open Capture → Use as is or custom value → Language + Category → optional Generation context → generate Draft → edit (trim an alternative, add a Mnemonic) → Voice list → preview voices → keep one → Save → back to the same Capture → create another Item (for example, the sentence as English → Sentence) → delete the Capture. Edge case: duplicate match, so the user sees Open existing / Cancel / Create anyway.
- **UJ-3 / SPEC Review flow steps 1–10: Pronunciation** (iPad). Open French → Pronunciation → Sync → first new/due Card → play reference → record → feedback (overall, word, phoneme-position) → replay and retry (×2) → choose Good → Anki schedules → next Card loads. Leaving the tab triggers a Sync and discards Attempts.
- **UJ-4: Study in AnkiMobile** (outside the LanguageLab UI): Understand, Produce and Write; siblings are not buried.
- **UJ-5 / FR-22–FR-24, FR-28: Fix an Item**. The user edits in Anki → opens the Item in LanguageLab and sees the fresh value → regenerates the example and compares → regenerates audio with a different Voice → Save. History is preserved, and the old audio is removed only after Save.
- **UJ-6 / FR-5–FR-6: First-time setup**. Start from the terminal → open the Tailscale URL → Setup shows AnkiConnect, Azure and OpenRouter status → preview decks, note types, templates and options → confirm → verify. A re-run changes nothing.
- **Edit Target text** (FR-23): duplicate re-check, plus a stale-audio warning with an offer to regenerate.
- **Delete** (FR-13, FR-25): explicit confirmation, then permanent removal.

---

## 6. States & errors

Failure table (PRD §5.2; SPEC Failure semantics):

| Failure | Required behavior |
| --- | --- |
| OpenRouter | Draft and Capture unchanged; error shown |
| Azure TTS | Current audio unchanged; error shown |
| Azure Pronunciation Assessment | Card stays unanswered; retry or exit allowed (FR-32) |
| AnkiConnect / Anki Desktop unavailable | Requested Anki-backed action blocked; visible error (FR-9, UJ-1) |
| Sync | Non-blocking; terminal log only; retried at next trigger (FR-36) |
| Failed Save | Prior field/media value never deleted or replaced (NFR-3, FR-28) |

Other states:
- Generation: validation fails, one silent(?) retry runs, then an error (FR-16). Whether the retry is visible to the user is not stated.
- Readiness: pass/fail per check, and a failure names the dependency (FR-5).
- Setup: preview (before confirm), applied, verified, and discrepancy reported (FR-6).
- Duplicate found (FR-19).
- Stale audio after a Target text change (FR-23).
- Item without Reference audio: no playback control in review (FR-31) and no audio button on Cards (FR-21).
- Preview vs current value, shown side by side (FR-24).
- Pronunciation queue empty: empty-state message (FR-30).
- Rating submission failed: error, Card stays current and unanswered (FR-34).
- Microphone permission (FR-2). The denied state is **not specified**.
- Unsaved Draft or Preview: edits stay local until Save (FR-18). Navigating away is **not specified**.
- Offline / Mac Mini down: no offline mode (NFR-10). The app is simply unreachable (PRD §4.1).
- Latency/loading states for generation, TTS, Assessment and Sync are **not specified**.

---

## 7. Constraints (tech that affects UX)

- Anki Desktop + AnkiConnect must be running on the Mac Mini. Otherwise every Anki-backed action is blocked with an error (PRD §4.1, §5.2).
- The app is available only while the Mac Mini, the process, Anki Desktop, Tailscale and the internet are all up (PRD §4.1).
- HTTPS via Tailscale is required for microphone access in mobile browsers (FR-2, ADD §A1).
- There is no application database. All data is read and written live through Anki, and opening an Item reads fresh values (NFR-2, FR-22). This implies a round-trip on most views.
- Credentials never reach the browser. All Azure, OpenRouter and Anki calls go through the backend (NFR-6, FR-27).
- Vanilla JS frontend with no framework (ADD §A1).
- Local storage is limited to the Voice per locale (FR-29).
- Generation may take two attempts (validate → retry) and fall back across models (FR-16, FR-17, ADD §A4), which adds latency.
- The browser recording is converted server-side to an Azure format before assessment (ADD §A5).
- Azure scripted assessment has per-request duration limits, so recording may need an automatic stop (PRD §10 Q1, open).
- Azure feedback differs by locale (`en-US` has more than `fr-CA`) (FR-32, ADD §A5). The feedback UI must adapt to each locale.
- The Pronunciation queue does not reproduce Anki limits. **All** new and due cards are shown (FR-30; PRD §10 Q4).
- Last-write-wins edits with no conflict detection (FR-23).
- Pronounce Cards are excluded from Anki study only by usage convention (study `<Prefix>::Study`) (FR-4, ADD §A3).
- API costs: spending guardrails are an open question (PRD §10 Q3). No cost UI is stated.
- Logs never contain content (NFR-7). Sync errors appear only in the terminal (FR-36).

---

## 8. Visual / tone hints

- **No explicit visual style, brand, color, typography or tone guidance in any source.**
- Implied tone and values:
  - The user needs to "trust that my Anki collection … is never damaged" (PRD §2.1 emotional JTBD), so the UI should make safety, explicit commits and confirmations clear (NFR-3, NFR-4).
  - Content should be "concise, contextually relevant"; "never … a dictionary dump" (FR-14, FR-15; SM-C1 "Don't optimize for volume").
  - Scores are "feedback, not a target"; "Don't chase scores" (SM-C2). Do not gamify the pronunciation scores.
  - No streaks, goals or analytics (§6). This rules out gamification elements.
- Card design consistency: "consistent card design" (PRD §1). Cards show no IPA or Voice metadata (FR-21).

---

## 9. Non-goals (PRD §6, §7.2; SPEC Product boundaries)

- Multi-user, accounts, sharing, teachers, shared decks (§2.2, §6).
- Application database, offline mode, PWA, native mobile app.
- Analytics, goals, streaks, pronunciation history.
- Study-capacity or backlog management.
- Migration or import of existing Anki notes.
- OCR, URL, browser-selection, image or audio capture (Capture is text only).
- Automatic pronunciation rating and Rating suggestions.
- Exact reproduction of Anki's native card queue.
- Custom scheduling (FSRS or legacy).
- IPA, phonemizer, Speechace, SPPAS, named-French-sound diagnosis.
- Capture search (v1) (FR-10).
- Disabling Exercises per Item; conflict detection; extra languages, locales or translation languages; non-Azure providers; C1–C2 advanced exercises (§7.2).
- General-purpose Anki front-end (§2.2).
- Background service, auto-start, auto-opening a browser (FR-1).
- In-app model configuration (FR-17, which is set in configuration only).

---

## 10. Open UX questions left unresolved by the sources

From PRD §10:
1. Maximum Attempt recording length and auto-stop behavior (Q1).
2. Capture search or filtering as the backlog grows (Q2).
3. Spending guardrails for OpenRouter and Azure, and whether any cost visibility appears in the UI (Q3).
4. A cap on new Pronounce Cards per session; the queue could feel overwhelming (Q4).
5. Duplicate normalization of whitespace, apostrophes and diacritics (Q5), which affects the duplicate prompt.
6. How Setup reports unexpected non-managed notes or decks under the Prefix (Q6).

Unaddressed by the sources (gaps for UX to resolve):
7. UI language: English or Russian interface chrome? Not stated.
8. Loading and latency feedback for generation (with retry and model fallback), TTS Preview, Assessment and Rating submission.
9. Whether the user ever sees Sync status (or failures) in-app. Currently it is terminal-only.
10. Global "Anki unavailable" / readiness indicator outside Setup. Is there one, or do errors appear only per action?
11. Microphone permission denied or unavailable state, and the recording UI on iOS Safari (tap-to-toggle vs hold).
12. Navigating away from an unsaved Draft or Preview: warn or discard silently?
13. Item-creation entry points: only from a Capture (FR-11), or can an Item be created directly in the Items tab? The sources describe only the Capture path.
14. Presentation of Assessment feedback: how overall, word, phoneme(-position) and prosody scores are visualized, and how to avoid implying a Rating (FR-34, SM-C2).
15. Queue progress or count in Pronunciation (remaining cards). Not stated.
16. Layout of the side-by-side Preview on a phone width (FR-24 vs FR-3).
17. How the Russian meaning's "primary + alternatives" is structured in the editor (one field `Russian` per ADD §A3).
18. Voice list size and its filter/search affordance. Comparing several voices is implied by UJ-2.
19. Does a Capture show which Items it has already spawned? Not stated (there is no persisted link).
20. Accessibility targets: none stated.

---

## 11. Source discrepancies noted

- `Audio` field: SPEC lists `Audio` without "optional" for both Vocabulary and Sentence. PRD FR-20 and ADD §A3 make it **optional** ("decided at review", PRD §11). PRD/ADD supersede.
- SPEC Setup step 5 says "Applies setup only after Save/confirmation". PRD FR-6 says "confirming", and NFR-4 lists "Setup confirmation" as a commit separate from Save.

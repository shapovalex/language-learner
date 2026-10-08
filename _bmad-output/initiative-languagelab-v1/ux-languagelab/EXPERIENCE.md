---
title: LanguageLab Experience
status: final
created: 2026-10-08
updated: 2026-10-08
design: DESIGN.md
sources:
  - ../prd-languagelab/prd-languagelab.md
  - ../prd-languagelab/addendum.md
  - ../../../spec-draft.md
---

# LanguageLab — Experience Spine

## Foundation

- **Form factor:** responsive web, all three first-class: iPhone Safari, iPad Safari, and current desktop browsers (FR-2, FR-3, NFR-10). No native app, PWA, or offline mode.
- **Stack:** vanilla HTML/CSS/JS, no frontend framework, served by FastAPI (ADD §A1). No UI component system; components below are hand-built.
- **Theme:** light only.
- **Language:** UI chrome in English. Content is English (`en-US`), French (`fr-CA`), and Russian; mark French/English content with `lang`.
- **Visual reference:** `DESIGN.md` (Studio direction). The 14 mockups in `mockups/` (canonical set, indexed in Information Architecture → Mockup) show composition; **the spines (`DESIGN.md`, this file) win on conflict with the mockups**. Mockup content is placeholder.
- **Single user** (Oleksii). Every Anki-backed view reads live from Anki; there is no app database (NFR-2).
- **Shorthand:** **ADD** = PRD addendum (`../prd-languagelab/addendum.md`). **memlog** = the UX session decision log (`.memlog.md`). **(decision)** = settled with the user during UX, not in the PRD; both spines use this one label. Straight quotes delimit UI strings; curly quotes inside them are part of the copy.

## Information Architecture

The Mockup column is the single mockup index for this file.

| Surface | Purpose | Serves | Reached from | Journey | Mockup |
|---|---|---|---|---|---|
| App shell / nav | Switch areas | FR-3 | Always | all | `mockups/S-Items.dc.html` (desktop), `mockups/S-Review.dc.html` (phone header); phone Menu not mocked |
| Captures | Save a new Capture; list newest first | FR-9, FR-10 | Nav "Captures" | J1, J2 | `mockups/S-Captures.dc.html` (phone), `mockups/S-CapturesDesk.dc.html` (desktop two-pane with Capture detail) |
| Capture detail + Make an Item | Show Capture; choose text, Language, Category, and Generation context; delete Capture. Does **not** show Items created from it (decision) | FR-11, FR-12, FR-13 | Capture row | J2 | `mockups/S-NewItem.dc.html` (phone), `mockups/S-CapturesDesk.dc.html` (desktop right pane, with post-Save banner) |
| Draft editor | Review or edit generated fields, Voice and audio Preview, Save | FR-14–FR-18, FR-20, FR-26–FR-29 | "Generate Draft" | J2 (climax) | `mockups/C-Draft.dc.html` (desktop), `mockups/S-DraftPhone.dc.html` (phone, sticky action bar) |
| Duplicate sheet | Open existing / Cancel / Create anyway | FR-19, FR-23 | Before create; on Target change | J2 edge | `mockups/S-Duplicate.dc.html` |
| Items (per Language) | Search Target and Russian meaning, both Categories | FR-22 | English/French → Items | J4 | `mockups/S-Items.dc.html` (desktop); phone search not mocked (OQ-8) |
| Item detail | Edit; regenerate with side-by-side Preview; Voice; Delete | FR-23–FR-25, FR-26–FR-28 | Item row | J4 | `mockups/S-ItemDetail.dc.html` |
| Delete dialog | Confirm permanent delete of Item or Capture | FR-13, FR-25 | Delete actions | J2, J4 | `mockups/S-Delete.dc.html`; unsaved-changes variant not mocked |
| Pronunciation (per Language) | Queue, Reference audio, record, Assessment, Rating | FR-30–FR-35 | English/French → Pronunciation | J3 | `mockups/S-Review.dc.html` (iPhone, en-US, queue count), `mockups/S-iPadReview.dc.html` (iPad, fr-CA, queue count) |
| Setup | Readiness, preview changes, apply, verify, migrations | FR-5–FR-8 | Nav "Setup" | J5 | `mockups/S-Setup.dc.html` (readiness and change preview), `mockups/S-SetupStates.dc.html` (failing check, applying, verified, discrepancies) |
| (Out of app) Anki cards | Understand / Produce / Write in AnkiMobile/Desktop | FR-21, UJ-4 | Anki | — | not designed (OQ-5) |
| (Out of app) Terminal | Startup URLs, Sync errors | FR-1, FR-36 | — | — | — |

State reference for all surfaces: `mockups/S-States.dc.html`.

**Navigation model.** Top level: Captures · English · French · Setup (pills on tablet/desktop; Menu on phone, see Component Patterns → Menu). Inside a Language: segmented Items / Pronunciation. Detail screens have a back link to their parent. Overlays stack one level deep. Item creation starts only from a Capture (FR-11). Sync has no UI (FR-36).

## Voice and Tone

Plain, short, calm. Say what happened and what is safe. No exclamation marks, no praise, no encouragement copy, no emoji.

| Do | Don't |
|---|---|
| "Not saved — Anki isn't reachable" + what to do + "Your text is still here." | "Error 503" / "Oops!" |
| "Nothing changes until you apply." | Vague reassurance |
| "How did that feel? You decide." | "Great job! 🎉" / "You scored 78 — try Good?" |
| "Nothing to practice in French" | "All done! Streak +1" |
| Name the object: "Delete “jump to conclusions”?" | "Are you sure?" |

**Glossary (use verbatim, PRD §3):** Anki, Capture, Generation context, Draft, Item, Target text, Russian meaning, Hint, Mnemonic, Note field, Exercise (Understand, Produce, Write, Pronounce), Card, Study decks, Study Cards, Pronunciation decks, Reference audio, Voice, Preview, Save, Attempt, Assessment, Rating (Again, Hard, Good, Easy), Pronunciation session, Sync, Setup, Prefix, Managed resource, Language, and Category (Vocabulary, Sentence). Glossary terms keep their capitalization everywhere, including UI copy ("Save Capture", "Generate Draft").

**Key strings** (from mockups; where a mockup differs, the string here is canonical). State, error, and confirmation copy lives in State Patterns → Treatment.

| Context | String |
|---|---|
| Captures | "New Capture", placeholder "Paste or type a word, phrase or sentence", "Save Capture", "Newest first" (phone), "N Captures · newest first" (desktop) |
| Capture detail | "Captured today · 21:14", "Delete Capture", "Make an Item", "Use as is", "Custom value", "Write it in the language you're learning, not in Russian.", "Generation context · optional · used once, never saved", "Generate Draft" |
| Draft | "From Capture “…”", chip "Draft — not saved yet", "Discard", "Save to Anki", "Hint · optional" (placeholder "Shown on Produce and Write"), "Mnemonic · optional · only you write this", "Example" + "Clear", "Reference audio · optional", "Voice" (`en-US · Andrew`) |
| Duplicate | "Possible duplicate · English · Vocabulary", "You already have an Item with this text", "Nothing has been saved yet. You can still create a second Item.", "Open existing" / "Cancel" / "Create anyway" |
| Items | Search label "Search English Items", placeholder "Search English or Russian", "4 Items · Vocabulary and Sentence" |
| Item detail | "‹ English Items", chip "2 unsaved changes", "Delete", "Save changes", "Regenerate Russian meaning", "Example · compare", "CURRENT" / "PREVIEW · NOT SAVED", "Keep current" / "Use preview", "The old audio is removed only after Save succeeds." |
| Delete | "Delete “…”?", "This permanently removes the Item and its 4 Cards from Anki, with their review history:", "There is no undo.", "Delete permanently" / "Cancel" |
| Review | "Try again", "Reference", "Sentence · Attempt 3", "Accuracy / Fluency / Completeness / Prosody" (the iPhone review mockup shows "Complete"; the spine wins), "· 54 · mispronounced", "Where in the word", "Listen to the reference and compare the end of the word.", "French feedback covers the overall score, words and where in a word a sound slipped. Prosody isn't available.", "How did that feel? You decide." |
| Queue header | "3 due · 7 new" chip (format "N due · M new", decision) |
| Setup | "Creates or repairs everything LanguageLab manages under the prefix LanguageLab. Safe to run again.", "Ready to go?", "What will change in Anki", "Nothing changes until you apply.", "Apply setup", "In Anki, study “LanguageLab::Study”, not the root deck" |

## Component Patterns

Behavioral. Visual specs in `DESIGN.md` → Components. The unsaved-changes rule for every way of leaving a screen is in Interaction Primitives.

### Navigation and overlays

| Component | Behavioral rules |
|---|---|
| App header / nav pills | `aria-current="page"` on active area ({colors.accent} fill). Areas keep no hidden state between visits except what Anki holds. |
| Menu (phone) | Menu icon button opens a bottom sheet (`role="dialog"`, labelled "Menu") listing Captures · English · French · Setup; current area has `aria-current="page"`. Focus moves to the current area's row and is trapped; selecting a row navigates and closes; scrim tap, Esc, or the Menu button close it and return focus to Menu. |
| Back link | Goes to the parent screen ("‹ Captures", "‹ English Items"). |
| Segmented control | Navigation use (Items / Pronunciation) changes route. Picker use (Language, Category) is single-select with `aria-pressed`; both must be chosen before "Generate Draft" (FR-11). Default selection unspecified (mockup shows English · Vocabulary). |
| Bottom sheet | Phone duplicate prompt; focus trapped; Cancel and scrim tap close it. Same content as a centered dialog on tablet/desktop. |
| Alert dialog | Delete and unsaved-warning confirmations. Focus starts on Cancel / Keep editing (safe default). Esc = cancel. Unsaved variant: "Discard" drops the local edits, Draft, or Preview and continues the navigation; "Keep editing" returns to the screen unchanged. |

### Forms and editing

| Component | Behavioral rules |
|---|---|
| Card | Container only; no tap behavior. |
| Buttons | One Primary per region. Primary = the commit (Save Capture, Generate Draft, Save to Anki, Save changes, Apply setup, Open existing, Run Setup again). Busy state: disabled, and the label stays; duplicate submits are ignored. Disabled buttons carry a visible reason next to them ("Fix the failing check to continue."). |
| Sticky action bar (phone) | Draft editor on iPhone: Discard and Save to Anki are pinned to the viewport bottom, so Save is reachable without scrolling; content scrolls beneath. |
| Icon button | Always labelled ("Menu", "Play reference audio", "Play audio preview"). |
| Text field / textarea / select | Edits stay local until Save (FR-18). Custom value field enabled only when "Custom value" is selected. |
| Text-source choice | Radio pair "Use as is" / "Custom value" (single-select). "Generate Draft" is disabled, with a visible reason, until a Language and Category are chosen and, when Custom value is selected, its field is non-empty (reason copy: "Choose a Language and Category." / "Enter the custom value."). |
| Search field | Filters as you type within one Language across Target and Russian meaning, both Categories (FR-22); the other Language is never shown. Debounced live search. |
| List row | Whole row is the link. Capture rows: newest first, no search (FR-10). Item rows show the audio icon only when Reference audio exists. Opening an Item re-reads Anki (FR-22). |
| Chip | Informational, not interactive. The "unsaved" chip counts unsaved fields. |

### Draft and Item media

| Component | Behavioral rules |
|---|---|
| Compare pair | Appears after a regenerate (FR-24) or audio Preview (FR-27). Keep current discards the Preview; Use preview moves it into the edit buffer; **Save** commits (NFR-4). Until Save, the Item in Anki is unchanged. |
| Audio player | Plays a Preview without touching Anki (FR-27). Changing Voice does not regenerate existing audio (FR-29); the last Voice per locale is stored in local storage. Save stores the exact previewed MP3 (FR-28). |

### Pronunciation review

| Component | Behavioral rules |
|---|---|
| Queue-count chip | Chip "N due · M new" (decision): iPhone in the review header next to Menu; iPad top right of the Target card. Updates after each Rating. No progress bar (decision). |
| Score ring | Displays the overall score from the latest Assessment only. Not interactive. Replaced on each Attempt; nothing persists (FR-35). |
| Word pill | One per word; color plus non-color cue shows the feedback step (Pronunciation Feedback). The weakest word drives the weak-word panel. Tapping another pill switches the weak-word panel to that word (not mocked). |
| Weak-word panel | Content per locale as in Pronunciation Feedback: en-US phoneme pills and prosody sub-score (FR-32); fr-CA position strip only. |
| Record button | Tap to start, tap to stop (decision). Shows the level meter while recording. Auto-stop: OQ-1. |
| Level meter | Live input level while recording only; reassurance only, not interactive. |
| Rating buttons | Four equal buttons; never pre-selected or emphasized by score (FR-34). Enabled once ≥ 1 Attempt on this Card has an Assessment, and they stay enabled while a later Attempt is being assessed. One tap commits immediately; the next Card loads after Anki confirms; a failure keeps the Card current. |

### Status and feedback

| Component | Behavioral rules |
|---|---|
| Inline alert | `role="alert"`, placed at the action that failed, keeps user input. Offers the recovery action. |
| Info callout | Static guidance; no dismissal. |
| Success banner | `role="status"`; shown once on the Capture after Save to Anki (FR-12); clears when the next Draft is generated or the Capture is left. No dismiss control, no auto-hide timer. |
| Skeleton | Shown while waiting on generation, Item load, Items list, Captures list, first Pronunciation Card, and Setup checks. |
| Empty state | Explains why it's empty; no CTA to "do more". |

### Setup

| Component | Behavioral rules |
|---|---|
| Readiness tile | One per check (AnkiConnect, Azure, OpenRouter); failure names the dependency (FR-5) and is followed by a fix hint; Apply is disabled until all pass. Prefix shown in subtitle. |
| Progress card | Shown while Apply setup runs; Apply and Setup's other actions are disabled. Leaving the screen does not cancel the run; returning to Setup re-reads Anki and shows the verification result or the current change list. |
| Verification banner | After Apply: Verified (`role="status"`) or Discrepancies (`role="alert"`) listing each mismatched Managed resource as expected vs. found, with "Run Setup again" (FR-6). |
| Change row | Lists Managed resources and planned action (Create / Repair / Migrate). Read-only. |

## Pronunciation Feedback

Scores are prominent (decision); the Rating stays the learner's (FR-32, FR-34, SM-C2); the tension with SM-C2 "feedback, not a target" is accepted.

**Feedback steps (canonical; visuals in `DESIGN.md` → Colors → Feedback scale).** Azure scores 0–100: **≥ 80 good**, **60–79 fair**, **< 60 poor**, applied alike to word pills, phoneme pills, and position cells. Fair adds a dotted underline; poor adds a solid border (word pill) or solid fill (phoneme pill, position cell); good has no cue.

| | `en-US` | `fr-CA` |
|---|---|---|
| Overall ring | yes | yes |
| Sub-scores | Accuracy, Fluency, Completeness, Prosody | Accuracy, Fluency, Completeness |
| Word pills | yes | yes |
| Weak-word detail | phoneme pills | start / middle / end position strip only |
| Named sound | allowed: phoneme pills show Azure's IPA symbols as returned (decision) | **never** named |
| Note line | — | "Prosody isn't available." |

No score is stored after leaving the Card (FR-35). The ring color never changes with the score. The PRD's "No IPA" (§6 non-goals; FR-21 "No Card shows IPA") applies to Cards and to building a phonemizer or IPA overlay; showing Azure's own en-US phoneme labels in review feedback is in scope (decision).

## State Patterns

| State | Surface | Treatment |
|---|---|---|
| Anki unreachable | Any Anki-backed action | Per-action Inline alert (error) "Not saved — Anki isn't reachable" / "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here." + Try again. No global indicator. A Capture is not reported as saved (FR-9). |
| Unsaved Draft / edits / Preview | Draft, Item detail | On leave (Interaction Primitives): alert dialog "Discard unsaved changes?" with body "N unsaved changes to “<Target>”" or "This Draft isn't saved." — "Discard" / "Keep editing" (decision). |
| Loading — Item, Captures list, Items list, Setup checks | Item detail, Captures, Items, Setup | Skeleton; Items label "Loading English Items…". |
| Captures empty | Captures | "No Captures yet." under the input. |
| Saved from a Capture | Capture detail | Back on the same Capture (FR-12) with the success banner "Saved “<Target>” to Anki. Make another Item from this Capture, or delete it." |
| Loading — generation | Draft | Skeleton + "Writing your Draft…". Automatic retry (FR-16) is not shown. |
| Model unreachable (OpenRouter down) | Draft | Inline alert (error) "Couldn't reach the model" / "Your Capture is unchanged." + Try again (PRD §5.2). |
| Generation failed (after retry) | Draft | Inline alert (error) "Couldn't generate a Draft" / "The model's answer failed the checks twice. Your Capture is unchanged." + Try again. Malformed output is never shown. |
| Duplicate found | Draft (before create), Item detail (Target changed) | Duplicate sheet (FR-19, FR-23). |
| Voice list failed (FR-26) | Draft, Item detail | Inline alert (error) at the Voice select "Couldn't load voices" + Try again; current Voice and audio kept. |
| Azure TTS failed | Draft, Item detail | Inline alert (error) at the audio card: "Couldn't make the audio. Current audio is unchanged." |
| Save failed | Draft, Item detail | Inline alert (error); prior Anki values and media untouched (NFR-3); edits kept. |
| Stale audio after Target change | Item detail | Warning that audio no longer matches, with an offer to regenerate (FR-23). Not mocked (OQ-14). |
| Items empty | Items | Empty state "No English Items yet" / "Items are made from Captures." No create button (FR-11). Search field hidden. |
| Search no matches | Items | "No English Items match “…”." |
| No Reference audio | Review, Item rows | No play control; recording still works (FR-31). |
| Loading — first Card | Pronunciation | Skeleton in the Target card while the Card is read from Anki. The pre-session Sync (FR-36) runs in the background and is not awaited: no Sync label, spinner, or delay (decision). |
| Recording | Review | Danger pill "Listening… tap to stop" + level meter. |
| Assessing | Review | Record button busy "Checking…"; Reference stays playable; Rating buttons follow their rule (Component Patterns). Not mocked. |
| Mic blocked / unavailable | Review | Inline alert (warning) "LanguageLab can't hear you" / "Allow microphone access for this site in Safari, then reload the page." Reference playback still works. |
| Assessment failed | Review | Inline alert (error) "Couldn't assess that Attempt" / "This Card isn't answered yet. Record again, or leave and come back later." Record again / Exit (FR-32). |
| Rating submit failed | Review | Inline alert (error) "Rating not saved — Anki isn't reachable." + Try again; the Card stays current and unanswered (FR-34). |
| Queue empty | Review | Empty state "Nothing to practice in French" / "No new or due Pronounce Cards right now." (FR-30) |
| Readiness check fails | Setup | Failing tile names the dependency, with a fix hint; Apply disabled with reason "Fix the failing check to continue." |
| Applying setup | Setup | Progress card "Applying setup and verifying… Keep Anki open." |
| Nothing to change | Setup | Readiness passes and the change list is empty: info callout "Nothing to change. Everything LanguageLab manages is already set up." replaces the list; Apply setup is not shown. Not mocked. |
| Setup verified / discrepancies | Setup | Verified banner "Setup applied and verified", or discrepancy banner "Setup applied, but 1 thing doesn't match" / "Setup applied, but N things don't match" with "Anki was changed. Review the difference below, then run Setup again.", the list (expected vs. found), and "Run Setup again" (FR-6). Non-managed-notes reporting not mocked (OQ-6). Migration preview reuses the change list (FR-7). |
| App unreachable (Mac mini/Tailscale down) | Out of app | Browser's own error; no offline mode (NFR-10). |
| Sync failure | Out of app | Terminal only (FR-36), including the pre- and post-session Sync; never blocks the session. |

## Interaction Primitives

- Tap/click to act; no gestures required. No swipe actions, no long-press, no drag.
- Every content change is explicit: Save (Draft, Item), Save Capture, Apply setup, Delete permanently, and Rating tap (NFR-4). Nothing autosaves to Anki.
- **Unsaved changes:** leaving a screen with an unsaved Draft, edits, or Preview — through a nav pill, the Menu, a back link, or Discard — first shows the unsaved warning (alert dialog). On browser unload, the browser's own prompt is used instead.
- **Reference audio never auto-plays** (decision; same on iPhone, iPad, and desktop). Per Card: the Card shows → Oleksii taps **Reference** to listen (optional, any number of times) → taps **Record**, speaks, and taps stop → the Assessment appears. **Try again:** he taps **Reference** first if he wants to hear it again, then taps **Try again**, which starts recording at once (it never plays the Reference). The Reference control is disabled while recording; tapping Record while the Reference plays stops playback. No Reference audio → no Reference control (FR-31).
- Destructive actions always go through the alert dialog; no undo, no trash.
- Desktop keyboard: Enter submits the focused form; Esc closes sheets/dialogs. No Rating hotkeys in v1.

## Accessibility Floor

Target: WCAG 2.2 AA. Contrast values in `DESIGN.md` → Colors.

- Targets ≥ {spacing.target-min}.
- Semantic landmarks: `nav aria-label="Main"`, per-Language `nav`, `aria-current` on active nav, `aria-pressed` on pickers.
- Sheets `role="dialog"`, delete/unsaved `role="alertdialog"` with labelled title and description; focus trapped and returned on close.
- Errors/warnings `role="alert"`; a new Assessment result is announced politely (score and weakest word).
- Feedback never by color alone: every non-good step carries a non-color cue (Pronunciation Feedback); the weak-word panel names the word, score, and error type in text.
- Queue-count chip has `aria-label` "N due, M new".
- Word pills, Target text, and French/English content carry `lang`.
- Visible focus ring on every control ({colors.accent} 2px); input text ≥ 16px (prevents iOS zoom on focus).
- Text fields, textareas, and selects are outlined in {colors.border-input} (≥ 3:1). Outline and Rating buttons keep the soft border — accepted deviation, see `DESIGN.md` → Colors.
- Reduced motion: level meter and ring render without animation.

## Key Flows

### J1 — Capture mid-task (UJ-1; iPad or desktop)

1. Oleksii meets "jump to conclusions" in an article on the iPad.
2. Switches to the LanguageLab tab (Captures).
3. Pastes into "New Capture"; taps "Save Capture".
4. **Climax:** the field clears and the Capture tops the list. The whole capture takes about 10 seconds.
5. Returns to reading.

Failure: Anki down → Anki unreachable state (text kept, Try again).
The layout supports capture on all three devices.

### J2 — Batch processing at the Mac (UJ-2; desktop, product climax)

1. Sunday evening, Oleksii opens Captures on desktop: "9 Captures · newest first" in the left pane.
2. Selects "I'd rather not jump to conclusions."; detail and Make an Item open in the right pane.
3. Chooses Custom value "jump to conclusions", English, and Vocabulary; taps "Generate Draft".
4. Skeleton "Writing your Draft…".
5. **Climax:** the Draft is right the first time — he glances and makes no edits.
6. Previews the Andrew Voice.
7. Taps "Save to Anki"; returns to the same Capture (FR-12) with the success banner (State Patterns → Saved from a Capture).
8. Makes a second Item: the full sentence as English → Sentence; Save.
9. Deletes the Capture (dialog) and opens the next.

Failure: duplicate → sheet (Open existing / Cancel / Create anyway); generation fails twice → error + Try again; leaving with an unsaved Draft → unsaved warning.
Draft editing (FR-18) and the Mnemonic remain required: every Draft field is editable inline before Save.

### J3 — Pronunciation session (UJ-3; iPhone or iPad, short or long)

1. Oleksii opens French → Pronunciation; the first Card shows immediately (no Sync UI). The queue-count chip shows "N due · M new" (header on iPhone, Target card on iPad).
2. He taps Reference to listen, then taps Record, speaks, and taps stop.
3. Ring, sub-scores, and word pills appear; the weakest word is highlighted.
4. **Climax:** "chien" is weak at the *end* position → he taps Reference, then Try again, twice. The score climbs, and he picks Good.
5. The next Card loads after Anki confirms.
6. He leaves after a few Cards (Sync runs; Attempts are discarded) or continues to "Nothing to practice in French".

Failure: mic blocked → warning; Assessment fails → Record again / Exit; Rating fails → Card stays current.

### J4 — Fix an Item (UJ-5; desktop)

1. Oleksii searches English Items for "conclu" and opens "jump to conclusions" (fresh from Anki).
2. Regenerates the example; Current and Preview appear side by side.
3. **Climax:** the Preview is clearly better → "Use preview".
4. Generates audio with a new Voice (Ava), compares, and taps "Use preview".
5. Taps "Save changes"; the old audio is removed only after Save succeeds.

Failure: leaving with "2 unsaved changes" → unsaved warning; Save fails → prior values intact.

### J5 — First-time setup (UJ-6; desktop)

1. Oleksii starts LanguageLab from the terminal and opens the printed Tailscale URL.
2. Setup shows readiness tiles for AnkiConnect, Azure, and OpenRouter, with the Prefix in the subtitle.
3. Reviews "What will change in Anki".
4. Taps "Apply setup".
5. The progress card shows (State Patterns → Applying setup).
6. **Climax:** "Setup applied and verified".
7. A later re-run shows "Nothing to change." and no Apply button.

Failure: a readiness check fails → failing tile names the dependency with a fix hint, Apply disabled; verification finds discrepancies → list + "Run Setup again".

UJ-4 (study in AnkiMobile) is outside the LanguageLab UI; card visuals are OQ-5.

## Responsive & Platform

| | iPhone | iPad | Desktop |
|---|---|---|---|
| Nav | Menu button → bottom sheet; Language and queue-count chip in review header | Pill row + segmented control in header | Wordmark + pill row; segmented control in content |
| Review | Stacked: header with queue-count chip, Target card, scores card, Rating 2×2 at bottom | Two columns: Target (queue-count chip top right) and Rating (4 across) left, scores 420px right | As iPad |
| Captures | List and Capture detail are separate screens | Two-pane as desktop in landscape | Two-pane: left = new-capture box, count, and list with the open Capture selected; right = Capture detail + Make an Item (and, after Save, the success banner). Panes stack on narrow widths (flex-wrap, left min 320px) |
| Compare pair | Panes stack vertically (Current above Preview) | Side by side when ≥ 2×300px | Side by side |
| Draft editor | Single column of cards; sticky bottom bar Discard + Save to Anki | Wraps like desktop | Form left (3fr), Example and audio right (2fr) |
| Items search | Not mocked; spine-only (OQ-8) | As desktop | Full-width pill search + rows |
| Sheets/dialogs | Bottom sheet; centered alert dialog | Centered dialog | Centered dialog |

- Session length is independent of device; the review layout must work for quick bursts and full queues on phone and iPad.
- iOS Safari microphone needs HTTPS (Tailscale) and a user gesture to start recording and audio playback (FR-2); both are always tap-started (Interaction Primitives). Permission denial → mic-blocked state.
- Respect safe areas on iPhone; bottom actions sit above the home indicator.
- Local storage only for the last Voice per locale (FR-29).

## Inspiration & Anti-patterns

- **Lifted (Studio direction):** warm rounded cards, pill buttons, score ring, and word pills.
- **Rejected directions:** A "Paper" (calm/serif) and B "Workbench" (dense/mono).
- **Rejected — gamification:** streaks, goals, badges, progress bars, confetti, analytics, and score history (PRD §6, SM-C2).
- **Rejected — score-driven Rating:** no suggested, pre-selected, or color-matched Rating, and no auto-advance after scoring (FR-34).
- **Rejected — dictionary dumps:** concise Drafts only (FR-14, SM-C1).
- **Rejected — global status bars** for Anki/Sync health; errors are per action.

## Open Questions

| ID | Question | Source |
|---|---|---|
| OQ-1 | Max recording length / auto-stop behavior | PRD Q1 |
| OQ-2 | Capture search as backlog grows | PRD Q2 |
| OQ-3 | Any cost visibility in UI (none in v1 so far) | PRD Q3 |
| OQ-4 | Cap on new Pronounce Cards per session (count shown; no cap) | PRD Q4 |
| OQ-5 | Anki card template visuals (FR-21) not designed | memlog |
| OQ-6 | How non-managed notes are reported in Setup (other Setup states are mocked) | PRD Q6, FR-6 |
| OQ-8 | Items search on phone not mocked (spine-only) | memlog |
| OQ-10 | Duplicate normalization (whitespace, apostrophes, diacritics) affects when the sheet appears | PRD Q5 |
| OQ-14 | Stale-audio warning (FR-23) and Sentence Note regenerate not mocked | FR-23, FR-24 |
| OQ-16 | Capture delete dialog copy (removes the Capture note and its suspended card; no Exercise Cards affected; Items unaffected, FR-13) — reuses Item dialog anatomy | FR-13 |

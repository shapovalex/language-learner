---
id: SPEC-languagelab
companions:
  - ../prd-languagelab/prd-languagelab.md
  - ../prd-languagelab/addendum.md
  - ../architecture-languagelab/architecture-languagelab.md
  - ../ux-languagelab/EXPERIENCE.md
  - ../ux-languagelab/DESIGN.md
sources:
  - ../../../spec-draft.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# LanguageLab v1

## Why

A vision to realize, plus a pain to solve. Its single user is a Russian-speaking learner who already uses Anki on iPhone, iPad, and desktop. They want to move English from B2 toward C1 and French to A1. The slow part is turning words and phrases they meet into good Anki notes by hand. They also have no way to practice pronunciation inside spaced repetition. LanguageLab is a personal web app that makes deck-building fast: capture text on any device, get an AI-drafted Item, approve it, and get four independently scheduled Exercises (Understand, Produce, Write, Pronounce). Pronounce adds Azure feedback. Anki stays the only store and the only scheduler, because a collection built over years must never be damaged by an experimental tool. Terms follow the PRD §3 Glossary.

## Capabilities

Each capability's full testable consequences are in the cited PRD FRs. Success references point to PRD §9 acceptance criteria (AC).

- **CAP-1: Run and reach**
  - **intent:** The user starts a versioned release with one documented command. They reach it privately over HTTPS from iPhone, iPad, and desktop, grant microphone access, and move between Captures, English, French, and Setup. Install and configuration are documented. (FR-1–FR-4)
  - **success:** AC1 and AC2 pass. The docs cover every item FR-4 lists.
- **CAP-2: Setup and repair**
  - **intent:** The user can check readiness, preview every Managed resource change, apply it only after confirming, and get a verified result. Schema migrations go through the same flow. Sibling Cards are never buried. (FR-5–FR-8)
  - **success:** AC3 and AC7 pass. Anki is unchanged before confirmation, and a repair leaves user-set scheduling options alone.
- **CAP-3: Captures**
  - **intent:** The user saves text from any browser as a Capture that is never studied, lists Captures newest first, and deletes one after confirming. (FR-9, FR-10, FR-13)
  - **success:** AC4 passes. With Anki down, the save shows a visible error and nothing is reported as saved.
- **CAP-4: Capture to Items**
  - **intent:** From a Capture, the user starts an Item with **Use as is** or a custom target-language value, a Language, a Category, and optional transient Generation context. After each Save they return to the same Capture to make more Items. (FR-11, FR-12)
  - **success:** AC5 passes. Generation context is never persisted.
- **CAP-5: Draft generation**
  - **intent:** The user gets a concise AI Draft for Vocabulary or Sentence that has passed schema validation, edits any field, and nothing reaches Anki until Save. (FR-14–FR-18)
  - **success:** AC9 and AC10 pass. Invalid output gets one retry and then an error. The model order changes through configuration alone.
- **CAP-6: Duplicate warning**
  - **intent:** Before creating an Item, or when its Target text is edited, the user is warned about normalized matches in the same Language and Category and can choose Open existing, Cancel, or Create anyway. (FR-19, FR-23)
  - **success:** AC8 passes. Creation is never blocked, and matches in the other Language or Category are not reported.
- **CAP-7: Item with four Cards**
  - **intent:** Saving a Draft creates one Item with four independently scheduled Cards in the correct managed decks. The Understand, Produce, and Write Cards render the agreed fronts, backs, and audio placement in Anki clients. (FR-20, FR-21)
  - **success:** AC6, AC7, and AC15 pass.
- **CAP-8: Maintain Items**
  - **intent:** The user searches Items within a Language and opens one with its current Anki values. They edit in place, regenerate the meaning, example, or Note with a side-by-side Preview, and delete permanently after a confirmation that names the Item. (FR-22–FR-25)
  - **success:** AC11, AC12, and AC21 pass. Discarding a Preview leaves the Item unchanged.
- **CAP-9: Reference audio**
  - **intent:** The user chooses an Azure Voice for the Item's locale, previews audio without touching Anki, and saves the exact previewed clip. Each browser remembers the last Voice per locale. (FR-26–FR-29)
  - **success:** AC13 and AC14 pass. A failed Save keeps the previous audio.
- **CAP-10: Pronunciation review**
  - **intent:** The user reviews new and due Pronounce Cards for one Language. For each Card they play the Reference audio, record Attempts, see Azure feedback for the locale, and retry as often as they like. Then they pick a Rating, which Anki's scheduler applies. Nothing from the Attempts is kept. (FR-30–FR-35)
  - **success:** AC16–AC19 pass. A failed Assessment or Rating submission leaves the Card unanswered and current.
- **CAP-11: Sync**
  - **intent:** LanguageLab keeps AnkiWeb current by syncing at startup, every five minutes, before and after each Pronunciation session, and at graceful shutdown. (FR-36)
  - **success:** AC20 passes. Sync failures are logged, retried at the next trigger, and never block work.

## Constraints

- Anki is the only persistent store. There is no application database. LanguageLab holds only runtime state, configuration, and the per-browser Voice preference. (NFR-2, AD-2)
- LanguageLab never creates, edits, or deletes Anki resources outside the configured Prefix. (NFR-1, AD-4)
- A failed Save never deletes or replaces the prior field or media value. (NFR-3, AD-6)
- Content changes commit only through an explicit Save. The only other commits are Capture Save, Setup confirmation, deletion confirmation, and Rating. (NFR-4)
- Anki schedules everything. The user always picks the Rating; an Assessment never chooses, pre-selects, or suggests one. (FR-34, addendum A6)
- Services bind to localhost only. Remote access goes only through Tailscale Serve HTTPS, which mobile microphone capture requires. There are no accounts and no login; the tailnet is the access boundary. (NFR-5, AD-16)
- The browser calls only the LanguageLab backend. Credentials never reach the browser. (NFR-6)
- Logs go to stdout/stderr only, carry request IDs, and never contain captured text, generated content, payloads, or audio. (NFR-7, NFR-9, AD-15)
- The stack is fixed: a Python/FastAPI wheel run with `uvx`, and vanilla HTML/CSS/JS served from the wheel. No Node, frontend build toolchain, Docker, or launchd. (NFR-11, addendum A1, architecture Stack)
- The UI is a responsive web app for iPhone Safari, iPad Safari, and desktop browsers. (NFR-10)
- Languages are `en-US` and `fr-CA`, and Russian is the only translation language. French feedback never names an incorrect sound. (FR-32)
- No IPA on Cards or in note fields. English review feedback may show the IPA that Azure returns. (FR-21, AD-14)
- OpenRouter runs with its default privacy and provider-routing behavior. (NFR-8)
- Understand, Produce, and Write Card templates use the Studio palette from DESIGN.md. (FR-21)

## Non-goals

- Multiple users, accounts, sharing, or a general-purpose Anki front-end.
- An application database, offline mode, PWA, or native app.
- Analytics, goals, streaks, pronunciation history, or study-capacity and backlog management.
- Importing or migrating existing Anki notes.
- Any Capture input other than text: no OCR, URL, selection, image, or audio capture.
- Automatic Ratings, Rating suggestions, a custom scheduler, or an exact copy of Anki's native queue.
- An IPA phonemizer, Speechace, SPPAS, other pronunciation providers, or naming incorrect French sounds.
- Exercise design for C1–C2, more languages or translation languages, and disabling Exercises per Item.
- Detecting conflicts between edits made in Anki and in LanguageLab (saves are last-write-wins).
- Deferred past v1: Capture search, spend guardrails or cost display, and a cap on new Pronounce Cards per session.

## Success signal

- All 22 PRD §9 acceptance criteria pass on the Mac Mini with real devices, and every FR's testable consequences hold.
- After one month of use, most new English and French Items come from LanguageLab rather than hand-made Anki notes, and Pronounce reviews keep pace with Study Cards. Both are read from Anki's own counts and deck stats. Neither Item volume nor Azure scores is a target.

## Assumptions

- Card templates use Studio colors and type as far as Anki allows. Where Figtree isn't embedded they fall back to the system font, they don't rely on app-only components, and Anki's night mode may override the colors. (UX OQ-5/DQ-4)
- The Setup preview lists unrecognized content under the Prefix as read-only "Not managed by LanguageLab" rows showing kind, name, and location. Non-managed notes and decks get no action. Orphan media and misplaced or unsuspended managed cards appear as separate opt-in repair items. (UX OQ-6/DQ-3, AD-3)
- Items search on phone is one column: a search field at the top and a result list below. Tapping a result opens the Item full screen. Matching is the same as on desktop. (UX OQ-8, AD-12)
- When the Target text of an Item with audio changes, an inline warning on the Audio field says "Audio no longer matches the text." and offers Regenerate audio. Save still works without regenerating. (UX OQ-14, FR-23)
- Regenerating the Sentence Note uses the same Current vs Preview pattern as the example: Keep current or Use preview. (UX OQ-14, FR-24)
- The Capture delete dialog uses the same layout as Item delete. Title: "Delete this Capture?" Body: "This removes the Capture from Anki. Items you made from it stay." Buttons: Cancel and Delete permanently. (UX OQ-16, FR-13)

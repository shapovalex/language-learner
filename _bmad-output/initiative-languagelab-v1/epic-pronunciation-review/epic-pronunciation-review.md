---
type: epic
title: "Pronunciation review"
parent: initiative-languagelab-v1
covers: [CAP-10]
after: []
assignee: ""
risk: high
---

# Pronunciation review

## Description

Per Language, the user reviews new and due Pronounce Cards: plays the Reference audio, records Attempts in the browser, sees Azure feedback shaped for the locale, retries freely, and picks a Rating that Anki's scheduler applies. Nothing from the Attempts is kept, and Sync runs before and after each session. Delivers CAP-10 in the spec.

## Outcome

Pronunciation practice happens inside Anki's spaced repetition on iPhone, iPad, and desktop — AC16–AC19, the microphone part of AC2, and the session part of AC20.

## Done when

1. On the released wheel, from iPhone Safari over Tailscale, the user plays Reference audio, records Attempts, sees Azure feedback, and retries without changing Anki (AC16).
2. iPhone Safari, iPad Safari, and a desktop browser grant microphone permission to LanguageLab over Tailscale HTTPS, and a denied permission shows the mic-blocked state (AC2, microphone part).
3. A Rating answers only that Pronounce Card through Anki's scheduler and loads the next; a retried Rating is not applied twice (AC17, AD-20).
4. Feedback never selects or suggests a Rating; `en-US` shows IPA and prosody, and `fr-CA` shows only overall, word, and position scores without naming a sound (AC18).
5. Nothing from recordings or Assessments is retained once the review ends, and logs carry no audio or scores (AC19, NFR-7).
6. Sync is requested on session start and end, including when the tab is hidden or closed, and a failed Assessment or Rating leaves the Card unanswered and current (AC20 session part, CAP-10).

## Boundaries

`features/pronunciation` (queue, session start/end, Attempt, Rating), `adapters/azure` assessment, PyAV conversion, the Pronunciation screen on phone, iPad, and desktop. Not a queue cap, pronunciation history, or other providers (spec Non-goals, Deferred).

## References

- parent — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, CAP-10
- prd — prd-languagelab/prd-languagelab.md, FR-30–FR-35, FR-36 (session triggers), AC16–AC20; addendum.md A5, A6
- architecture — architecture-languagelab/architecture-languagelab.md, AD-2, AD-5 (pronunciation start), AD-6 (queue selection), AD-14, AD-17, AD-20
- ux — ux-languagelab/mockups/S-Review.dc.html, S-iPadReview.dc.html; EXPERIENCE.md review flow

## Notes

- Decision (2026-10-08): this epic is last; no early recording spike.
- Waits on epic-reference-audio because: it needs the Azure adapter and `/api/media` for Reference playback.
- Waits on epic-capture-to-item because: it needs Pronounce Cards in the Pronunciation decks.
- Waits on epic-anki-setup-sync because: it needs the SyncRequester port and AnkiStore with the setup gate.
- Decision (2026-10-08): this epic owns the microphone-permission part of AC2, moved from epic-platform-baseline.
- Decision (2026-10-25): the user asked for a reasonably small number of stories: four entries in one lane. 7.1 is the tracer (queue, Reference playback, Rating with the reps check, session Sync) without Attempts. 7.2 adds Attempts and Azure feedback, the least certain part, after it because both change the review screen and the AnkiStore port. The Refactor sweep (7.3) comes before the released-wheel acceptance (7.4), as in epic 6.
- Decision (2026-10-25): Rating buttons are always enabled in 7.1; 7.2 adds the EXPERIENCE.md rule that enables them once one Attempt on the Card has an Assessment.
- Decision (2026-10-25): the user asked for a real Azure probe instead of an open question on 7.2. It ran with the repo `.env` key and public audio samples; results are in `research-azure-assessment/findings.md`, and its replies and samples are 7.2's fixtures. 7.4 still compares a real iPhone recording.
- Decision (2026-10-25): a nothing-heard Assessment (HTTP 200, every word Omission, all scores 0) shows an inline warning "Couldn't hear that Attempt" / "Record again closer to the microphone." with Record again; the Card stays unanswered and that Attempt does not enable Rating.
- Decision (2026-10-25): AnkiConnect queue and answer exchanges are hand-built in 7.1 and replaced in 7.4 by recordings from a new `language-lab-record-fixtures anki` wheel subcommand run in a throwaway Anki profile.

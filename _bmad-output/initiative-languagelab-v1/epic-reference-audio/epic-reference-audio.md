---
type: epic
title: "Reference audio"
parent: initiative-languagelab-v1
covers: [CAP-9]
after: []
assignee: ""
risk: medium
---

# Reference audio

## Description

In the Draft editor and Item detail, the user chooses an Azure Voice for the Item's locale, previews audio without touching Anki, and saves the exact previewed clip; each browser remembers the last Voice per locale. Adds `audio=replace` and `remove` to Save, deterministic media names, the `/api/media` route, the stale-audio warning, and audio regeneration. Delivers CAP-9 in the spec.

## Outcome

Items carry Reference audio the user picked and heard, retaining the previous note and clip until the new note write succeeds and safely tolerating partial failures after that write — AC13, AC14, adopted AD-6.

## Done when

1. On the released wheel, an audio Preview leaves Anki unchanged, and Save stores exactly the previewed MP3 under `<Prefix>_<ItemId>_<hash>.mp3`, served by `/api/media` (AC13, AD-7).
2. Regenerating audio keeps the old clip until the note write succeeds; a failure before that write preserves the previous note and audio, superseded media is removed only after that write, and failures in later steps stop the sequence without rollback and leave repairable leftovers (AC13, adopted AD-6).
3. The last `en-US` and `fr-CA` Voices persist independently in each browser's local storage (AC14).
4. Editing an Item's Target text shows "Audio no longer matches the text." with Regenerate audio, and Save still works without it (FR-23).
5. Deleting an Item with saved audio removes its managed media, and its Cards play the audio in Anki Desktop and AnkiMobile (AC21, AC15 with real audio).

## Boundaries

`ports/Speech` (TTS and voices), `adapters/azure` TTS and voice list, `features/audio`, Save `replace`/`remove` and media steps, `/api/media`, `static/voice-pref.js`, and the audio card on the Draft editor and Item detail. Not pronunciation assessment (epic-pronunciation-review).

## References

- parent — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, CAP-9; Assumptions (stale-audio warning)
- prd — prd-languagelab/prd-languagelab.md, FR-20 (audio part), FR-23 (stale audio), FR-24 (audio regeneration), FR-26–FR-29, AC13, AC14; addendum.md A2, A5 (Azure)
- architecture — architecture-languagelab/architecture-languagelab.md, AD-6, AD-7, AD-13 (voice preference), AD-14 (Preview)
- ux — ux-languagelab/mockups/C-Draft.dc.html, S-DraftPhone.dc.html, S-ItemDetail.dc.html; EXPERIENCE.md audio player and error states

## Notes

- Waits on epic-capture-to-item because: it extends the Draft editor and Save.
- Waits on epic-maintain-items because: it extends the editable Item detail and Item delete.

- Decision (2026-10-24): the user requests a reasonably small story count, ideally fewer than five.
- Decision (2026-10-24): approved four stories in one lane: Draft Preview and Save tracer; existing Item audio lifecycle; Refactor sweep; integrated end-to-end and released-wheel acceptance, with no CAP-9 scope deferred.
- Tracer bullet: 6.1 demonstrates choosing a locale Voice, explicitly previewing and accepting an MP3, saving that exact clip with a new Draft, and playing the stored clip through /api/media; it owns Speech/Azure, binary api.js, audio=replace media writes and the saved-audio read contract, while 6.2 owns existing-Item audio UI and replacement/removal lifecycle completion.
- Sequencing: 6.1 waits on 4.1 and 4.3 for the Draft editor, existing Save and Item read contract; 6.2 waits on 6.1, 5.1 and 5.3 for the audio contracts, editable Item and managed-media deletion; 6.3 follows both implementations; 6.4 follows cleanup and verifies the integrated released wheel; these stories share Save, media and screen infrastructure and cannot run in parallel.
- Assumption (2026-10-24): the builder will define the unspecified Voice-list response shape, absent or unavailable stored-Voice fallback and removal-control copy against FR-26–29 and the UX, recording choices in its plan; none changes the proposed story boundaries.
- Assumption (2026-10-24): a preview is associated with the Target text used to create it, so subsequent Target edits must warn or invalidate that candidate before it can be mistaken for matching audio; Save may still explicitly keep existing audio as FR-23 permits.
- Failure boundary: AD-6 permits a reported failure after a successful note write (for example, during cleanup); the previous note/audio is guaranteed untouched only until the note write succeeds, and partial leftovers are tolerated and repaired through Setup rather than inline rollback.

- Source conflict: CAP-9 / AC13 / NFR-3 — the spec, UX and original epic wording promise the previous audio after every failed Save, while adopted AD-6 permits an error after a successful note write when later cleanup fails.
- Decision (2026-10-24): follow the previously adopted architecture AD-6 write-order contract; the approved Outcome and Done when use its note-write boundary, with no inline rollback and Setup repairing partial leftovers. The broader spec and UX wording can be reconciled through bmad-spec separately.

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

Items carry Reference audio the user picked and heard, without ever losing the previous clip on failure — AC13, AC14.

## Done when

1. On the released wheel, an audio Preview leaves Anki unchanged, and Save stores exactly the previewed MP3 under `<Prefix>_<ItemId>_<hash>.mp3`, served by `/api/media` (AC13, AD-7).
2. Regenerating audio keeps the old clip until Save succeeds; a failed Save keeps the previous audio, and the superseded file is removed only after the note write (AC13, AD-6).
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

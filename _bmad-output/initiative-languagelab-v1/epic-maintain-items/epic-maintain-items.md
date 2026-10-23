---
type: epic
title: "Maintain Items"
parent: initiative-languagelab-v1
covers: [CAP-8]
after: []
assignee: ""
risk: medium
---

# Maintain Items

## Description

The user searches Items within a Language, opens one with its current Anki values, edits it in place, regenerates the Russian meaning, example, or Sentence Note with a side-by-side Preview, and deletes it permanently after a confirmation that names the Item. Builds on the view-only Item detail from epic-capture-to-item. Delivers CAP-8 in the spec.

## Outcome

The user keeps existing Items correct without leaving LanguageLab or losing review history — AC11, AC12, AC21.

## Done when

1. On the released wheel, editing an Item updates the existing note without replacing its Cards or review histories, and a duplicate warning appears when Target text is edited into a match (AC11, FR-23).
2. A managed field edited directly in Anki shows when the Item is next opened in LanguageLab (AC12).
3. Regenerating the meaning, example, or Sentence Note shows Current vs Preview; Keep current leaves the Item unchanged, and only Save commits (FR-24, NFR-4).
4. Search matches normalized substrings in Target, Russian, and alternatives across both Categories of one Language, on phone and desktop layouts (FR-22, AD-12).
5. Delete, after a confirmation naming the Item, removes the note, its four Cards and histories, and every media file named `<Prefix>_<ItemId>_*`, checked with a test media file in Anki (AC21, AD-6).

## Boundaries

`features/items` search, update, and delete; Items list, editable Item detail, regenerate compare pair, and Item delete dialog. Not Voice, audio Preview, audio regeneration, or the stale-audio warning (epic-reference-audio).

## References

- parent — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, CAP-8; Assumptions (phone search layout, Sentence Note regenerate)
- prd — _bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md, FR-22–FR-25, NFR-3, NFR-4, AC11, AC12, AC21
- architecture — _bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md, AD-4 (Prefix guard), AD-6 (write order), AD-7 (managed media), AD-9, AD-11 (regeneration), AD-12, AD-13 (router dirty state)
- ux — _bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md, Items and Item detail copy, search, row audio presence, compare pair, delete dialog, dirty and error states, responsive layouts
- ux — _bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md, Studio visual language
- ux — _bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Items.dc.html
- ux — _bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-ItemDetail.dc.html
- ux — _bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Delete.dc.html

## Notes

- Decision (2026-10-08): delete's media removal is verified here with a test media file; epic-reference-audio repeats it on audio saved through Preview.
- Waits on epic-capture-to-item because: it needs ItemContent, Save, Item read and detail, generation, and the duplicate read.
- Waits on epic-captures because: Item delete reuses the delete dialog pattern.
- Decision (2026-10-23): the user requests a reasonably small number of stories, ideally fewer than five.
- Decision (2026-10-23): the user approved three stories: search/open/edit, content regeneration, and deletion with released-wheel acceptance; acceptance accompanies the last functional story to keep the set small, with automated checks in every story, and the set is approved for publication by commit.
- Tracer bullet: story 5.1 makes search -> fresh Item read -> edit -> Save runnable on phone and desktop using the existing ItemId; story 5.2 follows to prove the least certain integration, regeneration without replacing Item identity or unrelated edits.
- Sequencing: 5.1, 5.2 and 5.3 share the Item detail and API surface and run in that order; 5.3 also waits on 5.2 because its released-wheel acceptance checks the whole epic, so no stories are proposed in parallel.
- Risk: 5.1 is high because an incorrect update could lose fields or review history; 5.2 is medium because generated content remains a Preview until Save; 5.3 is high because deletion permanently removes Cards and histories.
- Independent check for high-risk stories 5.1 and 5.3: the user verifies note/Card identity, scheduling and history preservation before deletion, and deletion isolation on a LanguageLabDev released wheel in 5.3, beyond those stories' automated checks.
- Implementation context: existing Save already updates by ItemId; Item reads and duplicate matching exist, while the Items list is a heading and detail is view-only; reuse these contracts rather than rebuilding them.
- Implementation context: Draft generation currently issues a fresh ItemId; regeneration must share the Category generation function/model and return the full generated model (AD-11), preserving the existing ItemId and unrelated local edits.
- Open question (5.1): choose the smallest read-only audio-presence metadata contract for the Items row icon required by EXPERIENCE.md; current Item reads do not expose it, and audio controls, generation and the stale-audio warning remain owned by epic-reference-audio.
- Verification: no epic-5-specific test plan exists, so no separate closing end-to-end story is proposed; 5.3 includes the released-wheel acceptance required by this epic and the initiative, using an existing test clip for media cleanup and reviewed Cards for history checks.

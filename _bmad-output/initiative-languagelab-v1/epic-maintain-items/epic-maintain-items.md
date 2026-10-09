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
- prd — prd-languagelab/prd-languagelab.md, FR-22–FR-25, NFR-3, NFR-4, AC11, AC12, AC21
- architecture — architecture-languagelab/architecture-languagelab.md, AD-6, AD-9, AD-11 (regeneration), AD-12, AD-13 (router dirty state)
- ux — ux-languagelab/mockups/S-Items.dc.html, S-ItemDetail.dc.html, S-Delete.dc.html

## Notes

- Decision (2026-10-08): delete's media removal is verified here with a test media file; epic-reference-audio repeats it on audio saved through Preview.
- Waits on epic-capture-to-item because: it needs ItemContent, Save, Item read and detail, generation, and the duplicate read.
- Waits on epic-captures because: Item delete reuses the delete dialog pattern.

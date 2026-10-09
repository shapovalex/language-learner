---
type: epic
title: "Capture to Item: Drafts, duplicates, and four Cards"
parent: initiative-languagelab-v1
covers: [CAP-4, CAP-5, CAP-6, CAP-7]
after: []
assignee: ""
risk: high
---

# Capture to Item: Drafts, duplicates, and four Cards

## Description

The core deck-building flow: from a Capture the user starts an Item (Use as is or custom Target text, Language, Category, transient Generation context), gets a schema-validated OpenRouter Draft, edits it, is warned about duplicates, and saves one Item with four independently scheduled Cards whose Understand, Produce, and Write templates render as agreed. Includes reading an Item and a view-only Item detail screen so "Open existing" works. Delivers CAP-4–CAP-7 in the spec.

## Outcome

The user turns a Capture into finished Anki Items in one pass — AC5, AC6, AC7 (independent schedules), AC8, AC9, AC10, AC15.

## Done when

1. On the released wheel, one Capture creates an English Vocabulary and a French Sentence Item; each Save makes one note and exactly four Cards in the correct Study and Pronunciation decks with independent schedules, and returns to the same Capture (AC5, AC6, AC7).
2. OpenRouter Drafts validate against the strict schema with one retry, then `llm_invalid_output`; Vocabulary Drafts have a removable example and never a mnemonic; the model order changes through `.env` alone (AC9, AC10, FR-17).
3. A normalized duplicate in the same Language and Category offers Open existing (opens the view-only Item detail), Cancel, and Create anyway; matches in the other Language or Category are not shown (AC8).
4. Understand, Produce, and Write Cards show the agreed fronts, backs, hints, and audio placement in Anki Desktop and AnkiMobile, checked with a test clip stored in Anki (AC15).
5. Generation context is never persisted, and a retried Save with the same ItemId updates instead of creating a second note (AD-20).

## Boundaries

`domain/items.py` (ItemContent, generation schemas, `normalize_text`), `features/drafts`, `features/items` (Save with `audio=keep`, Item read, duplicate read), `adapters/openrouter`, final template markup and CSS under `adapters/anki/templates/`, New Item, Draft editor, duplicate sheet, and view-only Item detail screens, and the model-evaluation fixtures doc (FR-4). Not search, edit, regenerate, or delete (epic-maintain-items); not Voice, Preview, or audio replace/remove (epic-reference-audio).

## References

- parent — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, CAP-4–CAP-7
- prd — prd-languagelab/prd-languagelab.md, FR-11, FR-12, FR-14–FR-21, NFR-3, NFR-4, NFR-8, AC5–AC10, AC15; addendum.md (OpenRouter call, fields)
- architecture — architecture-languagelab/architecture-languagelab.md, AD-6, AD-8, AD-9, AD-10, AD-11, AD-12, AD-20, Deferred (card template visuals)
- ux — ux-languagelab/mockups/S-NewItem.dc.html, C-Draft.dc.html, S-DraftPhone.dc.html, S-Duplicate.dc.html, S-ItemDetail.dc.html; DESIGN.md Studio palette for templates

## Notes

- Decision (2026-10-08): Item read and a view-only Item detail screen live here so "Open existing" is verifiable in this epic.
- Decision (2026-10-08): Save is built per AD-6 with `audio=keep`; epic-reference-audio adds `replace` and `remove`.
- Waits on epic-captures because: it starts Items from the Capture detail screen.
- Waits on epic-anki-setup-sync because: it needs the Vocabulary and Sentence note types, deck tree, ord-to-deck mapping, and codec.

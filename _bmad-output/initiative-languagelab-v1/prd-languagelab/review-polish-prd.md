# Polish Log: prd-languagelab.md

Date: 2026-10-08. Process: bmad-review, structure lens first, then prose. Findings applied directly. The PRD was 5,654 words before the pass, and the net change is small. No IDs, numbering, frontmatter, scope or decisions changed.

Purpose read: this PRD helps downstream BMad workflows (architecture, UX, tickets) build v1 of LanguageLab. Structure model: reference/specification. The overall shape is sound, so no sections were cut, merged or moved.

## Structure (3)

1. §4.8 FR-33 now has a **Consequences (testable):** block like every other FR. The existing sentence "Attempts and Assessments never change Anki." moved into it. SM-1 relies on "every FR's testable consequences", so the block matters.
2. §11: one bundled bullet was split into three. Its cross-reference "§4.3 FR-13 / §4.6 FR-20–FR-23" was wrong, because FR-13 is Capture deletion. It now reads FR-20 (optional audio), FR-23 (re-check and stale-audio warning) and §3 Glossary / §4.1 FR-4 (LanguageLab-only usage convention).
3. §0 Document Purpose: the two sentences about the addendum were condensed into one.

## Prose and terminology (15)

- Glossary terms are now capitalized consistently in the User Journeys:
  - UJ-1: Capture
  - UJ-2: Capture (three times), Draft, Item
  - UJ-3: Reference audio, Attempt, Sync, Attempts
  - UJ-5: Item
- §1 Vision: "assessment" became "Assessment" and "rating" became "Rating".
- §4.6 table: "optional hint" became "optional Hint" in the Produce and Write rows.
- Glossary, Note field: "It is not the same thing as" became "Not to be confused with".
- FR-11: removed the repeated "into the target Language".
- FR-28: "has been saved successfully" became "saves successfully".
- FR-30: "Ordering is simple and defined by the app" became "LanguageLab defines a simple order".
- NFR-11: the addendum pointer became a parenthetical.

## Preserved on purpose

- The Glossary's usage-convention sentence under Pronunciation decks repeats FR-4. Both stay because each points to the other.
- The FR-17 Note repeats FR-4's fixture guidance. It stays as a cross-referenced reminder.
- Section §9 overlaps the FR consequences. It stays because SM-1 defines §9 as the headline gate.

## Declined (would change meaning)

- NFR-1: "Inside the Prefix there are no pre-existing user notes." This reads as a stated assumption more than a requirement, and it overlaps Open Question 6. Rewording it as "is assumed to contain" would change its normative force, so it is left as written. The author should decide.
- §1 Vision lowercase "capture", "learning item" and "reference audio". These come before the Glossary in a narrative passage. Capitalizing them or replacing "learning item" was skipped to keep the author's voice. Consider aligning them later if strict term use is wanted everywhere.

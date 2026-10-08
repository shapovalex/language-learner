# Polish log: addendum.md

Date: 2026-10-08. Review: bmad-review, lenses `structure` then `prose`. Style guide: Microsoft Writing Style Guide. Reader: humans.

Purpose read: this addendum gives architects and implementers the binding technical decisions (runtime, config, Anki model, integrations) behind `prd-languagelab.md`.
Structure model: Reference/Database. 992 words before, about 990 after (negligible change).

## Structure pass: no edits

- PRESERVE: the A1-A7 order and headings. Each section is a self-contained lookup unit.
- PRESERVE: the repeated shared fields (`ItemId`, `Target`, `Russian`, `Hint`, `Audio`, `SchemaVersion`) in the Vocabulary and Sentence lists in A3. A full list per note type works better for lookup than factoring shared fields out.
- PRESERVE: "Run manually in a terminal" and "The process stays attached to the terminal" (A1). They overlap slightly but state separate constraints.
- PRESERVE: A7 External References.

## Prose pass: 6 edits applied

| # | Section | Before | After | Why |
|---|---------|--------|-------|-----|
| 1 | A1 Backend | "with operational errors and request IDs and no content" | "and contain operational errors and request IDs, never content" | Removed the awkward double "and" |
| 2 | A1 Network | "mandatory, not optional" | "mandatory" | Removed redundancy |
| 3 | A2 | "Before it is configured, it should be evaluated" | "Before a model is configured, it should be evaluated" | Fixed an unclear "it" |
| 4 | A3 Note types | "The configured Prefix replaces" | "The configured Prefix (`ANKI_PREFIX`) replaces" | Links the term to its config key |
| 5 | A3 Deck hierarchy | "leaves them out" | "excludes them" | More precise |
| 6 | A4 | "OpenRouter's default privacy and provider-routing behavior (NFR-8)." | "... behavior applies (NFR-8)." | The fragment had no verb, so the decision was unclear |

## Declined

- Adding the Oxford comma throughout. The author leaves it out consistently, so this is kept as an intentional style choice.
- Rewording "as documented (FR-4)" in A2. It could mean "per the docs" or "and record the result", so rewording it might change the meaning.

Code blocks, config keys, field names, the deck tree, commands, URLs, frontmatter, A1-A7 IDs, and FR/NFR references were not changed.

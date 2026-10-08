# Reconciliation: spec-draft.md → PRD + Addendum

- Source: `spec-draft.md`
- Targets: `prd-languagelab.md`, `addendum.md`
- Date: 2026-10-08

I walked the source statement by statement. Fidelity is high: there are no hard contradictions with an explicit source statement. The 7 gaps below are mostly small alterations, an unaddressed mechanism, and untagged inferences.

## Gaps

### G1. Pronounce-review exclusivity is asserted, but no mechanism or constraint is given (weakened). Severity: medium
- **Source:** "Ordinary Anki clients own Understand, Produce, and Write reviews. LanguageLab exclusively owns Pronounce reviews." and "The managed hierarchy separates ordinary Anki study from app-only pronunciation cards."
- **PRD location:** §3 Glossary "Pronunciation decks … reviewed only in LanguageLab"; §4.8 description; addendum §A3 "Keeping Pronounce Cards in a separate branch keeps them out of ordinary Anki study, while Anki still schedules them."
- **Issue:** No FR says how exclusivity holds. A separate deck branch is still visible and reviewable in AnkiMobile and Anki Desktop. The addendum's rationale claims more than the structure delivers, and this claim does not appear in the source.
- **Suggested fix:** Add an Open Question, or an FR-30 consequence, that states the mechanism. Option A: it is a user convention that the user does not study the Pronunciation branch in Anki clients. Option B: Setup applies a deck-options preset to the Pronunciation branch that keeps these cards out of native queues, and the AnkiConnect-built queue in FR-30 still works with that preset. Soften the addendum §A3 sentence to "separates them from ordinary Study decks".

### G2. Acceptance criterion 1 dropped the concrete wheel/uvx test (altered). Severity: low
- **Source:** AC1 "A versioned **wheel** starts successfully on the Mac Mini through the documented `uvx --from ... language-lab` command…"
- **PRD location:** §9 item 1 "A versioned release starts … through the documented command"; FR-1. The command is kept only in addendum §A1.
- **Issue:** The release gate no longer checks the packaging format or the uvx invocation, so a non-wheel release would pass.
- **Suggested fix:** In §9 item 1, write "versioned wheel … via the documented `uvx --from <wheel> language-lab` command (addendum §A1)".

### G3. Russian translation language changed from "for the initial version" to "always" (altered). Severity: low
- **Source:** "Russian remains the translation language for the initial version."
- **PRD location:** §3 Glossary, Language: "The translation language is always Russian."
- **Issue:** "Always" overstates the source. §7.2 correctly defers other translation languages, so the glossary contradicts the PRD's own scoping.
- **Suggested fix:** Change it to "In v1 the translation language is Russian."

### G4. "No dictionary dumps" is not carried to Sentence generation (dropped for Sentence). Severity: low
- **Source:** Under Draft generation, applying to both Categories: "It does not produce dictionary dumps or mnemonics."
- **PRD location:** FR-14 (Vocabulary) only. FR-15 (Sentence) is silent.
- **Suggested fix:** Add to FR-15: "Generation never produces a dictionary dump." The mnemonic rule is moot for Sentences because the Sentence note has no Mnemonic field.

### G5. The FR-15 assumption has Sentence generation fill Hint, which the source never lists as generated (altered via assumption). Severity: low
- **Source:** Generation produces "one contextually relevant primary Russian meaning; a short list of relevant alternatives when useful; applicable grammatical metadata; one Vocabulary example…". Hint is not listed. Regeneration covers "translations, examples, notes, or audio", which also excludes hints.
- **PRD location:** FR-15 `[ASSUMPTION: Sentence generation fills Russian, optional Hint and optional Note…]`; §11.
- **Issue:** The assumption is tagged but goes beyond the source's explicit generation list. It is also asymmetric: FR-14 does not have Vocabulary generate Hint.
- **Suggested fix:** Drop Hint from the FR-15 assumption (generate Russian and Note only). Otherwise, confirm it with the user and apply it to both Categories consistently.

### G6. Sentence `Russian` field semantics are missing in the addendum (dropped detail). Severity: low
- **Source:** Sentence fields: "`Russian`, containing one primary contextual meaning and optional short alternatives".
- **PRD location:** Addendum §A3 Sentence lists a bare `Russian`. The Vocabulary entry keeps the annotation. The §3 Glossary "Russian meaning" covers the concept indirectly.
- **Suggested fix:** Copy the annotation to the Sentence `Russian` field in addendum §A3.

### G7. Untagged inferences presented as fact (additions; none contradicts the source). Severity: low
- **PRD locations and source status:**
  - §2.1 JTBD "high-quality Anki item **in under a minute**": the source has no time target.
  - §2 "its builder (Oleksii) … already uses Anki and studies on iPhone, iPad and desktop": inferred.
  - NFR-8 "No additional data-retention guarantees are required in v1": inferred from "OpenRouter's default privacy … behavior".
  - FR-34 / §6 "Assessment scores never … **suggest** a Rating" and "no Rating suggestions": the source says only that scores never *choose* a rating. This is a stricter rule.
  - FR-34 "If submission fails, the user sees an error and the Card stays current and unanswered", and FR-30 empty-state message: reasonable, but not in the source.
  - Addendum §A3 rationale sentence (see G1).
- **Suggested fix:** Tag these `[ASSUMPTION]` and index them in §11, or remove the quantitative claim ("under a minute").

## Preserved (confirmed)

Everything else in the source is carried into the PRD or the addendum with matching meaning:
- Purpose and milestones: B2→C1 and A1, long-term C2, advanced exercises out of scope, `en-US`/`fr-CA`.
- All 10 product-boundary exclusions: §6 and NFR-10.
- Anki authority and runtime-only state: NFR-2.
- Runtime architecture, logging rules, frontend constraints, local-storage limit, and network bindings/Tailscale/secure-context rationale: FR-1, FR-2, NFR-5–7, NFR-9–11, addendum §A1.
- Config file location, `.env.example` keys, model-ID caveat, and keyless AnkiConnect warning: FR-4, addendum §A2.
- Navigation: FR-3.
- Prefix ownership boundary, owned-resource list, user field-editing rights, read-on-open and last-write-wins: NFR-1, FR-22, FR-23, addendum §A3.
- The five note types, all fields, no IPA/voice metadata, full deck tree, prefix substitution, and sibling-burying rule: addendum §A3, FR-8.
- Exercise table, four cards per note, no per-item disabling, card-back content, audio-placement rules, advisory typing, and independent schedules: FR-20, FR-21, FR-31.
- Capture workflow steps 1–11 and non-persistence of Generation context: FR-9, FR-11–FR-13.
- Duplicate normalization and the three options, never blocking: FR-19.
- OpenRouter parameters, separate schemas, generation contents, Clear button, one retry and then error, and draft-until-Save: FR-14, FR-16–FR-18, addendum §A4.
- Preview-and-save rules, exact audio bytes, deferred removal of superseded audio, and permanent deletion with named confirmation and no trash: FR-24, FR-25, FR-28, NFR-3, NFR-4.
- Azure voice catalog filtering, backend-only credentials, per-locale browser voice memory, and no implicit regeneration: FR-26–FR-29.
- Pronunciation review flow steps 1–10, rating as the commit action, feedback limits per locale, no Speechace/SPPAS/IPA, user-chosen ratings, and ephemeral data: FR-30–FR-35, addendum §A5.
- AnkiConnect scheduler use, simple queue, the five sync triggers, non-blocking retried sync failures, visible Anki errors, and no sync while stopped: FR-30, FR-36, §5.2, addendum §A6.
- Setup steps 1–6, idempotency, and schema-versioned in-prefix migrations: FR-5–FR-7.
- Failure-semantics table: §5.2 and NFR-3.
- Acceptance criteria 2–22: §9 items 2–22, equivalent. AC1 is covered under G2.
- External references: addendum §A7.

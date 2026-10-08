# Validation Report — language-learner

- **DESIGN.md:** `_bmad-output/initiative-languagelab-v1/ux-languagelab/DESIGN.md`
- **EXPERIENCE.md:** `_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md`
- **Run at:** 2026-10-08T16:03:47-04:00

## Overall verdict
The pair is a usable contract. Every color token has a hex value, every `{token}` reference resolves, all 14 mockups are cited inline, and each in-app PRD journey has a Key Flow with a climax and a failure path. No finding is critical. Three high findings should be fixed before story-dev: Reference audio auto-play contradicts FR-31 and the iOS user-gesture rule; the 2px `border` outline on text fields (1.38:1) fails the stated WCAG 2.2 AA non-text contrast target; and the Pronunciation surface has no cold-load / pre-session Sync state. No spine content contradicts `.memlog.md`. One memlog decision is missing from the spines (see §7).

**Post-review status.** All 19 findings are addressed in the spines (critical 0, high 3, medium 6, low 10): 4 resolved by user decision, 10 fixed, 5 fixed with `[ASSUMPTION]` specs. The three high findings were closed by decisions logged in `.memlog.md`: Reference audio is tap-to-play and never auto-plays; new `border-input` #948A7E for fields, with outline and Rating buttons keeping #E2DACF as an accepted deviation; pre-session Sync runs in the background. en-US IPA in feedback was kept by decision. The category verdicts below are the reviewer's and describe the pre-fix state; each finding carries its resolution. After the fixes, 254 token references and 14 mockup links resolve (memlog). The memlog records 12 low findings from the reviewer summary; review-rubric.md contains 10 low bullets, and those are reported here.

## Category verdicts
- Flow coverage — adequate
- Token completeness — adequate
- Component coverage — adequate
- State coverage — adequate
- Visual reference coverage — strong
- Bloat & overspecification — strong
- Inheritance discipline — adequate
- Shape fit — strong

_Verdicts are the reviewer's and describe the pre-fix state._

## Findings by severity

### Critical (0)
None.

### High (3)

**[Flow coverage]** — Reference audio auto-play contradicts FR-31 and the iOS user-gesture rule (§ EXPERIENCE.md Interaction Primitives; Responsive & Platform; J3 step 2)
Interaction Primitives says "Reference audio auto-plays before the first Attempt and before each retry (FR-31)". FR-31 only says the user *can play* it. iOS Safari needs a user gesture to start playback, and the first Card loads with no gesture. The order of events after "Try again" is also undefined; J3 step 2 inherits the ambiguity.
Fix: Pick one rule: an explicit play tap (matches FR-31 and iOS), or auto-play only on a gesture-initiated load with a stated fallback. Then state the order of "Try again", replay and record.
Resolution: **resolved by decision**. Reference audio never auto-plays, on any device: tap Reference to listen, then Record. "Try again" starts recording at once and never plays the Reference.

**[Token completeness]** — `border` #E2DACF (1.38:1) is the only boundary of text fields, failing WCAG 1.4.11 (§ DESIGN.md Colors `border` row; components `text-field`, `rating-button`)
`border` is the only visible boundary of `text-field`, `button-secondary` and `rating-button` on white cards, at 1.38:1 (1.32:1 on `ground`). For text inputs the boundary identifies the control, and WCAG 2.2 AA 1.4.11 (the stated target) requires 3:1.
Fix: Add a stronger outline token (≥3:1 against `surface`) for field borders, or give fields a `surface-sunken` fill. State the decision for buttons explicitly.
Resolution: **resolved by decision**. New token `border-input` #948A7E (3.39:1 on white, 3.22:1 on ground) for text fields, textareas and selects. Outline buttons and Rating buttons keep #E2DACF as an accepted deviation (label-identified). Mockups updated.

**[State coverage]** — Pronunciation has no cold-load / pre-session Sync state (§ EXPERIENCE.md State Patterns; J3 step 1)
PRD UJ-3 and FR-36 sync before the session, which can take seconds. No loading row exists, J3 step 1 jumps straight to the queue chip, and Sync-failure behavior is unstated.
Fix: Add a row for syncing/loading the queue, with Sync failure proceeding silently, and add the step to J3.
Resolution: **resolved by decision**. Pre-session Sync runs in the background and is non-blocking; the first Card shows immediately; no Sync UI. A first-Card skeleton was added as `[ASSUMPTION]`.

### Medium (6)

**[Component coverage]** — Phone Menu has no visual or behavioral spec (§ EXPERIENCE.md IA → Navigation model; DESIGN.md Components → App header)
The Menu is the only top-level navigation on iPhone, yet neither spine specifies presentation, contents, focus or close. It survives only as `[ASSUMPTION]` and OQ-12.
Fix: Add a Menu row to both spines (e.g. a bottom sheet listing the four areas with `aria-current`, closing on selection or scrim).
Resolution: **fixed as assumption**. Menu specified as a bottom sheet.

**[Component coverage]** — Unsaved-changes confirmation reuses the delete-specific Alert dialog (§ EXPERIENCE.md Component Patterns → Alert dialog; DESIGN.md Components → Alert dialog)
The Alert dialog visual spec is delete-specific (trash icon, Destructive button first, Card chips). Whether "Discard" is destructive-styled or which icon appears is unclear.
Fix: Add an unsaved-warning variant naming its icon (or none), button order and styles.
Resolution: **fixed as assumption**. Unsaved variant: no icon, Discard / Keep editing.

**[State coverage]** — Items (per Language) lacks loading and empty states (§ EXPERIENCE.md State Patterns)
Only "Search no matches" is covered; the Loading row omits Items.
Fix: Add both rows with copy, e.g. "No English Items yet. Items are made from Captures."
Resolution: **fixed as assumption**. Items empty/loading copy added.

**[State coverage]** — Setup "nothing to change" state unspecified (§ EXPERIENCE.md State Patterns; J5 step 7)
J5 step 7 references it, but whether Apply is disabled, hidden or shown with a message is unclear.
Fix: Add a row with copy and the Apply button's state.
Resolution: **fixed as assumption**. "Nothing to change…" callout; Apply setup is hidden.

**[Inheritance discipline]** — en-US phoneme pills render IPA despite the "No IPA" non-goal (§ DESIGN.md Weak-word panel; EXPERIENCE.md Weak-word panel / Pronunciation Feedback)
`S-Review` shows IPA symbols; addendum, spec-draft and PRD non-goals say no IPA overlay. Neither spine commits the alphabet or the reasoning.
Fix: Commit the alphabet and record the reasoning, or switch to a non-IPA rendering.
Resolution: **resolved by decision**. en-US feedback keeps IPA as returned by Azure; the PRD IPA ban applies to Cards, not review feedback.

**[Inheritance discipline]** — Memlog decision "Capture detail does not show Items created from it" missing from spines (§ EXPERIENCE.md IA → Capture detail; Component Patterns)
A builder adding a "made from this capture" list would not be stopped.
Fix: State it in the IA row or the Success banner rule.
Resolution: **fixed**.

### Low (10)

**[Flow coverage]** — J2 departs from PRD UJ-2 without a deviation note (§ EXPERIENCE.md J2)
Custom value instead of Use as is, no edits, no Mnemonic. The memlog sanctions this, but unlike J1 the flow carries no deviation note, so no flow exercises Draft editing (FR-18) or the Mnemonic.
Fix: Add a one-line note like J1's, or add a variant step where Oleksii edits a field and adds a Mnemonic.
Resolution: **fixed**.

**[Token completeness]** — Component values bypass the scale as raw literals (§ DESIGN.md frontmatter `components`)
`readiness-fix-hint.radius: 16px`, `bottom-sheet.radius: '28px 28px 0 0'`, `nav-pill.height: 44px`, and `queue-count-chip` fontSize/weight (13/700) match no token.
Fix: Reference existing tokens, or add a `count` typography role.
Resolution: **fixed**.

**[Token completeness]** — `rounded.word-pill-tablet` unused; destructive button lacks small height (§ DESIGN.md frontmatter; Components → Buttons, Inline alert)
No component references `rounded.word-pill-tablet`. Prose gives destructive buttons a 44px in-alert height, while `button-destructive.height` is 52 with no small variant.
Fix: Add `radiusTablet` to the word-pill components and `heightSmall: 44px` to `button-destructive`.
Resolution: **fixed**.

**[Component coverage]** — Component names drift between files; Level meter and Progress card half-specified (§ both spines, Components sections)
"Queue-count chip" vs "Queue count", "Text field / textarea / select" vs "Text field", "Verification banners" vs "banner". Level meter has no DESIGN.md bullet; Progress card has no behavior row.
Fix: Align names verbatim, add a Level meter bullet and a Progress card behavior row.
Resolution: **fixed**. Progress card rule (leaving during Apply doesn't cancel) added as `[ASSUMPTION]`.

**[Component coverage]** — Back link and text-source choice have no component spec (§ EXPERIENCE.md Navigation model, Key strings; DESIGN.md Text field)
The "‹ Captures" back link and the "Use as is / Custom value" choice are not specified in either file.
Fix: Name the control type (radio pair or segmented picker) and the back-link style.
Resolution: **fixed**.

**[State coverage]** — Smaller state gaps: voice fetch failure, model outage, Generate disabled, Assessing (§ EXPERIENCE.md State Patterns; Component Patterns)
Voice catalog fetch failure (FR-26), OpenRouter outage vs validation failure (PRD §5.2), when "Generate draft" is disabled, and the unmocked "Assessing" rule vs the Rating row.
Fix: Add one row each, or fold them into existing rows.
Resolution: **fixed as assumption**. "Couldn't load voices", "Couldn't reach the model", Generate-draft disabled reason, Reference disabled while recording.

**[Visual reference coverage]** — Key strings differ from the mockups they cite (§ EXPERIENCE.md Voice and Tone → Key strings; Pronunciation Feedback)
`S-Items` shows "Search English Items" vs spine "Search English or Russian"; `S-Review` shows "Complete" vs "Complete(ness)" / "Completeness".
Fix: Commit one string per slot, drop "(ness)", mark the spine value canonical.
Resolution: **fixed**.

**[Bloat & overspecification]** — Components prose restates frontmatter literals (§ DESIGN.md Components; EXPERIENCE.md Pronunciation Feedback)
E.g. "`border` (`#E2DACF`) fill, `ink-muted` text (5.1:1)" in Disabled button; pixel values in Success banner and Queue-count chip; Pronunciation Feedback rows repeat IA and Component Patterns.
Fix: Keep the token references and drop the restated literals.
Resolution: **fixed**.

**[Inheritance discipline]** — Flow titles, glossary and OQ-16 drift from the PRD (§ EXPERIENCE.md Key Flows headings; Glossary; OQ-16)
Key Flow titles use memlog names rather than PRD UJ titles; glossary omits "Anki" and "Study Cards"; OQ-16 says Capture delete has "no Cards" but FR-13 deletes the Capture's suspended card.
Fix: Append PRD UJ titles to headings, complete the glossary, reword OQ-16.
Resolution: **fixed**.

**[Shape fit]** — DESIGN.md Open design questions nested under Do's and Don'ts (§ DESIGN.md end)
DQ-1…4 sit as an H3 under Do's and Don'ts, so a parser of hard visual rules picks up open questions.
Fix: Move it to a separate trailing H2.
Resolution: **fixed**.

## Mechanical notes (pre-fix)
- Frontmatter: both spines carry title, status, created, updated and sources; DESIGN.md also carries `name` and `description`. YAML well-formed by inspection.
- Cross-refs: all token references resolve. The shorthand "`{typography.score-headline}` / `-tablet`" is not a resolvable path; write `{typography.score-headline-tablet}`.
- Unused tokens: `rounded.word-pill-tablet`. `colors.danger-outline` and `colors.accent-hover` are named in prose without `{}` syntax.
- Name inconsistencies: Queue-count chip / Queue count; Text field / textarea / select / Text field; Verification banners / banner; Complete / Completeness.
- No Mermaid diagrams present.
- Open-question IDs cross-reference correctly (DQ-1↔OQ-11, DQ-3↔OQ-6, DQ-4↔OQ-5).

## Reviewer files
- `review-rubric.md`

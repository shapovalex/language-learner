# Editorial Review — DESIGN.md + EXPERIENCE.md (structure, prose)

Lenses: structure → prose (prose ran on top of structure). Overlap between lenses is noted, not deduped.

## structure-design

Structure lens findings for DESIGN.md (reference/database model):
1. QUESTION/MOVE: §Components 30 flat bullets — add H3 groups (Navigation, Actions, Inputs, Lists & chips, Pronunciation feedback, Status, Overlays, Loading/empty).
2. CONDENSE: normalize every Components entry to **Name**: `{components.x}` → visual spec → mockup pointer or "not mocked".
3. CUT: §Open Design Questions "Resolved:" line (DQ-3 ID collision).
4. CUT: §Colors "Not for:" line (duplicated in Do's and Don'ts).
5. CONDENSE: §Brand & Style inline list of 14 mockup paths → one sentence.
6. CONDENSE: Word pill / Weak-word panel restate thresholds + cues → point to Colors → Feedback scale; keep per-component offsets.
7. CONDENSE: Colors table `border` row Text-use cell.
8. CONDENSE: §Shapes paragraph → token/used-by table.
PRESERVE: Do's and Don'ts rows; "Names match EXPERIENCE.md"; Control boundaries paragraph; YAML components block.

## prose-design

Prose lens findings for DESIGN.md (23 rows):
1. Buttons heights: "Heights (px): 56 for phone Primary and Record; 52 for dialog, Rating and sticky-bar buttons; 48 standard; 44 small and in-alert."
2. Feedback scale: drop "Fills are unchanged;" and spell out "relative luminance ≈ 0.83 / ≈ 0.85".
3. "read without colour vision" → "can therefore be told apart without colour vision".
4. Weak-word panel: split listening hint into its own sentence ("The panel ends with a one-line listening hint.").
5. Text field: "On focus, and while a custom value is active, the border switches to `accent`."
6. App header: "`nav-pill` row Captures · English · French · Setup; desktop also shows the wordmark at left."
7. Success banner: clarify "Never feedback-good semantics" → "It shares accent-soft with feedback-good but never signals a pronunciation score; it has no dismiss control." (confirm reading)
8. "spines" jargon in Brand & Style → "the spec documents ("spines")".
9. Segmented control: "unselected segments transparent".
10. Colors: state target first: "WCAG AA is the target. All text/background pairs used in the mockups meet it (≥ 4.5:1)."
11. Unify "(decision)" / "(user decision)" labels.
12. Add px units where missing (10–14px gaps; 44 / 48 / 56px; desktop 32px / phone 26px).
13. Label weights: "weight 600"; "Target (17px, weight 700) over Russian meaning (15px, muted)".
14. Layout table headers: "Phone (mockup width 390px)" etc.
15. "side 300px" → "side panel 300px".
16. Score ring: "when weak" → define (fair 60–79?) — confirm.
17. Typography: "(verify Figtree's Cyrillic coverage during the build)".
18. Level meter: "centred above the Record button; shown only while recording."
19. Inline alert: "+ an optional Secondary button outlined in `danger-outline`".
20. Do's and Don'ts: "(dotted underline for fair, solid border/fill for poor, plus the score number or a label)".
21. Unify quote style (straight vs curly).
22. British vs US spelling (colour/centred/practised) — Microsoft style is US.
23. Serial (Oxford) comma — Microsoft style requires it.

## structure-experience

Structure lens findings for EXPERIENCE.md (reference/database model):
1. QUESTION: group §Component Patterns 35-row table under H3s (Navigation & overlays, Forms & editing, Draft/Item media, Pronunciation review, Setup).
2. QUESTION: sort §State Patterns rows by surface (Any → Captures → Draft/Item → Items → Review → Setup → Out of app).
3. CONDENSE: thresholds/cues stated 4x → canonical in §Pronunciation Feedback; pointers elsewhere.
4. MOVE: §Pronunciation Feedback to right after Component Patterns; Weak-word panel row points to it; cut duplicated last sentence of fr-CA paragraph.
5. CONDENSE: unsaved-warning trigger repeated in 5 component rows → one rule in Interaction Primitives.
6. MOVE/MERGE: IA "Desktop Captures is two-pane" paragraph into Responsive Captures row.
7. CONDENSE: IA "Navigation model" paragraph; phone Menu detail → point to Component Patterns → Menu.
8. CONDENSE: mockup paths repeated ~25x → IA Mockup column as single index.
9. MOVE: Key strings table to end of Voice and Tone (after Glossary).
10. CONDENSE: duplicate state copy (Key strings vs State Patterns vs J1) → one home.
11. MERGE: gamification bans → keep in Inspiration & Anti-patterns.
12. CUT: Interaction Primitives "Recording: tap to start, tap to stop."
13. CONDENSE: State Patterns "Assessing" row Rating restatement.
14. CONDENSE: "does not show Items" decision → keep in IA row only.
15. MOVE: Key Flows PRD-reconciliation "Note:" lines → Open Questions resolved (or keep only the rule sentence).
16. CONDENSE: J1–J5 headings with quoted PRD titles.
17. QUESTION/CUT: Open Questions "Resolved:" line.
Minor: pre-session Sync "not awaited" in 3 places; auto-play restated in Responsive; OQ-8 cross-ref; role=status repeated in Accessibility.
PRESERVE: Foundation "spines win" bullet; Voice Do/Don't table; Climax markers.

## prose-experience

Prose lens findings for EXPERIENCE.md (16 rows + 5 minor):
1. Microcopy agreement: "Setup applied, but 1 thing doesn't match" / "N things don't match" (pluralize at runtime).
2. Glossary "Capitalised in UI copy" contradicts strings ("Save capture", "Your capture is unchanged", "Couldn't assess that attempt") — scope the rule or capitalize strings.
3. "Mac Mini" → "Mac mini".
4. UK/US spelling mix (Capitalised, colour, emphasised, centred, practise, "right first time") — Microsoft style is US; microcopy "Nothing to practise in French" → "practice"?
5. Serial comma missing in prose lists (leave quoted UI strings).
6. J5 step 2: "readiness tiles for AnkiConnect, Azure, and OpenRouter, with the Prefix in the subtitle."
7. J3 step 4: "→ he taps Reference, then Try again, twice. The score climbs, and he picks Good."
8. J4 step 4: "...compares, and taps "Use preview"."
9. Interaction Primitives: give "he" an antecedent (Oleksii); consistent person in Try again sentence.
10. Rating buttons: "Enabled once ≥ 1 Attempt on this Card has an Assessment, and they stay enabled while a later Attempt is being assessed."
11. Compare pair: "Until Save, the Item in Anki is unchanged." replacing "Discarding leaves the Item unchanged."
12. Define shorthand once in Foundation: memlog, (decision), ADD.
13. Use "Inline alert (error)" / "Inline alert (warning)" instead of "Error alert"/"Warning alert".
14. J1 step 4: "The whole capture takes about 10 seconds."
15. Microcopy: "The model's answer failed the checks twice."?
16. Accessibility: "input text ≥ 16px (prevents iOS zoom on focus)".
Minor: "≥1" vs "≥ 80" spacing; "mock" vs "mockup"; "Review/edit" → "or"; "Attempts dropped" → "Attempts are discarded"; "Automatic retry (FR-16) invisible" → "is not shown".


---
title: LanguageLab Visual Identity
status: final
created: 2026-10-08
updated: 2026-10-08
sources:
  - ../prd-languagelab/prd-languagelab.md
  - ../prd-languagelab/addendum.md
  - ../../../spec-draft.md
name: LanguageLab · Studio
description: Warm, rounded, friendly study tool for one learner. Light theme only. Prominent pronunciation feedback; the learner always chooses the Rating.
colors:
  # Ground and surfaces
  ground: '#FFF8F1'
  surface: '#FFFFFF'
  surface-sunken: '#F0EAE2'
  surface-readonly: '#FBF8F4'
  border: '#E2DACF'
  border-input: '#948A7E'
  scrim: '#221E2E6B'
  # Ink
  ink: '#221E2E'
  ink-muted: '#5C5669'
  # Accent (violet)
  accent: '#5A45C8'
  accent-hover: '#3F2F96'
  on-accent: '#FFFFFF'
  accent-soft: '#ECE8FB'
  on-accent-soft: '#2E2470'
  accent-tint: '#F7F5FE'
  # Feedback scale (scores) and status
  feedback-good: '#ECE8FB'
  on-feedback-good: '#2E2470'
  feedback-fair: '#FFEBC7'
  on-feedback-fair: '#7A4A00'
  on-feedback-fair-strong: '#5A3600'
  feedback-poor: '#FFD9C7'
  on-feedback-poor: '#8F2F05'
  on-feedback-poor-strong: '#5E2003'
  feedback-poor-strong: '#C2410C'
  feedback-panel: '#FFF3EC'
  # Destructive / error
  danger: '#8F2F05'
  on-danger: '#FFFFFF'
  danger-soft: '#FFD9C7'
  danger-outline: '#E8B9A1'
typography:
  wordmark:
    fontFamily: Figtree
    fontSize: 20px
    fontWeight: '700'
  display:
    fontFamily: Figtree
    fontSize: 32px
    fontWeight: '700'
  display-phone:
    fontFamily: Figtree
    fontSize: 26px
    fontWeight: '700'
  dialog-title:
    fontFamily: Figtree
    fontSize: 22px
    fontWeight: '700'
    lineHeight: '1.25'
  title:
    fontFamily: Figtree
    fontSize: 18px
    fontWeight: '700'
  section-title:
    fontFamily: Figtree
    fontSize: 16px
    fontWeight: '700'
  target-text:
    fontFamily: Figtree
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.35'
  target-text-tablet:
    fontFamily: Figtree
    fontSize: 30px
    fontWeight: '600'
  score-headline:
    fontFamily: Figtree
    fontSize: 32px
    fontWeight: '700'
  score-headline-tablet:
    fontFamily: Figtree
    fontSize: 40px
    fontWeight: '700'
  score-value:
    fontFamily: Figtree
    fontSize: 18px
    fontWeight: '700'
  body-lg:
    fontFamily: Figtree
    fontSize: 17px
    fontWeight: '500'
    lineHeight: '1.45'
  body:
    fontFamily: Figtree
    fontSize: 16px
    fontWeight: '500'
  body-sm:
    fontFamily: Figtree
    fontSize: 15px
    fontWeight: '400'
  label:
    fontFamily: Figtree
    fontSize: 14px
    fontWeight: '600'
  count:
    fontFamily: Figtree
    fontSize: 13px
    fontWeight: '700'
  count-tablet:
    fontFamily: Figtree
    fontSize: 14px
    fontWeight: '700'
  banner:
    fontFamily: Figtree
    fontSize: 15px
    fontWeight: '600'
  caption:
    fontFamily: Figtree
    fontSize: 13px
    fontWeight: '400'
  overline:
    fontFamily: Figtree
    fontSize: 12px
    fontWeight: '700'
    letterSpacing: 0.06em
  button:
    fontFamily: Figtree
    fontSize: 16px
    fontWeight: '700'
  button-sm:
    fontFamily: Figtree
    fontSize: 15px
    fontWeight: '700'
rounded:
  bar: 3px
  phoneme: 10px
  chip: 12px
  word-pill-tablet: 14px
  count-chip: 14px
  field: 14px
  hint: 16px
  inner: 18px
  row: 20px
  card: 24px
  card-lg: 28px
  full: 9999px
spacing:
  '1': 4px
  '2': 6px
  '3': 8px
  '4': 10px
  '5': 12px
  '6': 14px
  '7': 16px
  '8': 18px
  '9': 20px
  '10': 24px
  '11': 28px
  gutter-phone: 16px
  gutter-desktop: 24px
  gutter-tablet: 28px
  stack-phone: 14px
  stack-desktop: 16px
  stack-tablet: 20px
  card-pad-phone: 18px
  card-pad-desktop: 20px
  card-pad-tablet: 28px
  content-max: 980px
  target-min: 44px
components:
  card:
    background: '{colors.surface}'
    radius: '{rounded.card}'
    padding: '{spacing.card-pad-phone}'
    shadow: '0 1px 2px rgba(34,30,46,0.06), 0 6px 20px rgba(34,30,46,0.06)'
  card-tablet:
    background: '{colors.surface}'
    radius: '{rounded.card-lg}'
    padding: '{spacing.card-pad-tablet}'
    shadow: '0 1px 2px rgba(34,30,46,0.06), 0 6px 20px rgba(34,30,46,0.06)'
  nav-pill:
    background: '{colors.surface-sunken}'
    foreground: '{colors.ink}'
    typography: '{typography.label}'
    radius: '{rounded.full}'
    height: '{spacing.target-min}'
    paddingX: '{spacing.7}'
  nav-pill-active:
    background: '{colors.accent}'
    foreground: '{colors.on-accent}'
  segmented-control:
    track: '{colors.surface-sunken}'
    trackPadding: 4px
    radius: '{rounded.full}'
    segmentHeight: 40px
    segmentSelected: '{colors.surface}'
    segmentSelectedPicker: '{colors.accent}'
  button-primary:
    background: '{colors.accent}'
    foreground: '{colors.on-accent}'
    typography: '{typography.button}'
    radius: '{rounded.full}'
    height: 48px
    heightLarge: 56px
  button-secondary:
    background: '{colors.surface}'
    foreground: '{colors.ink}'
    border: '2px solid {colors.border}'
    typography: '{typography.button}'
    radius: '{rounded.full}'
    height: 48px
  button-soft:
    background: '{colors.accent-soft}'
    foreground: '{colors.on-accent-soft}'
    radius: '{rounded.full}'
    height: 44px
  button-text:
    background: 'transparent'
    foreground: '{colors.accent}'
    typography: '{typography.label}'
    height: '{spacing.target-min}'
  button-disabled:
    background: '{colors.border}'
    foreground: '{colors.ink-muted}'
    radius: '{rounded.full}'
  button-destructive:
    background: '{colors.danger}'
    foreground: '{colors.on-danger}'
    radius: '{rounded.full}'
    height: 52px
    heightSmall: 44px
  button-destructive-text:
    background: 'transparent'
    foreground: '{colors.danger}'
  icon-button:
    background: '{colors.surface-sunken}'
    foreground: '{colors.ink}'
    radius: '{rounded.full}'
    size: 44px
    sizeLarge: 56px
  text-field:
    background: '{colors.surface}'
    foreground: '{colors.ink}'
    border: '2px solid {colors.border-input}'
    borderFocus: '2px solid {colors.accent}'
    backgroundReadonly: '{colors.surface-readonly}'
    foregroundReadonly: '{colors.ink-muted}'
    radius: '{rounded.field}'
    padding: '12px 14px'
    typography: '{typography.body}'
  search-field:
    background: '{colors.surface}'
    border: '2px solid {colors.accent}'
    radius: '{rounded.full}'
    height: 56px
  list-row:
    background: '{colors.surface}'
    radius: '{rounded.row}'
    padding: '14px 16px'
    minHeight: '{spacing.target-min}'
  list-row-selected:
    background: '{colors.accent-soft}'
    border: '2px solid {colors.accent}'
    radius: '{rounded.inner}'
  chip:
    background: '{colors.surface-sunken}'
    foreground: '{colors.ink}'
    radius: '{rounded.chip}'
    padding: '4px 10px'
    typography: '{typography.caption}'
  chip-accent:
    background: '{colors.accent-soft}'
    foreground: '{colors.on-accent-soft}'
  chip-unsaved:
    background: '{colors.feedback-fair}'
    foreground: '{colors.on-feedback-fair}'
  queue-count-chip:
    background: '{colors.surface-sunken}'
    foreground: '{colors.ink}'
    typography: '{typography.count}'
    typographyTablet: '{typography.count-tablet}'
    radius: '{rounded.count-chip}'
    padding: '6px 12px'
  compare-current:
    border: '2px solid {colors.border}'
    radius: '{rounded.inner}'
  compare-preview:
    background: '{colors.accent-tint}'
    border: '2px solid {colors.accent}'
    radius: '{rounded.inner}'
    labelColor: '{colors.accent}'
  audio-player:
    trackHeight: 6px
    track: '{colors.accent-soft}'
    fill: '{colors.accent}'
    radius: '{rounded.bar}'
  score-ring:
    size: 104px
    sizeTablet: 128px
    stroke: 10px
    strokeTablet: 12px
    track: '{colors.accent-soft}'
    fill: '{colors.accent}'
    numeral: '{typography.score-headline}'
  word-pill-good:
    background: '{colors.feedback-good}'
    foreground: '{colors.on-feedback-good}'
    radius: '{rounded.chip}'
    radiusTablet: '{rounded.word-pill-tablet}'
  word-pill-fair:
    background: '{colors.feedback-fair}'
    foreground: '{colors.on-feedback-fair}'
    textDecoration: 'underline dotted 2px'
    underlineOffset: 5px
    underlineOffsetTablet: 6px
    radius: '{rounded.chip}'
    radiusTablet: '{rounded.word-pill-tablet}'
  word-pill-poor:
    background: '{colors.feedback-poor}'
    foreground: '{colors.on-feedback-poor}'
    border: '2px solid {colors.feedback-poor-strong}'
    radius: '{rounded.chip}'
    radiusTablet: '{rounded.word-pill-tablet}'
  phoneme-pill:
    background: '{colors.surface}'
    backgroundFair: '{colors.feedback-fair}'
    foregroundFair: '{colors.on-feedback-fair}'
    decorationFair: 'underline dotted 2px'
    underlineOffsetFair: 4px
    backgroundPoor: '{colors.feedback-poor-strong}'
    foregroundPoor: '{colors.on-danger}'
    radius: '{rounded.phoneme}'
  position-strip:
    cellHeight: 40px
    radius: '{rounded.chip}'
    cellNeutral: '{colors.surface}'
    cellFair: '{colors.feedback-fair}'
    cellFairDecoration: 'underline dotted 2px'
    cellFairUnderlineOffset: 4px
    cellPoor: '{colors.feedback-poor-strong}'
    cellPoorForeground: '{colors.on-danger}'
  weak-word-panel:
    background: '{colors.feedback-panel}'
    radius: '{rounded.inner}'
  record-button:
    background: '{colors.accent}'
    backgroundRecording: '{colors.danger}'
    foreground: '{colors.on-accent}'
    radius: '{rounded.full}'
    height: 56px
    heightTablet: 60px
  level-meter:
    bar: '{colors.accent}'
    barWidth: 5px
    radius: '{rounded.bar}'
    height: 40px
  rating-button:
    background: '{colors.surface}'
    foreground: '{colors.ink}'
    border: '2px solid {colors.border}'
    typography: '{typography.button}'
    radius: '{rounded.full}'
    height: 52px
    heightTablet: 60px
  inline-alert-error:
    background: '{colors.danger-soft}'
    titleColor: '{colors.danger}'
    bodyColor: '{colors.on-feedback-poor-strong}'
    radius: '{rounded.row}'
  inline-alert-warning:
    background: '{colors.feedback-fair}'
    titleColor: '{colors.on-feedback-fair}'
    bodyColor: '{colors.on-feedback-fair-strong}'
    radius: '{rounded.row}'
  info-callout:
    background: '{colors.feedback-panel}'
    radius: '{rounded.row}'
  readiness-tile:
    backgroundPass: '{colors.accent-soft}'
    foregroundPass: '{colors.on-accent-soft}'
    backgroundFail: '{colors.feedback-poor}'
    foregroundFail: '{colors.on-feedback-poor}'
    borderFail: '2px solid {colors.feedback-poor-strong}'
    radius: '{rounded.inner}'
  readiness-fix-hint:
    background: '{colors.feedback-panel}'
    foreground: '{colors.on-feedback-poor-strong}'
    radius: '{rounded.hint}'
  success-banner:
    background: '{colors.accent-soft}'
    foreground: '{colors.on-accent-soft}'
    radius: '{rounded.inner}'
    padding: '12px 16px'
    typography: '{typography.banner}'
  verification-banner-verified:
    background: '{colors.accent-soft}'
    foreground: '{colors.on-accent-soft}'
    iconDisc: '{colors.accent}'
    iconForeground: '{colors.on-accent}'
    radius: '{rounded.card}'
    padding: '18px 20px'
  verification-banner-discrepancy:
    background: '{colors.surface}'
    border: '2px solid {colors.feedback-poor-strong}'
    titleColor: '{colors.danger}'
    radius: '{rounded.card}'
    padding: 20px
  progress-card:
    background: '{colors.surface}'
    spinner: '{colors.accent}'
    radius: '{rounded.card}'
    padding: 20px
  change-row:
    border: '2px solid {colors.border}'
    radius: '{rounded.inner}'
  sticky-action-bar:
    background: '{colors.ground}'
    borderTop: '1px solid {colors.border}'
    padding: '12px 16px 24px'
    columns: '1fr 2fr'
    gap: 8px
    buttonHeight: 52px
  bottom-sheet:
    background: '{colors.ground}'
    radiusTop: '{rounded.card-lg}'
    radiusBottom: 0px
    handle: '{colors.border}'
  alert-dialog:
    background: '{colors.surface}'
    radius: '{rounded.card-lg}'
    iconBackground: '{colors.danger-soft}'
    iconForeground: '{colors.danger}'
  menu-sheet:
    background: '{colors.ground}'
    radiusTop: '{rounded.card-lg}'
    row: '{components.list-row}'
    rowActive: '{components.list-row-selected}'
    rowTypography: '{typography.body}'
  back-link:
    foreground: '{colors.accent}'
    typography: '{typography.label}'
    minHeight: '{spacing.target-min}'
  skeleton:
    background: '{colors.surface-sunken}'
    lineHeight: 14px
  empty-state:
    background: '{colors.surface}'
    iconBackground: '{colors.accent-soft}'
    iconForeground: '{colors.accent}'
---

## Brand & Style

LanguageLab is a private studio for one learner, not a game. **Studio** direction: warm, rounded, and friendly, so a daily practice tool feels calm to open on any device. A warm paper ground (`{colors.ground}`) holds white rounded cards; one violet accent marks the next thing to do. Pronunciation feedback is deliberately prominent (a big score ring and color-coded word pills), but it informs; it never decides. The Rating row is the visual opposite of the scores: four identical, neutral buttons.

Composition references are the 14 canonical Studio mockups in `mockups/`, indexed per surface in `EXPERIENCE.md` → Information Architecture; sample content in them is placeholder. Precedence between the spec documents ("spines") and the mockups, and labels such as "(decision)", are defined in `EXPERIENCE.md` → Foundation.

## Colors

Light theme only; there are no dark tokens.

| Token | Hex | Role | Text use |
|---|---|---|---|
| `ground` | `#FFF8F1` | Page background; bottom-sheet surface | — |
| `surface` | `#FFFFFF` | Cards, rows, fields, dialogs | — |
| `surface-sunken` | `#F0EAE2` | Inactive nav pills, segmented track, icon buttons, neutral chips, queue-count chip, skeleton | Fill only (ink on it 13.6:1) |
| `surface-readonly` | `#FBF8F4` | Read-only field fill ("Use as is" text on desktop Make an Item) | Fill only (ink-muted on it 6.6:1) |
| `border` | `#E2DACF` | 2px Secondary-button and Rating outlines; compare-pane, change-row, and sheet-handle edges; disabled-button fill | **Fill/border only**; 1.38:1 on white, 1.32:1 on ground (accepted deviation, see Control boundaries). `ink-muted` on it 5.1:1 |
| `border-input` | `#948A7E` | 2px outline of text fields, textareas, and selects (decision) | **Border only.** Non-text 3.39:1 on white, 3.22:1 on ground, 3.20:1 on `surface-readonly` (passes 3:1) |
| `scrim` | `#221E2E` @ 42% | Behind sheets and dialogs | — |
| `ink` | `#221E2E` | All primary text | Text: 16.2:1 on white, 15.4:1 on ground |
| `ink-muted` | `#5C5669` | Metadata, hints, sub-score labels, helper text | Text: 7.0:1 on white, 6.7:1 on ground, 5.9:1 on `surface-sunken` |
| `accent` | `#5A45C8` | Primary buttons, active nav, links, focus border, score ring, level meter | Text **and** fill: 6.7:1 vs white |
| `accent-hover` | `#3F2F96` | Link hover | Text: 10.2:1 |
| `accent-soft` / `on-accent-soft` | `#ECE8FB` / `#2E2470` | Category chip, readiness pass, "Use preview" button, ring track, success banner, verified banner, selected Capture row | Pair: 10.9:1 |
| `accent-tint` | `#F7F5FE` | Preview panel background | Fill only |
| `feedback-good` / `on-…` | `#ECE8FB` / `#2E2470` | Word scored well | Pair: 10.9:1 |
| `feedback-fair` / `on-…` | `#FFEBC7` / `#7A4A00` | Word/sub-score needs attention; "unsaved" chip; warning alert | Pair: 6.4:1 (`on-feedback-fair-strong` `#5A3600`: 9.2:1) |
| `feedback-poor` / `on-…` | `#FFD9C7` / `#8F2F05` | Word mispronounced; error alert; failing readiness tile | Pair: 6.2:1 (`on-feedback-poor-strong` `#5E2003`: 9.5:1) |
| `feedback-poor-strong` | `#C2410C` | Poor-word border; poor phoneme / position cell fill; failing-tile and discrepancy-banner border | White text on it 5.2:1; as a border on `feedback-poor` 3.95:1 (non-text, passes 3:1) |
| `feedback-panel` | `#FFF3EC` | Weak-word panel; info callout; readiness fix hint | Fill only (ink-muted on it 6.5:1; `on-feedback-poor-strong` 11.5:1) |
| `danger` / `on-danger` | `#8F2F05` / `#FFFFFF` | Destructive buttons, recording state, error titles, destructive text links | Text and fill: 8.2:1 |
| `danger-soft` | `#FFD9C7` | Error alert fill, delete-dialog icon disc | Fill only |
| `danger-outline` | `#E8B9A1` | Secondary button border inside an error alert | Border only |

WCAG AA is the target. All text/background pairs used in the mockups meet it (≥ 4.5:1).

**Control boundaries (WCAG 1.4.11).** Text fields, textareas, and selects are identified by their outline, so they use `{colors.border-input}` (≥ 3:1 on every surface they sit on). **Accepted deviation (decision):** Secondary (outline) buttons and Rating buttons keep the soft `{colors.border}` outline (1.38:1). They are identified by their visible label, pill shape, and white fill against the `ground` page; the outline is decorative. Do not reuse `border` as the only boundary of any other interactive control.

**Feedback scale.** Good is violet-blue (`feedback-good`), fair is amber, and poor is orange. Good (relative luminance ≈ 0.83) and fair (≈ 0.85) are nearly the same lightness, so each non-good step also carries a **non-color cue** (decision): fair = 2px dotted underline on the text (offset 4–6px); poor = 2px solid `feedback-poor-strong` border on word pills, and solid `feedback-poor-strong` fill with white text on phoneme pills and position cells. Good has no decoration. The three steps can therefore be told apart without color vision.

**Score thresholds** (Azure 0–100; word pills, phoneme pills, and position-strip cells alike): **≥ 80 good**, **60–79 fair**, **< 60 poor**.

## Typography

One family: **Figtree** (weights 400/500/600/700), fallback `system-ui, sans-serif`. The woff2 files are vendored into the wheel under `static/vendor/` and never loaded from Google Fonts at runtime (architecture AD-13). Figtree ships Latin and Latin Extended subsets only, so English and French render in Figtree and Russian (Cyrillic) renders in the `system-ui` fallback. That is accepted for v1.

| Role | Token | Where |
|---|---|---|
| Wordmark | `{typography.wordmark}` | "LanguageLab" in the desktop header |
| Display | `{typography.display}` / `{typography.display-phone}` | Page and Item titles (desktop 32px / phone 26px) |
| Dialog title | `{typography.dialog-title}` | Sheet and dialog headings |
| Title | `{typography.title}` | Card heading ("Make an Item") |
| Section title | `{typography.section-title}` | Card section headings ("Example", "Reference audio") |
| Target text | `{typography.target-text}` / `{typography.target-text-tablet}` | The phrase being practiced (word pills) |
| Score | `{typography.score-headline}` / `{typography.score-headline-tablet}`, `{typography.score-value}` | Ring numeral; sub-score values |
| Body | `{typography.body-lg}`, `{typography.body}`, `{typography.body-sm}` | Example sentence / field values / supporting text |
| Label | `{typography.label}` | Field labels, nav pills, text buttons |
| Caption | `{typography.caption}` | Timestamps, chips, helper text |
| Overline | `{typography.overline}` (uppercase) | "CURRENT", "PREVIEW · NOT SAVED" |
| Button | `{typography.button}` / `{typography.button-sm}` | Pill buttons |
| Count | `{typography.count}` / `{typography.count-tablet}` | Queue-count chip (phone / tablet) |
| Banner | `{typography.banner}` | Success banner line |

Field input text is never below 16px (prevents iOS Safari zoom on focus). Optional-field qualifiers ("optional · only you write this") are set inline after the label in `ink-muted`, weight 400.

## Layout & Spacing

Scale: 4 · 6 · 8 · 10 · 12 · 14 · 16 · 18 · 20 · 24 · 28 px (`{spacing.1}`…`{spacing.11}`). Chip and pill groups use `{spacing.2}` gaps; stacks inside cards use 10–14px gaps.

| | Phone (mockup width 390px) | Tablet (mockup width 1180px, landscape) | Desktop (mockup width 1280px) |
|---|---|---|---|
| Page gutter | `{spacing.gutter-phone}` | `{spacing.gutter-tablet}` | `{spacing.gutter-desktop}` |
| Stack gap between cards | `{spacing.stack-phone}` | `{spacing.stack-tablet}` | `{spacing.stack-desktop}` |
| Card padding | `{spacing.card-pad-phone}` | `{spacing.card-pad-tablet}` | `{spacing.card-pad-desktop}` |
| Content width | full | full, two columns | centered, max `{spacing.content-max}` |

Layout is intrinsic: multi-column regions use `flex-wrap` with flex-basis minimums (form 420px / side panel 300px on the Draft; compare panes 300px; Setup tiles `minmax(200px, 1fr)`), so columns stack on narrow widths without breakpoint-specific markup. Primary actions on phone sit at the bottom of the viewport (`margin-top: auto`). Every interactive target is at least `{spacing.target-min}`.

## Elevation & Depth

Two levels, both soft and warm-tinted:

- **Card** — `0 1px 2px rgba(34,30,46,0.06), 0 6px 20px rgba(34,30,46,0.06)` on primary content cards.
- **Flat** — list rows, compare panes, alerts, chips, and dialogs carry no shadow; they separate by tone (`surface` on `ground`) or a 2px `border` (`border-input` on fields).

Overlays (bottom sheet, alert dialog) sit above a `{colors.scrim}` layer and use no shadow.

## Shapes

Round and soft everywhere. Circles only for icon buttons, the score ring, and the empty-state/dialog icon discs.

| Token | Radius | Used by |
|---|---|---|
| `{rounded.full}` | half the height | Buttons, nav pills, segmented controls, search field, record button |
| `{rounded.card-lg}` | 28px | Tablet cards, dialogs, sheet top corners |
| `{rounded.card}` | 24px | Cards |
| `{rounded.row}` | 20px | Rows |
| `{rounded.inner}` | 18px | Inner panels, compare panes |
| `{rounded.hint}` | 16px | Readiness fix hint |
| `{rounded.field}` | 14px | Fields |
| `{rounded.count-chip}` | 14px | Queue-count chip |
| `{rounded.word-pill-tablet}` | 14px | Word pills on tablet |
| `{rounded.chip}` | 12px | Chips, word pills |
| `{rounded.phoneme}` | 10px | Phoneme pills |

## Components

Names match `EXPERIENCE.md` Component Patterns. Each entry: token, visual spec, then the mockup that shows it (or "Not mocked").

### Navigation

- **App header / nav pills** — `{components.nav-pill}`, active `{components.nav-pill-active}`. Desktop and tablet: `nav-pill` row Captures · English · French · Setup; desktop also shows the wordmark at left. Phone: screen title (Language overline over "Pronunciation") at left; `queue-count-chip` and 44px `icon-button` "Menu" at right. → `mockups/S-Items.dc.html` (desktop), `mockups/S-Review.dc.html` (phone).
- **Menu (phone)** — `{components.menu-sheet}`: a bottom sheet (same shell as Bottom sheet: `ground`, `{rounded.card-lg}` top corners, handle, scrim) titled "Menu" in `dialog-title`, listing Captures · English · French · Setup as full-width `list-row`s (`body`, weight 600, trailing chevron); the current area uses `list-row-selected`. No icons, no counts. Not mocked.
- **Back link** — `{components.back-link}`: `accent` text in `label`, leading chevron, no fill, 44px-tall hit area, top left of detail screens ("‹ Captures", "‹ English Items"). → `mockups/S-NewItem.dc.html`, `mockups/S-ItemDetail.dc.html`.
- **Segmented control** — `{components.segmented-control}`: `surface-sunken` track, 4px inset, 40px segments. Navigation use (Items / Pronunciation): selected segment `surface`. Picker use (Language, Category): selected segment `accent` with white bold text; unselected segments transparent. → `mockups/S-NewItem.dc.html`.

### Actions

- **Card** — `{components.card}`; tablet `{components.card-tablet}`. → all mockups.
- **Buttons** — `{components.button-primary}` (`accent` fill), `{components.button-secondary}` (white, 2px `border`), `{components.button-soft}` (`accent-soft`, used for "Use preview"), `{components.button-text}` (`accent`, no fill), `{components.button-destructive}` (`danger` fill), `{components.button-destructive-text}` (`danger` text: "Delete", "Delete Capture"). Heights: 56px for phone Primary and Record; 52px for dialog, Rating, and sticky-bar buttons; 48px standard; 44px small and in-alert. → `mockups/C-Draft.dc.html`, `mockups/S-ItemDetail.dc.html`.
- **Disabled button** — `{components.button-disabled}`: `border` fill, `ink-muted` text, no shadow, label unchanged; a muted reason sits to its left ("Fix the failing check to continue."). → `mockups/S-SetupStates.dc.html`.
- **Sticky action bar (phone)** — `{components.sticky-action-bar}`: pinned to the viewport bottom over `ground`, 1px `border` top rule, full-bleed (cancels the 16px gutter), 24px bottom padding for the home indicator. Grid 1fr / 2fr: Secondary "Discard", then Primary "Save to Anki", both 52px. → `mockups/S-DraftPhone.dc.html`.
- **Icon button** — `{components.icon-button}`: circular `surface-sunken`, 44px / 48px / 56px; always has an accessible label. → `mockups/S-Review.dc.html`.

### Inputs and media

- **Text field / textarea / select** — `{components.text-field}`: 2px `{colors.border-input}` outline (≥ 3:1). On focus, and while a custom value is active, the border switches to `accent`. Label above in `{typography.label}`. Read-only ("Use as is" text): `surface-readonly` fill, `ink-muted` text, same `border-input` outline. → `mockups/S-CapturesDesk.dc.html`.
- **Text-source choice** — native radio pair in a `fieldset` with legend "Text" (`label`): "Use as is" / "Custom value", 20px radios in `accent`, each label row ≥ 44px; stacked on phone, inline on desktop. The Custom value text field sits below. → `mockups/S-NewItem.dc.html`, `mockups/S-CapturesDesk.dc.html`.
- **Search field** — `{components.search-field}`: 56px pill, 2px `accent` border, leading magnifier in `ink-muted`. → `mockups/S-Items.dc.html`.
- **Compare pair** — `{components.compare-current}` (2px `border`) next to `{components.compare-preview}` (`accent-tint`, 2px `accent`, overline label in `accent`). Actions below, right-aligned: Keep current (Secondary), Use preview (Soft). → `mockups/S-ItemDetail.dc.html`.
- **Audio player** — `{components.audio-player}`: play `icon-button`, 6px progress bar (`accent` on `accent-soft`), and duration in caption. Voice `select` reads `<locale> · <Voice>`. → `mockups/C-Draft.dc.html`, `mockups/S-DraftPhone.dc.html`.

### Lists and chips

- **List row** — `{components.list-row}`. Capture row: text (`body`, weight 600) over timestamp (`caption`, muted), trailing chevron. Item row: Target (17px, weight 700) over Russian meaning (15px, muted), Category chip, and a trailing speaker icon when Reference audio exists (blank space otherwise). Selected Capture row (desktop two-pane list): `{components.list-row-selected}`, `aria-current`. → `mockups/S-Captures.dc.html`, `mockups/S-CapturesDesk.dc.html`, `mockups/S-Items.dc.html`.
- **Chip** — `{components.chip}` neutral (Sentence, Exercise names), `{components.chip-accent}` (English, Vocabulary, Setup counts), `{components.chip-unsaved}` (`feedback-fair`: "Draft — not saved yet", "2 unsaved changes"). → `mockups/C-Draft.dc.html`, `mockups/S-ItemDetail.dc.html`.
- **Queue-count chip** — `{components.queue-count-chip}`: "N due · M new" in a `surface-sunken` pill (`count` on phone, `count-tablet` on tablet), ink text, `aria-label` "N due, M new"; no bar or ring. Phone: in the review header, left of Menu. iPad: top right of the Target card, opposite "Sentence · Attempt N". → `mockups/S-Review.dc.html`, `mockups/S-iPadReview.dc.html`.
- **Change row** — `{components.change-row}`: 2px `border` row with resource name (weight 600) and muted detail, trailing accent chip with action and count ("Create 5"). → `mockups/S-Setup.dc.html`.

### Pronunciation feedback

Thresholds and non-color cues for every feedback element: Colors → Feedback scale.

- **Score ring** — `{components.score-ring}`; numeral centered. Ring color is always `accent`, whatever the score. Beside it: sub-score grid (label in `caption`/muted over value in `score-value`); a sub-score value takes `on-feedback-fair` when it scores fair (60–79) or `on-feedback-poor` when it scores poor (< 60). → `mockups/S-Review.dc.html`, `mockups/S-iPadReview.dc.html`.
- **Word pill** — `{components.word-pill-good}`, `{components.word-pill-fair}`, `{components.word-pill-poor}`: one per word of the Target text, in `target-text`, variant by score. Fair underline offset: 5px phone, 6px tablet. → `mockups/S-Review.dc.html`, `mockups/S-iPadReview.dc.html`.
- **Weak-word panel** — `{components.weak-word-panel}`: `feedback-panel` block under the scores. It shows the word, score, and error type in `on-feedback-poor`, then either an en-US `{components.phoneme-pill}` row showing Azure's phoneme symbols (IPA) as returned, or an fr-CA `{components.position-strip}` (start / middle / end cells). Phoneme pills and position cells are neutral white when good and take the fair and poor treatments otherwise (fair underline offset 4px). The panel ends with a one-line listening hint. → `mockups/S-Review.dc.html` (en-US phonemes), `mockups/S-iPadReview.dc.html` (fr-CA positions).
- **Record button** — `{components.record-button}`: Primary pill with mic icon ("Try again" after the first Attempt). Recording: `danger` fill, white stop square, label "Listening… tap to stop", with the Level meter above. → `mockups/S-States.dc.html`.
- **Level meter** — `{components.level-meter}`: 8 rounded 5px `accent` bars, 40px tall, centered above the Record button; shown only while recording. → `mockups/S-States.dc.html`.
- **Rating buttons** — `{components.rating-button}`, four identical: white, 2px `border` (accepted contrast deviation, see Colors), ink text. Phone 2×2 grid; tablet/desktop 4 across. Prompt above in `ink-muted`. No variant, color, or emphasis per button, ever. → `mockups/S-Review.dc.html`, `mockups/S-iPadReview.dc.html`.

### Status

- **Inline alert** — `{components.inline-alert-error}`: `danger-soft`, title `danger`, body `on-feedback-poor-strong`, `button-destructive` at `heightSmall`, plus an optional Secondary button outlined in `danger-outline`. `{components.inline-alert-warning}`: `feedback-fair`, title `on-feedback-fair`, body `on-feedback-fair-strong`. → `mockups/S-States.dc.html`.
- **Info callout** — `{components.info-callout}`: `feedback-panel`, bold line plus muted line. → `mockups/S-Setup.dc.html`.
- **Success banner** — `{components.success-banner}`, `role="status"`: `accent-soft` row, check icon, and one line in `on-accent-soft` (`banner`). It shares `accent-soft` with `feedback-good` but never signals a pronunciation score; it has no dismiss control. Used for the post-Save confirmation on the Capture. → `mockups/S-CapturesDesk.dc.html`.
- **Readiness tile** — `{components.readiness-tile}`. Pass: `accent-soft` with check icon and dependency name. Fail: `feedback-poor` fill, `on-feedback-poor` bold text, 2px `feedback-poor-strong` border, cross icon ("OpenRouter not configured"); followed by a `{components.readiness-fix-hint}` (`feedback-panel`, `on-feedback-poor-strong`, `role="alert"`) and the disabled Apply button. → `mockups/S-Setup.dc.html`, `mockups/S-SetupStates.dc.html`.
- **Progress card** — `{components.progress-card}`: white card, `accent` spinner arc, and one line ("Applying setup and verifying… Keep Anki open."). → `mockups/S-SetupStates.dc.html`.
- **Verification banner** — Verified: `{components.verification-banner-verified}`, `role="status"`, 44px `accent` disc with white check, bold title, and one line. Discrepancies: `{components.verification-banner-discrepancy}`, `role="alert"`, white card with 2px `feedback-poor-strong` border, title in `danger`, muted explanation, then `change-row`-style items (resource in weight 600 plus muted expected/found), and Primary "Run Setup again" right-aligned. → `mockups/S-SetupStates.dc.html`.

### Overlays

- **Bottom sheet** — `{components.bottom-sheet}`: `ground` surface, `card-lg` top corners, 40×5px handle in `border`, over scrim. Overline context in `on-feedback-fair`, dialog title, matched Item in a white inner card with 2px `feedback-fair` border, then stacked Primary / Secondary / Text buttons. → `mockups/S-Duplicate.dc.html`.
- **Alert dialog** — `{components.alert-dialog}`: centered white `card-lg` card over scrim; 48px `danger-soft` icon disc with trash glyph; title names the object; body lists affected Cards as neutral chips; Destructive, then Secondary, full width, stacked. → `mockups/S-Delete.dc.html`.
  - *Unsaved-changes variant*: same card, **no icon disc**, no chips. Title "Discard unsaved changes?"; one muted line naming what is lost ("2 unsaved changes to “jump to conclusions”" or "This Draft isn't saved."). Buttons full width, stacked: Destructive "Discard", then Secondary "Keep editing". Not mocked.

### Loading and empty

- **Skeleton** — `{components.skeleton}`: spinner arc in `accent` plus label, then 14px `surface-sunken` bars at 80/60/70% width. → `mockups/S-States.dc.html`.
- **Empty state** — `{components.empty-state}`: white card, centered: 56px `accent-soft` disc with check, title (`title`), and muted line. → `mockups/S-States.dc.html`.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Keep all four Rating buttons identical, neutral, and unselected | Tint, enlarge, order-by-score, or pre-select any Rating |
| Show scores big; ring always in `accent` | Color the ring by score, or add confetti, badges, streaks, or progress bars |
| Pair every feedback color with a non-color cue (dotted underline for fair, solid border/fill for poor, plus the score number or a label) | Rely on hue alone, or use red/green right-wrong pairs |
| Use `danger` only for destructive actions, errors, and the recording state | Use `danger` or orange decoratively |
| One Primary button per region | Two accent-filled buttons side by side |
| Set field text ≥ 16px | Shrink inputs on phone (iOS zoom) |
| Use `border` / `surface-sunken` as fills or outlines only | Set text in `border`, `surface-sunken`, `accent-tint`, or `feedback-panel` |
| Outline every text field, textarea, and select in `border-input` | Use the soft `border` as a field's only boundary |
| Light theme only | Ship a dark variant |

## Open Design Questions

Not visual rules; tracked here until resolved.

- **DQ-3** How non-managed notes are reported in Setup (FR-6) is not designed — see `EXPERIENCE.md` OQ-6.
- **DQ-4** Anki card template visuals (FR-21: Understand, Produce, Write in AnkiMobile/Desktop) are not designed; whether they adopt this palette is open.

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

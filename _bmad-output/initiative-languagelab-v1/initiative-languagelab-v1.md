---
type: initiative
title: LanguageLab v1
parent: none
covers: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5, CAP-6, CAP-7, CAP-8, CAP-9, CAP-10, CAP-11]
after: []
assignee: ""
risk: high
---

# LanguageLab v1

## Description

A personal web app that turns words and phrases met on any device into AI-drafted Anki Items with four independently scheduled Exercises (Understand, Produce, Write, Pronounce), and adds Azure-assessed pronunciation practice inside Anki's spaced repetition. Anki stays the only store and the only scheduler. The spec owns the capabilities, constraints, and non-goals; this initiative delivers all of them as v1 on the Mac Mini.

## Outcome

The single learner builds English (B2→C1) and French (→A1) decks mostly through LanguageLab instead of hand-made Anki notes, and keeps Pronounce reviews in pace with Study Cards — the spec's Success signal, read from Anki's own counts.

## Done when

1. Every PRD §9 acceptance criterion (AC1–AC22) passes on the Mac Mini with a released wheel, from iPhone, iPad, and a desktop browser.
2. Across that acceptance run, nothing in Anki outside the configured Prefix was created, edited, or deleted, and no failed Save lost a prior field or audio value (NFR-1, NFR-3).
3. After one month of use, most new English and French Items come from LanguageLab and Pronounce reviews keep pace with Study Cards, read from Anki's counts and deck stats.
4. Logs from that month contain no captured text, generated content, payloads, or audio (NFR-7, NFR-9).

## Boundaries

Capability boundaries from the spec, one owner (one developer with agent lanes). Not multiple users, an app database, offline/PWA/native, analytics, imports, non-text Capture, automatic Ratings, other pronunciation providers, or C1–C2 exercise design; see the spec's Non-goals. Deferred past v1: Capture search, spend guardrails, Pronounce queue cap, live-Anki test harness.

Tracer path: start the released wheel → Setup creates the managed decks and note types → save a Capture from the iPhone → generate a Draft → Save → four Cards in Anki Desktop (E1→E4).

- Touch point: Tailscale Serve — configured only (HTTPS to 127.0.0.1); owner: epic-platform-baseline
- Touch point: GitHub Actions / GitHub releases — release workflow; owner: epic-platform-baseline
- Touch point: Anki Desktop + AnkiConnect — consumed through `adapters/anki`; owner: epic-anki-setup-sync
- Touch point: AnkiWeb — reached only through AnkiConnect sync; owner: epic-anki-setup-sync
- Touch point: OpenRouter — consumed through `adapters/openrouter`; owner: epic-capture-to-item
- Touch point: AnkiMobile — card rendering checked only; owner: epic-capture-to-item
- Touch point: Azure Speech — `adapters/azure` created for TTS and voices by epic-reference-audio, extended with assessment by epic-pronunciation-review

## References

- spec — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, section Capabilities
- constraint — the same spec, sections Constraints and Non-goals
- architecture — _bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md (AD-1–AD-20, Consistency Conventions, Stack); settles every decision more than one epic adopts
- prd — _bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md, §4 FRs, §5 NFRs, §9 acceptance criteria; addendum.md beside it
- ux — _bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md and DESIGN.md, mockups/

## Notes

- Decision (2026-10-08): every epic and story is self-sustainable and verifiable — its Done when is checkable with only earlier epics in place, on a released wheel on the Mac Mini; no check waits on a later epic, no placeholders.
- Decision (2026-10-08): seven epics in order — platform baseline, Anki setup and Sync, Captures, Capture to Item, Maintain Items, Reference audio, Pronunciation review.
- Decision (2026-10-08): Captures is its own epic, usable early to collect words before Drafts exist.
- Decision (2026-10-08): Sync (CAP-11) lives in the Anki setup epic; Pronunciation session Sync triggers belong to the Pronunciation epic.
- Decision (2026-10-08): Pronunciation review is last; no early recording spike.
- Decision (2026-10-08): reading an Item and a view-only Item detail screen belong to Capture to Item (for "Open existing"); Maintain Items adds edit, regenerate, and delete.
- Decision (2026-10-08): the FR-5 readiness check tests only that Azure and OpenRouter keys are configured, no live calls.
- Decision (2026-10-08): card template visuals belong to Capture to Item while the manifest belongs to the Anki setup epic (architecture Deferred); a template-only change needs no SchemaVersion bump.
- Decision (2026-10-08): Save follows AD-6; Capture to Item builds it with `audio=keep`, Reference audio adds `replace`/`remove` and the media steps.

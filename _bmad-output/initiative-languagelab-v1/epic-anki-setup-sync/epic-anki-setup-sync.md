---
type: epic
title: "Anki safely managed: Setup, repair, and Sync"
parent: initiative-languagelab-v1
covers: [CAP-2, CAP-11]
after: []
assignee: ""
risk: high
---

# Anki safely managed: Setup, repair, and Sync

## Description

Everything LanguageLab needs to own a slice of Anki safely: the Anki adapter (one lock with timeouts, the field codec, the Prefix guard, the SetupState write gate), the managed manifest of note types, decks, preset, and template files, the Setup screen (readiness, preview, confirmed apply, verify, migrations), and the Sync feature (startup, every five minutes, graceful shutdown, coalesced). Delivers CAP-2 and CAP-11 in the spec.

## Outcome

The user previews and applies every Managed resource change with confirmation, a repeat run changes nothing, and AnkiWeb stays current without ever blocking work — AC3, AC7 (no sibling burying), AC20 (non-session triggers), and AC22 enforcement.

## Done when

1. On the released wheel, Setup against an empty `LanguageLabDev` Prefix previews, applies after confirmation, and verifies the five note types, the complete deck tree, and the `<Prefix>` preset with sibling burying off; Anki is unchanged before confirmation, and a second run shows no changes (AC3, FR-6, FR-8).
2. The readiness checks report AnkiConnect reachability, Azure and OpenRouter keys configured, the Prefix in effect, and full-sync-required status, each pass/fail on its own (FR-5).
3. A schema migration fixture runs only inside a confirmed plan, and a repair leaves user-set deck options alone (FR-7, CAP-2).
4. Any adapter write outside the Prefix is rejected, and non-Setup writes return `409 setup_required` unless SetupState is `ready` (AD-4, AD-19, NFR-1).
5. With the wheel running, Sync happens at startup, every five minutes, and at graceful shutdown; with AnkiConnect down, failures are logged and nothing blocks (FR-36, AC20 partial).

## Boundaries

`ports/` (AnkiStore, SyncRequester), `adapters/anki` (client, lock, codec, Prefix guard, setup-state gate, `manifest.py`, template files), `features/setup`, `features/sync`, the Setup screen, and docs for upgrade, never-downgrade, and the full-sync upload step. Not the final card template visuals (epic-capture-to-item) and not the Pronunciation session triggers (epic-pronunciation-review).

## References

- parent — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, CAP-2, CAP-11; Assumptions (unrecognized content rows)
- prd — prd-languagelab/prd-languagelab.md, FR-5–FR-8, FR-36, NFR-1–NFR-3, AC3, AC7, AC20, AC22; addendum.md A3 (note types, fields, deck tree)
- architecture — architecture-languagelab/architecture-languagelab.md, AD-1, AD-2, AD-3, AD-4, AD-5, AD-7, AD-9, AD-10, AD-17, AD-19
- ux — ux-languagelab/mockups/S-Setup.dc.html, S-SetupStates.dc.html; EXPERIENCE.md Setup states

## Notes

- Decision (2026-10-08): the readiness check tests only that Azure and OpenRouter keys are configured, no live calls.
- Decision (2026-10-08): this epic owns `manifest.py` and ships working template files; epic-capture-to-item writes their final markup and CSS as a template-only change with no SchemaVersion bump.
- Decision (2026-10-14): real Anki with AnkiConnect runs only on the Mac Mini; live checks and AnkiConnect fixture recording go through a wheel command there (see memory: Mac Mini is uvx and wheels only), and development tests run against fakes and recorded fixtures.
- Decision (2026-10-14): AnkiConnect behavior on schema changes, Sync results (full sync required, not logged in, offline), and deck-config bury fields is settled by a hitl spike right after the tracer, not by unknowns on entries.
- Decision (2026-10-14): `newer_schema` shows a blocking inline alert on Setup ("Anki was set up by a newer LanguageLab. Install the latest release."), Apply hidden, writes gated; visual pattern from the failing readiness tile.
- Decision (2026-10-14): opt-in repairs (orphan media, misplaced or unsuspended managed cards) are change rows with an unchecked checkbox each; only checked rows enter the plan and its hash; non-managed rows stay read-only.
- Decision (2026-10-14): entry 1 is the tracer; the Sync feature (10) follows the spike and goes before the guard-and-preview entry (6) because both edit the adapter, port, and fake; the manifest (4) is a parallel lane after the tracer; repairs (11) follow migrations (9) because they share the setup service and screen.
- Decision (2026-10-14): the user merged the field codec into the manifest entry (4) and the Prefix guard into the preview entry (6), giving 12 entries; ids 3 and 5 are retired.
- Decision (2026-10-14): spike 2 probes in a throwaway Anki profile logged in to a throwaway AnkiWeb account, so the real collection and LanguageLabDev stay untouched.
- Decision (2026-10-14): entry 6 stays merged and carries `refine = true`, so it gets full acceptance criteria before the build.
- Decision (2026-10-14): the Refactor sweep (14) runs after device acceptance (13), as in epic 1; CI covers the sweep.
- Waits on epic-platform-baseline because: it needs the composition root, settings, error envelope, shell, and test harness.

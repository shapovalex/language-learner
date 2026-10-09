---
type: epic
title: "Captures"
parent: initiative-languagelab-v1
covers: [CAP-3]
after: []
assignee: ""
risk: low
---

# Captures

## Description

The user saves text from any browser as a Capture that is never studied, lists Captures newest first, opens one, and deletes it after confirmation. Usable on its own to collect words before Drafts exist. Delivers CAP-3 in the spec.

## Outcome

Words met on the iPhone, iPad, or desktop land in Anki as suspended Capture notes without loss — AC4.

## Done when

1. On the released wheel, a Capture saved from the iPhone over Tailscale is stored as a suspended Capture note under the Prefix, and retrying the same request creates no second note (AC4, AD-20).
2. The Captures list shows text and creation time, newest first, on phone and desktop layouts (FR-10).
3. Deleting a Capture asks "Delete this Capture?" and removes only that note after confirmation (FR-13).
4. With AnkiConnect down, Save shows a visible error and nothing is reported as saved (CAP-3).

## Boundaries

`features/captures`, the AnkiStore Capture methods, Captures list, Capture detail, and the delete confirmation dialog (reused later for Item delete). Not starting an Item from a Capture (epic-capture-to-item) and not Capture search (deferred).

## References

- parent — _bmad-output/initiative-languagelab-v1/spec-languagelab/spec-languagelab.md, CAP-3; Assumptions (Capture delete dialog)
- prd — prd-languagelab/prd-languagelab.md, FR-9, FR-10, FR-13, AC4
- architecture — architecture-languagelab/architecture-languagelab.md, AD-6 (Create Capture order), AD-8, AD-20
- ux — ux-languagelab/mockups/S-Captures.dc.html, S-CapturesDesk.dc.html, S-Delete.dc.html

## Notes

- Decision (2026-10-08): Captures is its own epic so it is usable early.
- Waits on epic-anki-setup-sync because: it needs the Capture note type and deck in the manifest and AnkiStore with the setup gate.

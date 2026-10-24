---
storyId: '5.3'
status: 'not-run'
prepared: '2026-10-24'
releaseTag: ''
wheel: ''
operator: ''
devices: []
---

# Maintain Items — released-wheel acceptance (Story 5.3)

Prepared during ATDD and updated with automated build evidence. No released-wheel or
real-Anki check has run for this story. Complete this record after the feature PR is
merged and the epic is separately released. The user runs the
release on the Mac mini against `LanguageLabDev`, from phone and desktop. Automated
replay tests cannot establish real review-history deletion or device acceptance.

## Automated implementation evidence

The [build verification record](../atdd/implementation-validation-5-3.json) records the
activated AC-1 through AC-12 RED/GREEN runs, added destructive-boundary checks and
regression results. The deletion checks run against the real guarded adapter over the
replay collection and against the browser UI with page-local API doubles:

- [HTTP contract](../../../tests/api/test_items_delete.py): validation, empty 204,
  scoped/repeated requests, fresh reads and safe error envelopes.
- [Guarded adapter](../../../tests/integration/test_anki_item_delete.py): exact scopes,
  both Categories, SetupGate, lock contention/release, note-before-media ordering,
  malformed replies, isolation and retry after partial cleanup/enumeration failure.
- [Browser behavior](../../../tests/e2e/test_item_delete.py): persisted Target and four
  Cards, safe confirmation/focus, edits and Previews retained on Cancel/failure,
  pending-navigation protection and refreshed phone/desktop/French lists.

These checks do not supply observed real-Anki replies, review-history deletion or
phone/desktop acceptance. Every manual result below remains not run. No production
release was made during this build; the release tag and wheel fields stay blank until
the separate release is available. Retain the five checks and raw-reply comparison
below as the release handoff.

## Setup and evidence

1. Record the release tag, wheel URL/path, `/api/health` version, operator, date,
   macOS/Anki/AnkiConnect versions and phone/desktop browser versions below. Install
   the released wheel using [the install guide](../../../docs/install.md), unset
   `LANGUAGE_LAB_DEV` and start with `ANKI_PREFIX=LanguageLabDev`. Check the startup
   Prefix, Tailscale Serve URL and Setup readiness before proceeding.
2. Use disposable English Vocabulary and Sentence Items, a French Item, and an
   unrelated English Item under `LanguageLabDev`. Record each ItemId, note id and
   all four card ids. Review the deletion candidate's cards in Anki before deletion.
   Save Card Info evidence (review history and scheduling) before the edit check.
   The edit and duplicate checks must retain those exact note/card identities.
3. Put a small test MP3 in Anki media named
   `LanguageLabDev_<ItemId>_<sha256-of-bytes-first-12-hex>.mp3`; put its exact name in
   the candidate's Audio field as `[sound:<name>]`. Add a second matching media file
   with different bytes/hash, unreferenced, to prove deletion cleans up leftovers
   as well as the current clip. This uses existing Anki media; epic 6 is not needed.
4. Record control note/card/media inventories for the unrelated Item and another
   Prefix. A second-Prefix test note with the same ItemId, plus media named for that
   Prefix, makes the isolation check stronger. Compare exact inventories afterwards.

## All five epic Done-when checks

| Check | Procedure | Required evidence | Result |
| --- | --- | --- | --- |
| 1 — AC11 / FR-23 | On phone and desktop, edit an existing Item, Save, then edit Target into a duplicate. Exercise Cancel/Open existing and the confirmed Save choice. | The saved fields change on the original note; note id, four card ids, scheduling and review-history entries stay the same. Duplicate choices preserve the intended ItemId. Failed Save keeps local edits. | not run |
| 2 — AC12 | Edit a managed field directly in Anki Desktop, leave and reopen the Item in LanguageLab. | The fresh read shows the Anki edit; it is not a stale browser snapshot. | not run |
| 3 — FR-24 / NFR-4 | Regenerate Russian meaning/alternatives, a Vocabulary example/translation and a Sentence Note. Exercise Keep current and Use preview, checking Anki before Save and after Save. | Current and Preview differ visibly. Keep current preserves fields; Use preview changes only the requested local field group; unrelated edits stay. Only Save changes the existing note. | not run |
| 4 — FR-22 / AD-12 | Search Target, Russian meaning and alternatives with mixed case, extra whitespace and normalized Unicode forms; check both Categories and switch Languages. Repeat on phone and desktop. | Normalized substring matches span both Categories of the selected Language; foreign-Language Items do not appear. Record the actual queries and matched ItemIds. | not run |
| 5 — AC21 / AD-6 | Open the reviewed candidate. Check the Target and all four Cards in the Delete confirmation, Cancel once, then confirm Delete permanently. Reopen/search and inspect Anki. | Cancel changes nothing. Confirmation removes exactly that note, its four Cards, their review histories and both matching media files. The refreshed list omits it. Other Items, media and Prefix inventories are unchanged. | not run |

For deletion evidence, show that the candidate's note and card ids existed before
the action and cannot be found afterwards. Do not count an empty initial history
or an unreviewed card as proof that review histories were removed.

## Failures and retry

| Check | Procedure | Required evidence | Result |
| --- | --- | --- | --- |
| Anki unreachable | Open an Item, make a local edit, close Anki, confirm deletion. Reopen Anki and confirm again. | The first request fails visibly with local edits retained. The second succeeds after a fresh confirmation; no unrelated Item changes. | not run |
| Partial cleanup | Use the automated failure-injection evidence linked from the ATDD checklist; if a real cleanup failure occurs, retain the response and remaining-media inventory and retry the same ItemId. | No media deletion follows a failed note deletion. A cleanup failure stops the sequence; retry can finish even when the note is already gone. Do not manufacture a pass without observing the failure. | not run |

## AnkiConnect reply checks

Retain sanitized request/response exchanges with the actual AnkiConnect version and
Prefix. Compare these with `tests/support/anki_state.py` and
`tests/support/anki_connect.py`; most existing note/media write replies are synthetic,
not recorded fixtures. Check success/error/result shapes, not generated numeric ids.

| Exchange | Expected replay shape to verify | Evidence path / result |
| --- | --- | --- |
| `notesInfo` before and after deletion | Existing note includes fields and four card ids; an already-gone note answers an empty entry. | not run |
| `deleteNotes` for a disposable dev note, then the same already-gone note | `{"result": null, "error": null}` on success, including the retry. Record any difference. | not run |
| `getMediaFilesNames` for `LanguageLabDev_<ItemId>_*` before/after | `{"result": ["<matching-name>", "..."], "error": null}` then an empty result. | not run |
| `deleteMediaFile` success and an already-missing disposable dev file | Replay uses `{"result": null, "error": null}`; retain the actual replies, including any missing-file error. | not run |

Store verified exchanges under `tests/fixtures/anki/` using the existing
`{"request": ..., "response": ...}` convention; update the fixture README and replay
behavior if observations differ. Link the committed paths here. Merely reporting
that the run worked does not verify a reply's shape.

## Recorded run

| Field | Value |
| --- | --- |
| Release tag / wheel URL / health version | not recorded |
| Operator / date / Mac mini / Anki / AnkiConnect | not recorded |
| Phone / desktop browsers and versions | not recorded |
| Test Items and before/after inventories | not recorded |
| Review-history and scheduling evidence | not recorded |
| Raw reply fixtures and comparison notes | not recorded |
| Findings / follow-up tickets | not recorded |
| Final acceptance decision | pending |

Keep `status: not-run` until evidence exists. Record pass, fail or could-not-measure
per check; this ATDD scaffold does not close the story's human acceptance requirement.

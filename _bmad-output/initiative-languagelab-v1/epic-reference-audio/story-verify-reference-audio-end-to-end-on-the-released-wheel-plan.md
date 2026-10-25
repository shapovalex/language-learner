---
title: 'Verify Reference audio end to end on the released wheel'
type: 'chore'
ticket: '4'
created: '2026-10-25'
status: 'built'
baseline_revision: '99a4b49c54d5fb6b307354603ae99e719874b17a'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Stories 6.1–6.3 test the Draft audio card and the Item audio card separately, mostly against page-local API doubles. Nothing drives one Item's audio through its whole life in the real app, and the epic has no released-wheel acceptance record.

**Approach:** Add one integrated Playwright journey against the live app, driven and checked only through the UI. Write a short acceptance checklist the user runs on the released wheel using only the LanguageLab UI and the Anki Desktop / AnkiMobile UI.

## Boundaries & Constraints

**Always:**
- User decision (2026-10-25): acceptance testing is simple and UI only. No API requests to Anki (AnkiConnect) or to the app (`curl`, `page.request`, `/api/...` calls in checks).
- The automated journey runs on the existing `live_server` (FakeAnkiStore, FakeSpeech). It acts only through roles and labels. It observes only what is on the page: alerts, chips, the card's native players, list rows. The players' sources may be read with the existing in-page probes (`rendered_audio_bytes`, `player_bytes`), because that is exactly what the user hears. One `page.route` on the Preview endpoint may return `SECOND_MP3` so a regeneration can be told apart from the first clip.
- The manual checklist uses only LanguageLab screens on iPhone Safari, iPad Safari and a desktop browser, plus Anki Desktop (Browse, card preview, Tools → Check Media) and AnkiMobile review. It runs with `ANKI_PREFIX=LanguageLabDev` and real Azure Voices in `en-US` and `fr-CA`. Every result starts as `not run`.
- No production code changes. If the journey finds a bug, record it and stop; do not fix it here.

**Never:** Raw AnkiConnect reply tables or fixture capture, `curl` steps, a release cut during this build, edits to ticket files, or invented manual passes. Push the branch and create a PR (AGENTS.md).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Create | Capture → Draft (en and fr), Voice, Preview, Use preview, Save | Saved banner. Opening the Item from Items search shows a player whose clip equals the previewed one | — |
| Stale | Edit the Target on the opened Item | "Audio no longer matches the text." and Regenerate audio. Save still works | — |
| Regenerate | Regenerate (Preview returns `SECOND_MP3`), Use preview, Save, reopen | Current player holds `SECOND_MP3` | — |
| Remove | Remove audio, Save, reopen | No player in the card | — |
| Delete | Delete permanently, confirm | Back on the Items list, without that Item | — |
| Failure (manual) | Anki Desktop closed during Save of an accepted Preview | Error shown. Edits and Preview kept. Retry after reopening Anki succeeds | — |

</frozen-after-approval>

## Code Map

- `tests/e2e/test_draft_audio.py::test_unintercepted_app_save_and_playback_preserve_preview_bytes` (L398–433) — the Capture → Draft → Preview → Save steps to follow. It ends with `page.request.get` checks, which the new journey must replace with opening the Item in the UI.
- `tests/support/audio_screen.py` — `preview_button`, `audio_button`, `rendered_audio_bytes`, `STALE_AUDIO`. `tests/support/item_audio_screen.py` — `item_audio_card`, `card_button`, `player_bytes`. `tests/support/audio.py` — `MP3`, `SECOND_MP3`, `PREVIEW_API`.
- `tests/support/captures_screen.py` (`compose_box`, `rows`, `is_save`), `items_screen.py` (`choose`, `write_it_myself`, `is_item_save`), `maintain_items_screen.py` (`search_box`, `item_row`, `edit_field`, `save_changes`), `delete_item_screen.py` (`delete_button`, `confirm_button`), `regenerate_screen.py` (`USE_PREVIEW`), `viewports.py` (`PHONE`, `DESKTOP`).
- `tests/fakes/speech.py` — returns `MP3` for every synthesis. Leave it unchanged.
- Model for the checklist: `_bmad-output/test-artifacts/acceptance/capture-to-item-acceptance-4-4.md` (layout, privacy note, Mac Mini `uvx` only) and `maintain-items-acceptance-5-3.md` (Done-when table). Leave out 5.3's AnkiConnect reply section.
- Install: `docs/install.md` (`uvx --from <wheel URL> language-lab`). Latest tag is `v0.7.0`; this epic ships in the next release, so the tag field stays blank.

## Tasks & Acceptance

**Execution:**
- [ ] `tests/e2e/test_reference_audio_journey.py` (new) — one `p0` journey, parametrized over English/French × phone/desktop. It runs every Matrix row except Failure, in order, on a fresh Target per run.
- [ ] `_bmad-output/test-artifacts/acceptance/reference-audio-acceptance-6-4.md` (new) — frontmatter `status: not-run`. Sections: Setup (install the wheel, LanguageLabDev, disposable Items, note the Anki Browse counts for other decks); one table for Done-when 1–5; rows for AC13, AC14, FR-23, FR-24, AC21 and AC15 (card audio placement in Anki Desktop and AnkiMobile); the Failure check; the out-of-Prefix check; and a Recorded run table. Each row says what to do in which UI and what you should see there. It links to the automated journey.

**Acceptance Criteria:**
- Given the new journey, when it runs in Chromium and WebKit, then all four cases pass, and the test makes no `page.request` calls and has no Anki or `/api` assertions.
- Given the checklist, when it is read, then every check can be done by tapping or clicking in LanguageLab, Anki Desktop or AnkiMobile, and every listed criterion has a row.

## Review Triage Log

Pass 1 (quick, 2026-10-25): high 0, medium 2, low 4, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence/action |
|---|---|---|---|
| Journey never picks a Voice in the Create step | low | patch | `make_item_with_audio` goes from Russian meaning straight to Preview, so the Matrix "Voice" step is never exercised. Select the locale Voice explicitly. |
| Checklist rows contradict each other on order and on which Item each uses | medium | patch | FR-24 can remove E's audio before DW5 deletes it, which defeats DW5's media check. Fix the run order and name the Item in each row. |
| Failure check creates an untracked third Item | low | patch | The Draft retry saves an Item that S5 doesn't list and nothing deletes. Add it as D and a cleanup step. |
| DW2's post-note-write leftovers clause has no row | medium | patch | No row covers AD-6 leftovers that Setup repairs. Add a row pointing to the automated failure injection, plus the Setup orphan-repair observation. |
| AC21 review-history removal is assumed, not checked | low | patch | Add before/after `rated:1` Browse searches. |
| French AC15 plays audio left stale by DW4 | low | patch | Fixed by the run order: FR-23 regenerates F before AC15. |

After the patches (commit 3011466), verification on my side: journey 8 passed in Chromium and WebKit; `make test` 1183 passed; `make lint` and `git diff --check` clean. Nothing deferred.

## Design Notes

UI-only ways to see the Anki side: the Audio field in Browse shows `[sound:LanguageLabDev_<ItemId>_<hash>.mp3]`. Tools → Check Media lists unused files, which shows leftovers after Remove/Delete and shows that Preview stored nothing. The note count for `deck:LanguageLabDev*` before and after Preview shows Preview wrote no note. The counts for other decks show nothing outside the Prefix changed. To check the exact clip by ear, play the Preview and then the saved clip in Anki: same Voice, same text, same sound.

## Verification

**Commands:**
- `uv run pytest tests/e2e/test_reference_audio_journey.py --browser chromium --browser webkit -q` — expected: 8 passed.
- `make test`, `make lint`, `git diff --check` — expected: clean.

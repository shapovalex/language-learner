---
storyId: '6.4'
status: 'not-run'
prepared: '2026-10-25'
releaseTag: ''
wheel: ''
operator: ''
devices: []
---

# Reference audio — released-wheel acceptance (Story 6.4)

The manual run that proves the released LanguageLab gives Items the Reference audio the user
picked and heard, in a real Anki collection on the Mac mini, used from the iPhone, the iPad and
a desktop browser. It covers epic-reference-audio Done-when 1 to 5 (DW1–DW5) and the criteria
behind them: AC13, AC14, FR-23, FR-24, AC21 and AC15 with real audio.

Every check is done by tapping or clicking: in LanguageLab on iPhone Safari, iPad Safari and a
desktop browser, in Anki Desktop (Browse, the card preview, Tools → Check Media) and in
AnkiMobile review. No terminal command is part of a check, and nothing is sent to AnkiConnect
or to the app's API by hand.

- **Release under test:** the next release after `v0.7.0`, the first with all of
  epic-reference-audio. Not cut yet: fill in the tag below when it exists.
- **Prefix under test:** `LanguageLabDev`, set as an environment override. Never `LanguageLab`.
- **Mode:** release (no `LANGUAGE_LAB_DEV`)
- **Voices:** real Azure Voices in `en-US` and `fr-CA`
- **Devices:** Mac mini (host, with Anki Desktop, AnkiConnect and Tailscale Serve), iPhone
  Safari and AnkiMobile, iPad Safari, a desktop browser on another computer

On the Mac mini use only `uvx`: no clone, no repository script.

This repository is public. Do not write your real tailnet name, machine name, login, AnkiWeb
account or any address in this file, and do not name decks or note types outside
`LanguageLabDev`. Write `<tailnet>` where a name would appear.

Every result starts as **not run**. Record each one as **pass**, **fail** or **not run** with
the reason, from what you saw yourself. Anything that fails or surprises you goes in
[Recorded run](#recorded-run) under Findings.

## Automated evidence

[`tests/e2e/test_reference_audio_journey.py`](../../../tests/e2e/test_reference_audio_journey.py)
drives one Item's audio through its whole life in the running app (fake Anki, fake Speech), in
Chromium and WebKit, English and French, at phone and desktop width, using only the UI:
Capture → Draft → Preview → Use preview → Save, then open the Item from Items search and hear
the same clip; edit the Target and see the stale warning, Save; Regenerate audio, Use preview,
Save, reopen and hear the new clip; Remove audio, Save, reopen and see no player; Delete
permanently and find the Item gone from the list. It cannot prove what real Anki stores, what
Azure sounds like, or how the Cards play on the devices: that is this run.

## Setup

| Step | Do | You should see |
| --- | --- | --- |
| S1 | On the Mac mini, install and start the released wheel as [the install guide](../../../docs/install.md) says, with the Prefix override: `ANKI_PREFIX=LanguageLabDev uvx --from <wheel URL> language-lab`. `LANGUAGE_LAB_DEV` must not be set. Your LanguageLab config must hold a working Azure Speech key and region. | The startup lines name `http://127.0.0.1:8787/` and `https://<tailnet>/`. |
| S2 | Open `/setup` in the desktop browser. Apply setup if it offers changes. | "LanguageLab v<the release under test>". After any Apply, "Nothing to change." |
| S3 | In Anki Desktop, open Browse. Search `deck:LanguageLabDev*` and write down the note count. Then, for each deck outside the Prefix, search `deck:"<that deck>"` and write down its card count (keep these numbers out of this file if the deck names are private; you only need to compare them later). | The counts, noted for later. |
| S4 | In Anki Desktop, run Tools → Check Media. | Note any unused `LanguageLabDev_*` files already listed, so you don't count them as new later. |
| S5 | Use only disposable Items made for this run, each from a new Capture with a Target you have never saved before: Item **E**, English Vocabulary (made in DW1); Item **F**, French Vocabulary or Sentence (make it the same way as E in DW1, on the iPhone, with an `fr-CA` Voice); Item **D**, made from a Draft in the Failure check. | — |

## Run order

The rows below share Items E, F and D, so run them in this one fixed order, not in table order:

1. Setup S1–S5
2. DW1 (E; then make F the same way)
3. DW2 (E), then AC13 (E)
4. DW3, then AC14
5. DW4 (F)
6. FR-23 (F: regenerates, so F's audio matches its Target again)
7. Failure check (F, then D)
8. AC15 (E and F, both with audio)
9. FR-24 (F's removal), then AC15's no-audio check on F
10. DW5 and AC21 (delete E, which still has audio)
11. Cleanup C1 (F and D)
12. DW2 leftovers (looks back over the whole run)
13. Out-of-Prefix check

## Done when

| Check | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| DW1 — Preview leaves Anki unchanged; Save stores the previewed clip (E) | LanguageLab on iPhone: new Capture → Make an Item → English → Vocabulary → Write it myself; fill the Russian meaning. Pick an `en-US` Voice, tap Preview and play it. Then in Anki Desktop Browse, search `deck:LanguageLabDev*` again and run Tools → Check Media. Back on iPhone, tap Use preview, then Save to Anki: this is Item E. In Browse, open E's note and look at its Audio field; play it in the card preview. In LanguageLab, open E from English Items search and play its clip. Then make F the same way (French, `fr-CA` Voice). | Before Save: the note count is the same as in S3 and Check Media lists no new file. After Save: the "Saved “<Target>” to Anki." banner. The Audio field reads `[sound:LanguageLabDev_<ItemId>_<hash>.mp3]`. The clip in Anki and the clip on Item detail sound exactly like the Preview: same Voice, same text. | not run |
| DW2 — Regenerating keeps the old clip until Save (E) | LanguageLab on the desktop browser: open E, choose a different Voice, click Regenerate audio. Play Current and the Preview. Before saving, play E's audio in the Anki Desktop card preview. Click Use preview, then Save changes. Reopen E from Items search; play its audio in Anki again and run Tools → Check Media. | Current and Preview sound different (two Voices). Before Save, Anki still plays the old clip. After Save, Item detail and Anki both play the new Voice, the Audio field names a new `LanguageLabDev_<ItemId>_<hash>.mp3`, and Check Media lists no unused `LanguageLabDev_<E's ItemId>_*` file. | not run |
| DW2 leftovers — failures after the note write stop without rollback and leave repairable leftovers | Cannot be induced from the UI: covered by the automated failure injection in [`tests/integration/test_anki_audio_lifecycle.py`](../../../tests/integration/test_anki_audio_lifecycle.py) (cleanup failures after the note write are retryable and Setup-repairable). Manual part: if `/setup` offers an orphan-media repair at any point in this run, Apply it, then run Tools → Check Media in Anki Desktop. | After Apply, Check Media no longer lists that `LanguageLabDev_*` file. If Setup never offered such a repair, record "not observed". | not run |
| DW3 — Voices persist per locale per browser | LanguageLab on iPad: in an English Draft pick one `en-US` Voice; in a French Draft pick an `fr-CA` Voice (discard both Drafts). Close the tab, open LanguageLab again, start a new English and a new French Draft. Then open a Draft on the iPhone. | On the iPad, each language shows the Voice last picked for it, and changing one never changes the other. The iPhone shows its own choices, not the iPad's. | not run |
| DW4 — Target edit warns of stale audio; Save still works (F) | LanguageLab on iPhone: open F, change its Target. Do not regenerate. Tap Save changes. In Anki Desktop Browse, open F's note. | "Audio no longer matches the text." with Regenerate audio, while editing. Save changes succeeds and the unsaved chip goes away. In Anki the Target field has the new text and the Audio field still names the earlier clip. | not run |
| DW5 — Delete removes managed media; Cards play the audio (E) | AC15 (step 8) and FR-24 (step 9) come first. Then in LanguageLab on the desktop browser, open E → Delete → check the dialog names E's Target and its four Cards → Delete permanently. In Anki Desktop Browse, search for E's Target; run Tools → Check Media. | Back on English Items without E. Browse finds no note and no Cards for E. Check Media lists no unused `LanguageLabDev_<E's ItemId>_*` file. | not run |

## Criteria

| Criterion | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| AC13 — Preview changes nothing; Save writes the exact clip; regeneration keeps the old audio until Save (E) | Covered by DW1 and DW2 above. Also, right after DW2: on E's Item detail, Regenerate audio, then Keep current; leave the screen and reopen E. | Keep current leaves E's Current clip and Anki's Audio field as they were. | not run |
| AC14 — last `en-US` and `fr-CA` Voices persist independently in each browser | Covered by DW3. Also repeat DW3 on the desktop browser. | As DW3, independently in each browser. | not run |
| FR-23 — Target edit on an Item with audio warns and offers regeneration (F) | Right after DW4, on the desktop browser: open F (its Target now edited, its audio stale), click Regenerate audio, Use preview, Save changes. | The warning goes once the new clip is accepted; after Save, Anki plays F's new Target text. | not run |
| AC15 — audio placement on the Cards (E and F) | With E and F both saved with matching audio (after the Failure check), in Anki Desktop open the card preview of E's Understand, Produce and Write Cards; then Sync and review the same Cards in AnkiMobile on the iPhone. Repeat for F. After FR-24 removes F's audio, Sync and look at F's Cards again in Anki Desktop and AnkiMobile. | Understand: an audio button may show on the front, and on the back. Produce: audio only after the answer is shown. Write: audio only after you submit or reveal the answer. The clip plays in both Anki Desktop and AnkiMobile. After the removal, F's Cards show no audio button at all. | not run |
| FR-24 — audio regeneration with side-by-side Preview; Anki unchanged until Save; discarding leaves the Item unchanged (F) | After AC15, LanguageLab on iPhone: open F, Regenerate audio, then Keep current. Then Remove audio and Keep audio. Then Remove audio and Save changes; reopen F; check F's note in Browse and run Tools → Check Media. Then do AC15's no-audio check on F. | Current and "Preview · not saved" side by side. Keep current and Keep audio leave F and Anki as they were. After the saved removal, F's Item detail has no player, its Audio field is empty, its French Items row has no audio icon, and Check Media lists no unused `LanguageLabDev_<F's ItemId>_*` file. | not run |
| AC21 — permanent deletion removes the note, Cards, review histories and managed audio (E) | Before DW5, review at least one of E's Cards in Anki (Desktop or AnkiMobile, then Sync). In Anki Desktop Browse search `rated:1 "<E's Target>"`. Then do DW5 and run the same `rated:1` search again. | Before deleting, the search lists E's reviewed Card. After deleting, it lists no Card for E's Target. Otherwise as DW5. | not run |

## Failure check

| Check | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| Anki closed during Save (F, then D) | LanguageLab on the desktop browser: open F, edit its Mnemonic, Regenerate audio and Use preview. Quit Anki Desktop on the Mac mini. Click Save changes. Then open Anki Desktop again and click Save changes once more. Check F's note in Browse and play its audio. Then on the iPhone, make Item D from a new Capture with the DW1 flow (Preview, Use preview), quit Anki Desktop, tap Save to Anki; open Anki Desktop again and tap Save to Anki once more. | F: the first Save shows an error alert, and the Mnemonic edit and the accepted Preview are still on screen. The second Save succeeds, and Anki has the edited Mnemonic and plays the new clip. D: "Not saved — Anki isn't reachable", the text and Preview are kept, and the retry saves D. | not run |

## Cleanup

| Step | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| C1 — delete F and D | LanguageLab on the desktop browser: open F → Delete → Delete permanently; then the same for D. In Anki Desktop, run Tools → Check Media. | Both are gone from their Items lists. Check Media lists no unused `LanguageLabDev_<F's or D's ItemId>_*` file. | not run |

## Out-of-Prefix check

| Check | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| Nothing outside `LanguageLabDev` changed | At the end, in Anki Desktop Browse, repeat the S3 card counts for every deck outside the Prefix, and run Tools → Check Media. | Every outside count matches S3. Check Media lists no new unused file other than those noted in S4. | not run |

## Recorded run

| Field | Value |
| --- | --- |
| Release tag / wheel URL / version on Setup | not recorded |
| Operator / date | not recorded |
| Mac mini macOS / Anki Desktop / AnkiConnect versions | not recorded |
| iPhone, iPad and desktop browser versions; AnkiMobile version | not recorded |
| Voices used (`en-US`, `fr-CA`) | not recorded |
| Disposable Items E, F and D (Target, Language, Category) | not recorded |
| Findings / follow-up tickets | not recorded |
| Final acceptance decision | pending |

Keep `status: not-run` until the run is done. A result counts only when you saw it yourself on
the device named in its row.

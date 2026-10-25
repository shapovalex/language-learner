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
| S5 | Use only disposable Items made for this run: one English Vocabulary Item and one French Item (Vocabulary or Sentence), each from a new Capture with a Target you have never saved before. | — |

## Done when

| Check | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| DW1 — Preview leaves Anki unchanged; Save stores the previewed clip | LanguageLab on iPhone: new Capture → Make an Item → English → Vocabulary → Write it myself; fill the Russian meaning. Pick a Voice, tap Preview and play it. Then in Anki Desktop Browse, search `deck:LanguageLabDev*` again and run Tools → Check Media. Back on iPhone, tap Use preview, then Save to Anki. In Browse, open the new note and look at its Audio field; play it in the card preview. In LanguageLab, open the Item from English Items search and play its clip. | Before Save: the note count is the same as in S3 and Check Media lists no new file. After Save: the "Saved “<Target>” to Anki." banner. The Audio field reads `[sound:LanguageLabDev_<ItemId>_<hash>.mp3]`. The clip in Anki and the clip on Item detail sound exactly like the Preview: same Voice, same text. | not run |
| DW2 — Regenerating keeps the old clip until Save | LanguageLab on the desktop browser: open the English Item, choose a different Voice, click Regenerate audio. Play Current and the Preview. Before saving, play the note's audio in the Anki Desktop card preview. Click Use preview, then Save changes. Reopen the Item from Items search; play the note's audio in Anki again and run Tools → Check Media. | Current and Preview sound different (two Voices). Before Save, Anki still plays the old clip. After Save, Item detail and Anki both play the new Voice, the Audio field names a new `LanguageLabDev_<ItemId>_<hash>.mp3`, and Check Media lists no unused `LanguageLabDev_<ItemId>_*` file. | not run |
| DW3 — Voices persist per locale per browser | LanguageLab on iPad: in an English Draft or Item pick one `en-US` Voice; in a French one pick an `fr-CA` Voice. Close the tab, open LanguageLab again, start a new English and a new French Draft. Then open a Draft on the iPhone. | On the iPad, each language shows the Voice last picked for it, and changing one never changes the other. The iPhone shows its own choices, not the iPad's. | not run |
| DW4 — Target edit warns of stale audio; Save still works | LanguageLab on iPhone: open the French Item, change its Target. Do not regenerate. Tap Save changes. In Anki Desktop Browse, open the note. | "Audio no longer matches the text." with Regenerate audio, while editing. Save changes succeeds and the unsaved chip goes away. In Anki the Target field has the new text and the Audio field still names the earlier clip. | not run |
| DW5 — Delete removes managed media; Cards play the audio | First do the AC15 row below. Then in LanguageLab on the desktop browser, open the English Item → Delete → check the dialog names the Target and its four Cards → Delete permanently. In Anki Desktop Browse, search for the Target; run Tools → Check Media. | Back on English Items without that Item. Browse finds no note and no Cards for it. Check Media lists no unused `LanguageLabDev_<ItemId>_*` file. | not run |

## Criteria

| Criterion | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| AC13 — Preview changes nothing; Save writes the exact clip; regeneration keeps the old audio until Save | Covered by DW1 and DW2 above. Also: on Item detail, Regenerate audio, then Keep current; leave the screen and reopen. | Keep current leaves the Current clip and Anki's Audio field as they were. | not run |
| AC14 — last `en-US` and `fr-CA` Voices persist independently in each browser | Covered by DW3. Also repeat on the desktop browser. | As DW3, independently in each browser. | not run |
| FR-23 — Target edit on an Item with audio warns and offers regeneration | Covered by DW4. Also on the desktop browser: edit the Target, then click Regenerate audio, Use preview, Save changes. | The warning goes once the new clip is accepted; after Save, Anki plays the new text. | not run |
| FR-24 — audio regeneration with side-by-side Preview; Anki unchanged until Save; discarding leaves the Item unchanged | LanguageLab on iPhone: Regenerate audio, then Keep current. Then Remove audio and Keep audio. Then Remove audio and Save changes; reopen the Item; check Browse and Tools → Check Media. | Current and "Preview · not saved" side by side. Keep current and Keep audio leave the Item and Anki as they were. After the saved removal, Item detail has no player, the Audio field is empty, the English Items row has no audio icon, and Check Media lists no unused `LanguageLabDev_<ItemId>_*` file. | not run |
| AC21 — permanent deletion removes the note, Cards, review histories and managed audio | Covered by DW5. Review at least one of the Item's Cards in Anki before deleting it. | As DW5; the reviewed Card is gone with the rest. | not run |
| AC15 — audio placement on the Cards | With the English Item saved with audio (before DW5), in Anki Desktop open the card preview of its Understand, Produce and Write Cards; then Sync and review the same Cards in AnkiMobile on the iPhone. Repeat for the French Item. | Understand: an audio button may show on the front, and on the back. Produce: audio only after the answer is shown. Write: audio only after you submit or reveal the answer. The clip plays in both Anki Desktop and AnkiMobile. An Item without audio (after the FR-24 removal) shows no audio button at all. | not run |

## Failure check

| Check | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| Anki closed during Save | LanguageLab on the desktop browser: open the French Item, edit its Mnemonic, Regenerate audio and Use preview. Quit Anki Desktop on the Mac mini. Click Save changes. Then open Anki Desktop again and click Save changes once more. Check the note in Browse and play its audio. | First Save: an error alert; the Mnemonic edit and the accepted Preview are still on screen. Second Save succeeds. Anki has the edited Mnemonic and plays the new clip. Also try it once from a Draft (DW1 flow) on the iPhone: "Not saved — Anki isn't reachable", the text and Preview kept, and the retry saves. | not run |

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
| Disposable Items (Target, Language, Category) | not recorded |
| Findings / follow-up tickets | not recorded |
| Final acceptance decision | pending |

Keep `status: not-run` until the run is done. A result counts only when you saw it yourself on
the device named in its row.

---
storyId: '7.4'
status: 'not-run'
prepared: '2026-10-25'
releaseTag: ''
wheel: ''
operator: ''
devices: []
---

# Pronunciation review — released-wheel acceptance (Story 7.4)

The manual run that proves the released LanguageLab runs a real Pronunciation review against a
real Anki collection on the Mac mini, with real Azure assessment, used from the iPhone, the iPad
and a desktop browser. It covers epic-pronunciation-review Done-when 1 to 6 (DW1–DW6) and the
criteria behind them: AC16, AC2 (microphone part), AC17, AC18, AC19, AC20 (session part) and
CAP-10.

Every check is done by tapping or clicking: in LanguageLab on iPhone Safari, iPad Safari and a
desktop browser over Tailscale HTTPS, in Anki Desktop (Browse, Card Info, Tools → Check Media,
the sync button) and in AnkiMobile (deck list, Sync). No terminal command is part of a check,
and nothing is sent to AnkiConnect, to Azure or to the app's API by hand.

- **Release under test:** the next release after `v1.0.0`, the first with all of
  epic-pronunciation-review. Not cut yet: fill in the tag below when it exists.
- **Prefix under test:** `LanguageLabDev`, set as an environment override. Never `LanguageLab`.
- **Mode:** release (no `LANGUAGE_LAB_DEV`)
- **Assessment:** real Azure Speech, `en-US` and `fr-CA`
- **Devices:** Mac mini (host, with Anki Desktop, AnkiConnect and Tailscale Serve), iPhone
  Safari and AnkiMobile, iPad Safari, a desktop browser on another computer

On the Mac mini use only `uvx` and the wheel: no clone, no repository script.

This repository is public. Do not write your real tailnet name, machine name, login, AnkiWeb
account or any address in this file, and do not name decks or note types outside
`LanguageLabDev`. Write `<tailnet>` where a name would appear.

Every result starts as **not run**. Record each one as **pass**, **fail** or **not run** with
the reason, from what you saw yourself. Anything that fails or surprises you goes in
[Recorded run](#recorded-run) under Findings.

## Automated evidence

[`tests/e2e/test_pronunciation_journey.py`](../../../tests/e2e/test_pronunciation_journey.py)
drives one review session through the running app (fake Anki seeded with one due and one new
Pronounce Card per Language, fake Speech answering the real Azure reply fixture parsed by the
real adapter, a fake microphone), in Chromium and WebKit, English and French, at phone and
desktop width, using only the UI: open the queue and see "1 due · 1 new" with Ratings disabled;
tap Reference and see the browser load the Card's clip; record an Attempt and see the score ring and Word
feedback (English: IPA phonemes and prosody; French: start, middle and end, no sound named);
Try again and see new feedback on the same Card; rate Good and move to the new Card with
"0 due · 1 new"; record and rate Easy and see "Nothing to practice in {Language}". It cannot
prove real microphone permission, what Azure answers, what Anki's scheduler does, or when Anki
syncs: that is this run.

Logs carrying no audio, scores or Target (DW5, NFR-7) cannot be seen from a UI; that part is
covered by [`tests/api/test_pronunciation_attempt.py`](../../../tests/api/test_pronunciation_attempt.py)
and [`tests/api/test_pronunciation.py`](../../../tests/api/test_pronunciation.py).

A failed Assessment leaving the Card unanswered and current (DW6, CAP-10) cannot be induced
from the UI against real Azure; it is covered by
`test_assessment_failure_offers_record_again_or_exit_without_answering` in
[`tests/e2e/test_pronunciation_attempt.py`](../../../tests/e2e/test_pronunciation_attempt.py).

## Setup

| Step | Do | You should see |
| --- | --- | --- |
| S1 | On the Mac mini, install and start the released wheel as [the install guide](../../../docs/install.md) says, with the Prefix override: `ANKI_PREFIX=LanguageLabDev uvx --from <wheel URL> language-lab`. `LANGUAGE_LAB_DEV` must not be set. Your LanguageLab config must hold a working Azure Speech key and region. | The startup lines name `http://127.0.0.1:8787/` and `https://<tailnet>/`. |
| S2 | Open `/setup` in the desktop browser. Apply setup if it offers changes. | "LanguageLab v<the release under test>". After any Apply, "Nothing to change." |
| S3 | In LanguageLab make two disposable Items per Language, each from a new Capture with a Target you have never saved before and with Reference audio (Preview, Use preview, Save to Anki): **E1**, **E2** (English) and **F1**, **F2** (French). Use short, plain Targets you can say easily. | Each Save shows "Saved “<Target>” to Anki." |
| S4 | In Anki Desktop, open Browse and search `deck:LanguageLabDev* card:3 (is:due OR is:new)`. | Exactly four Cards: the Pronounce Cards of E1, E2, F1 and F2. If anything else is listed, LanguageLab would queue it too and there is no skip control: start again from an empty `LanguageLabDev` collection (a fresh Anki profile) and redo S1–S4. |
| S5 | In Anki Desktop, open Browse, search `deck:LanguageLabDev*`, and for each of the four Items open its Pronounce Card → Card Info. Write down its Reviews count, Due date and last Rating (none for a new Card). Then run Tools → Check Media and note any unused `LanguageLabDev_*` files already listed. | The four Pronounce Cards, each with "Reviews 0" (new), and the Check Media list, noted for later. |
| S6 | In Anki Desktop, click Sync. Then in AnkiMobile on the iPhone, tap Sync and note the `LanguageLabDev` Pronounce deck's New and Due counts. | AnkiMobile's counts include the four new Pronounce Cards. |

## Run order

The rows below share the Items, so run them in this one fixed order, not in table order:

1. Setup S1–S6
2. DW2 (all three devices), then DW2 denied
3. DW1 (E1 on the iPhone), then DW4 en-US
4. DW4 fr-CA (F1 on the iPad)
5. DW1 retry check (E1, still unrated)
6. DW3 (rate E1 and F1 Easy)
7. DW6 Anki closed (E2)
8. DW6 Sync (start, finish, close mid-session)
9. DW5 (afterwards)

## Done when

| Check | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| DW2 — microphone permission on each device | On the iPhone (Safari), then the iPad (Safari), then the desktop browser, each over `https://<tailnet>/`: open English Pronunciation and tap Record. When the browser asks for the microphone, tap Allow. Say the Target, tap again to stop. | The browser's own microphone prompt names the `<tailnet>` site. After Allow, the button reads "Listening… tap to stop" with a moving level meter, then "Checking…", then a score ring. | not run |
| DW2 — denied permission shows mic-blocked | On the iPad: in Safari's website settings for `<tailnet>`, set Microphone to Deny (or Ask, then tap Don't Allow at the prompt). Reload English Pronunciation and tap Record. Afterwards set Microphone back to Allow. | "LanguageLab can't hear you" and "Allow microphone access for this site in Safari, then reload the page." No score ring, Ratings stay disabled, and no Attempt is assessed. | not run |
| DW1 — Reference, Attempt, feedback (E1, iPhone) | LanguageLab on the iPhone: open English Pronunciation; E1 (made first) is the current Card. Tap Reference and listen. Tap Record, say E1's Target, tap to stop. | The chip "N due · M new"; E1's Target. Reference plays the clip saved in S3. Ratings are disabled until the Attempt. Then a score ring, sub-scores and Word feedback for E1's words. | not run |
| DW4 — en-US feedback (E1, iPhone) | Right after DW1, on the same screen: look at the scores and Word feedback; tap another word pill. | Accuracy, Fluency, Completeness and Prosody scores. The Word feedback for the selected word lists IPA symbols (for example `θ`, `ɔ`) each with a score. No Rating is highlighted, preselected or suggested by the feedback. | not run |
| DW4 — fr-CA feedback (F1, iPad) | LanguageLab on the iPad: open French Pronunciation with F1 current. Tap Record, say F1's Target, tap to stop. Look at the Word feedback; tap another word pill. | An overall score, Accuracy, Fluency, Completeness, word scores, and "Where in the word" with start, middle and end scores. "Prosody isn't available." No IPA symbol and no named sound anywhere. No Rating is highlighted or suggested. | not run |
| DW1 — retry leaves Anki unchanged (E1) | LanguageLab on the iPhone, E1 current: tap Try again, say the Target, stop; do it once more. Do not rate. Then in Anki Desktop Browse open E1's Pronounce Card → Card Info. | Each retry shows new feedback, E1 stays the current Card and the chip is unchanged. In Card Info, Reviews, Due date and last Rating are exactly as noted in S5. | not run |
| DW3 — a Rating answers only that Card, once (E1, F1) | LanguageLab on the iPhone, E1 current with feedback: tap Easy. On the iPad, F1 current with feedback: double-tap Easy quickly. (Easy graduates a new Card out of learning, so neither comes back during this run.) Then in Anki Desktop Browse open Card Info for E1, F1, E2 and F2. Click Sync in Anki Desktop, then tap Sync in AnkiMobile and look at the Pronounce deck counts. | After each Rating the next Card's Target shows (E2 on the iPhone, F2 on the iPad: they are now the next Cards) and the chip drops by one. E1's Card Info shows Reviews 1, an Easy rating and a Due date days away; F1's shows Reviews 1 (not 2, despite the double-tap) and Easy. E2 and F2 are unchanged from S5. AnkiMobile's New count is two lower than in S6. A Rating whose reply was lost and is retried is covered by `test_a_retried_rating_with_stale_reps_is_already_answered_without_a_second_answer` in [`tests/api/test_pronunciation.py`](../../../tests/api/test_pronunciation.py). | not run |
| DW6 — Anki closed during a Rating keeps the Card current (E2) | LanguageLab on the desktop browser: open English Pronunciation with E2 current; record an Attempt. Quit Anki Desktop on the Mac mini. Click Good. Open Anki Desktop again, wait until it is ready, click Good once more. Then open E2's Card Info. | The first Good shows "Rating not saved — Anki isn't reachable." and E2 stays current with its Target and feedback. The second Good moves to the next Card. Card Info shows Reviews 1 (not 2) and a Good rating. | not run |
| DW6 — Sync on session start, finish and tab close | Anki Desktop open on the Mac mini, watched. (a) On the iPhone, open French Pronunciation with F2 queued: watch Anki Desktop's sync indicator. (b) Record an Attempt for F2, rate Easy until "Nothing to practice in French" shows: watch the indicator again. Before (b), with F2 current, switch to another app on the iPhone for a few seconds (the tab is hidden), watch the indicator, then come back. (c) On the iPad, open English Pronunciation with a Card left (or re-add one by making a new Item); then close the Safari tab without rating. Watch the indicator. Then, without clicking Sync in Anki Desktop, open AnkiMobile and tap Sync. | Anki Desktop shows it syncing shortly after (a), after the switch away, after (b) and after (c), each without you clicking Sync. AnkiMobile picks up F2's Rating without a manual desktop Sync. | not run |
| DW5 — nothing left to delete afterwards | After all rows above: in Anki Desktop run Tools → Check Media. In LanguageLab on each device, leave Pronunciation, come back to it. | Check Media lists no new unused file compared with S5: no recording or Assessment file was stored. Coming back shows no earlier score ring or Word feedback; Ratings are disabled until a new Attempt. | not run |

## Cleanup

| Step | Do (where) | You should see | Result |
| --- | --- | --- | --- |
| C1 — delete the disposable Items | LanguageLab on the desktop browser: open E1, E2, F1 and F2 (and any Item made in DW6) → Delete → Delete permanently. In Anki Desktop run Tools → Check Media. | All are gone from their Items lists. Check Media lists no unused `LanguageLabDev_<their ItemId>_*` file. | not run |

## Recorded run

| Field | Value |
| --- | --- |
| Release tag / wheel URL / version on Setup | not recorded |
| Operator / date | not recorded |
| Mac mini macOS / Anki Desktop / AnkiConnect versions | not recorded |
| iPhone, iPad and desktop browser versions; AnkiMobile version | not recorded |
| Disposable Items E1, E2, F1, F2 (Target, Language, Category) | not recorded |
| Findings / follow-up tickets | not recorded |
| Final acceptance decision | pending |

Keep `status: not-run` until the run is done. A result counts only when you saw it yourself on
the device named in its row.

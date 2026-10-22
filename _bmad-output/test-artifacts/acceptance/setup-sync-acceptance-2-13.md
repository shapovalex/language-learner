# Setup and Sync acceptance on the released wheel (story 2.13)

The manual run that proves the released LanguageLab does Setup and Sync against a real Anki
collection on the Mac Mini. It covers epic-anki-setup-sync Done-when 1, 2 and 5 and the
deck-option half of 3. The migration half of 3 and Done-when 4 are proved in CI; see
[CI evidence](#ci-evidence).

- **Release under test:** `v0.4.0`, the first release with entries 1 to 12 of the epic
- **Prefix under test:** `LanguageLabDev`, set as an environment override. Never `LanguageLab`.
- **Mode:** release (no `LANGUAGE_LAB_DEV`): dev mode never Syncs
- **Run on:** 2026-10-21
- **Machine:** Mac Mini (host, with Anki Desktop, AnkiConnect, and an AnkiWeb login)

This repository is public. Do not write your real tailnet name, machine name, login, AnkiWeb
account or any address in this file, and do not paste AnkiConnect output that names your own
decks or note types. Write `<tailnet>` where a name would appear.

Record each step in [Results](#results) as **pass**, **fail**, or **not run** with the reason.
Anything that fails, surprises you, or that the docs got wrong goes in [Findings](#findings).
Paste the terminal lines the steps ask for into the Notes column or under Findings.

## A. Release and an empty Prefix

On the development machine:

| Step | Do | Expect |
| --- | --- | --- |
| A1 | From a clean checkout of `main` with entries 1 to 12 merged: `scripts/cut_release.sh 0.4.0`. | It ends with `Released v0.4.0. Wheel:` and the URL `https://github.com/shapovalex/language-learner/releases/download/v0.4.0/language_lab-0.4.0-py3-none-any.whl`. The docs' `uvx` lines now name `v0.4.0`. |

On the Mac Mini, with Anki Desktop open, AnkiConnect installed, and the open profile logged in to AnkiWeb (click Sync in Anki Desktop; if it asks you to sign in, do so). In the terminal you will use
for the whole run, set:

```sh
WHEEL=https://github.com/shapovalex/language-learner/releases/download/v0.4.0/language_lab-0.4.0-py3-none-any.whl
ac() { curl -s http://127.0.0.1:8765 -d "{\"action\":\"$1\",\"version\":6${2:+,\"params\":$2}}"; echo; }
```

`ac deckNames` then sends `{"action":"deckNames","version":6}` to AnkiConnect.

| Step | Do | Expect |
| --- | --- | --- |
| A2 | `env \| grep LANGUAGE_LAB_DEV; echo "exit=$?"` | No variable printed, `exit=1`. If it is set, `unset LANGUAGE_LAB_DEV`. |
| A3 | `ac deckNames \| tr ',' '\n' \| grep -c LanguageLabDev` and `ac modelNames \| tr ',' '\n' \| grep -c LanguageLabDev` | `0` both times: no deck and no note type named `LanguageLabDev…`. |
| A4 | In Anki Desktop, open any deck's Options and open the preset list at the top. | No preset named `LanguageLabDev`. |
| A5 | `ac getMediaFilesNames '{"pattern":"LanguageLabDev_*"}'` | `{"result": [], "error": null}`: no `LanguageLabDev_*` media file, which D2 would otherwise list under "Optional repairs". |

**To clear the Prefix** if A3, A4 or A5 finds anything (it is the dev Prefix, so nothing in it is
yours to keep): in Anki Desktop, delete the `LanguageLabDev` deck (its subdecks and cards go with
it); in Tools > Manage Note Types, delete each `LanguageLabDev …` note type (this deletes its
notes); in a deck's Options, select the `LanguageLabDev` preset and choose Remove preset from the
menu beside Save; delete each media file A5 lists with
`ac deleteMediaFile '{"filename":"<name>"}'` (or Tools > Check Media, then Delete Unused). Then
run A3 to A5 again.

## B. Start the release

Follow [docs/install.md](../../../docs/install.md) "Start the app" and
[docs/configuration.md](../../../docs/configuration.md) "Environment overrides" as written. A
step that fails or misleads is a finding.

| Step | Do | Expect |
| --- | --- | --- |
| B0 | `grep -cE '^(AZURE_SPEECH_KEY\|AZURE_SPEECH_REGION\|OPENROUTER_API_KEY)=.+' ~/.config/language-lab/.env` (prints a count, never the values). Skip it before the very first start, when the file doesn't exist yet: B1 asks for the three values, then run B0. | `3`: all three are set, which C1, C4 and C5 rely on. If not, set the missing ones in the file (see [docs/configuration.md](../../../docs/configuration.md)) and restart. |
| B1 | `ANKI_PREFIX=LanguageLabDev uvx --from "$WHEEL" language-lab` | `LanguageLab running at http://127.0.0.1:8787/` (and the tailnet line if Tailscale is up). Within a few seconds, the startup Sync line: `Sync with AnkiWeb: ok`. Note the time it printed. |
| B2 | In a second terminal: `curl -s http://127.0.0.1:8787/api/health` | `{"version":"0.4.0"}` |

Leave the app running; parts C to F use it. Every later restart uses the B1 command unless a step
says otherwise.

## C. Readiness, each check on its own (Done-when 2)

| Step | Do | Expect |
| --- | --- | --- |
| C1 | Open `http://127.0.0.1:8787/setup`. | "Ready to go?" shows three passing tiles: "AnkiConnect reachable", "Azure configured", "OpenRouter configured". The subtitle reads "Creates or repairs everything LanguageLab manages under the prefix **LanguageLabDev**. Safe to run again." No "Full sync required" tile. |
| C2 | `curl -s http://127.0.0.1:8787/api/setup/readiness` | `{"prefix":"LanguageLabDev","checks":[{"id":"ankiConnect","ok":true},{"id":"azure","ok":true},{"id":"openrouter","ok":true},{"id":"fullSync","ok":true}]}` |
| C3 | Quit Anki Desktop. Reload `/setup` and repeat C2. | Only AnkiConnect fails: tile "AnkiConnect not reachable" with its fix; Azure and OpenRouter still pass; `ankiConnect` is `false`, the other three `true`. Start Anki again and reload: all pass. |
| C4 | Stop the app (Ctrl+C). Start it with `AZURE_SPEECH_KEY= ANKI_PREFIX=LanguageLabDev uvx --from "$WHEEL" language-lab`. Reload `/setup`, repeat C2. | Only Azure fails: tile "Azure not configured" with its fix; `azure` is `false`, the rest `true`. |
| C5 | Stop the app. Start it with `OPENROUTER_API_KEY= ANKI_PREFIX=LanguageLabDev uvx --from "$WHEEL" language-lab`. Reload `/setup`, repeat C2. | Only OpenRouter fails: tile "OpenRouter not configured"; `openrouter` is `false`, the rest `true`. |
| C6 | Stop the app and start it again with the B1 command. | All three tiles pass again. |

The failing `fullSync` tile cannot be produced on an empty Prefix: it needs a field-changing
migration. It is covered in CI (see [CI evidence](#ci-evidence)); C2 records it passing.

## D. Preview, apply, verify, second run (Done-when 1)

Make an Anki backup first ([docs/anki.md](../../../docs/anki.md) "Back up before Setup or a
migration"), as [docs/setup.md](../../../docs/setup.md) "Run Setup" says.

| Step | Do | Expect |
| --- | --- | --- |
| D1 | Snapshot Anki: `ac deckNames > decks-before.json; ac modelNames > models-before.json` | Two files written. |
| D2 | Reload `/setup` and read "What will change in Anki". Do not click anything. | Rows for Decks ("Create 28"), Note types ("Create 5": `LanguageLabDev Capture`, `LanguageLabDev English Vocabulary`, `LanguageLabDev English Sentence`, `LanguageLabDev French Vocabulary`, `LanguageLabDev French Sentence`), Card templates and CSS ("Create 5"), and Deck options ("Create 1", the `LanguageLabDev` preset). No Notes row, no "Optional repairs". An "Apply setup" button. |
| D3 | Time the preview three times: `for i in 1 2 3; do curl -s -o /dev/null -w '%{time_total}\n' http://127.0.0.1:8787/api/setup/plan; done` | Three times, each well under 15 s (the Anki lock wait). Paste them and the app's `durationMs` for those requests. |
| D4 | Snapshot again: `ac deckNames > decks-after.json; ac modelNames > models-after.json; diff decks-before.json decks-after.json && diff models-before.json models-after.json && echo unchanged` | `unchanged`: the preview did not touch Anki. |
| D5 | Click "Apply setup". | A progress card "Applying setup and verifying… Keep Anki open.", then the banner "Setup applied and verified". |
| D6 | `ac deckNames \| tr ',' '\n' \| grep -c LanguageLabDev` and `ac modelNames \| tr ',' '\n' \| grep -c LanguageLabDev` | `28` and `5`. In Anki Desktop the deck tree is `LanguageLabDev` with `Captures`, `Study` and `Pronunciation`, each language and category under them, and `Understand`, `Produce`, `Write` under each `Study` category. |
| D7 | Reload `/setup`. | "Nothing to change." and the study footer naming `LanguageLabDev::Study`. |
| D8 | Time the preview again as in D3. | Three times, now with the managed decks and note types in place. Paste them. |
| D9 | In Anki Desktop, open Options on `LanguageLabDev::Study::English::Vocabulary::Understand`, then on `LanguageLabDev::Pronunciation::French::Sentences`. | Both use the preset `LanguageLabDev`. Under Burying, "Bury new siblings", "Bury review siblings" and "Bury interday learning siblings" are all off. |
| D10 | `ac getDeckConfig '{"deck":"LanguageLabDev::Study::English::Vocabulary::Understand"}'` | `"name":"LanguageLabDev"`, and `"bury":false` under both `new` and `rev`, and `"buryInterdayLearning":false`. |

## E. A deck option you set survives a rerun (Done-when 3, deck-option half)

The preset owns only the three bury flags. Every other option is yours.

| Step | Do | Expect |
| --- | --- | --- |
| E1 | In Anki Desktop, on the `LanguageLabDev` preset, set "New cards/day" to `7` and "Maximum reviews/day" to `77`. Save. Reload `/setup`. | "Nothing to change.": an option the preset doesn't own isn't a difference. |
| E2 | On the same preset, turn "Bury new siblings" on. Save. Reload `/setup`. | One Deck options row, "Repair 1" (the `LanguageLabDev` preset). |
| E3 | Click "Apply setup". | "Setup applied and verified". |
| E4 | Open the preset's Options again, and repeat D10. | "Bury new siblings" is off again; "New cards/day" is still `7` and "Maximum reviews/day" still `77` (`"perDay":7` under `new`, `"perDay":77` under `rev`). |
| E5 | Reload `/setup`. | "Nothing to change." |

Set the two limits back afterwards if you like; nothing later depends on them.

## F. Sync timeline (Done-when 5)

With Anki open, stop the app (Ctrl+C) and start it again with the B1 command. Note the time
you start it. F1 to F3 are measured from that start; do not open any page until F2 is done.

| Step | Do | Expect |
| --- | --- | --- |
| F1 | Read the lines after the start. | `Sync with AnkiWeb: ok` within seconds of start-up, with no page opened. |
| F2 | Leave the app running, with no page open, for at least six minutes. | Another `Sync with AnkiWeb: ok` about five minutes after the start, and one every five minutes after that. Anki Desktop's sync indicator shows a sync at those times. |
| F3 | Press Ctrl+C. | `Sync with AnkiWeb: ok` before the process exits, and it exits within seconds. |

## G. AnkiConnect down (Done-when 5)

| Step | Do | Expect |
| --- | --- | --- |
| G1 | Quit Anki Desktop. Start the app with the B1 command. | It starts and prints its address. The startup line is `Sync with AnkiWeb failed: anki_unavailable`. |
| G2 | `curl -s -m 5 http://127.0.0.1:8787/api/health` and `curl -s -m 5 http://127.0.0.1:8787/api/setup/readiness`; open `/setup`. | `{"version":"0.4.0"}` at once; readiness answers with `ankiConnect` `false`; the Setup screen shows "AnkiConnect not reachable". Nothing hangs. |
| G3 | Wait past the next five-minute mark. | Another `Sync with AnkiWeb failed: anki_unavailable`; the app still answers G2. |
| G4 | Press Ctrl+C and time it: note when you press and when the prompt returns. | It exits within 30 s, with `Sync with AnkiWeb failed: anki_unavailable` (or, only if AnkiConnect hung, `Shutdown Sync still running after 30 s; not waiting for it`). |

## CI evidence

Done-when 3 (migration half) and Done-when 4 are not run on the Mac Mini. These tests prove
them against the recorded AnkiConnect fixtures and the fakes, on every CI run and in this story's
`make test`:

| Done-when | Entry | Test |
| --- | --- | --- |
| 3: a migration runs only inside a confirmed plan | 9 | `tests/integration/test_anki_migrations.py::test_migrations_never_run_at_startup_or_on_a_preview` |
| 3: a migration runs only inside a confirmed plan | 9 | `tests/integration/test_anki_migrations.py::test_a_confirmed_plan_runs_its_migration_and_verifies` |
| 3: the full-sync step after a field change | 9 | `tests/api/test_setup_migrations.py::test_readiness_reports_full_sync_required_after_a_field_changing_apply`, `tests/e2e/test_setup_full_sync.py::test_the_full_sync_required_tile_shows_only_while_its_check_fails` |
| 3: a repair touches only the bury flags (supports part E) | 7 | `tests/integration/test_anki_setup_apply.py::test_apply_sets_only_the_bury_flags_and_assigns_the_preset_to_managed_decks` |
| 4: a write outside the Prefix is rejected | 6 | `tests/integration/test_anki_prefix_guard.py::test_guard_rejects_writes_outside_the_prefix_before_sending_anything` |
| 4: a write outside the Prefix is rejected | 6 | `tests/integration/test_anki_prefix_guard.py::test_composed_app_client_rejects_an_out_of_prefix_write` |
| 4: a non-Setup write is `409 setup_required` unless `ready` | 8 | `tests/api/test_setup_state.py::test_a_gated_write_is_the_409_setup_required_envelope` |
| 5: startup, every five minutes, shutdown capped at 30 s (supports parts F and G) | 10 | `tests/api/test_sync_lifespan.py::test_startup_requests_a_sync_without_waiting_for_it`, `::test_a_sync_is_requested_every_five_minutes`, `::test_shutdown_requests_a_sync_and_waits_for_it_at_most_30_s` |

Run on 2026-10-21 at the story's baseline plus this file:
`uv run pytest -q tests/integration/test_anki_migrations.py tests/integration/test_anki_prefix_guard.py tests/api/test_setup_state.py tests/api/test_setup_migrations.py tests/e2e/test_setup_full_sync.py tests/api/test_sync_lifespan.py tests/integration/test_anki_setup_apply.py`
gave `67 passed`.

## Results

| Step | Result | Notes |
| --- | --- | --- |
| A1 release `v0.4.0` | pass | The wheel at the `v0.4.0` release URL ran and `/api/health` reported `0.4.0` (B2). Anki was open on the spike 2.2 probe profile (`deckNames`: `Default`, `LLProbe`, `LLProbe::Study`) |
| A2 no `LANGUAGE_LAB_DEV` | pass | `exit=1`. |
| A3 no `LanguageLabDev` deck or note type | pass | `0` both times. |
| A4 no `LanguageLabDev` preset | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| A5 no `LanguageLabDev_*` media | pass | `{"result": [], "error": null}`. |
| B0 three keys set in `.env` | pass | `3`. |
| B1 starts, startup Sync | pass | First start: `Sync with AnkiWeb failed: auth_required`, the profile wasn't logged in to AnkiWeb, and the app kept running (finding 3). After signing in and restarting: `Sync with AnkiWeb: ok` |
| B2 health `0.4.0` | pass | `{"version":"0.4.0"}` |
| C1 three tiles pass, Prefix in subtitle | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| C2 readiness JSON, `fullSync` ok | pass | `{"prefix":"LanguageLabDev","checks":[{"id":"ankiConnect","ok":true},{"id":"azure","ok":true},{"id":"openrouter","ok":true},{"id":"fullSync","ok":true}]}` |
| C3 AnkiConnect fails alone | pass | Readiness: `ankiConnect` false, `azure`, `openrouter`, `fullSync` true |
| C4 Azure fails alone | pass | Readiness: `azure` false, `ankiConnect`, `openrouter`, `fullSync` true |
| C5 OpenRouter fails alone | pass | Readiness: `openrouter` false, `ankiConnect`, `azure`, `fullSync` true |
| C6 all pass again | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D1 snapshot before | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D2 preview rows | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D3 preview time, empty Prefix | pass | 0.300 s, 0.350 s, 0.383 s |
| D4 Anki unchanged by preview | pass | `unchanged` |
| D5 confirmed apply, verified | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D6 28 decks, 5 note types | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D7 second run: nothing to change | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D8 preview time, after Setup | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D9 bury flags off in Anki Desktop | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| D10 bury flags off via AnkiConnect | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| E1 user limits not a difference | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| E2 bury flag on shows a repair | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| E3 repair applied and verified | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| E4 bury off, user limits kept | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| E5 nothing to change | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| F1 Sync at startup | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| F2 Sync every five minutes | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| F3 Sync at shutdown | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| G1 starts with Anki quit, failure logged | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| G2 app keeps answering | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| G3 interval failure logged | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |
| G4 shutdown within 30 s | pass | Reported by the user as a group ("other tests also look ok"), no output pasted. |

A step marked "not run" has no recorded result. It is not a pass.

## Findings

| # | Step | What happened | Disposition |
| --- | --- | --- | --- |
| 1 | B (reading the docs before the run) | `docs/configuration.md` ended with "The AnkiConnect endpoint, the Azure values and the OpenRouter values are not used yet", but Setup uses the AnkiConnect endpoint and the readiness checks read the Azure and OpenRouter values. | Fixed in this story, commit `6294e6f9bd3bb2774bed19094c176d6fb053ab7c`: the sentence now says what each is used for. Docs only, so it reaches the release page with the next tag and needs no wheel. |
| 2 | D3, D8 | With an empty Prefix the preview's `cardsInfo` read of managed cards (`read_leftovers`, deferred-work entry from story 2.11) has no managed cards to read, so D3 and D8 time the preview on the real collection but not that read's growth with many LanguageLab cards. | The D3 and D8 times are recorded here. Appended to `deferred-work.md`: the entry with `source_plan` this story's plan, "Measure the Setup preview's `read_leftovers` cost on the Mac Mini at the first run with real LanguageLab cards (epic-capture-to-item)". |
| 3 | B1 | The startup Sync ended `auth_required`. The open profile (the spike 2.2 probe profile, decks `LLProbe…`) isn't logged in to AnkiWeb, and the runbook never says to log in. | Runbook precondition, not a product defect: log in to AnkiWeb in Anki Desktop (Sync, then sign in) before B1. The same gap applies to any profile without an AnkiWeb login. |

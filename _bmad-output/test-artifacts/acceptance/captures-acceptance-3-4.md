# Captures acceptance on the released wheel from the iPhone (story 3.4)

The manual run that proves the released LanguageLab saves, lists and deletes Captures in a real
Anki collection on the Mac Mini, used from the iPhone over Tailscale. It covers epic-captures
Done-when 1 to 4 and the deferred unsaved-changes check on iOS Safari (R-03). It also records
the real AnkiConnect replies to `suspend` and `deleteNotes`, which the tests have so far
hand-built.

- **Release under test:** `v0.5.0`, the first release with entries 1 to 3 of the epic
- **Prefix under test:** `LanguageLabDev`, set as an environment override. Never `LanguageLab`.
- **Mode:** release (no `LANGUAGE_LAB_DEV`)
- **Run on:** 2026-10-22
- **Devices:** Mac Mini (host, with Anki Desktop, AnkiConnect and Tailscale Serve), iPhone
  Safari, iPad Safari, desktop browser on another computer

This repository is public. Do not write your real tailnet name, machine name, login, AnkiWeb
account or any address in this file, and do not paste AnkiConnect output that names your own
decks or note types. Write `<tailnet>` where a name would appear.

Record each step in [Results](#results) as **pass**, **fail**, or **not run** with the reason.
Anything that fails, surprises you, or that the docs got wrong goes in [Findings](#findings).
Paste the terminal lines the steps ask for into the Notes column or under Findings.

## A. Release and the Mac Mini

On the development machine:

| Step | Do | Expect |
| --- | --- | --- |
| A1 | From a clean checkout of `main` with entries 1 to 3 merged: `scripts/cut_release.sh 0.5.0`. | It ends with `Released v0.5.0. Wheel:` and the URL `https://github.com/shapovalex/language-learner/releases/download/v0.5.0/language_lab-0.5.0-py3-none-any.whl`. |

On the Mac Mini, with Anki Desktop open on the profile story 2.13 set up, AnkiConnect installed,
and the profile logged in to AnkiWeb. In the terminal you will use for the whole run, set:

```sh
WHEEL=https://github.com/shapovalex/language-learner/releases/download/v0.5.0/language_lab-0.5.0-py3-none-any.whl
ac() { curl -s http://127.0.0.1:8765 -d "{\"action\":\"$1\",\"version\":6${2:+,\"params\":$2}}"; echo; }
Q='{"query":"note:\"LanguageLabDev Capture\""}'
APP=http://127.0.0.1:8787
```

`ac findNotes "$Q"` then lists the ids of every `LanguageLabDev Capture` note. Anki ids are
creation times in milliseconds, so the largest id is the newest note.

| Step | Do | Expect |
| --- | --- | --- |
| A2 | `env \| grep LANGUAGE_LAB_DEV; echo "exit=$?"` | No variable printed, `exit=1`. If it is set, `unset LANGUAGE_LAB_DEV`. |
| A3 | `tailscale serve status` (see [docs/remote-access.md](../../../docs/remote-access.md)) | HTTPS on `<tailnet>` proxied to `http://127.0.0.1:8787`. |

## B. Start the release and check the Prefix is set up

| Step | Do | Expect |
| --- | --- | --- |
| B1 | `ANKI_PREFIX=LanguageLabDev uvx --from "$WHEEL" language-lab` | `LanguageLab running at http://127.0.0.1:8787/`, `On your tailnet: https://<tailnet>/`, then `Sync with AnkiWeb: ok`. |
| B2 | In a second terminal (set the four lines above there too): `curl -s $APP/api/health` | `{"version":"0.5.0"}` |
| B3 | Open `/setup` in any browser. | "Nothing to change." If it lists changes, click "Apply setup" and wait for "Setup applied and verified": the Prefix must be set up before part C. |
| B4 | `ac findNotes "$Q"` | `{"result": [...], "error": null}`. Note how many ids it lists (usually none). |

Leave the app running; parts C to H use it.

## C. Save from the iPhone, suspended, no duplicate on retry (Done-when 1)

| Step | Do | Expect |
| --- | --- | --- |
| C1 | On the iPhone, with Tailscale connected, open `https://<tailnet>/captures` in Safari. | The Captures screen with the "New Capture" box, placeholder "Paste or type a word, phrase or sentence", and "Save Capture" disabled while the box is empty. |
| C2 | Type `acceptance one` and tap "Save Capture". | The box clears and `acceptance one` tops the list with "Today · HH:MM" (the time now). |
| C3 | `ac findNotes "$Q"` | One more id than B4. |
| C4 | `ac findCards "$Q"`, then with the largest card id: `ac cardsInfo '{"cards":[<card id>]}' \| tr ',' '\n' \| grep -E '"(deckName\|queue)"'` | `"deckName": "LanguageLabDev::Captures"` and `"queue": -1` (suspended). |
| C5 | In Anki Desktop, Browse, search `"note:LanguageLabDev Capture"`. | The note is there with a suspended card (yellow row) in `LanguageLabDev::Captures`. Its fields: Text `acceptance one`, CreatedAt like `2026-10-22T19:14:05Z` (UTC), CaptureId a lowercase UUID, SchemaVersion `1`. |
| C6 | `curl -s $APP/api/captures`, then, in the same terminal you use for C7 to C9: `ID=$(curl -s $APP/api/captures \| grep -o '"captureId":"[^"]*"' \| head -1 \| cut -d'"' -f4); echo "[$ID]"` | `{"captures":[{"captureId":"…","text":"acceptance one","createdAt":"…Z"},…]}`, then the newest Capture's id in brackets: 36 lowercase characters like `[1b4e28ba-2fa1-4d2e-883f-0016d3cca427]`, nothing else inside. |
| C7 | Replay the save: `curl -s -i -X POST $APP/api/captures -H "Origin: $APP" -H 'Content-Type: application/json' -d "{\"captureId\":\"$ID\",\"text\":\"acceptance one\"}"` | `HTTP/1.1 201` and the same `captureId`, `text` and `createdAt` as C6. |
| C8 | The same with `"text":"something else"`. | `201` with the stored `"text":"acceptance one"` and the C6 `createdAt`: the first save stands. |
| C9 | `ac findNotes "$Q"` | The same ids as C3: the replays added no note. |
| C10 | Read the app's terminal lines for C7 and C8. | One JSON line each: `POST`, route `/api/captures`, status `201`, and no Capture text. |

## D. The list on phone and desktop layouts (Done-when 2)

| Step | Do | Expect |
| --- | --- | --- |
| D1 | On the iPhone, save `acceptance two`. | The list under the box, headed "Newest first", shows `acceptance two` above `acceptance one`, each with its text and time. |
| D2 | Tap `acceptance one`. Then tap "‹ Captures". | Capture detail on its own screen: the text, "Captured today · HH:MM" and "Delete Capture". The back link returns to the list. |
| D3 | On the iPad in landscape, open `https://<tailnet>/captures` and tap `acceptance one`. Then turn it to portrait. | Landscape: two panes, the list headed "2 Captures · newest first" (or more, counting B4's), the tapped Capture selected on the left and shown on the right. Portrait: the iPhone layout. |
| D4 | In the desktop browser, open `https://<tailnet>/captures` and click each Capture. | As D3 landscape. Before any click the right pane reads "Choose a Capture to see it here." |
| D5 | Compare the times shown with C6's `createdAt`. | The screens show the device's local time of the UTC `createdAt`. |

## E. Delete after confirmation (Done-when 3)

| Step | Do | Expect |
| --- | --- | --- |
| E1 | `curl -s $APP/api/captures`, then `ID2=$(curl -s $APP/api/captures \| grep -o '"captureId":"[^"]*"' \| head -1 \| cut -d'"' -f4); echo "[$ID2]"`, and `ac findNotes "$Q"` | `acceptance two` is the newest Capture, so `ID2` is its id, in brackets as in C6. Note the note ids. |
| E2 | On the iPhone, open `acceptance two` and tap "Delete Capture". | A dialog "Delete this Capture?", "This removes the Capture from Anki. Items you made from it stay.", with "Delete permanently" and "Cancel". |
| E3 | Tap "Cancel". | The dialog closes and `acceptance two` is still shown. |
| E4 | Tap "Delete Capture", then "Delete permanently". | You land on the list without `acceptance two`; `acceptance one` is still there. |
| E5 | `ac findNotes "$Q"`; then Browse in Anki Desktop. | E1's ids less exactly one. Anki shows no `acceptance two`. |
| E6 | Retry the delete: `curl -s -o /dev/null -w '%{http_code}\n' -X DELETE -H "Origin: $APP" $APP/api/captures/$ID2`, then `ac findNotes "$Q"` | `204`, and the same ids as E5. |

## F. AnkiConnect down (Done-when 4)

| Step | Do | Expect |
| --- | --- | --- |
| F1 | Quit Anki Desktop. On the iPhone, type `acceptance three` and tap "Save Capture". | "Not saved — Anki isn't reachable", "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here." and "Try again". The text stays in the box; the list does not show it. |
| F2 | Read the app's terminal line for F1. | `POST`, `/api/captures`, status `503`, code `anki_unavailable`. |
| F3 | Start Anki Desktop and wait for `ac version` to print `{"result": 6, "error": null}`. On the iPhone tap "Try again". | The box clears and `acceptance three` tops the list. |
| F4 | `ac findNotes "$Q"`; Browse in Anki Desktop. | Exactly one note more than E5, and one `acceptance three`, suspended. |

## G. Unsaved text on iOS: swipe back and return from background (R-03)

Do G1 to G6 on the iPhone, then again on the iPad. Moving between the list and a Capture stays
on the Captures screen and never asks, so G1 arrives from another screen first.

| Step | Do | Expect |
| --- | --- | --- |
| G1 | Open `https://<tailnet>/en/items`, then go to Captures with the navigation (Menu on iPhone, pills on iPad). Type `acceptance four`; do not save. | The text is in the box at `/captures`. |
| G2 | Swipe right from the left edge of the screen. | An alert "Discard unsaved changes?" with "This Capture isn't saved.", "Discard" and "Keep editing". The address is still `/captures`. |
| G3 | Tap "Keep editing". | The alert closes; the text is still in the box at `/captures`. |
| G4 | Switch to another app for at least a minute, then return to Safari. | Still `/captures`, the text still in the box, no reload. |
| G5 | Swipe back from the left edge again. | The alert again. Tap "Discard": the English Items screen, with English marked. |
| G6 | Go to Captures again, then swipe back with the box empty. | No alert; you leave at once. |

This part closes the R-03 entry deferred from story 1.10 in `deferred-work.md` ("Check the unsaved-changes alert on iOS Safari swipe-back…"). Its outcome is in [Results](#results), rows G1–G6.

If Safari reloads the page in G4 (a blank flash, the box empty), record it as a fail with what you
saw: iOS gives no warning before a reload, so the text is lost.

## H. Record the real `suspend` and `deleteNotes` replies

The tests' fake Anki answers `suspend` and `deleteNotes` with replies written from AnkiConnect's
docs. These steps record the real ones on a `LanguageLabDev` Capture made for the purpose. Paste
each reply exactly.

| Step | Do | Expect |
| --- | --- | --- |
| H1 | Save `acceptance fixture` from any device. Then `ac findNotes "$Q"` and `ac findCards "$Q"`, and set `NID` and `CID` to the largest id of each. | `ac notesInfo "{\"notes\":[$NID]}"` shows Text `acceptance fixture`. |
| H2 | `ac unsuspend "{\"cards\":[$CID]}"` | `{"result": true, "error": null}` |
| H3 | `ac suspend "{\"cards\":[$CID]}"` (the card is not suspended) | Paste. Docs say `{"result": true, "error": null}`. |
| H4 | The same again (now already suspended). | Paste. Docs say `{"result": false, "error": null}`. |
| H5 | `ac deleteNotes "{\"notes\":[$NID]}"` | Paste. Docs say `{"result": null, "error": null}`. |
| H6 | The same again (the note is gone). | Paste. Expected the same as H5. |
| H7 | Reload the Captures list. | No `acceptance fixture`. |

Everything this run made is in the dev Prefix; leave it or delete it as you like.

## CI evidence

These tests back each Done-when on every CI run, against the fake Anki and the recorded fixtures. The fake's `suspend` and `deleteNotes` replies are still hand-built from AnkiConnect's docs (finding 2):

| Done-when | Entry | Test |
| --- | --- | --- |
| 1: added to `<Prefix>::Captures`, then suspended | 1 | `tests/integration/test_anki_captures.py::test_a_new_capture_is_added_then_its_card_suspended` |
| 1: a retry with the same CaptureId makes no second note | 1 | `tests/integration/test_anki_captures.py::test_an_existing_capture_id_returns_the_stored_capture_and_writes_nothing`, `tests/api/test_captures.py::test_a_retry_with_the_same_capture_id_returns_the_first_capture`, `tests/e2e/test_captures_compose.py::test_a_retry_keeps_the_capture_id_and_the_next_composition_gets_a_new_one` |
| 1: no user text in any Anki query | 1 | `tests/integration/test_anki_captures.py::test_the_capture_id_lookup_queries_only_the_exact_capture_scope` |
| 2: newest first, phone and desktop layouts | 2 | `tests/api/test_captures_read.py::test_get_lists_the_captures_newest_first`, `tests/e2e/test_captures_list.py::test_on_the_phone_the_list_is_under_the_compose_box_newest_first`, `::test_on_desktop_list_and_detail_are_two_panes_with_the_open_capture_selected`, `::test_ipad_landscape_has_two_panes` |
| 3: confirmation, only that note deleted, a retry succeeds | 3 | `tests/integration/test_anki_capture_delete.py::test_delete_capture_deletes_only_the_note_with_that_capture_id`, `::test_a_repeated_delete_succeeds_and_sends_no_write`, `tests/e2e/test_captures_delete.py::test_cancel_closes_the_dialog_and_keeps_the_capture`, `::test_on_the_phone_delete_permanently_lands_on_the_list_without_it` |
| 4: AnkiConnect down shows the error and keeps the text | 1 | `tests/integration/test_anki_captures.py::test_a_failing_anki_returns_anki_unavailable_with_no_note`, `tests/api/test_captures.py::test_an_unreachable_anki_is_503_anki_unavailable`, `tests/e2e/test_captures_compose.py::test_anki_unreachable_keeps_the_text_and_shows_the_error_with_try_again` |
| R-03: leaving with unsaved text asks first | 1 | `tests/e2e/test_captures_compose.py::test_leaving_with_unsaved_text_raises_the_alert_with_the_capture_copy`, `tests/e2e/test_unsaved_alert.py::test_every_leave_path_raises_the_alert` (browser back in WebKit, not a real iOS swipe) |

Run on 2026-10-22 at the story's baseline plus this file:
`uv run pytest -q tests/integration/test_anki_captures.py tests/integration/test_anki_capture_delete.py tests/api/test_captures.py tests/api/test_captures_read.py tests/api/test_captures_delete.py tests/e2e/test_captures_compose.py tests/e2e/test_captures_list.py tests/e2e/test_captures_delete.py tests/e2e/test_unsaved_alert.py`
gave `166 passed`.

## Results

| Step | Result | Notes |
| --- | --- | --- |
| A1 release `v0.5.0` | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| A2 no `LANGUAGE_LAB_DEV` | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| A3 Tailscale Serve to 8787 | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| B1 starts, tailnet line, Sync ok | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| B2 health `0.5.0` | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| B3 Prefix set up | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| B4 Capture notes before | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C1 Captures screen on iPhone | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C2 save from iPhone | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C3 one more note | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C4 card suspended in `LanguageLabDev::Captures` | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C5 note and fields in Anki Desktop | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C6 `GET /api/captures` | pass | The user set `ID` with the one-line command C6 now gives (finding 1), then reported the run passing as a group ("everything looks good"), no output pasted. |
| C7 replay answers the stored Capture | pass | First try `422 validation_failed`: `$ID` not set to the CaptureId (finding 1). After setting it as C6 now says, reported passing ("everything looks good"), no output pasted. |
| C8 replay with other text keeps the first | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C9 no second note | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| C10 log lines without text | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| D1 iPhone list newest first | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| D2 iPhone detail and back link | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| D3 iPad two panes and portrait | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| D4 desktop two panes | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| D5 local times | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| E1 ids before delete | pass | Run with the earlier wording ("Set `ID2=<captureId of acceptance two>`"), before finding 1 rewrote it; reported passing as a group ("everything looks good"), no output pasted. |
| E2 confirmation dialog | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| E3 Cancel keeps it | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| E4 Delete permanently | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| E5 exactly one note gone | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| E6 retried delete `204` | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| F1 error with text kept | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| F2 `503 anki_unavailable` logged | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| F3 Try again saves | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| F4 exactly one note | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| G1–G6 iPhone | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| G1–G6 iPad | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| H1 fixture Capture | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| H2 unsuspend | pass | Reported by the user as a group ("everything looks good"), no output pasted. |
| H3 `suspend` reply | pass | Run and reported passing ("everything looks good"), but the reply was not pasted, so it was not compared with the fake's reply (finding 2). |
| H4 `suspend` reply, already suspended | pass | Run and reported passing ("everything looks good"), but the reply was not pasted, so it was not compared with the fake's reply (finding 2). |
| H5 `deleteNotes` reply | pass | Run and reported passing ("everything looks good"), but the reply was not pasted, so it was not compared with the fake's reply (finding 2). |
| H6 `deleteNotes` reply, note gone | pass | Run and reported passing ("everything looks good"), but the reply was not pasted, so it was not compared with the fake's reply (finding 2). |
| H7 gone from the list | pass | Reported by the user as a group ("everything looks good"), no output pasted. |

A step marked "not run" has no recorded result. It is not a pass.

**R-03 outcome (2026-10-22):** G1–G6 reported passing on iPhone and iPad, which closes the R-03 entry in `deferred-work.md` deferred from story 1.10.

## Findings

| # | Step | What happened | Disposition |
| --- | --- | --- | --- |
| 1 | C7 | The replay answered `422 validation_failed`. C6 only said "Set `ID=<that captureId>`", so `$ID` was not a canonical CaptureId in the terminal running C7 (likely unset or copied with extra characters). The `422` itself is correct: the API refuses a malformed CaptureId. | Runbook gap, fixed in this story, commit `1427668ecccf9824c96df2d6047be310be2c6a24`: C6 and E1 now set the id with one command and echo it in brackets for checking. |
| 2 | H3–H6 | The steps ran (H7 passed), but no `suspend` or `deleteNotes` reply was pasted, so the hand-built replies in the tests stay unchecked against real Anki. Both results are ignored by the adapter, so only an error reply would matter. | The user chose to finish without them. Appended to `deferred-work.md`: "Record the real AnkiConnect `suspend` … and `deleteNotes` … replies as `tests/fixtures/anki/` exchanges". |

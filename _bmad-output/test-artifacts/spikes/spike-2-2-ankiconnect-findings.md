# Spike 2.2: AnkiConnect behavior for Setup and Sync

The manual run that records how AnkiConnect really answers the actions epic 2 uses, and the
findings that entries 4, 6, 9 and 10 build on. Plan:
[spike-ankiconnect-behavior-for-setup-and-sync-plan.md](../../initiative-languagelab-v1/epic-anki-setup-sync/spike-ankiconnect-behavior-for-setup-and-sync-plan.md).

- **Release under test:** `v0.3.0`, the first release with `language-lab-record-fixtures anki probe`
- **Run on:** 2026-10-15, R1–R9 and R11. R10 (offline) can't be run: the Mac Mini is a remote host, and cutting its network also cuts the operator's access to it. Q4 stays open.
- **Anki:** `<version>` (Help > About)
- **AnkiConnect:** `<add-on version>`; `anki` (bare) reports API `<n>`

This repository is public. Do not write your real profile name, AnkiWeb email or any path under
your home folder in this file. The recorder replaces profile names with `LLProbeProfile`, email
addresses with `redacted@example.com` and the home folder with `/Users/redacted`. Read every
fixture before committing it anyway.

## Runbook

Run everything on the Mac Mini from the released wheel, never from a clone. Set `WHEEL` to the
release asset URL. The probe refuses to run (exit 1, one line, nothing written to Anki) in a
profile holding any `LanguageLab…` note type, or when the active profile is not `--profile`.
That is what keeps your real profile and `LanguageLabDev` untouched. If it refuses, stop: you
are in the wrong profile.

| Step | Do | Expect |
| --- | --- | --- |
| R1 | Create a throwaway AnkiWeb account. In Anki Desktop, File > Switch Profile > Add, name it (for example `Probe`), and open it. | Anki shows the new empty profile. |
| R2 | In the throwaway profile, Sync and log in with the throwaway account. Choose Upload if asked. | Sync completes. |
| R3 | Write the Anki and AnkiConnect versions above. Run `uvx --from "$WHEEL" language-lab-record-fixtures anki`. | The version exchange prints. |
| R4 | `mkdir anki && uvx --from "$WHEEL" language-lab-record-fixtures anki probe --profile Probe --out anki`. At the pause, look at Anki Desktop, press Enter, and watch for a dialog while `modelFieldAdd` runs. Answer any dialog, and write its exact wording and the "answered after N s" line under Q1. | One `<action>.json` per action in `anki/`; exit 0. |
| R5 | In Anki Desktop, Sync. If it asks for a one-way sync, choose Upload. | Anki and AnkiWeb are in step. |
| R6 | `uvx --from "$WHEEL" language-lab-record-fixtures anki sync --profile Probe --label normal --out anki`. It pauses for Enter after each of its three exchanges (v6 `sync`, v6 `multi[sync]`, v1 `collection.sync` with its polling): at each pause, wait until Anki Desktop's sync has finished, answer any dialog, and write its exact wording under the question for this label before pressing Enter. | `anki/sync-normal.json`; no dialog expected. |
| R7 | Run the probe again into a second folder: `mkdir anki-rerun && uvx --from "$WHEEL" language-lab-record-fixtures anki probe --profile Probe --out anki-rerun --yes`. It reuses `LLProbe Probe` and the `LLProbe` preset and adds one more field. | Exit 0; it prints that it reuses the note type and preset. |
| R8 | Without syncing in Anki Desktop first: `… anki sync --profile Probe --label after-field-change --out anki`. At each pause, if Anki asks for a one-way sync, note which exchange raised it and its wording (Q2), and cancel it so the next exchange meets the same state. After the run, Sync in Anki Desktop and Upload. | `anki/sync-after-field-change.json`. |
| R9 | In Anki Desktop, Preferences > Syncing > Log Out. Then `… anki sync --profile Probe --label logged-out --out anki`. At each pause, note any login prompt and which exchange raised it (Q3); close it without logging in. Log back in afterwards. | `anki/sync-logged-out.json`. |
| R10 | Turn off Wi-Fi and unplug Ethernet. Then `… anki sync --profile Probe --label offline --out anki`. At each pause, note any error dialog and which exchange raised it (Q4), and dismiss it. Reconnect afterwards. | `anki/sync-offline.json`. |
| R11 | Read every file in `anki/` and `anki-rerun/`. Copy `anki/*` into `tests/fixtures/anki/` and `anki-rerun/*` into `tests/fixtures/anki/rerun/` in the repository. Fill in the findings below. | No real profile name, email or home path anywhere. |

About API v1: if a `sync` fixture shows `/api/v1` asking for permission (for example
`authenticationRequired`, code 1011) and Anki Desktop offers to grant it, grant it and repeat
that `sync` step with the same label. If Anki offers nothing, keep the refusal: it is the
finding for Q7.

Delete the throwaway profile and AnkiWeb account only after the findings are written.

## Findings

Each answer names the fixture that shows it, relative to `tests/fixtures/anki/`.

| # | Question | Answer | Fixture | Design consequence |
| --- | --- | --- | --- | --- |
| Q1 | No reply-side sign of a modal. `modelFieldAdd` returned `{"result": null, "error": null}`, and `modelFieldNames-after` shows the new field at index 2 in both runs. The operator saw no dialog during R4 or R7: the only dialog in the whole run appeared during R8 (operator's recollection). The "answered after N s" time was not recorded. | `modelFieldAdd.json`, `modelFieldNames-after.json`, `rerun/modelFieldAdd.json` | Entry 9: treat `modelFieldAdd` as a plain request with no modal to wait for. The prompt comes later, at sync time (Q2). |
| Q2 | No exchange reported it. After the field change, v6 `sync` and `multi[sync]` both returned `{"result": null, "error": null}`, the same as `sync-normal`, and v1 `collection.sync` ended `succeeded` with `{"collectionComplete": true, "mediaComplete": true}` after 2 polls. Anki Desktop did show a dialog during R8, the only one in the run, but which exchange raised it and its wording were not recorded. It was presumably the one-way sync prompt. So Anki knows a full sync is needed, but it tells only the person at Anki Desktop, never the API caller. | `sync-after-field-change.json`, `sync-normal.json` | Entry 9: the replies give no full-sync-required signal, and the prompt appears on the Mac Mini's screen where nobody may see it. So LanguageLab must detect a full sync before changing a field, not from `sync`. Entry 10: a v6 `sync` that returns null proves only that the sync started, not that it finished. |
| Q3 | v6 `sync` returned `{"result": null, "error": "sync: auth not configured"}`, and `multi[sync]` returned the same error in its inner result with the outer `error` null. v1 `collection.sync` accepted the call, and its operation was already `failed` at the first poll with `{"code": 1011, "message": "Sync authentication is not configured.", "data": {"type": "authenticationRequired"}}`. No login prompt appeared in Anki Desktop on any exchange. | `sync-logged-out.json` | Entry 10: map v1 `data.type == "authenticationRequired"` (or v6's error text) to a "log in to AnkiWeb in Anki" message. Read `multi`'s inner errors; its outer `error` stays null. |
| Q4 | **Not recorded.** R10 needs the host offline, which can't be done on the remote Mac Mini. | `sync-offline.json` (absent) | Entry 10: without a recorded reply, treat any `failed` v1 operation whose `data.type` is not one Q3 recorded, any v6 `sync` error other than the auth one, and a timed-out poll as "AnkiWeb could not be reached". Add a fixture when an offline failure is first seen in use. |
| Q5 | The keys are `new.bury`, `rev.bury` and the top-level `buryInterdayLearning`. `saveDeckConfig` returned `{"result": false, "error": null}` on both runs, and `mod` stayed `1792093018` in `getDeckConfig-after`, so nothing was saved. The probe also wrote the values the preset already held (all `false`), so even a successful save would have shown no change. Whether it keeps other keys is **not answered**. | `getDeckConfig.json`, `saveDeckConfig.json`, `getDeckConfig-after.json`, `rerun/saveDeckConfig.json` | Entry 4: read the three flags from those keys. Entry 6: `saveDeckConfig` can't be relied on until a working save is shown. Treat `false` as a failure, and verify with `getDeckConfig` (see Surprises). |
| Q6 | `createDeck` returns the existing id (`1792093017900` both runs). A second `addNote` without `allowDuplicate` fails: `{"result": null, "error": "cannot create note because it is a duplicate"}`. `storeMediaFile` on an existing name succeeds and returns a filename; overwrite of the content is not provable from the replies. On re-run, `getDeckConfig-initial` already showed the `LLProbe` preset, so the probe skipped `cloneDeckConfigId`. | `rerun/createDeck.json`, `rerun/addNote.json`, `rerun/storeMediaFile.json` | Entry 6: `createDeck` can be called unconditionally. Find existing notes before adding, rather than relying on the duplicate error, or pass `allowDuplicate` deliberately. Use the filename `storeMediaFile` returns. |
| Q7 | Move Sync to v1 and keep everything else on v6. v1 `collection.sync` returns an `operationId` straight away, and `operations.get` gives the state (`running` → `succeeded`/`failed`), the result and a typed error code. v6 `sync` returns null before the sync finishes and reports failure only as free text. `/api/v1` needed no permission grant. | `sync-normal.json` (`v1`), `version.json` | Entry 10: the adapter's `sync()` calls v1 `collection.sync` and polls `operations.get` within the 120 s budget, and maps `failed` errors by `data.type`. Other actions stay on v6. |

Reply shapes the adapter will parse (v6, `{"result": …, "error": null}` unless noted):

- `createModel`: the full model object (`id`, `name`, `flds[]`, `tmpls[]`, `css`, …).
- `modelFieldNames`: a list of field names in order.
- `modelTemplates`: `{"<card name>": {"Front": str, "Back": str}}`.
- `modelStyling`: `{"css": str}`.
- `updateModelTemplates`, `updateModelStyling`: `null`.
- `createDeck`: the deck id (int), the same id when the deck exists.
- `deckNames`: a list of full deck names, parents included (`LLProbe`, `LLProbe::Study`).
- `cloneDeckConfigId`: the new preset id (int).
- `setDeckConfigId`: `true`.
- `findNotes`: a list of note ids.
- `notesInfo`: a list of `{noteId, profile, tags, fields: {name: {value, order}}, modelName, mod, cards}`. `profile` carries the profile name (redacted here).
- `storeMediaFile`: the stored filename (str), whose case may differ from the request (see Surprises).
- `getMediaFilesNames`: a list of filenames.

## Surprises

Anything the runbook got wrong, or that the epic's entries assume and the fixtures contradict.

- **The probe's first R4 attempt failed** with `cannot read the note types (modelNames); nothing written`. The message drops AnkiConnect's `error`, so the cause was not recorded. A retry succeeded. The recorder should print the error text.
- **`saveDeckConfig` returns `false`** with `error: null`, on both runs, and the preset's `mod` does not change. An error-only check would treat that as success. The probe also wrote the values already stored, so Q5's "keeps every other key" needs a re-probe that flips at least one flag.
- **`storeMediaFile` changed the case of the name.** The first run sent `LLProbe_probe.mp3` and got back `llprobe_probe.mp3`; the re-run got back `LLProbe_probe.mp3`. `getMediaFilesNames` with `LLProbe_*` returned `[]` both times, right after the store, so its pattern match looks case-sensitive against the stored name. LanguageLab should use lowercase media names and the filename `storeMediaFile` returns, and not discover its own media through `getMediaFilesNames` patterns with uppercase letters.
- **`modelFieldAdd` with `index` inserts at that position**, so the re-run's `LLProbeExtra2` landed before `LLProbeExtra1`. Entry 9 should send the index it means, or append without one.
- **`getProfiles` redacts to duplicates**: both profiles come out as `LLProbeProfile`, so the fixture can't tell them apart. Tests must not count profiles by distinct names.
- **v6 `sync` looks identical in the normal and the field-changed runs**, so the v6 reply cannot show whether a sync happened.
- **v1 reported `succeeded` while a full sync was pending.** In R8 the one-way sync dialog appeared and was cancelled, per the runbook. Even so, v1 `collection.sync` returned `succeeded` with `collectionComplete: true`. A v1 success therefore does not prove AnkiWeb holds the change. Entry 10 should not tell the user "synced" based on that state alone.

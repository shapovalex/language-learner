# Spike 2.2: AnkiConnect behavior for Setup and Sync

The manual run that records how AnkiConnect really answers the actions epic 2 uses, and the
findings that entries 4, 6, 9 and 10 build on. Plan:
[spike-ankiconnect-behavior-for-setup-and-sync-plan.md](../../initiative-languagelab-v1/epic-anki-setup-sync/spike-ankiconnect-behavior-for-setup-and-sync-plan.md).

- **Release under test:** `<vX.Y.Z>`, the first release with `language-lab-record-fixtures anki probe`
- **Run on:** `<date>`
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
| Q1 | Does a field-changing action (`modelFieldAdd`) raise a modal in Anki Desktop, and does the AnkiConnect reply wait for it? | | `modelFieldAdd.json`, `modelFieldNames-after.json` | Entry 9: |
| Q2 | How does `sync` report full sync required, over v6 alone, v6 in `multi`, and v1? | | `sync-after-field-change.json` | Entry 9: Entry 10: |
| Q3 | How does `sync` report not logged in? | | `sync-logged-out.json` | Entry 10: |
| Q4 | How does `sync` report offline? | | `sync-offline.json` | Entry 10: |
| Q5 | Which deck-config keys hold the three sibling-burying flags (new, review, interday learning), and does `saveDeckConfig` keep every other key? | | `getDeckConfig.json`, `saveDeckConfig.json`, `getDeckConfig-after.json` | Entry 4: Entry 6: |
| Q6 | What does a re-run do: does `createDeck` return the existing id, does a second `addNote` need `allowDuplicate`, does `storeMediaFile` overwrite? | | `rerun/*.json` | Entry 6: |
| Q7 | Should the adapter stay on v6, move Sync to v1, or move everything to v1? | | `sync-normal.json` (`v1`), `version.json` | Entry 10: |

Also record the reply shapes the adapter will parse, one line each, for: `createModel`,
`modelFieldNames`, `modelTemplates`, `modelStyling`, `updateModelTemplates`,
`updateModelStyling`, `createDeck`, `deckNames`, `cloneDeckConfigId`, `setDeckConfigId`,
`findNotes`, `notesInfo`, `storeMediaFile`, `getMediaFilesNames`.

## Surprises

Anything the runbook got wrong, or that the epic's entries assume and the fixtures contradict.

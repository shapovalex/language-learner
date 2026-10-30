# Recorded fixtures

Inputs captured from real externals, replayed by tests so nothing reaches them (architecture Testing convention).

| File | What it is | Used by |
| --- | --- | --- |
| `tailscale-status.json` | `tailscale status --json` on the Mac Mini | `tests/unit/test_tailscale_discovery.py` |
| `tailscale-serve-headers.json` | The request headers Tailscale Serve forwards to `127.0.0.1:8787` for a browser `POST` | `tests/api/test_host_origin_allow_list.py` |
| `design-tokens.md` | The front matter of the initiative's DESIGN.md (the Studio tokens), kept when the planning artifacts were removed (da6b547). Not recorded: copied as it was | `tests/unit/test_studio_assets.py` via `tests/support/design_tokens.py` |
| `anki/version.json` | AnkiConnect's `version` exchange: `{"request", "response"}`. **Synthetic** (AnkiConnect's documented v6 reply) until recorded on the Mac Mini in story 2.1 | `tests/integration/test_anki_adapter.py`, `tests/integration/test_record_anki_fixtures.py` |

## Recorded on the Mac Mini (R-05)

Both Tailscale files were recorded on the Mac Mini on 2026-10-14 during story 1.10 (device acceptance), with Tailscale 1.104.1 and LanguageLab 0.2.1. They replaced synthetic files written from Tailscale's documented formats.

They come from the `language-lab-record-fixtures` command in the wheel, which replaces the tailnet name, logins, display names, addresses, keys and ids with the placeholders the tests use (`mac-mini.tail1234.ts.net`, `user@example.com`, ...). Every other header value and status string is `redacted`. Header names and status keys are as Tailscale sent them.

What the recording showed: Tailscale Serve keeps the tailnet name in `Host` and sends the same name in `X-Forwarded-Host`, with `X-Forwarded-Proto: https` and the browser's `https://` Origin. It also adds `Tailscale-User-Login`, `Tailscale-User-Name`, `Tailscale-User-Profile-Pic` and `Tailscale-Headers-Info`.

To record them again, on the host machine, with `WHEEL` set to the release asset URL:

```bash
# Stop language-lab, then:
uvx --from "$WHEEL" language-lab-record-fixtures serve
# open https://<tailnet>/ in a tailnet browser and press "Record headers"; Ctrl-C to stop
tailscale status --json | uvx --from "$WHEEL" language-lab-record-fixtures status > tailscale-status.json
```

Read both files before committing them.

## AnkiConnect (story 2.1)

`anki/version.json` is written by hand from AnkiConnect's documented API v6 reply. Replace it with the recording from the Mac Mini, with Anki open:

```bash
uvx --from "$WHEEL" language-lab-record-fixtures anki > version.json
```

The exchange holds nothing private. Read it before committing it anyway. Spike 2.2 records the other actions the epic uses into the same folder.

## AnkiConnect probe (spike 2.2)

**Pending the Mac Mini run.** None of these files exist yet. The spike's runbook,
`_bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md`, records them in a
throwaway Anki profile logged in to a throwaway AnkiWeb account:

| File | What it is |
| --- | --- |
| `anki/<action>.json` | One `{"request", "response"}` per action Setup uses, in probe order: `getProfiles`, `getActiveProfile`, `modelNames`, `createModel`, `modelFieldNames`, `modelFieldAdd`, `modelFieldNames-after`, `modelTemplates`, `modelStyling`, `updateModelTemplates`, `updateModelStyling`, `createDeck`, `deckNames`, `getDeckConfig-initial`, `cloneDeckConfigId`, `setDeckConfigId`, `getDeckConfig` (before), `saveDeckConfig`, `getDeckConfig-after`, `addNote`, `findNotes`, `notesInfo`, `storeMediaFile`, `getMediaFilesNames`. An AnkiConnect error reply is kept as the response. |
| `anki/sync-<label>.json` | `{"label", "v6": {"sync", "multi"}, "v1": {"collection.sync", "operations.get", "pollCount"}}`: v6 `sync` alone and inside `multi`, and API v1 `collection.sync` with the `operations.get` polls whose reply changed. Labels: `normal`, `after-field-change`, `logged-out`, `offline`. |
| `anki/rerun/<action>.json` | The probe run a second time in the same profile. |

The probe touches only `LLProbe`-prefixed note types, decks, presets and media. It refuses to run
when the active profile isn't `--profile` or holds a `LanguageLab…` note type. It replaces profile
names with `LLProbeProfile`, email addresses with `redacted@example.com` and the home folder with
`/Users/redacted` (a profile name only where a value is exactly that name, so `LLProbe Probe`
stays intact with `--profile Probe`). To record them again, on the host machine, in the throwaway profile named `Probe`:

```bash
uvx --from "$WHEEL" language-lab-record-fixtures anki probe --profile Probe --out anki
uvx --from "$WHEEL" language-lab-record-fixtures anki sync --profile Probe --label normal --out anki
```

`sync` pauses for Enter after each of its three exchanges, so Anki's sync can finish and any dialog be noted before the next starts; `--yes` skips the pauses (the tests use it). The runbook gives the state Anki must be in for each sync label. Read every file before committing it.

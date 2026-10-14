# Device acceptance over Tailscale Serve (story 1.10)

The manual run that proves the released LanguageLab is reachable from iPhone, iPad and a desktop
browser over Tailscale Serve, and from nowhere else. It covers the epic's Done-when 1 and 2 and
the risks R-05 (real Serve headers), R-09 (real iOS Safari) and R-12 (LAN exposure).

- **Release under test:** `v0.2.1`, the first release with the recorder command used in part E
- **Run on:** _date_
- **Devices:** Mac Mini (host), iPhone Safari, iPad Safari, desktop browser on another computer

This repository is public. Do not write your real tailnet name, machine name, login or any
address in this file. Write `<tailnet>` and `<LAN IP>` as they appear below.

Record each step in [Results](#results) as **pass**, **fail**, or **not run** with the reason.
Anything that fails, surprises you, or that the docs got wrong goes in [Findings](#findings).

## A. Start the release on the Mac Mini

Follow the docs as written, without using what you already know. A step that fails or misleads
is a finding.

| Step | Do | Expect |
| --- | --- | --- |
| A1 | Follow [docs/install.md](../../../docs/install.md) "Requirements" and "Start the app". | The app starts. On a first start it asks for the three keys and creates `~/.config/language-lab/.env`. |
| A2 | Run `stat -f '%Sp' ~/.config/language-lab/.env`. | `-rw-------` |
| A3 | Follow [docs/remote-access.md](../../../docs/remote-access.md) "Tailscale Serve command". | The command returns and `tailscale serve status` shows HTTPS proxied to `http://127.0.0.1:8787`. |
| A4 | Stop the app with Ctrl+C and start it again. Read what it prints. | Both lines: `LanguageLab running at http://127.0.0.1:8787/` and `On your tailnet: https://<tailnet>/`. |
| A5 | On the Mac Mini, run `curl http://127.0.0.1:8787/api/health`. | `{"version":"0.2.1"}` |

Leave the app running for parts B to D.

## B. Reach the shell from each device

Do every step on **iPhone Safari**, **iPad Safari** and the **desktop browser**. Tailscale must
be connected on each. The secure-context check for iPhone and iPad is in part E.

| Step | Do | Expect |
| --- | --- | --- |
| B1 | Open `https://<tailnet>/`. | The shell loads at `/captures` with no certificate warning. |
| B2 | Go to each destination with the navigation: Captures, English, French, Setup, and for each language both Items and Pronunciation. iPhone uses the Menu; iPad and desktop use the pills. | The address becomes `/captures`, `/en/items`, `/en/pronunciation`, `/fr/items`, `/fr/pronunciation`, `/setup`, the heading matches, and the current destination is marked. |
| B3 | Type each of those six addresses into the address bar and load it. | Each opens its own screen directly. |
| B4 | Load `https://<tailnet>/nope`. | It lands on `/captures`. |
| B5 | Open Setup. | It shows `LanguageLab v0.2.1`, so a `GET /api` passes through Serve. |
| B6 | Desktop only: on the shell, open the console and run `window.isSecureContext`. | `true` |

Extra checks on iOS, handed over by earlier stories:

| Step | Device | Do | Expect |
| --- | --- | --- | --- |
| B7 | iPhone | Open the Menu, then close it three ways: tap the scrim, tap Menu again, choose a row. | The sheet opens from the bottom, marks the current destination, and each way closes it. |
| B8 | iPhone | Look at the header and the open Menu sheet in portrait and in landscape. | Nothing sits under the notch or Dynamic Island, and the last Menu row is clear of the home indicator. |
| B9 | iPhone, iPad | Visit three destinations, then swipe back from the left edge twice and forward once. | Each swipe shows the screen that matches the address, with the right destination marked. |
| B10 | iPhone, iPad | Switch to another app for a minute, then return to Safari. | The shell is still on the same screen and the navigation still works. |

## C. Host and Origin allow-list over Tailscale

The release has no write route yet. The allow-list runs before routing, so `POST /api/health`
tells the two cases apart: an allowed Origin gets past the check and is answered `405` with code
`not_found`, and a foreign Origin is stopped with `403` and code `forbidden_origin`.

On the desktop computer, in a terminal, set `HOST=<tailnet>` first.

| Step | Do | Expect |
| --- | --- | --- |
| C1 | In the desktop browser console, on the shell: `fetch("/api/health", {method: "POST"}).then(async r => console.log(r.status, await r.text()))` | `405` and a body with `"code":"not_found"`. Not `forbidden_origin`. |
| C2 | `curl -s -i -X POST -H 'Origin: https://evil.example' https://$HOST/api/health` | `403` and a body with `"code":"forbidden_origin"`. |
| C3 | `curl -s -i -X POST https://$HOST/api/health` (no Origin) | `403` and `"code":"forbidden_origin"`. |
| C4 | `curl -s -i -X POST -H "Origin: https://$HOST" https://$HOST/api/health` | `405` and `"code":"not_found"`. |
| C5 | Read the Mac Mini terminal lines for C1 to C4. | One JSON line per request with `requestId`, `method`, `route`, `status`, `code`, `durationMs`, and no header value, host name or address. |

## D. Nothing is reachable from the LAN

On the Mac Mini, find its LAN address with `ipconfig getifaddr en0` (or `en1`). It is not the
`100.x` Tailscale address. Start Anki with the AnkiConnect add-on on the Mac Mini, so port 8765
is in use. Run D2 and D3 from another device on the same network, e.g. the desktop computer.

| Step | Do | Expect |
| --- | --- | --- |
| D1 | On the Mac Mini: `curl -m 5 http://127.0.0.1:8765` | AnkiConnect answers. This shows the D3 probe is testing a live port. |
| D2 | From the other device: `curl -m 5 http://<LAN IP>:8787/api/health; echo "exit=$?"` | No response: `exit=7` (refused) or `exit=28` (timed out). |
| D3 | From the other device: `curl -m 5 http://<LAN IP>:8765; echo "exit=$?"` | No response: `exit=7` or `exit=28`. |

## E. Secure context on iOS, and the real fixtures

The wheel carries a second command, `language-lab-record-fixtures`, that stands in for the app
on port 8787. It shows whether the browser treats the tailnet origin as a secure context, which
is the same origin the shell is served from, and it records the headers Tailscale Serve
forwards. It replaces your tailnet name, login, display name and addresses with placeholders
before it writes anything.

Nothing is cloned. Run it from the same release, in any folder you can write to. Set
`WHEEL=https://github.com/shapovalex/language-learner/releases/download/v0.2.1/language_lab-0.2.1-py3-none-any.whl`
first.

| Step | Do | Expect |
| --- | --- | --- |
| E1 | Stop the app with Ctrl+C. Run `uvx --from $WHEEL language-lab-record-fixtures serve`. | `Recorder listening on http://127.0.0.1:8787/` |
| E2 | On iPhone, iPad and desktop, open `https://<tailnet>/`. | The "Tailscale fixture recorder" page, with **Secure context: yes**. |
| E3 | On the desktop page, press **Record headers**. | The page lists the recorded header names, and the terminal prints what it wrote to `tailscale-serve-headers.json` in the current folder. |
| E4 | Stop the recorder with Ctrl+C. Run `tailscale status --json \| uvx --from $WHEEL language-lab-record-fixtures status > tailscale-status.json`. | The file is written. |
| E5 | Read both files. Run `grep -nE '[a-z0-9-]+\.ts\.net' tailscale-*.json \| grep -v tail1234`. | Nothing of yours in either file, and no output from `grep`. |
| E6 | Send both files back (paste their contents, or copy them to the development machine) and start the app again. | They replace `tests/fixtures/tailscale-serve-headers.json` and `tests/fixtures/tailscale-status.json`, and the allow-list and discovery tests are run on them there. |

Note in Findings which headers Serve sent that the synthetic fixture did not have, and whether
`host` was the tailnet name or loopback.

## Results

| Step | Mac Mini | iPhone | iPad | Desktop | Notes |
| --- | --- | --- | --- | --- | --- |
| A1 install and start | | n/a | n/a | n/a | |
| A2 config mode 600 | | n/a | n/a | n/a | |
| A3 Tailscale Serve | | n/a | n/a | n/a | |
| A4 both startup lines | | n/a | n/a | n/a | |
| A5 local health | | n/a | n/a | n/a | |
| B1 HTTPS shell loads | n/a | | | | |
| B2 every destination by nav | n/a | | | | |
| B3 every destination by direct URL | n/a | | | | |
| B4 unknown path | n/a | | | | |
| B5 Setup shows the version | n/a | | | | |
| B6 secure context on the shell | n/a | n/a | n/a | | |
| B7 Menu sheet | n/a | | n/a | n/a | |
| B8 safe-area insets | n/a | | n/a | n/a | |
| B9 swipe back and forward | n/a | | | n/a | |
| B10 return from background | n/a | | | n/a | |
| C1 browser POST not forbidden | n/a | n/a | n/a | | |
| C2 foreign Origin forbidden | n/a | n/a | n/a | | |
| C3 missing Origin forbidden | n/a | n/a | n/a | | |
| C4 tailnet Origin not forbidden | n/a | n/a | n/a | | |
| C5 content-free log lines | | n/a | n/a | n/a | |
| D1 AnkiConnect live locally | | n/a | n/a | n/a | |
| D2 LAN 8787 unreachable | n/a | n/a | n/a | | |
| D3 LAN 8765 unreachable | n/a | n/a | n/a | | |
| E2 secure context | n/a | | | | |
| E3 headers recorded | n/a | n/a | n/a | | |
| E4 status recorded | | n/a | n/a | n/a | |
| E5 nothing private | | n/a | n/a | n/a | |
| E6 files sent back | | n/a | n/a | n/a | |

## Not covered by this run

- **Unsaved-changes alert on iOS swipe-back (R-03).** No screen in `v0.2.1` can have unsaved
  changes, so the alert cannot be raised on a device. Logged in `deferred-work.md` for the first
  epic with such a screen.
- **Microphone permission (AC2).** Moved to epic-pronunciation-review, where the microphone is
  first used.

## Findings

| # | Step | Device | What happened | Disposition |
| --- | --- | --- | --- | --- |
| | | | | |

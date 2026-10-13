# LanguageLab

A local web app for building and reviewing Anki language cards. It is a FastAPI server that
serves a plain HTML/CSS/JS front end, keeps no database of its own, and stores everything in
Anki via AnkiConnect.

The server binds to `127.0.0.1` only. To use it from other devices (iPhone, iPad, another
computer), put it behind [Tailscale Serve](https://tailscale.com/kb/1312/serve), which gives it
HTTPS. Browsers only allow microphone access over HTTPS.

## Requirements

- [uv](https://docs.astral.sh/uv/) 0.12 or newer. uv installs Python 3.14 for you if needed.
- [Anki](https://apps.ankiweb.net/) with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159)
  add-on, running on the same machine (default endpoint `http://127.0.0.1:8765`).
- Optional, for remote access: [Tailscale](https://tailscale.com/download), logged in on the
  server machine and on every device you want to use.
- Optional, for features that use them: an Azure Speech key and region, and an OpenRouter API key.

## Run locally (development)

```sh
git clone git@github.com:shapovalex/language-learner.git
cd language-learner
uv sync                       # creates .venv and installs the app plus dev tools
```

Start the server in dev mode:

```sh
LANGUAGE_LAB_DEV=1 uv run language-lab
```

Dev mode reads `./.env` (gitignored). On the first start, if it is missing, the app asks in the
terminal for `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` and `OPENROUTER_API_KEY` (keys are not
shown as you type; leave any empty to set it later), creates `./.env` from the template with
`ANKI_PREFIX=LanguageLabDev`, and starts. The dev Prefix keeps dev work away from your real
decks: in dev mode the app refuses to start if `ANKI_PREFIX` is `LanguageLab` (in any letter
case).

Open <http://127.0.0.1:8787/>. Check it with `curl http://127.0.0.1:8787/api/health`.

`LANGUAGE_LAB_DEV=1` must be set in the shell, not in `.env`: it decides which `.env` is read.

### Tests and lint

```sh
make browsers      # one-time: install Playwright's Chromium and WebKit
make test-fast     # unit, API and integration tests, no browser
make test          # everything, including E2E in Chromium
make lint          # ruff check and format check
make ci-local      # what CI runs: lint, full suite, short E2E burn-in
```

## Run on another machine (release)

On the machine that will host the app (e.g. a Mac mini that runs Anki), you only need uv,
Anki with AnkiConnect, and a config file. There is no need to clone the repo.

### 1. Build a wheel

On your dev machine:

```sh
uv build --wheel   # writes dist/language_lab-<version>-py3-none-any.whl
```

Copy the wheel to the host machine (`scp`, AirDrop, a GitHub release asset, etc.).

### 2. Create the config

Nothing to do by hand: the first start (step 3) creates `~/.config/language-lab/.env` from the
template inside the wheel. It asks in the terminal for `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`
and `OPENROUTER_API_KEY` (keys are not shown as you type; leave any empty to set it later),
writes the file with mode `600`, and starts. Without a terminal (e.g. under a service manager)
it writes the file with those keys empty, tells you to set them, and exits; edit the file and
start again.

For release use, keep `ANKI_PREFIX=LanguageLab`. See [Configuration](#configuration) for every
key.

### 3. Run it

```sh
uvx --from /path/to/language_lab-0.2.0-py3-none-any.whl language-lab
```

`uvx` also accepts a URL to the wheel. The app prints the address it listens on, and, if it
finds Tailscale, the tailnet address too:

```
LanguageLab running at http://127.0.0.1:8787/
On your tailnet: https://mac-mini.tailnet-name.ts.net/
```

To upgrade, build a new wheel and run `uvx --from` with the new file.

### 4. Reach it from other devices with Tailscale Serve

Run this once on the host machine. It proxies HTTPS on your tailnet name to the local server,
and keeps doing so in the background, including after a restart:

```sh
tailscale serve --bg 8787
```

Then open `https://<machine>.<tailnet>.ts.net/` on any device logged in to the same tailnet.
Check the current setup with `tailscale serve status`. Turn it off with `tailscale serve reset`.

On macOS, if `tailscale` is not on your `PATH`, use
`/Applications/Tailscale.app/Contents/MacOS/Tailscale` instead.

The app finds its tailnet name at startup from `tailscale status --json` and only accepts
requests addressed to `127.0.0.1:<port>`, `localhost:<port>`, or that name. Other hosts get
`403 Forbidden`. If discovery fails (Tailscale not running, a different CLI location), set
`LANGUAGE_LAB_PUBLIC_HOST` to the name yourself.

## Configuration

The app reads `~/.config/language-lab/.env` (release) or `./.env` (dev, with
`LANGUAGE_LAB_DEV=1`). Variables in the process environment override the file. If the file is
missing, the app creates it from the template shipped in the package (`language_lab/env.example`,
which documents every key) and asks for the three service keys, as described above; without a
terminal it creates the file, names the path and the keys to set, and exits. An existing file,
even an empty one, is never changed.

| Key | Default | Meaning |
| --- | --- | --- |
| `LANGUAGE_LAB_HOST` | `127.0.0.1` | Address to bind to. Keep loopback and use Tailscale Serve for remote access. |
| `LANGUAGE_LAB_PORT` | `8787` | Port to listen on. If you change it, change the `tailscale serve` port too. |
| `LANGUAGE_LAB_PUBLIC_HOST` | auto | Tailnet hostname, e.g. `mac-mini.tailnet-name.ts.net`. Discovered from Tailscale when empty. |
| `LANGUAGE_LAB_DEV` | off | Dev mode. Set it in the shell, not in `.env`. |
| `ANKI_CONNECT_URL` | `http://127.0.0.1:8765` | AnkiConnect endpoint. |
| `ANKI_PREFIX` | `LanguageLab` | Prefix for every deck and note type the app creates: letters and digits, starting with a letter. Use something like `LanguageLabDev` in dev. |
| `AZURE_SPEECH_KEY` | | Azure Speech key (secret). |
| `AZURE_SPEECH_REGION` | | Azure Speech region, e.g. `westeurope`. |
| `OPENROUTER_API_KEY` | | OpenRouter API key (secret). |
| `OPENROUTER_MODELS` | | Comma-separated OpenRouter model IDs, in order of preference. Each must support strict JSON Schema output. |

## License

MIT. See [LICENSE](LICENSE).

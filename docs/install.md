# Install

How to start a released version of LanguageLab on the machine that hosts it, e.g. a Mac mini
that runs Anki. There is nothing to clone and nothing to build: one command downloads the
release and runs it.

## Requirements

- [uv](https://docs.astral.sh/uv/) 0.12 or newer. uv installs Python 3.14 for you if needed.
- [Anki](https://apps.ankiweb.net/) with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159)
  add-on, on the same machine. The app starts without it, but [Setup](setup.md) and every
  feature that stores data in Anki need it. Read [Anki](anki.md) before you install the add-on.
- Optional, for use from other devices: [Tailscale](https://tailscale.com/download), logged in on
  the host machine and on every device you want to use. See [Remote access](remote-access.md).
- Optional, for the features that will use them: an Azure Speech key and region, and an
  OpenRouter API key. You can leave them empty and set them later.

## Start the app

Run this in a terminal on the host machine:

```sh
uvx --from https://github.com/shapovalex/language-learner/releases/download/v1.4.0/language_lab-1.4.0-py3-none-any.whl language-lab
```

`uvx` downloads the wheel attached to that GitHub release, installs it with its
dependencies into uv's cache, and runs the `language-lab` command from it. Later starts reuse the
cache.

## First start

The app reads its configuration from `~/.config/language-lab/.env`. On the first start that file
does not exist, so the app creates it:

1. It asks in the terminal for `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` and
   `OPENROUTER_API_KEY`. The two keys are not shown as you type. Leave any answer empty to set it
   later.
2. It writes `~/.config/language-lab/.env` from the template inside the wheel, with mode `600`.
3. It starts.

Press Ctrl+C at a question to cancel; no file is written.

Without a terminal (input piped or redirected), the app cannot ask. It writes the file with
those three keys empty, prints the path and the keys to set, and exits. Edit the file and start
again.

An existing file, even an empty one, is never changed. See [Configuration](configuration.md) for
every key.

## What it prints

The app prints the address it listens on and, if it finds Tailscale, the tailnet address too:

```
LanguageLab running at http://127.0.0.1:8787/
On your tailnet: https://mac-mini.tailnet-name.ts.net/
```

Open the first address in a browser on the host machine. Check the server with:

```sh
curl http://127.0.0.1:8787/api/health
```

The second address works from other devices once Tailscale Serve is set up. See
[Remote access](remote-access.md).

If a value in the config is invalid, the app prints one line per problem, naming the key, and
exits without starting.

## Stop it

The app runs in the terminal you started it from, for as long as that terminal stays open. Press
Ctrl+C to stop it. Start it again with the same command.

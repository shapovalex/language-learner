# Development

Running LanguageLab from a clone, in dev mode.

## Clone and install

You need [uv](https://docs.astral.sh/uv/) 0.12 or newer.

```sh
git clone git@github.com:shapovalex/language-learner.git
cd language-learner
uv sync                       # creates .venv and installs the app plus dev tools
```

## Run in dev mode

```sh
LANGUAGE_LAB_DEV=1 uv run language-lab
```

Dev mode reads `./.env` at the repo root (gitignored) instead of `~/.config/language-lab/.env`.
On the first start, if it is missing, the app asks in the terminal for `AZURE_SPEECH_KEY`,
`AZURE_SPEECH_REGION` and `OPENROUTER_API_KEY` (keys are not shown as you type; leave any empty
to set it later), creates `./.env` from the template with mode `600`, and starts.

`LANGUAGE_LAB_DEV=1` must be set in the shell, not in `.env`: it decides which `.env` is read.

Open <http://127.0.0.1:8787/>. Check it with:

```sh
curl http://127.0.0.1:8787/api/health
```

See [Configuration](configuration.md) for every key.

## The dev Prefix

A `.env` created in dev mode has `ANKI_PREFIX=LanguageLabDev`. The dev Prefix keeps dev work away
from your real decks. In dev mode the app refuses to start if `ANKI_PREFIX` is `LanguageLab`, the
release Prefix, in any letter case; it prints the reason and exits.

If you write `./.env` by hand, set `ANKI_PREFIX` to `LanguageLabDev` or another name that is not
the release Prefix.

## Tests and lint

```sh
make browsers      # one-time: install Playwright's Chromium and WebKit
make test-fast     # unit, API and integration tests, no browser
make test          # everything, including E2E in Chromium
make lint          # ruff check and format check
make ci-local      # what CI runs: lint, full suite, short E2E burn-in
```

[`tests/README.md`](../tests/README.md) describes the suite.

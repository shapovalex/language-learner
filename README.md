# LanguageLab

A local web app for building and reviewing Anki language cards. It is a FastAPI server that
serves a plain HTML/CSS/JS front end and keeps no database of its own: it stores everything
in Anki via AnkiConnect.

The server binds to `127.0.0.1` only. To use it from other devices (iPhone, iPad, another
computer), put it behind [Tailscale Serve](https://tailscale.com/kb/1312/serve), which gives it
HTTPS. Browsers only allow microphone access over HTTPS.

## Requirements

- [uv](https://docs.astral.sh/uv/) 0.12 or newer. uv installs Python 3.14 for you if needed.
- [Anki](https://apps.ankiweb.net/) with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159)
  add-on, on the same machine. This release starts without it; the features that store data in
  Anki need it when they arrive.
- Optional, for remote access: [Tailscale](https://tailscale.com/download), logged in on the
  server machine and on every device you want to use.
- Optional, for features that use them: an Azure Speech key and region, and an OpenRouter API key.

## Quick start

On the machine that hosts the app, with uv installed, start the current release:

```sh
uvx --from https://github.com/shapovalex/language-learner/releases/download/v1.1.0/language_lab-1.1.0-py3-none-any.whl language-lab
```

The first start asks for the service keys, creates `~/.config/language-lab/.env`, and prints the
address to open: <http://127.0.0.1:8787/>.

To work on the app, run it from a clone in dev mode, which reads `./.env` instead:

```sh
git clone git@github.com:shapovalex/language-learner.git
cd language-learner
uv sync
LANGUAGE_LAB_DEV=1 uv run language-lab
```

## Documentation

Everything else is in [`docs/`](docs/README.md):

- [Install](docs/install.md): requirements, the start command, the first-start prompt, stopping.
- [Configuration](docs/configuration.md): where the `.env` lives, its permissions, every key.
- [Remote access](docs/remote-access.md): the one-time Tailscale Serve command.
- [Anki](docs/anki.md): the AnkiConnect warning, which deck to study, backups.
- [Setup](docs/setup.md): running Setup, upgrades and migrations, the full-sync upload.
- [Development](docs/development.md): dev mode, tests and lint.

## License

MIT. See [LICENSE](LICENSE).

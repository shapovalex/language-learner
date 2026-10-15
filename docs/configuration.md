# Configuration

LanguageLab is configured by one `.env` file of `KEY=value` lines. The app creates it on the
first start (see [Install](install.md#first-start)); after that you edit it by hand and restart
the app.

## Where the file lives

| Mode | File |
| --- | --- |
| Release (the `uvx` command) | `~/.config/language-lab/.env` |
| Dev (`LANGUAGE_LAB_DEV=1` in the shell) | `./.env` in the directory you start the app from, normally the repo root, where it is gitignored |

If the file for the current mode is missing, the app creates it from the template shipped in the
package. An existing file, even an empty one, is never changed.

## File permissions

The file holds two secrets, so the app creates it with mode `600`: only your user can read or
write it. If you create the file by hand, set the same mode yourself:

```sh
mkdir -p ~/.config/language-lab
touch ~/.config/language-lab/.env
chmod 600 ~/.config/language-lab/.env
```

The app does not check or change the mode of a file that already exists.

## Environment overrides

A variable set in the process environment overrides the same key in the file. For one run on a
different port:

```sh
LANGUAGE_LAB_PORT=8788 uvx --from https://github.com/shapovalex/language-learner/releases/download/v0.3.0/language_lab-0.3.0-py3-none-any.whl language-lab
```

Keys the app does not know are ignored.

## Configuration keys

The template the app copies is
[`src/language_lab/env.example`](../src/language_lab/env.example). It lists every key with a
comment, and a new `.env` is that file with your answers filled in; in dev mode it also has
`ANKI_PREFIX` set to `LanguageLabDev`. The table below explains the same keys. The default is what the app uses when the key is absent from both the file and the
environment.

| Key | Default | Meaning |
| --- | --- | --- |
| `LANGUAGE_LAB_HOST` | `127.0.0.1` | Address the server binds to. Keep the default and use Tailscale Serve for other devices. |
| `LANGUAGE_LAB_PORT` | `8787` | Port the server listens on. If you change it, change the Tailscale Serve port too. See [Remote access](remote-access.md#changing-the-port). |
| `LANGUAGE_LAB_PUBLIC_HOST` | discovered | Tailnet hostname the app is reached by, e.g. `mac-mini.tailnet-name.ts.net`. When empty, the app asks Tailscale at startup. See [Remote access](remote-access.md#allowed-hosts). |
| `LANGUAGE_LAB_DEV` | off | Dev mode. Set it in the shell, not in the file: it decides which file is read. See [Development](development.md). |
| `ANKI_CONNECT_URL` | `http://127.0.0.1:8765` | AnkiConnect endpoint; the default is the add-on's own. |
| `ANKI_PREFIX` | `LanguageLab` | Prefix for every deck and note type the app will create: a letter, then letters or digits only. Keep `LanguageLab` for release. Dev mode refuses it. See [Anki](anki.md#the-prefix). |
| `AZURE_SPEECH_KEY` | empty | Azure Speech key (secret). |
| `AZURE_SPEECH_REGION` | empty | Azure Speech region, e.g. `westeurope`. |
| `OPENROUTER_API_KEY` | empty | OpenRouter API key (secret). |
| `OPENROUTER_MODELS` | empty | OpenRouter model IDs, comma-separated, in order of preference. The template fills in three example IDs. Every model must support strict JSON Schema output. |

This release reads and validates every key at startup. The AnkiConnect endpoint, the Azure values
and the OpenRouter values are not used yet: the features that use them arrive in later releases.

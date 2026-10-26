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
LANGUAGE_LAB_PORT=8788 uvx --from https://github.com/shapovalex/language-learner/releases/download/v1.2.1/language_lab-1.2.1-py3-none-any.whl language-lab
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

This release reads and validates every key at startup. [Setup](setup.md) and Sync use the
AnkiConnect endpoint. Setup's readiness checks only that the Azure key and region and the
OpenRouter key are set. Generate Draft calls OpenRouter with `OPENROUTER_MODELS`; the features
that call Azure arrive in later releases.

## Evaluating a model

Generate Draft sends every request to OpenRouter with `OPENROUTER_MODELS` as an ordered fallback
list: the first model that answers writes the Draft. A model on the list must support
strict JSON Schema output (OpenRouter's structured outputs), or no provider will take the
request.

Before you add a model to `OPENROUTER_MODELS`, or reorder the list so a different model comes
first, evaluate that model against the fixtures below. Put it alone in `OPENROUTER_MODELS`,
restart the app, and generate a Draft for each row from a Capture of its Target, with its
Generation context. Keep the model only if every Draft passes; you can discard the Drafts
without saving.

| Language | Category | Target | Generation context | A good Draft has |
| --- | --- | --- | --- | --- |
| English | Vocabulary | jump to conclusions | Said about a hasty post-mortem of an outage. | One Russian meaning that fits the context, such as "делать поспешные выводы", not a list of dictionary senses; at most a few alternatives with no commas; one example sentence using the Target and its Russian translation; no mnemonic. |
| English | Vocabulary | bank | The river overflowed its banks after the storm. | The Russian meaning of the riverside sense ("берег"), not the financial one. |
| English | Sentence | I'd rather not jump to conclusions. | | A natural Russian translation of the whole sentence; no example; a note only if it says something useful about "I'd rather". |
| French | Vocabulary | avoir du mal à | Heard in Montréal: "J'ai du mal à me réveiller." | One Russian meaning such as "с трудом удаётся", the grammar (avoir du mal à + infinitive), and a French example with its Russian translation. |
| French | Sentence | Ne tirons pas de conclusions hâtives. | | A Russian translation of the whole sentence, and a hint in French that doesn't give the sentence away. |

Every Russian meaning must be Russian, and every hint and example in the Target's Language. The
model never writes the Target: the Draft keeps the text you chose. A model that fails any row,
or answers "Couldn't generate a Draft" for one, stays out of the list.

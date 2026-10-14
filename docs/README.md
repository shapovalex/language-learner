# LanguageLab documentation

First-time installation and configuration, in the order you need them.

| Page | What it covers |
| --- | --- |
| [Install](install.md) | Requirements, the one command that starts a release, the first-start prompt, what the app prints, stopping it. |
| [Configuration](configuration.md) | Where the `.env` lives, its permissions, environment overrides, every key. |
| [Remote access](remote-access.md) | The one-time Tailscale Serve command and which hosts the app accepts. |
| [Anki](anki.md) | The keyless-AnkiConnect warning, the Prefix, which deck to study, backups. |
| [Development](development.md) | Running from a clone in dev mode, tests and lint. |

## Setup documentation checklist

Each setup topic the product requires, and the heading that states it.

| Topic | Where |
| --- | --- |
| Every configuration key, with an explanation | [Configuration: Configuration keys](configuration.md#configuration-keys) |
| The one-time Tailscale Serve command | [Remote access: Tailscale Serve command](remote-access.md#tailscale-serve-command) |
| Any local process can control a keyless AnkiConnect | [Anki: AnkiConnect has no key](anki.md#ankiconnect-has-no-key) |
| Study `<Prefix>::Study`, never the `<Prefix>` root | [Anki: Study only the Study deck](anki.md#study-only-the-study-deck) |
| Back up Anki before Setup or a migration | [Anki: Back up before Setup or a migration](anki.md#back-up-before-setup-or-a-migration) |

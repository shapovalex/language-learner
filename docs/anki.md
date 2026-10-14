# Anki

LanguageLab keeps no database of its own. It will store everything in Anki, through the
[AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on on the same machine.

This release does not talk to Anki yet. Setup (which creates the decks and note types),
migrations, and the decks themselves arrive with later releases. The conventions on this page
apply from then; the AnkiConnect warning applies as soon as you install the add-on.

## AnkiConnect has no key

AnkiConnect listens on `http://127.0.0.1:8765` and, as LanguageLab uses it, has no API key. Any
process running on the machine can send it requests, and so can read, change or delete anything
in your Anki collection. That is true whether or not LanguageLab is running.

- Keep AnkiConnect bound to `127.0.0.1`, its default. Do not expose it to your network.
- Only run software you trust on the machine that runs Anki.

The browser never talks to AnkiConnect. Other devices reach LanguageLab only, through Tailscale
Serve (see [Remote access](remote-access.md)).

## The Prefix

`ANKI_PREFIX` names the root of everything LanguageLab will own in Anki: every deck and note type
it creates starts with it, and it never touches anything outside it. The default is
`LanguageLab`. Dev mode uses a different Prefix so that development never touches your real
decks (see [Development](development.md#the-dev-prefix)).

Below, `<Prefix>` stands for the value of `ANKI_PREFIX`.

## Study only the Study deck

Once Setup has created the decks, there will be two branches under `<Prefix>` that hold cards:

- `<Prefix>::Study` holds the cards you review in ordinary Anki clients.
- `<Prefix>::Pronunciation` holds the Pronounce cards, which are reviewed only in LanguageLab,
  where your recording is scored.

In Anki Desktop, AnkiMobile and any other Anki client, study `<Prefix>::Study` (with the default
Prefix, `LanguageLab::Study`) or a deck beneath it. Never study the `<Prefix>` root: a deck
includes its subdecks, so the root would show the Pronounce cards in Anki too, and answering them
there changes their schedule without any pronunciation check.

This is a convention you keep. Nothing in Anki or LanguageLab enforces it.

## Back up before Setup or a migration

Setup and migrations change note types and decks under the Prefix. Make an Anki backup before
you run either one, so a mistake can be undone.

In Anki Desktop: File > Create Backup. To keep a copy outside Anki, use File > Export, choose
"Anki Collection Package (.colpkg)", and include media.

Setup and migrations arrive with later releases; this release has neither.

# Anki

LanguageLab keeps no database of its own. It stores everything in Anki, through the
[AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on on the same machine.
[Setup](setup.md) creates the decks and note types and runs migrations.

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

## Leave an Item out of Pronunciation

To stop practising an Item aloud, tap "Don't practise this card" on the Pronunciation screen, or
uncheck "Practise pronunciation" on the Item's page. LanguageLab suspends only that Item's
Pronounce card in Anki; its Study cards are not changed. Check "Practise pronunciation" again to
bring it back: it returns to Pronunciation the next time it is new or due. A Pronounce card you
suspend in Anki yourself counts as left out too.

## Find and fix flagged Items

When you spot a mistake on a card while reviewing in Anki, flag it (any flag colour). On the
Items screen, tap "Flagged" beside the search to list only the Items with a flagged card; the
search still narrows that list, and each flagged row shows a flag. Open the Item, fix it and
save, then tap "Clear flag" on its page: LanguageLab sets every flagged card of that Item back to
no flag in Anki. Saving alone never clears the flag, and you can also unflag the cards in Anki
yourself. The flag lives only in Anki.

## French reading rules deck

Setup creates `<Prefix>::Study::French::Reading Rules` and fills it with 46 French reading rules,
one card each, with the note type `<Prefix> French Reading Rule`. A card's front shows a letter
combination, such as "ou" or "eau"; its back shows the combination's phonetic transcription, a
short note when the rule has one, and three example words, each with a play button for its own
audio (a Canadian French voice). The audio ships with LanguageLab: Setup stores it in Anki and
never calls Azure for it.

Setup only creates these notes. It never updates or deletes them, so your edits to a rule stay.
If you delete a rule's note, the next Setup offers to create it again; to stop studying a rule,
suspend its card instead. A missing rule never blocks the rest of LanguageLab.

## Back up before Setup or a migration

Setup and migrations change note types and decks under the Prefix. Make an Anki backup before
you run either one, so a mistake can be undone.

In Anki Desktop: File > Create Backup. To keep a copy outside Anki, use File > Export, choose
"Anki Collection Package (.colpkg)", and include media.

Setup runs a migration only when a new release changes LanguageLab's note types, and only once
you confirm it (see [Setup: Upgrade to a new release](setup.md#upgrade-to-a-new-release)).

## Full sync after a migration

A migration that changes a note type's fields needs a one-way Upload to AnkiWeb from Anki
Desktop. See [Setup: Upload to AnkiWeb after a full sync](setup.md#upload-to-ankiweb-after-a-full-sync).

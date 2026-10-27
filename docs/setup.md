# Setup

Setup creates and repairs everything LanguageLab manages in Anki under the Prefix (see
[Anki: The Prefix](anki.md#the-prefix)): the note types, the deck tree, the card templates and
CSS, and the `<Prefix>` deck options preset. It also runs the migrations a new release brings.
Until Setup has run, the features that write to Anki refuse ("Setup isn't complete yet.").

## Run Setup

1. Start LanguageLab (see [Install](install.md)) and open Anki on the same machine.
2. [Back up Anki](anki.md#back-up-before-setup-or-a-migration).
3. Open Setup in LanguageLab (`/setup`). The "Ready to go?" card checks that AnkiConnect is
   reachable and that the Azure and OpenRouter keys are configured. A failing check shows its fix.
4. Read "What will change in Anki". Each row names a kind of resource (Decks, Note types, Notes,
   Card templates and CSS, Deck options) and the resources it touches, with a chip for the action
   and count, such as "Create 5". Nothing changes until you apply.
5. Click "Apply setup". Setup applies the changes, then verifies them against what LanguageLab
   expects and shows "Setup applied and verified".

Setup is safe to run again: a second run shows "Nothing to change." "Optional repairs" (orphan
media, misplaced or unsuspended cards) are never applied unless you check them.

## Upgrade to a new release

Stop LanguageLab (Ctrl+C) and start the new release with its own command, for this release:

```sh
uvx --from https://github.com/shapovalex/language-learner/releases/download/v1.3.0/language_lab-1.3.0-py3-none-any.whl language-lab
```

A migration never runs at startup, only inside a plan you confirm. If the release changes
LanguageLab's note types, Setup's change list shows rows with a "Migrate" chip. To migrate:

1. [Back up Anki](anki.md#back-up-before-setup-or-a-migration).
2. Open Setup and review the rows with a "Migrate" chip. A row marked "Needs a full sync
   afterwards." changes a note type's fields (see [Upload to AnkiWeb after a full sync](#upload-to-ankiweb-after-a-full-sync)).
3. Click "Apply setup".

Until you apply, features that write to Anki refuse with "Setup isn't complete yet."

## Never downgrade after a migration

Once a release has migrated Anki, don't go back to an older release. The older release can't
read the newer schema. Its Setup screen shows "Anki was set up by a newer LanguageLab. Install
the latest release.", hides "Apply setup", and every feature that writes to Anki refuses. Start
the latest release instead. To undo a migration, restore the Anki backup you made before it.

## Upload to AnkiWeb after a full sync

A migration that changes a note type's fields needs a one-way full sync: Anki Desktop uploads the
whole collection to AnkiWeb, replacing what AnkiWeb holds.

Before it applies such a plan, Setup syncs first. If that Sync doesn't end OK, Setup refuses to
apply ("Anki couldn't sync with AnkiWeb. Sync in Anki Desktop, then apply again."), so the upload
can't overwrite changes Anki hasn't pulled yet. Sync in Anki Desktop, then apply again.

After the migration, Setup shows a "Full sync required" tile with its fix, "Open Anki Desktop,
sync, and choose Upload to AnkiWeb.":

1. Open Anki Desktop and sync.
2. When Anki asks, choose Upload to AnkiWeb.
3. Back in LanguageLab's Setup, click "I've uploaded".

Anki tells only the person at Anki Desktop that a full sync is needed; its sync replies to
LanguageLab end OK either way. So LanguageLab can't see whether the upload happened, and the tile
stays until you click "I've uploaded". Upload before you stop LanguageLab: the tile does not
survive a restart, and nothing reminds you after one. Other Anki clients (AnkiMobile) then
download the collection on their next sync.

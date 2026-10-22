"""Story 2.12: the Setup, upgrade, migration and full-sync docs say what the screen says.

`docs/setup.md` gets one heading per topic: running Setup, upgrading to a new release, never
downgrading after a migration, and the one-way Upload to AnkiWeb after a full-sync-required
change. Each section must quote the Setup screen's copy as `static/screens/setup.js` and the
error messages hold it, so a renamed button or a reworded alert fails here until the docs follow.
The full-sync section must also state what spike 2.2 recorded (Q2): Anki's sync never reports a
full sync to LanguageLab, so the tile stays until the user says they uploaded.

The index links each topic to its heading, as story 1.9 did for FR-4. `docs/anki.md` loses its
"not yet" sentences now that Setup and migrations ship.
"""

import pytest

from language_lab.domain.errors import MESSAGES, ErrorCode
from tests.support.release import REPO_ROOT
from tests.unit.test_docs_consistency import (
    ANKI,
    INDEX,
    _app_script,
    _expected_asset_url,
    _name,
    _relative_links,
    _section,
    _slug,
    _text,
)

pytestmark = pytest.mark.p2

SETUP_DOCS = REPO_ROOT / "docs" / "setup.md"
SETUP_SCREEN = REPO_ROOT / "src" / "language_lab" / "static" / "screens" / "setup.js"

RUN_SETUP = "Run Setup"
UPGRADE = "Upgrade to a new release"
NEVER_DOWNGRADE = "Never downgrade after a migration"
UPLOAD = "Upload to AnkiWeb after a full sync"

BACKUP_LINK = "anki.md#back-up-before-setup-or-a-migration"


def screen(copy: str) -> str:
    """`copy` as a string literal of the Setup screen, so the docs can only quote what it shows."""
    assert f'"{copy}"' in SETUP_SCREEN.read_text(encoding="utf-8"), f"setup.js lost {copy!r}"
    return copy


def missing(heading: str, phrases: tuple[str, ...]) -> list[str]:
    section = _section(_text(SETUP_DOCS), heading) if SETUP_DOCS.exists() else None
    assert section is not None, f"{_name(SETUP_DOCS)} has no heading {heading!r}"
    return [phrase for phrase in phrases if phrase not in section]


# Each topic of entry 12: (topic, heading). A heading is renamed here and in the page together.
TOPICS = [
    ("running Setup", RUN_SETUP),
    ("upgrading by running the new wheel and confirming any migration", UPGRADE),
    ("never downgrading after a migration", NEVER_DOWNGRADE),
    ("the one-way Upload to AnkiWeb after a full-sync-required change", UPLOAD),
]


class TestRunSetup:
    def test_section_quotes_the_preview_and_the_apply_button(self) -> None:
        """AC-1. The change list's heading and note, Apply setup, and the backup first."""
        phrases = (
            screen("What will change in Anki"),
            screen("Nothing changes until you apply."),
            screen("Apply setup"),
            BACKUP_LINK,
        )

        assert missing(RUN_SETUP, phrases) == []


class TestUpgrade:
    def test_section_runs_the_new_wheel_and_confirms_the_migration(self) -> None:
        """AC-2. Upgrading is the current release's uvx command, then Migrate rows and Apply."""
        command = f"uvx --from {_expected_asset_url()} {_app_script()}"

        assert missing(UPGRADE, (command, screen("Migrate"), screen("Apply setup"))) == []

    # Green phase: the section also says a migration never runs at startup (entry 9), backup link.


class TestNeverDowngrade:
    def test_section_quotes_the_newer_schema_alert(self) -> None:
        """AC-3. An older wheel after a migration shows this alert and hides Apply setup."""
        alert = screen("Anki was set up by a newer LanguageLab. Install the latest release.")

        assert missing(NEVER_DOWNGRADE, (alert,)) == []


class TestUploadToAnkiWeb:
    def test_section_gives_the_one_way_upload_step_in_the_screens_words(self) -> None:
        """AC-4. The tile's title and fix, its button, and the refusal when the first Sync fails."""
        phrases = (
            "one-way",
            screen("Full sync required"),
            screen("Open Anki Desktop, sync, and choose Upload to AnkiWeb."),
            screen("I've uploaded"),
            MESSAGES[ErrorCode.SYNC_REQUIRED],
        )

        assert missing(UPLOAD, phrases) == []

    def test_section_states_the_spikes_recorded_sync_behavior(self) -> None:
        """AC-5. Spike 2.2 Q2: Sync ends OK after a field change and reports no full sync."""
        phrases = ("can't see whether the upload happened", "stays until you click")

        assert missing(UPLOAD, phrases) == []


class TestIndex:
    @pytest.mark.parametrize(
        "heading", [pytest.param(heading, id=topic) for topic, heading in TOPICS]
    )
    def test_index_links_each_topic_to_its_heading(self, heading: str) -> None:
        """AC-6. The id of a failing case is the topic of entry 12."""
        link = f"{SETUP_DOCS.name}#{_slug(heading)}"

        assert link in _relative_links(_text(INDEX))


class TestAnkiPage:
    @pytest.mark.parametrize(
        "stale",
        ["This release does not talk to Anki yet.", "This release has no migration yet"],
    )
    def test_anki_page_no_longer_says_setup_is_to_come(self, stale: str) -> None:
        """AC-7. Setup, migrations and the full sync ship in this epic."""
        assert stale not in " ".join(_text(ANKI).split())

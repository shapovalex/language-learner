"""What Setup's preview is made of (FR-6, AD-3): plan items, unmanaged entries, the plan hash
and the SetupState (AD-19).

A plan item names a managed resource by its full Anki name and what Setup would do to it. The
hash is what apply (entry 7) re-checks before it writes, so it depends on the items as a set:
Anki's listing order can't change it, and any change to an item does. Unmanaged entries are
shown read-only and stay outside the plan and its hash.

Opt-in repairs (entry 11): leftovers under the Prefix (orphan media, a managed card in the
wrong deck, an unsuspended Capture card) are offered in `SetupPreview.repairs`, one row per
resource, unchecked. They stay out of `items` and the SetupState; only the rows the user
checks (by `key`, `checked_repairs(preview, keys)`) join the items in the hash:
`plan_hash((*items, *checked))`.

`SetupState` says whether feature writes may go to Anki: only when it is `ready` (AD-19).
"""

import hashlib
import json
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class SetupState(StrEnum):
    READY = "ready"
    NEEDS_SETUP = "needs_setup"
    NEEDS_MIGRATION = "needs_migration"
    NEWER_SCHEMA = "newer_schema"  # set up by a newer release: an older one never writes it


class PlanAction(StrEnum):
    CREATE = "create"
    REPAIR = "repair"
    MIGRATE = "migrate"


class ResourceKind(StrEnum):
    DECK = "deck"
    NOTE_TYPE = "noteType"
    NOTES = "notes"  # a note type's notes, by its name: their SchemaVersion (entry 9)
    TEMPLATES = "templates"  # a note type's card templates and CSS together
    PRESET = "preset"
    # Opt-in repairs (entry 11), each one resource
    ORPHAN_MEDIA = "orphanMedia"  # an AD-7 media file no managed note references
    MISPLACED_CARD = "misplacedCard"  # a managed card outside its manifest deck, by card id
    UNSUSPENDED_CARD = "unsuspendedCard"  # an unsuspended Capture card, by card id


@dataclass(frozen=True)
class PlanItem:
    action: PlanAction
    kind: ResourceKind
    name: str  # the deck path, the note type, the preset (the Prefix), a file name or card id
    # Display detail of an opt-in repair row: outside equality and the hash
    detail: Mapping[str, str] = field(default_factory=dict, compare=False, hash=False)

    @property
    def key(self) -> str:
        """How the user checks an opt-in repair row: `"<kind>:<name>"`."""
        return f"{self.kind}:{self.name}"

    @property
    def requires_full_sync(self) -> bool:
        """A field change (Migrate noteType) needs a one-way full sync (AD-3, AD-17). A
        property, so it changes neither item equality nor the plan hash.
        """
        return self.action is PlanAction.MIGRATE and self.kind is ResourceKind.NOTE_TYPE


@dataclass(frozen=True)
class Unmanaged:
    """A deck or note type under the Prefix that the manifest doesn't declare."""

    kind: ResourceKind
    name: str


@dataclass(frozen=True)
class SetupPreview:
    items: tuple[PlanItem, ...] = ()
    unmanaged: tuple[Unmanaged, ...] = ()
    repairs: tuple[PlanItem, ...] = ()  # every opt-in repair row offered, unchecked
    state: SetupState = SetupState.READY  # what an empty preview is


def checked_repairs(preview: SetupPreview, keys: Collection[str]) -> tuple[PlanItem, ...]:
    """The offered repair rows whose key is in `keys`; a key no longer offered drops out."""
    wanted = set(keys)
    return tuple(r for r in preview.repairs if r.key in wanted)


def plan_hash(items: Iterable[PlanItem]) -> str:
    """sha256, as 64 lowercase hex characters, of the items as a set."""
    rows = sorted({(str(i.action), str(i.kind), i.name) for i in items})
    payload = json.dumps([list(row) for row in rows], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

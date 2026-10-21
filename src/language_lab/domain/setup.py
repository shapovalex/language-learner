"""What Setup's preview is made of (FR-6, AD-3): plan items, unmanaged entries and the plan hash.

A plan item names a managed resource by its full Anki name and what Setup would do to it. The
hash is what apply (entry 7) re-checks before it writes, so it depends on the items as a set:
Anki's listing order can't change it, and any change to an item does. Unmanaged entries are
shown read-only and stay outside the plan and its hash.
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class PlanAction(StrEnum):
    CREATE = "create"
    REPAIR = "repair"
    MIGRATE = "migrate"


class ResourceKind(StrEnum):
    DECK = "deck"
    NOTE_TYPE = "noteType"
    TEMPLATES = "templates"  # a note type's card templates and CSS together
    PRESET = "preset"


@dataclass(frozen=True)
class PlanItem:
    action: PlanAction
    kind: ResourceKind
    name: str  # the deck path, the note type, or the preset (the Prefix)


@dataclass(frozen=True)
class Unmanaged:
    """A deck or note type under the Prefix that the manifest doesn't declare."""

    kind: ResourceKind
    name: str


@dataclass(frozen=True)
class SetupPreview:
    items: tuple[PlanItem, ...] = ()
    unmanaged: tuple[Unmanaged, ...] = ()


def plan_hash(items: Iterable[PlanItem]) -> str:
    """sha256, as 64 lowercase hex characters, of the items as a set."""
    rows = sorted({(str(i.action), str(i.kind), i.name) for i in items})
    payload = json.dumps([list(row) for row in rows], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

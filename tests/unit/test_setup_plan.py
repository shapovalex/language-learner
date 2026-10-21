"""Story 2.6: the Setup plan and its hash (AD-3).

`domain/setup.py` holds what Setup's preview is made of: a `PlanItem` (`action` create, repair
or migrate; `kind` deck, noteType, notes (story 2.9), templates or preset; `name`, the
resource's full Anki name), an `Unmanaged` entry (`kind` deck or noteType, `name`), and
`SetupPreview(items, unmanaged)`.

`plan_hash(items)` is what apply (entry 7) re-checks before it writes: a fresh diff must hash to
the plan the user confirmed. So the hash depends on the items alone, as a set: the order Anki
lists things in can't change it, and any change to an item does.
"""

import dataclasses
import hashlib
import json
import re

import pytest

from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, plan_hash

PREFIX = "LanguageLab"
SHA256_HEX = re.compile(r"[0-9a-f]{64}")


@pytest.mark.p0
def test_plan_hash_is_stable_across_order_and_changes_with_any_item() -> None:
    """AC-7: the same items hash the same in any order; a changed, added or dropped item doesn't."""
    items = (
        PlanItem(PlanAction.CREATE, ResourceKind.DECK, f"{PREFIX}::Study"),
        PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, f"{PREFIX} English Vocabulary"),
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, f"{PREFIX} French Sentence"),
        PlanItem(PlanAction.CREATE, ResourceKind.PRESET, PREFIX),
    )

    assert plan_hash(tuple(reversed(items))) == plan_hash(items)
    assert SHA256_HEX.fullmatch(plan_hash(items))
    first, second, *rest = items
    changed = {
        "action": (first, PlanItem(PlanAction.CREATE, second.kind, second.name), *rest),
        "kind": (first, PlanItem(second.action, ResourceKind.NOTE_TYPE, second.name), *rest),
        "name": (PlanItem(first.action, first.kind, f"{PREFIX}::Captures"), second, *rest),
        "dropped": items[:-1],
        "added": (*items, PlanItem(PlanAction.CREATE, ResourceKind.DECK, f"{PREFIX}::Captures")),
        "empty": (),
    }
    hashes = {label: plan_hash(variant) for label, variant in changed.items()}
    assert [label for label, value in hashes.items() if value == plan_hash(items)] == []
    assert len(set(hashes.values())) == len(hashes)
    assert [str(a) for a in PlanAction] == ["create", "repair", "migrate"]
    assert [str(k) for k in ResourceKind] == [
        "deck",
        "noteType",
        "notes",
        "templates",
        "preset",
        "orphanMedia",  # the opt-in repair kinds (story 2.11)
        "misplacedCard",
        "unsuspendedCard",
    ]


@pytest.mark.p1
def test_requires_full_sync_leaves_item_equality_and_the_plan_hash_alone() -> None:
    """Story 2.9, AC-2: only a Migrate noteType item requires a full sync, and the flag is
    derived, so the hash is the one of `(action, kind, name)` rows as before.
    """
    field_change = PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, f"{PREFIX} Capture")
    others = (
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTES, f"{PREFIX} Capture"),
        PlanItem(PlanAction.CREATE, ResourceKind.NOTE_TYPE, f"{PREFIX} Capture"),
        PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, f"{PREFIX} Capture"),
    )
    items = (field_change, *others)
    rows = sorted([str(i.action), str(i.kind), i.name] for i in items)
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))

    assert [i.requires_full_sync for i in items] == [True, False, False, False]
    assert plan_hash(items) == hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert field_change == PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, f"{PREFIX} Capture")
    assert "requires_full_sync" not in {f.name for f in dataclasses.fields(PlanItem)}


@pytest.mark.p1
def test_an_opt_in_rows_key_and_detail_leave_equality_and_the_plan_hash_alone() -> None:
    """Story 2.11, AC-6: `key` is `"<kind>:<name>"`, derived, and the display `detail` of an
    opt-in repair row changes neither item equality nor the hash.
    """
    card = PlanItem(
        PlanAction.REPAIR,
        ResourceKind.MISPLACED_CARD,
        "1792093019101",
        {"noteType": f"{PREFIX} Capture", "deck": "Default", "expectedDeck": f"{PREFIX}::Captures"},
    )
    bare = PlanItem(PlanAction.REPAIR, ResourceKind.MISPLACED_CARD, "1792093019101")

    assert card.key == "misplacedCard:1792093019101"
    assert card == bare
    assert plan_hash((card,)) == plan_hash((bare,))
    assert hash(card) == hash(bare)
    assert "key" not in {f.name for f in dataclasses.fields(PlanItem)}

"""Story 2.6: the Setup plan and its hash (AD-3).

`domain/setup.py` holds what Setup's preview is made of: a `PlanItem` (`action` create, repair
or migrate; `kind` deck, noteType, templates or preset; `name`, the resource's full Anki name),
an `Unmanaged` entry (`kind` deck or noteType, `name`), and `SetupPreview(items, unmanaged)`.

`plan_hash(items)` is what apply (entry 7) re-checks before it writes: a fresh diff must hash to
the plan the user confirmed. So the hash depends on the items alone, as a set: the order Anki
lists things in can't change it, and any change to an item does.

Skipped until the domain types exist. Un-skip the test, watch it fail, then implement. Hoist the
imports once it's green.
"""

import re

import pytest

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 2.6: un-skip with domain/setup.py")

PREFIX = "LanguageLab"
SHA256_HEX = re.compile(r"[0-9a-f]{64}")


@RED_PHASE
@pytest.mark.p0
def test_plan_hash_is_stable_across_order_and_changes_with_any_item() -> None:
    """AC-7: the same items hash the same in any order; a changed, added or dropped item doesn't."""
    from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, plan_hash

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
    assert [str(k) for k in ResourceKind] == ["deck", "noteType", "templates", "preset"]

"""Story 2.11: opt-in repairs over HTTP (AD-3, FR-6).

- **The plan.** GET /api/setup/plan gains `repairs`: every opt-in repair row the preview offers
  (orphan media, misplaced managed cards, unsuspended Capture cards), one per resource, each
  `{key, action, kind, name, checked}` with `key` = `"<kind>:<name>"`. `items` and `planHash`
  are unchanged while nothing is checked.
- **Checking a row.** GET /api/setup/plan?repair=<key>&repair=<key> answers with those rows
  `checked` and `planHash` over the required items plus the checked rows: the server re-plans,
  so the screen never hashes (decided with the user, 2026-10-21). A key the preview doesn't
  offer is ignored.
- **Apply.** POST /api/setup/apply takes `{planHash, repairs: [key, ...]}` and hands the
  checked keys to the store, which re-diffs and checks the hash over the same rows.

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/, whose preview
offers `repairs` and whose apply hashes the required items plus the checked ones. The repairs
themselves are in tests/integration/test_anki_setup_repairs.py.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupPreview
from language_lab.domain.setup import plan_hash as _plan_hash
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over

PLAN = "/api/setup/plan"
APPLY = "/api/setup/apply"
PREFIX = "LanguageLab"
MEDIA = f"{PREFIX}_{uuid.UUID(int=1, version=4)}_0123456789ab.mp3"
MISPLACED, UNSUSPENDED = "1792093019101", "1792093019102"

REQUIRED = (PlanItem(PlanAction.CREATE, ResourceKind.DECK, f"{PREFIX}::Study"),)


def repair_rows() -> tuple[PlanItem, ...]:
    """One opt-in row of each kind. Built in the test: the kinds don't exist before 2.11."""
    return (
        PlanItem(PlanAction.REPAIR, ResourceKind("orphanMedia"), MEDIA),
        PlanItem(PlanAction.REPAIR, ResourceKind("misplacedCard"), MISPLACED),
        PlanItem(PlanAction.REPAIR, ResourceKind("unsuspendedCard"), UNSUSPENDED),
    )


def row_key(item: PlanItem) -> str:
    return f"{item.kind}:{item.name}"


def client_and_store(settings_factory: SettingsFactory) -> tuple[TestClient, FakeAnkiStore]:
    """The app over a fake whose preview has one required item and one repair of each kind."""
    store = FakeAnkiStore(preview=SetupPreview(items=REQUIRED, repairs=repair_rows()))
    return client_over(settings_factory, store, anki_prefix=PREFIX), store


@pytest.mark.p0
def test_the_plan_lists_each_opt_in_repair_unchecked(settings_factory: SettingsFactory) -> None:
    """AC-4: `repairs` lists every offered row with its key, unchecked, and the plan hash is
    the required items' alone.
    """
    client, _ = client_and_store(settings_factory)

    body = client.get(PLAN).json()

    assert [(r.get("key"), r.get("checked")) for r in body.get("repairs", [])] == [
        (row_key(r), False) for r in repair_rows()
    ]
    assert body["planHash"] == _plan_hash(REQUIRED)
    assert body["items"] == [
        {"action": "create", "kind": "deck", "name": f"{PREFIX}::Study", "requiresFullSync": False}
    ]


@pytest.mark.p0
def test_checking_a_repair_enters_it_in_the_plan_hash(settings_factory: SettingsFactory) -> None:
    """AC-7: `?repair=<key>` answers with that row checked and the hash over the required
    items plus that row, which differs from the unchecked plan's.
    """
    client, _ = client_and_store(settings_factory)
    media = repair_rows()[0]

    body = client.get(PLAN, params={"repair": [row_key(media), "orphanMedia:gone.mp3"]}).json()

    assert body["planHash"] == _plan_hash((*REQUIRED, media))
    assert body["planHash"] != _plan_hash(REQUIRED)
    assert [r["checked"] for r in body["repairs"]] == [True, False, False]


@pytest.mark.p0
def test_apply_hands_the_checked_repairs_to_the_store(settings_factory: SettingsFactory) -> None:
    """AC-13: POST /api/setup/apply with `repairs` applies the plan its hash names: required
    items plus the checked row; without `repairs` that hash is stale.
    """
    client, store = client_and_store(settings_factory)
    card = repair_rows()[1]
    checked_hash = _plan_hash((*REQUIRED, card))

    response = client.post(APPLY, json={"planHash": checked_hash, "repairs": [row_key(card)]})

    assert response.status_code == 200
    assert store.applies == 1
    stale: Any = client.post(APPLY, json={"planHash": checked_hash})
    assert stale.status_code == 409


@pytest.mark.p1
def test_a_plan_without_leftovers_has_no_repairs_and_an_unchanged_hash(
    settings_factory: SettingsFactory,
) -> None:
    """AC-4: with nothing offered, `repairs` is `[]` and `items`, `planHash` and `state` are
    what they were before story 2.11, whatever `repair` keys the request names.
    """
    store = FakeAnkiStore(preview=SetupPreview(items=REQUIRED))
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    body = client.get(PLAN, params={"repair": [f"orphanMedia:{MEDIA}"]}).json()

    assert body["repairs"] == []
    assert body["planHash"] == _plan_hash(REQUIRED)
    assert body["state"] == "ready"


@pytest.mark.p1
def test_a_repeated_repair_key_counts_once(settings_factory: SettingsFactory) -> None:
    """AC-7: a key named twice checks its row once, in the plan and in the apply."""
    client, store = client_and_store(settings_factory)
    media = repair_rows()[0]

    body = client.get(PLAN, params={"repair": [row_key(media), row_key(media)]}).json()

    assert body["planHash"] == _plan_hash((*REQUIRED, media))
    assert [r["checked"] for r in body["repairs"]] == [True, False, False]
    applied = client.post(
        APPLY, json={"planHash": body["planHash"], "repairs": [row_key(media), row_key(media)]}
    )
    assert applied.status_code == 200
    assert store.applies == 1


@pytest.mark.p1
def test_a_card_rows_detail_is_on_the_wire(settings_factory: SettingsFactory) -> None:
    """AC-4: a misplaced card's row carries its note type, card, deck and expected deck."""
    detail = {
        "noteType": f"{PREFIX} Capture",
        "card": "Capture",
        "deck": "Default",
        "expectedDeck": f"{PREFIX}::Captures",
    }
    card = PlanItem(PlanAction.REPAIR, ResourceKind.MISPLACED_CARD, MISPLACED, detail)
    store = FakeAnkiStore(preview=SetupPreview(repairs=(card,)))
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    body = client.get(PLAN).json()

    assert body["repairs"] == [
        {
            "key": f"misplacedCard:{MISPLACED}",
            "action": "repair",
            "kind": "misplacedCard",
            "name": MISPLACED,
            "checked": False,
            **detail,
        }
    ]

"""Story 2.9: the full-sync steps of Setup over HTTP (AD-3, AD-17, AD-15).

- **The plan.** Each row of GET /api/setup/plan carries `requiresFullSync`, true only for a
  field-changing step: a Migrate `noteType` row.
- **Sync first.** POST /api/setup/apply of a plan with such a row awaits a Sync through the
  SyncRequester before it applies. A Sync that doesn't end OK refuses the apply with
  `409 sync_required` before any write (decided with the user, 2026-10-21), so the one-way
  upload can't overwrite AnkiWeb changes Anki hasn't pulled. Dev mode, where Sync is disabled,
  goes on.
- **Full sync required.** The apply result says `fullSyncRequired`, and readiness gains a
  fourth check, `{"id": "fullSync", "ok"}`, read from the last Sync status. It stays failing
  until the user says they uploaded: POST /api/setup/full-sync/uploaded answers 204 and clears
  it (decided with the user, 2026-10-21; spike 2.2 Q2: Sync never reports it).

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/. The app's own
SyncService Syncs through it (`outcome`, `sync_calls`). The TestClient isn't entered, so no
lifespan Sync runs. The migration itself is in tests/integration/test_anki_migrations.py.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupPreview, SetupState
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over

PLAN = "/api/setup/plan"
APPLY = "/api/setup/apply"
READINESS = "/api/setup/readiness"
UPLOADED = "/api/setup/full-sync/uploaded"
PREFIX = "LanguageLab"
VOCABULARY = f"{PREFIX} English Vocabulary"

FIELD_CHANGE = (PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, VOCABULARY),)
NO_FIELD_CHANGE = (
    PlanItem(PlanAction.CREATE, ResourceKind.DECK, f"{PREFIX}::Study"),
    PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, VOCABULARY),
)


def client_and_store(
    settings_factory: SettingsFactory, items: tuple[PlanItem, ...], **fake: Any
) -> tuple[TestClient, FakeAnkiStore]:
    """The app over a fake whose preview is `items` and whose apply verifies clean."""
    store = FakeAnkiStore(
        preview=SetupPreview(items=items, state=SetupState.NEEDS_MIGRATION), **fake
    )
    return client_over(settings_factory, store, anki_prefix=PREFIX), store


def apply_plan(client: TestClient, items: tuple[PlanItem, ...]) -> Any:
    return client.post(APPLY, json={"planHash": _plan_hash(items)})


def full_sync_ok(client: TestClient) -> bool | None:
    """The readiness `fullSync` check's `ok`, or None when there is no such check."""
    checks = client.get(READINESS).json().get("checks", [])
    return next((c.get("ok") for c in checks if c.get("id") == "fullSync"), None)


@pytest.mark.p0
def test_each_plan_row_says_whether_it_requires_a_full_sync(
    settings_factory: SettingsFactory,
) -> None:
    """AC-2: `requiresFullSync` is true for the Migrate noteType row only."""
    items = (
        *FIELD_CHANGE,
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTES, VOCABULARY),
        *NO_FIELD_CHANGE,
    )
    client, _ = client_and_store(settings_factory, items)

    rows = client.get(PLAN).json()["items"]

    assert [row.get("requiresFullSync") for row in rows] == [True, False, False, False]


@pytest.mark.p1
@pytest.mark.parametrize(
    ("items", "syncs"), [(FIELD_CHANGE, 1), (NO_FIELD_CHANGE, 0)], ids=["field-change", "none"]
)
def test_only_a_field_changing_plan_syncs_before_it_applies(
    settings_factory: SettingsFactory, items: tuple[PlanItem, ...], syncs: int
) -> None:
    """AC-10: a plan without a field-changing step applies without a Sync."""
    client, store = client_and_store(settings_factory, items)

    apply_plan(client, items)

    assert store.sync_calls == syncs
    assert store.applies == 1


@pytest.mark.p0
@pytest.mark.parametrize("outcome", [SyncOutcome.AUTH_REQUIRED, SyncOutcome.ANKIWEB_UNREACHABLE])
def test_a_sync_that_fails_before_a_field_change_refuses_the_apply(
    settings_factory: SettingsFactory, outcome: SyncOutcome
) -> None:
    """AC-11: 409 `sync_required`, and the plan isn't applied."""
    client, store = client_and_store(settings_factory, FIELD_CHANGE, outcome=outcome)

    response = apply_plan(client, FIELD_CHANGE)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "sync_required"
    assert store.apply_calls == 0


@pytest.mark.p0
def test_the_apply_result_says_a_full_sync_is_required(settings_factory: SettingsFactory) -> None:
    """AC-12: after a field-changing plan, `fullSyncRequired` tells the screen to say upload."""
    client, _ = client_and_store(settings_factory, FIELD_CHANGE)

    response = apply_plan(client, FIELD_CHANGE)

    assert response.json().get("fullSyncRequired") is True
    assert response.status_code == 200


@pytest.mark.p0
def test_readiness_reports_full_sync_required_after_a_field_changing_apply(
    settings_factory: SettingsFactory,
) -> None:
    """AC-13: the fullSync check passes before and fails after the apply."""
    client, _ = client_and_store(settings_factory, FIELD_CHANGE)

    before = full_sync_ok(client)
    apply_plan(client, FIELD_CHANGE)
    after = full_sync_ok(client)

    assert [before, after] == [True, False]


@pytest.mark.p0
def test_the_user_clears_full_sync_required_once_uploaded(
    settings_factory: SettingsFactory,
) -> None:
    """AC-15: POST /api/setup/full-sync/uploaded is 204, and the check passes again."""
    client, _ = client_and_store(settings_factory, FIELD_CHANGE)
    apply_plan(client, FIELD_CHANGE)

    response = client.post(UPLOADED)

    assert full_sync_ok(client) is True
    assert response.status_code == 204


# ---- secondary branches ------------------------------------------------------------------


@pytest.mark.p1
def test_dev_mode_applies_a_field_change_without_a_sync(
    settings_factory: SettingsFactory,
) -> None:
    """AC-11: with Sync disabled (dev mode) the plan applies, and a full sync is still flagged."""
    dev_prefix = "LanguageLabDev"
    items = (PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, f"{dev_prefix} Capture"),)
    store = FakeAnkiStore(preview=SetupPreview(items=items, state=SetupState.NEEDS_MIGRATION))
    client = client_over(settings_factory, store, dev=True, anki_prefix=dev_prefix)

    response = apply_plan(client, items)

    assert response.status_code == 200
    assert response.json()["fullSyncRequired"] is True
    assert (store.sync_calls, store.applies) == (0, 1)
    assert full_sync_ok(client) is False


@pytest.mark.p1
def test_anki_unavailable_during_the_sync_refuses_the_apply(
    settings_factory: SettingsFactory,
) -> None:
    """AC-11: a Sync that can't reach Anki refuses the field change the same way."""
    client, store = client_and_store(settings_factory, FIELD_CHANGE)
    store.outcome = SyncOutcome.ANKI_UNAVAILABLE

    response = apply_plan(client, FIELD_CHANGE)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "sync_required"
    assert store.apply_calls == 0
    assert full_sync_ok(client) is True


@pytest.mark.p1
def test_a_stale_hash_is_refused_as_plan_changed_without_a_sync(
    settings_factory: SettingsFactory,
) -> None:
    """AC-11: a hash the field-changing preview no longer has gets `plan_changed`, not a Sync
    and `sync_required`.
    """
    client, store = client_and_store(
        settings_factory, FIELD_CHANGE, outcome=SyncOutcome.AUTH_REQUIRED
    )

    response = client.post(APPLY, json={"planHash": "0" * 64})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "plan_changed"
    assert store.sync_calls == 0

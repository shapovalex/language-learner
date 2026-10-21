"""Story 2.6: GET /api/setup/plan returns the preview, without touching Anki (FR-6, AD-3).

The body is `{"prefix", "planHash", "state", "items": [{"action", "kind", "name",
"requiresFullSync"}], "repairs": [...], "unmanaged": [{"kind", "name"}]}` in camelCase (Consistency
Conventions), with the items in the order the AnkiStore returned them and `planHash` the
domain's `plan_hash(items)`. Apply (entry 7) sends that hash back. The Setup screen owns the copy.

The app takes the AnkiStore, so these tests pass the in-memory fake from tests/fakes/ with a
canned `SetupPreview` and never reach Anki. The diff itself is in
tests/integration/test_anki_setup_preview.py.
"""

import uuid

import pytest

from language_lab.app import create_app
from language_lab.domain.errors import MESSAGES, ErrorCode
from language_lab.domain.setup import (
    PlanAction,
    PlanItem,
    ResourceKind,
    SetupPreview,
    Unmanaged,
    plan_hash,
)
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client

PLAN = "/api/setup/plan"


@pytest.mark.p0
def test_plan_route_returns_items_unmanaged_rows_and_the_plan_hash(
    settings_factory: SettingsFactory,
) -> None:
    """AC-9: the route returns the store's preview, its hash and the Prefix, in camelCase."""
    prefix = f"Ll{uuid.uuid4().hex}"
    items = (
        PlanItem(PlanAction.CREATE, ResourceKind.DECK, f"{prefix}::Study"),
        PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, f"{prefix} English Vocabulary"),
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, f"{prefix} French Sentence"),
        PlanItem(PlanAction.REPAIR, ResourceKind.PRESET, prefix),
    )
    unmanaged = (Unmanaged(ResourceKind.DECK, f"{prefix}::Old stuff"),)
    store = FakeAnkiStore(preview=SetupPreview(items=items, unmanaged=unmanaged))
    settings = settings_factory(anki_prefix=prefix)
    app = create_app(settings, anki_store=store)

    response = app_client(app, settings).get(PLAN)

    assert response.status_code == 200
    assert response.json() == {
        "prefix": prefix,
        "planHash": plan_hash(items),
        "state": "ready",
        "items": [
            {
                "action": "create",
                "kind": "deck",
                "name": f"{prefix}::Study",
                "requiresFullSync": False,
            },
            {
                "action": "repair",
                "kind": "templates",
                "name": f"{prefix} English Vocabulary",
                "requiresFullSync": False,
            },
            {
                "action": "migrate",
                "kind": "noteType",
                "name": f"{prefix} French Sentence",
                "requiresFullSync": True,
            },
            {"action": "repair", "kind": "preset", "name": prefix, "requiresFullSync": False},
        ],
        "repairs": [],  # no leftovers offered (story 2.11)
        "unmanaged": [{"kind": "deck", "name": f"{prefix}::Old stuff"}],
    }


@pytest.mark.p1
@pytest.mark.parametrize(
    ("store", "code"),
    [(FakeAnkiStore(busy=True), "anki_busy"), (FakeAnkiStore(available=False), "anki_unavailable")],
    ids=["busy", "unavailable"],
)
def test_plan_route_while_anki_is_busy_or_down_is_the_503_envelope(
    settings_factory: SettingsFactory, store: FakeAnkiStore, code: str
) -> None:
    """AC-9: a preview Anki can't answer is the AD-15 503 envelope, with its fixed message."""
    settings = settings_factory()
    app = create_app(settings, anki_store=store)

    response = app_client(app, settings).get(PLAN)

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"] == MESSAGES[ErrorCode(code)]
    assert error["requestId"]

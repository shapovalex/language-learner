"""Story 2.7: POST /api/setup/apply and GET /api/setup/apply/status (FR-6, AD-3, AD-15).

POST carries `{"planHash"}`, the hash of the plan the user confirmed. The server re-diffs. A
hash the fresh plan no longer has is `409 plan_changed`, a code added with the user on
2026-10-21 with the fixed message below. Otherwise the run goes to its end and the response is
the verification `{"verified", "planHash", "discrepancies": [{"action", "kind", "name",
"requiresFullSync"}], "fullSyncRequired"}` (story 2.9 added the last two),
where `planHash` is what a fresh preview hashes to while Anki stays as verify found it.

GET /api/setup/apply/status is `{"state": "idle" | "running" | "finished", "result"}`, so a
screen coming back after leaving can show the run.

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/. After an apply,
its preview becomes the verification it returned. The apply logic is in
tests/integration/test_anki_setup_apply.py.
"""

import pytest

from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupPreview, plan_hash
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over

APPLY = "/api/setup/apply"
STATUS = "/api/setup/apply/status"
PLAN = "/api/setup/plan"
PREFIX = "LanguageLab"
PLAN_CHANGED_MESSAGE = "Anki changed since the preview. Review the changes and apply again."

ITEMS = (
    PlanItem(PlanAction.CREATE, ResourceKind.DECK, f"{PREFIX}::Study"),
    PlanItem(PlanAction.CREATE, ResourceKind.NOTE_TYPE, f"{PREFIX} Capture"),
    PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, f"{PREFIX} English Vocabulary"),
    PlanItem(PlanAction.REPAIR, ResourceKind.PRESET, PREFIX),
)
LEFT_OVER = (PlanItem(PlanAction.REPAIR, ResourceKind.PRESET, PREFIX),)


@pytest.mark.p0
@pytest.mark.parametrize(
    ("verification", "expected"),
    [
        (
            SetupPreview(),
            {
                "verified": True,
                "planHash": plan_hash(()),
                "discrepancies": [],
                "fullSyncRequired": False,
            },
        ),
        (
            SetupPreview(items=LEFT_OVER),
            {
                "verified": False,
                "planHash": plan_hash(LEFT_OVER),
                "discrepancies": [
                    {
                        "action": "repair",
                        "kind": "preset",
                        "name": PREFIX,
                        "requiresFullSync": False,
                    }
                ],
                "fullSyncRequired": False,
            },
        ),
    ],
    ids=["verified", "discrepancies"],
)
def test_apply_route_runs_the_confirmed_plan_and_returns_the_verification(
    settings_factory: SettingsFactory, verification: SetupPreview, expected: dict
) -> None:
    """AC-7: the confirmed hash applies the plan; the body is the verification, and a second
    preview shows what is left.
    """
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS), verified=verification)
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    response = client.post(APPLY, json={"planHash": plan_hash(ITEMS)})

    assert response.status_code == 200
    assert response.json() == expected
    assert store.applies == 1
    assert client.get(PLAN).json()["planHash"] == expected["planHash"]


@pytest.mark.p0
def test_apply_route_refuses_a_stale_plan_with_409_plan_changed(
    settings_factory: SettingsFactory,
) -> None:
    """AC-8: a hash the fresh plan doesn't have is the 409 `plan_changed` envelope; no apply."""
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS))
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    response = client.post(APPLY, json={"planHash": plan_hash(ITEMS[:-1])})

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "plan_changed"
    assert error["message"] == PLAN_CHANGED_MESSAGE
    assert error["requestId"]
    assert getattr(store, "applies", None) == 0
    assert client.get(PLAN).json()["planHash"] == plan_hash(ITEMS)


@pytest.mark.p1
def test_apply_status_is_idle_before_a_run_and_finished_with_its_result_after(
    settings_factory: SettingsFactory,
) -> None:
    """AC-9: the status route reports no run, then the finished run with the POST's result."""
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS), verified=SetupPreview(items=LEFT_OVER))
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    before = client.get(STATUS)

    assert before.json() == {"state": "idle", "result": None}
    assert before.status_code == 200
    result = client.post(APPLY, json={"planHash": plan_hash(ITEMS)}).json()
    after = client.get(STATUS)
    assert after.status_code == 200
    assert after.json() == {"state": "finished", "result": result}


@pytest.mark.p1
@pytest.mark.parametrize(
    ("store_options", "code"),
    [({"busy": True}, "anki_busy"), ({"available": False}, "anki_unavailable")],
    ids=["busy", "unavailable"],
)
def test_apply_route_answers_503_when_anki_is_busy_or_down(
    settings_factory: SettingsFactory, store_options: dict, code: str
) -> None:
    """AC-7: `anki_busy` / `anki_unavailable` from the apply are the 503 envelope; no apply."""
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS), **store_options)
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    response = client.post(APPLY, json={"planHash": plan_hash(ITEMS)})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == code
    assert store.applies == 0
    assert client.get(STATUS).json() == {"state": "idle", "result": None}


@pytest.mark.p1
@pytest.mark.parametrize("body", [{}, {"planHash": 7}, {"hash": "x"}], ids=["empty", "int", "key"])
def test_apply_route_without_a_plan_hash_is_422_validation_failed(
    settings_factory: SettingsFactory, body: dict
) -> None:
    """AC-7: a body without a string `planHash` is the 422 `validation_failed` envelope."""
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS))
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    response = client.post(APPLY, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert store.apply_calls == 0

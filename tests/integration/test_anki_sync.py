"""Story 2.10: `AnkiStore.sync` over AnkiConnect API v1, against spike 2.2's recorded runs.

Decided 2026-10-21 (spike 2.2, Q7): the adapter starts the Sync with v1 `collection.sync` on
`/api/v1` and polls `operations.get` until it succeeds or fails, all under the Anki lock and
within the 120 s Sync budget. The other actions stay on v6. The outcome comes from the final
state: `succeeded` is ok, a failure typed `authenticationRequired` is auth_required (Q3), and
any other failure or a poll that runs out the budget is ankiweb_unreachable (Q4).

A v1 success doesn't prove AnkiWeb holds the change (spike Surprises), so `ok` means only that
Anki reported the Sync finished.
"""

import inspect

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.sync import SyncOutcome
from tests.support.aio import settle
from tests.support.anki_connect import (
    ANKI_URL,
    API_V1_PATH,
    AnkiConnectReplay,
    recorded_v1_sync,
    synthetic_v1_sync,
)

SYNC_BUDGET_S = 120.0
RECORDED_RUNS = ("normal", "after-field-change", "logged-out")  # sync-<run>.json
SHORT_BUDGET_S = 0.05  # stands in for the 120 s budget, so a poll that never ends is quick


@pytest.mark.p0
@pytest.mark.parametrize(
    ("run", "expected", "budget_s"),
    [
        ("normal", "ok", SYNC_BUDGET_S),
        ("after-field-change", "ok", SYNC_BUDGET_S),
        ("logged-out", "auth_required", SYNC_BUDGET_S),
        ("unrecorded-failure", "ankiweb_unreachable", SYNC_BUDGET_S),
        ("never-ends", "ankiweb_unreachable", SHORT_BUDGET_S),
    ],
    ids=["normal", "after-field-change", "logged-out", "unrecorded-failure", "never-ends"],
)
def test_sync_runs_v1_collection_sync_to_its_end_and_reports_the_outcome(
    run: str, expected: str, budget_s: float
) -> None:
    """AC-3: one v1 Sync, polled to its end within the budget, under the lock; its outcome."""
    replies = recorded_v1_sync(run) if run in RECORDED_RUNS else synthetic_v1_sync(run)
    anki = AnkiConnectReplay(replies)
    client = AnkiConnectClient(ANKI_URL, transport=anki.transport)
    store = AnkiConnectStore(client, AnkiLock(), poll_interval_s=0, sync_budget_s=budget_s)

    outcome = settle(store.sync())

    assert outcome == SyncOutcome(expected)
    methods = [sent.body.get("method") for sent in anki.sent]
    assert methods[0] == "collection.sync"
    assert len(methods) > 1
    assert set(methods[1:]) == {"operations.get"}
    operation_id = replies["collection.sync"]({})["result"]["operationId"]
    assert all(sent.body["params"] == {"operationId": operation_id} for sent in anki.sent[1:])
    assert all(sent.url.rstrip("/") == ANKI_URL + API_V1_PATH for sent in anki.sent)
    assert not any("action" in sent.body for sent in anki.sent)  # no v6 `sync` any more
    default = inspect.signature(AnkiConnectStore).parameters["sync_budget_s"].default
    assert default == SYNC_BUDGET_S


@pytest.mark.p1
@pytest.mark.parametrize("state", ["waitingForUser", "cancelled"])
def test_sync_stops_at_once_when_anki_waits_for_the_user_or_cancels(state: str) -> None:
    """Decided 2026-10-21: a dialog in Anki or a cancelled Sync is ankiweb_unreachable after one
    poll, and the lock is free again for the next Anki call.
    """
    replies = synthetic_v1_sync(state)
    anki = AnkiConnectReplay(replies)
    store = AnkiConnectStore(
        AnkiConnectClient(ANKI_URL, transport=anki.transport),
        AnkiLock(wait_seconds=SHORT_BUDGET_S),
        poll_interval_s=0,
    )

    outcome = settle(store.sync())

    assert outcome == SyncOutcome.ANKIWEB_UNREACHABLE
    assert [sent.body.get("method") for sent in anki.sent] == [
        "collection.sync",
        "operations.get",
    ]
    assert settle(store.reachable()) is False  # the lock was released: no anki_busy

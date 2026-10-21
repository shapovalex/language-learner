"""Story 2.7: a confirmed apply runs to completion server-side, even if the client disconnects
(AD-3; EXPERIENCE.md Progress card: leaving the screen does not cancel the run).

`SetupService.apply(plan_hash)` runs `AnkiStore.setup_apply` in a task the service keeps, and
the request only awaits it. A disconnect cancels the request, not that task. Decided with the
user (2026-10-21): `SetupService.apply_status()` reports the run as
`{"state": "idle" | "running" | "finished", "result": ApplyResult | None}`, so a screen coming
back can show it.

The store is the fake from tests/fakes/ with `apply_gated=True`, so each `setup_apply` stays in
flight until `finish_apply()` ends it. Nothing waits in real time.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupPreview, plan_hash
from language_lab.features.setup.service import SetupService
from tests.fakes.anki_store import FakeAnkiStore
from tests.fakes.sync_requester import FakeSyncRequester
from tests.support.aio import settle
from tests.support.clock import bounded, drain, until

PREFIX = "LanguageLab"
ITEMS = (
    PlanItem(PlanAction.CREATE, ResourceKind.DECK, f"{PREFIX}::Study"),
    PlanItem(PlanAction.REPAIR, ResourceKind.PRESET, PREFIX),
)


@dataclass(frozen=True)
class Observed:
    applies: int  # store applies that ran to their end
    request_cancelled: bool
    while_running: Any  # apply_status() mid-run
    after: Any  # apply_status() once the store finished


async def disconnect_mid_apply() -> Observed:
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS), apply_gated=True)
    service = SetupService(
        store,
        sync=FakeSyncRequester(),
        prefix=PREFIX,
        azure_configured=True,
        openrouter_configured=True,
    )
    request = asyncio.create_task(service.apply(plan_hash(ITEMS)))
    await until(lambda: store.apply_calls == 1)
    while_running = service.apply_status()

    request.cancel()  # the client went away mid-apply
    await drain()
    store.finish_apply()
    await until(lambda: store.applies == 1)
    await drain()

    return Observed(store.applies, request.cancelled(), while_running, service.apply_status())


@pytest.mark.p0
def test_apply_completes_server_side_when_the_client_disconnects() -> None:
    """AC-6: a cancelled apply request leaves the run going; it finishes and its result is kept."""
    observed = settle(bounded(disconnect_mid_apply()))

    assert getattr(observed, "applies", None) == 1
    assert observed.request_cancelled
    assert observed.while_running == {"state": "running", "result": None}
    assert observed.after == {
        "state": "finished",
        "result": {
            "verified": True,
            "planHash": plan_hash(()),
            "discrepancies": [],
            "fullSyncRequired": False,
        },
    }


async def second_apply_mid_run() -> tuple[int, int, Any, Any]:
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS), apply_gated=True)
    service = SetupService(
        store,
        sync=FakeSyncRequester(),
        prefix=PREFIX,
        azure_configured=True,
        openrouter_configured=True,
    )
    first = asyncio.create_task(service.apply(plan_hash(ITEMS)))
    await until(lambda: store.apply_calls == 1)
    second = asyncio.create_task(service.apply(plan_hash(ITEMS)))
    await drain()

    store.finish_apply()
    bodies = await asyncio.gather(first, second)
    return store.apply_calls, store.applies, bodies[0], bodies[1]


@pytest.mark.p1
def test_a_second_apply_while_one_runs_awaits_the_same_run() -> None:
    """AC-6: a second POST mid-run doesn't start another apply; both get the one result."""
    apply_calls, applies, first, second = settle(bounded(second_apply_mid_run()))

    assert apply_calls == 1
    assert applies == 1
    assert (
        first
        == second
        == {
            "verified": True,
            "planHash": plan_hash(()),
            "discrepancies": [],
            "fullSyncRequired": False,
        }
    )


async def field_change_fails_mid_apply() -> tuple[ErrorCode | None, bool | None]:
    items = (PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, f"{PREFIX} Capture"),)
    store = FakeAnkiStore(preview=SetupPreview(items=items), apply_gated=True)
    service = SetupService(
        store,
        sync=FakeSyncRequester(),
        prefix=PREFIX,
        azure_configured=True,
        openrouter_configured=True,
    )
    request = asyncio.create_task(service.apply(plan_hash(items)))
    await until(lambda: store.apply_calls == 1)
    store.finish_apply(ErrorCode.ANKI_UNAVAILABLE)  # e.g. verify failed after the field was added
    try:
        await request
        code = None
    except AppError as exc:
        code = exc.code
    checks = (await service.readiness())["checks"]
    return code, next(c["ok"] for c in checks if c["id"] == "fullSync")


@pytest.mark.p1
def test_a_field_changing_apply_that_fails_after_its_sync_still_requires_a_full_sync() -> None:
    """Story 2.9, AC-13: a field change whose apply raises mid-run may have changed Anki's schema,
    so the error propagates and the fullSync check fails.
    """
    code, full_sync_ok = settle(bounded(field_change_fails_mid_apply()))

    assert full_sync_ok is False
    assert code is ErrorCode.ANKI_UNAVAILABLE

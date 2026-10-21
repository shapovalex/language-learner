"""Story 2.10: features/sync, the one owner of every Sync (AD-17, FR-36).

Requests coalesce: at most one Sync running and one pending, each through `AnkiStore.sync`.
`request_and_wait()` (for Setup) returns the status of a Sync that started after the call, not
of one already running. A failure is logged to the terminal and kept as the last status. It is
never raised. The last status lives in memory only (AD-2).

The AnkiStore is the in-memory fake. With `gated=True` each `sync()` stays in flight until the
test calls `finish()`, so the test decides when a Sync ends and nothing waits in real time.

Skipped until features/sync and the fake's gate exist. Un-skip one, watch it fail, then
implement. Hoist the imports once it's green.
"""

import asyncio

import pytest

from language_lab.domain.errors import ErrorCode
from tests.support.aio import settle, settled
from tests.support.clock import bounded, drain, until
from tests.support.fixtures.logs import LogCapture

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.10: un-skip with features/sync and the fake's sync gate"
)

SYNC_LOGGER = "language_lab.sync"
CONCURRENT_REQUESTS = 10


@RED_PHASE
@pytest.mark.p0
def test_ten_concurrent_requests_make_at_most_two_syncs() -> None:
    """AC-2: one Sync running and one pending; nine requests during a Sync add one more."""
    from language_lab.features.sync.service import SyncService
    from tests.fakes.anki_store import FakeAnkiStore

    async def scenario() -> tuple[int, int, int]:
        store = FakeAnkiStore(gated=True)
        service = SyncService(store, enabled=True)
        await service.request()
        await until(lambda: store.in_flight == 1)
        await asyncio.gather(*(service.request() for _ in range(CONCURRENT_REQUESTS - 1)))
        await drain()
        for _ in range(CONCURRENT_REQUESTS):  # bounded: a Sync per request would end here too
            if not store.in_flight:
                break
            store.finish()
            await drain()
        return store.sync_calls, store.max_in_flight, store.in_flight

    sync_calls, max_in_flight, in_flight = settle(bounded(scenario()))

    assert sync_calls == 2
    assert max_in_flight == 1  # the pending Sync starts only after the running one ends
    assert in_flight == 0


@RED_PHASE
@pytest.mark.p1
def test_request_and_wait_returns_the_status_of_a_sync_started_after_the_call() -> None:
    """AC-7: awaited while a Sync runs, the call waits for the pending one and gets its status."""
    from language_lab.domain.sync import SyncOutcome
    from language_lab.features.sync.service import SyncService
    from tests.fakes.anki_store import FakeAnkiStore

    async def scenario() -> tuple[object, bool, int]:
        store = FakeAnkiStore(gated=True)
        service = SyncService(store, enabled=True)
        await service.request()
        await until(lambda: store.in_flight == 1)
        waiter = asyncio.create_task(settled(service.request_and_wait()))
        await drain()
        store.finish(ErrorCode.ANKI_UNAVAILABLE)  # the Sync that was running before the call
        await drain()
        waiting_after_first = not waiter.done()
        store.finish(SyncOutcome.OK)
        return await waiter, waiting_after_first, store.sync_calls

    status, waiting_after_first, sync_calls = settle(bounded(scenario()))

    assert getattr(status, "outcome", status) == SyncOutcome.OK
    assert waiting_after_first
    assert sync_calls == 2


@RED_PHASE
@pytest.mark.p0
@pytest.mark.parametrize(
    "failure",
    ["anki_unavailable", "anki_busy", "auth_required", "ankiweb_unreachable"],
)
def test_a_failed_sync_is_logged_and_never_raised(failure: str, log_capture: LogCapture) -> None:
    """AC-9: whatever the failure, the caller gets a status, and the terminal gets one line."""
    from language_lab.domain.errors import AppError
    from language_lab.domain.sync import SyncOutcome
    from language_lab.features.sync.service import SyncService
    from tests.fakes.anki_store import FakeAnkiStore

    # anki_unavailable and anki_busy are raised by the store, the others are its outcome
    end = ErrorCode(failure) if failure in {c.value for c in ErrorCode} else SyncOutcome(failure)

    async def scenario() -> tuple[object, object]:
        store = FakeAnkiStore(gated=True)
        service = SyncService(store, enabled=True)
        waiter = asyncio.create_task(settled(service.request_and_wait()))
        await until(lambda: store.in_flight == 1)
        store.finish(end)
        waited = await waiter
        requested = await settled(service.request())
        await until(lambda: store.in_flight == 1)
        store.finish(end)
        await drain()
        return waited, requested

    waited, requested = settle(bounded(scenario()))

    assert not isinstance(waited, Exception)
    assert waited.outcome == SyncOutcome(failure)
    assert requested is None
    logged = [r for r in log_capture.records if r.name == SYNC_LOGGER]
    warnings = [r for r in logged if r.levelname == "WARNING"]
    assert len(warnings) == 2
    assert all(failure in r.getMessage() for r in warnings)
    assert not any(r.exc_info for r in log_capture.records)  # one line, no traceback
    assert not any(isinstance(v, AppError) for v in (waited, requested))


@RED_PHASE
@pytest.mark.p1
def test_the_last_sync_status_is_kept_in_memory() -> None:
    """AC-10: `last_status()` is the latest Sync's status, full-sync-required included."""
    from language_lab.domain.sync import SyncOutcome, SyncStatus
    from language_lab.features.sync.service import SyncService
    from tests.fakes.anki_store import FakeAnkiStore

    async def scenario() -> tuple[object, object, object, int]:
        store = FakeAnkiStore(outcome=SyncOutcome.AUTH_REQUIRED)
        service = SyncService(store, enabled=True)
        before = service.last_status()
        await service.request_and_wait()
        after_failure = service.last_status()
        store.outcome = SyncOutcome.OK
        await service.request_and_wait()
        return before, after_failure, service.last_status(), store.sync_calls

    before, after_failure, after_success, sync_calls = settle(bounded(scenario()))

    assert after_failure == SyncStatus(SyncOutcome.AUTH_REQUIRED, full_sync_required=False)
    assert after_success == SyncStatus(SyncOutcome.OK, full_sync_required=False)
    assert before is None
    assert sync_calls == 2  # reading the status never asks Anki

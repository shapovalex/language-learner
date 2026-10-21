"""Story 2.10: the app lifespan requests Sync at startup, every five minutes, and at shutdown.

AD-17 and FR-36. Startup requests a Sync and doesn't wait for it. While the app runs, the
scheduler requests one every 300 s. Graceful shutdown requests one more and waits for it for at
most 30 s, so a hung AnkiConnect can't hold the process. `LANGUAGE_LAB_DEV=1` turns all of it
off.

Decided 2026-10-21: time comes from an injected clock,
`create_app(settings, *, anki_store=None, clock=None)`, used for both the interval and the
shutdown cap. These tests pass `FakeClock` (tests/support/clock.py), which moves only when told
to, and the in-memory AnkiStore. They run the lifespan directly, with no server and no HTTP.

Skipped until the sync feature and the lifespan wiring exist. Un-skip one, watch it fail, then
implement. Hoist the imports once it's green.
"""

import asyncio

import pytest

from language_lab.settings import DEV_PREFIX
from tests.support.aio import settle
from tests.support.clock import FakeClock, bounded, drain, until
from tests.support.fixtures.settings import SettingsFactory
from tests.support.lifespan import LIFESPAN_BOUND_S, start_lifespan

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.10: un-skip with features/sync and create_app(clock=...)"
)

INTERVAL_S = 300.0  # five minutes (FR-36)
SHUTDOWN_CAP_S = 30.0  # graceful shutdown waits this long for its Sync, no longer (AD-17)


@RED_PHASE
@pytest.mark.p0
def test_startup_requests_a_sync_without_waiting_for_it(
    settings_factory: SettingsFactory,
) -> None:
    """AC-4: startup requests one Sync, and the app is up while that Sync is still running."""
    from language_lab.app import create_app
    from tests.fakes.anki_store import FakeAnkiStore

    store, clock = FakeAnkiStore(gated=True), FakeClock()
    app = create_app(settings_factory(), anki_store=store, clock=clock)

    async def scenario() -> tuple[int, int]:
        stack = await start_lifespan(app)
        await drain()
        observed = store.sync_calls, store.in_flight
        store.finish()
        exiting = asyncio.create_task(stack.aclose())
        await drain()  # shutdown starts and parks on its cap
        await clock.advance(SHUTDOWN_CAP_S)  # ends shutdown, whatever its own Sync does
        await asyncio.wait_for(exiting, LIFESPAN_BOUND_S)
        return observed

    sync_calls, in_flight = settle(bounded(scenario()))

    assert sync_calls == 1
    assert in_flight == 1  # startup returned before the Sync ended


@RED_PHASE
@pytest.mark.p0
def test_a_sync_is_requested_every_five_minutes(settings_factory: SettingsFactory) -> None:
    """AC-5: one more Sync at 300 s and at 600 s, and none before 300 s."""
    from language_lab.app import create_app
    from tests.fakes.anki_store import FakeAnkiStore

    store, clock = FakeAnkiStore(), FakeClock()
    app = create_app(settings_factory(), anki_store=store, clock=clock)

    async def scenario() -> dict[float, int]:
        stack = await start_lifespan(app)
        await drain()
        calls = {0.0: store.sync_calls}
        for step in (INTERVAL_S - 1, 1.0, INTERVAL_S):
            await clock.advance(step)
            calls[clock.now] = store.sync_calls
        exiting = asyncio.create_task(stack.aclose())
        await drain()  # shutdown starts and parks on its cap
        await clock.advance(SHUTDOWN_CAP_S)
        await asyncio.wait_for(exiting, LIFESPAN_BOUND_S)
        return calls

    calls = settle(bounded(scenario()))

    assert calls[INTERVAL_S] == calls[0.0] + 1
    assert calls[INTERVAL_S - 1] == calls[0.0]
    assert calls[2 * INTERVAL_S] == calls[0.0] + 2
    assert calls[0.0] == 1  # the startup Sync


@RED_PHASE
@pytest.mark.p0
def test_shutdown_requests_a_sync_and_waits_for_it_at_most_30_s(
    settings_factory: SettingsFactory,
) -> None:
    """AC-6: shutdown requests a Sync; with AnkiConnect hung, shutdown ends at 30 s, not before."""
    from language_lab.app import create_app
    from tests.fakes.anki_store import FakeAnkiStore

    store, clock = FakeAnkiStore(gated=True), FakeClock()
    app = create_app(settings_factory(), anki_store=store, clock=clock)

    async def scenario() -> tuple[int, int, bool, bool, BaseException | None]:
        stack = await start_lifespan(app)
        await until(lambda: store.in_flight == 1)
        store.finish()  # the startup Sync ends; the shutdown Sync below never does
        await drain()
        before = store.sync_calls
        exiting = asyncio.create_task(stack.aclose())
        await drain()
        at_shutdown = store.sync_calls
        await clock.advance(SHUTDOWN_CAP_S - 0.1)
        open_before_cap = not exiting.done()
        await clock.advance(0.1)
        closed_at_cap = exiting.done()
        if not closed_at_cap:
            exiting.cancel()
        error = exiting.exception() if closed_at_cap and not exiting.cancelled() else None
        return before, at_shutdown, open_before_cap, closed_at_cap, error

    before, at_shutdown, open_before_cap, closed_at_cap, error = settle(bounded(scenario()))

    assert at_shutdown == before + 1
    assert open_before_cap  # shutdown waits for its Sync...
    assert closed_at_cap  # ...but no longer than 30 s
    assert error is None


@RED_PHASE
@pytest.mark.p0
def test_dev_mode_never_syncs(settings_factory: SettingsFactory) -> None:
    """AC-8: with LANGUAGE_LAB_DEV on, no Sync at startup, on the interval, or at shutdown."""
    from language_lab.app import create_app
    from tests.fakes.anki_store import FakeAnkiStore

    store, clock = FakeAnkiStore(), FakeClock()
    settings = settings_factory(dev=True, anki_prefix=DEV_PREFIX)
    app = create_app(settings, anki_store=store, clock=clock)

    async def scenario() -> int:
        stack = await start_lifespan(app)
        await drain()
        await clock.advance(2 * INTERVAL_S)
        await asyncio.wait_for(stack.aclose(), LIFESPAN_BOUND_S)  # no Sync to wait for
        return store.sync_calls

    sync_calls = settle(bounded(scenario()))

    assert sync_calls == 0

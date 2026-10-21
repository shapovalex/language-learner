"""Story 2.10: the SyncRequester port, its fake and the sync feature keep step (AD-1, AD-17).

Features never call `AnkiStore.sync` themselves. They ask `SyncRequester`, which `features/sync`
implements and `app.py` injects. `request()` returns at once, `request_and_wait()` returns the
status of a Sync that started after the call (Setup, entry 9), and `last_status()` reads the
in-memory status without touching Anki.

Skipped until the port, the fake and the service exist. Un-skip it, watch it fail, then
implement. Hoist the imports once it's green.
"""

import inspect

import pytest

from tests.support.ports import public_methods

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.10: un-skip with ports/sync_requester.py and tests/fakes/"
)


@RED_PHASE
@pytest.mark.p1
def test_sync_requester_port_declares_request_wait_and_status_and_the_fake_matches() -> None:
    """AC-1: the port has exactly `request`, `request_and_wait` and `last_status`; all match."""
    from language_lab.features.sync.service import SyncService
    from language_lab.ports.sync_requester import SyncRequester

    from tests.fakes.sync_requester import FakeSyncRequester

    port = public_methods(SyncRequester)

    assert set(port) == {"request", "request_and_wait", "last_status"}
    assert inspect.iscoroutinefunction(SyncRequester.request)
    assert inspect.iscoroutinefunction(SyncRequester.request_and_wait)
    assert not inspect.iscoroutinefunction(SyncRequester.last_status)  # memory only, no I/O
    fake = public_methods(FakeSyncRequester)
    assert {name: fake.get(name) for name in port} == port
    service = public_methods(SyncService)
    assert {name: service.get(name) for name in port} == port

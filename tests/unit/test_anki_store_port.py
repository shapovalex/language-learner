"""Story 2.1: the AnkiStore port starts with readiness and sync, and its fake keeps step (AD-1).

The tracer declares only `reachable()` and `sync()`. Later entries add methods to the port, the
fake in tests/fakes/ and the AnkiConnect adapter together, and this test keeps them aligned.
"""

import inspect

import pytest

from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.ports.anki_store import AnkiStore
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.ports import public_methods


@pytest.mark.p1
def test_anki_store_port_declares_readiness_and_sync_and_the_fake_matches() -> None:
    """AC-1: the port has exactly `reachable` and `sync`; the fake and the adapter match it."""
    port = public_methods(AnkiStore)

    assert set(port) == {"reachable", "sync"}
    assert all(inspect.iscoroutinefunction(getattr(AnkiStore, name)) for name in port)
    fake = public_methods(FakeAnkiStore)
    assert {name: fake.get(name) for name in port} == port
    adapter = public_methods(AnkiConnectStore)
    assert {name: adapter.get(name) for name in port} == port

"""Stories 2.1 and 2.6: the AnkiStore port and its fake keep step (AD-1).

The tracer declared `reachable()` and `sync()`; story 2.6 adds `setup_preview()`. Later entries
add methods to the port, the fake in tests/fakes/ and the AnkiConnect adapter together, and
these tests keep them aligned.
"""

import inspect

import pytest

from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.setup import SetupPreview
from language_lab.ports.anki_store import AnkiStore
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.ports import public_methods


@pytest.mark.p1
def test_anki_store_port_declares_readiness_and_sync_and_the_fake_matches() -> None:
    """AC-1: the port has `reachable` and `sync`; the fake and the adapter match it.

    Story 2.6's test below holds the exact set of port methods.
    """
    port = public_methods(AnkiStore)

    assert {"reachable", "sync"} <= set(port)
    assert all(inspect.iscoroutinefunction(getattr(AnkiStore, name)) for name in port)
    fake = public_methods(FakeAnkiStore)
    assert {name: fake.get(name) for name in port} == port
    adapter = public_methods(AnkiConnectStore)
    assert {name: adapter.get(name) for name in port} == port


@pytest.mark.p1
def test_anki_store_port_adds_the_setup_preview_read_and_the_fake_matches() -> None:
    """AC-4: story 2.6 adds `setup_preview() -> SetupPreview`; the fake and the adapter match."""
    port = public_methods(AnkiStore)

    assert set(port) == {"reachable", "sync", "setup_preview"}
    assert inspect.iscoroutinefunction(AnkiStore.setup_preview)
    assert inspect.get_annotations(AnkiStore.setup_preview, eval_str=True)["return"] is SetupPreview
    fake = public_methods(FakeAnkiStore)
    assert {name: fake.get(name) for name in port} == port
    adapter = public_methods(AnkiConnectStore)
    assert {name: adapter.get(name) for name in port} == port

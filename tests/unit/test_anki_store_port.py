"""Stories 2.1 and 2.6: the AnkiStore port and its fake keep step (AD-1).

The tracer declared `reachable()` and `sync()`; story 2.6 adds `setup_preview()`, story 2.7
`setup_apply()` and story 2.8 `setup_state()`; story 2.11 gives `setup_apply()` its `repairs`,
story 3.1 adds `create_capture()`, story 3.2 `list_captures()` and `get_capture()`, story 3.3
`delete_capture()`, story 4.1 `save_item()`, and story 4.3 `item_candidates()` and
`get_item()`, and story 5.3 `delete_item()`.
Later entries add methods to the port, the fake in tests/fakes/ and the AnkiConnect adapter
together, and these tests keep them aligned.
"""

import inspect
from collections.abc import Collection
from datetime import datetime

import pytest

from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.captures import Capture
from language_lab.domain.setup import SetupPreview, SetupState
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
def test_anki_store_port_adds_setup_apply_and_the_fake_matches() -> None:
    """Story 2.7: `setup_apply(plan_hash) -> SetupPreview`, with the checked opt-in `repairs`
    keys since story 2.11 (default none); the fake and the adapter match.
    """
    hints = inspect.get_annotations(AnkiStore.setup_apply, eval_str=True)

    assert inspect.iscoroutinefunction(AnkiStore.setup_apply)
    assert hints == {"plan_hash": str, "repairs": Collection[str], "return": SetupPreview}
    assert inspect.signature(AnkiStore.setup_apply).parameters["repairs"].default == ()
    port = {"setup_apply": public_methods(AnkiStore)["setup_apply"]}
    fake = public_methods(FakeAnkiStore)
    assert {"setup_apply": fake.get("setup_apply")} == port
    adapter = public_methods(AnkiConnectStore)
    assert {"setup_apply": adapter.get("setup_apply")} == port


@pytest.mark.p1
def test_anki_store_port_adds_the_setup_preview_read_and_the_fake_matches() -> None:
    """AC-4: story 2.6 adds `setup_preview() -> SetupPreview`; the fake and the adapter match."""
    port = public_methods(AnkiStore)

    assert set(port) == {
        "reachable",
        "sync",
        "setup_state",
        "setup_preview",
        "setup_apply",
        "create_capture",
        "list_captures",
        "get_capture",
        "delete_capture",
        "save_item",
        "item_candidates",
        "get_item",
        "delete_item",
        "get_media",
    }
    assert inspect.iscoroutinefunction(AnkiStore.setup_preview)
    assert inspect.get_annotations(AnkiStore.setup_preview, eval_str=True)["return"] is SetupPreview
    fake = public_methods(FakeAnkiStore)
    assert {name: fake.get(name) for name in port} == port
    adapter = public_methods(AnkiConnectStore)
    assert {name: adapter.get(name) for name in port} == port


@pytest.mark.p1
def test_anki_store_port_adds_setup_state_and_the_fake_matches() -> None:
    """Story 2.8: `setup_state() -> SetupState`; the fake and the adapter match."""
    hints = inspect.get_annotations(AnkiStore.setup_state, eval_str=True)

    assert inspect.iscoroutinefunction(AnkiStore.setup_state)
    assert hints == {"return": SetupState}
    port = {"setup_state": public_methods(AnkiStore)["setup_state"]}
    fake = public_methods(FakeAnkiStore)
    assert {"setup_state": fake.get("setup_state")} == port
    adapter = public_methods(AnkiConnectStore)
    assert {"setup_state": adapter.get("setup_state")} == port


@pytest.mark.p1
def test_anki_store_port_adds_create_capture_and_the_fake_matches() -> None:
    """Story 3.1: `create_capture(capture_id, text, created_at) -> Capture`; the fake and the
    adapter match.
    """
    hints = inspect.get_annotations(AnkiStore.create_capture, eval_str=True)

    assert inspect.iscoroutinefunction(AnkiStore.create_capture)
    assert hints == {"capture_id": str, "text": str, "created_at": datetime, "return": Capture}
    port = {"create_capture": public_methods(AnkiStore)["create_capture"]}
    fake = public_methods(FakeAnkiStore)
    assert {"create_capture": fake.get("create_capture")} == port
    adapter = public_methods(AnkiConnectStore)
    assert {"create_capture": adapter.get("create_capture")} == port


@pytest.mark.p1
def test_anki_store_port_adds_the_item_reads_and_the_fake_matches() -> None:
    """AC-5: story 4.3 adds `item_candidates(language, category) -> list[Item]` and
    `get_item(language, item_id) -> Item`; the fake and the adapter match. Story 2.6's test
    above then lists both in the exact set of port methods.
    """
    from language_lab.domain.catalog import Category, Language
    from language_lab.domain.items import Item

    reads = {name: public_methods(AnkiStore).get(name) for name in ("item_candidates", "get_item")}

    assert {name: public_methods(FakeAnkiStore).get(name) for name in reads} == reads
    assert {name: public_methods(AnkiConnectStore).get(name) for name in reads} == reads
    assert inspect.iscoroutinefunction(AnkiStore.item_candidates)
    assert inspect.iscoroutinefunction(AnkiStore.get_item)
    assert inspect.get_annotations(AnkiStore.item_candidates, eval_str=True) == {
        "language": Language,
        "category": Category,
        "return": list[Item],
    }
    assert inspect.get_annotations(AnkiStore.get_item, eval_str=True) == {
        "language": Language,
        "item_id": str,
        "return": Item,
    }


@pytest.mark.p1
def test_audio_save_and_media_read_have_matching_port_fake_adapter_signatures():
    from language_lab.domain.items import AudioIntent

    port = public_methods(AnkiStore)
    for cls in (FakeAnkiStore, AnkiConnectStore):
        methods = public_methods(cls)
        assert methods["save_item"] == port["save_item"]
        assert methods["get_media"] == port["get_media"]
    parameters = port["save_item"].parameters
    assert parameters["audio"].default is AudioIntent.KEEP
    assert parameters["audio_bytes"].default is None
    assert parameters["audio_bytes"].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.p1
def test_fake_remove_mirrors_the_adapter_by_dropping_the_items_clip() -> None:
    """Story 6.2: the fake's `remove` drops the Item's clip; `remove` with bytes is refused."""
    import uuid

    from language_lab.domain.catalog import Language
    from language_lab.domain.errors import AppError
    from language_lab.domain.items import AudioIntent
    from tests.support.aio import run
    from tests.support.audio import MP3
    from tests.support.items import VOCABULARY, content

    store = FakeAnkiStore()
    item_id = str(uuid.uuid4())
    run(
        store.save_item(
            item_id, Language.EN, content(VOCABULARY), AudioIntent.REPLACE, audio_bytes=MP3
        )
    )
    assert store.audio[item_id] in store.media
    with pytest.raises(AppError):
        run(
            store.save_item(
                item_id, Language.EN, content(VOCABULARY), AudioIntent.REMOVE, audio_bytes=MP3
            )
        )
    assert item_id in store.audio
    run(store.save_item(item_id, Language.EN, content(VOCABULARY), AudioIntent.REMOVE))
    assert item_id not in store.audio
    assert store.media == {}
    assert run(store.get_item(Language.EN, item_id)).audio is None

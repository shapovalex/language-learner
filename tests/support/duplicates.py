"""Stored Item test data for the duplicate read and the Item read, shared by the Item read
integration and API tests (tests/integration/test_anki_item_reads.py,
tests/api/test_items_read.py).

`on_wire(item_id, wire)` is an Item as both reads answer it: `{itemId, ...ItemContent}`, flat
(AD-11). `vocabulary(target)` and `sentence(target)` are tests/support/items.py's ItemContent
with another Target. `store_with_items(*entries)` is the fake store holding each `(item_id,
language, wire)` entry, in order, as Save leaves it. `item(item_id, wire)` is the domain `Item`.
`language_lab.domain.items.Item` is imported inside the function, so collection passes before it
exists.
"""

from typing import Any

from language_lab.domain.catalog import Language
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.items import SENTENCE, VOCABULARY, content

TARGET = "jump to conclusions"
FRENCH_TARGET = "Ne tirons pas de conclusions hâtives."


def vocabulary(target: str = TARGET, **changes: Any) -> dict[str, Any]:
    return {**VOCABULARY, "target": target, **changes}


def sentence(target: str = FRENCH_TARGET, **changes: Any) -> dict[str, Any]:
    return {**SENTENCE, "target": target, **changes}


def on_wire(item_id: str, wire: dict[str, Any]) -> dict[str, Any]:
    """The Item `item_id` with content `wire`, as GET duplicates and GET one Item answer it."""
    return {"itemId": item_id, **wire}


def store_with_items(*entries: tuple[str, str, dict[str, Any]]) -> FakeAnkiStore:
    """The fake store holding each `(item_id, language, wire)` entry, in order."""
    store = FakeAnkiStore()
    for item_id, language, wire in entries:
        store.items[item_id] = (Language(language), content(wire))
    return store


def item(item_id: str, wire: dict[str, Any]) -> Any:
    """The domain `Item` the reads return: its ItemId and its ItemContent."""
    from language_lab.domain.items import Item

    return Item(item_id, content(wire))

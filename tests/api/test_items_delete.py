"""Story 5.3 HTTP contract; the real adapter is injected over a replay collection.

Provider endpoint: TODO — DELETE /api/items/{lang}/{itemId}, 204 with an empty body.
No fake delete implementation is supplied by this scaffold.
"""

import pytest

from tests.support.anki_state import managed_collection
from tests.support.captures import MANIFEST
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over
from tests.support.item_delete import put_item, wired_delete

pytestmark = pytest.mark.skip(reason="ATDD RED: story 5.3 Item deletion is not implemented")


@pytest.mark.p0
def test_delete_item_answers_204_and_subsequent_reads_leave_it_out(
    settings_factory: SettingsFactory,
) -> None:
    """[P0] AC-12 DELETE answers 204, then detail is absent and the list keeps other Items."""
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    other_id, other_note = put_item(collection)
    store, _ = wired_delete(collection)
    client = client_over(settings_factory, store)

    response = client.delete(f"/api/items/en/{item_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert note_id not in collection.notes
    assert other_note in collection.notes
    gone = client.get(f"/api/items/en/{item_id}")
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "not_found"
    listed = client.get("/api/items/en").json()["items"]
    assert [row["itemId"] for row in listed] == [other_id]

"""Story 4.1: POST /api/drafts/blank, the blank Draft that issues the ItemId (AD-8, AD-13).

"Write it myself" in the Make an Item pane asks for a blank Draft. The backend issues a fresh
ItemId, a UUIDv4 in lowercase canonical form, and the client carries it until Save (AD-8).
Decided for this story: the answer is 201 `{itemId}` and nothing else, since the client builds
the empty form itself from the Language and Category chosen in the pane, with Target prefilled.
Nothing is written to or read from Anki, so it works while Anki is down.

Entry 2 adds the generated Draft beside it, issuing the ItemId the same way.
"""

import re

import pytest

from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over

pytestmark = pytest.mark.skip(reason="ATDD red phase: un-skip when story 4.1 adds features/drafts")

BLANK = "/api/drafts/blank"
UUID4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


@pytest.mark.p0
def test_a_blank_draft_issues_a_fresh_item_id(settings_factory: SettingsFactory) -> None:
    """AC-9: POST /api/drafts/blank is 201 `{itemId}` with a fresh lowercase UUIDv4 each time,
    and nothing reaches Anki, so an unreachable Anki doesn't stop it.
    """
    store = FakeAnkiStore(available=False)
    client = client_over(settings_factory, store)

    first = client.post(BLANK)

    assert first.status_code == 201
    second = client.post(BLANK)
    assert set(first.json()) == {"itemId"}
    item_ids = [first.json()["itemId"], second.json()["itemId"]]
    assert all(UUID4.fullmatch(i) for i in item_ids)
    assert item_ids[0] != item_ids[1]

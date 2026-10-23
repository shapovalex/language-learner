"""Story 4.3: the duplicate read and the Item read under /api/items/<lang> (AD-4, AD-8, AD-11,
AD-12, AD-15; FR-19, FR-22).

- **Duplicates.** GET /api/items/<lang>/duplicates?category=&target=&itemId= is 200
  `{matches: [{itemId, ...ItemContent}]}`: each Item of that Language and Category whose
  `normalize_text(Target)` equals `normalize_text(target)` (AD-12). Case, surrounding
  punctuation, whitespace, apostrophe variants and Unicode composition don't matter; diacritics
  do. The other Language and Category are never searched. `itemId`, when given, leaves out the
  Draft's own Item. The matching is the service's, over the adapter's scoped candidates (AD-4).
- **One Item.** GET /api/items/<lang>/<itemId> is 200 `{itemId, ...ItemContent}`, flat like
  the Draft and the Save (AD-11). An ItemId no Item of that Language holds is 404 `not_found`,
  and so is one that isn't a UUIDv4, without reaching Anki (as Captures do).
- **Refused.** A missing or blank target, a missing or unknown category, an unknown Language or
  a malformed itemId is 422 `validation_failed` before Anki is read.

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/, holding Items as
Save leaves them. The adapter's reads are in tests/integration/test_anki_item_reads.py.
"""

import uuid
from typing import Any

import pytest

from tests.support.duplicates import (
    FRENCH_TARGET,
    TARGET,
    on_wire,
    sentence,
    store_with_items,
    vocabulary,
)
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over

pytestmark = pytest.mark.skip(
    reason="red phase (story 4.3): un-skip with the duplicate read and the Item read in "
    "features/items"
)


def duplicates_path(language: str = "en") -> str:
    return f"/api/items/{language}/duplicates"


def item_path(language: str, item_id: str) -> str:
    return f"/api/items/{language}/{item_id}"


def ask(
    category: str = "vocabulary", target: str = TARGET, item_id: str | None = None
) -> dict[str, str]:
    """The duplicate read's query parameters."""
    params = {"category": category, "target": target}
    if item_id is not None:
        params["itemId"] = item_id
    return params


# Stored Target -> the Target asked for: the same once normalized (AD-12)
SAME_ONCE_NORMALIZED = {
    "case": ("Jump To Conclusions", "jump to conclusions"),
    "surrounding-punctuation": ("jump to conclusions!", "«jump to conclusions»"),
    "whitespace": ("jump to conclusions", "  jump   to\tconclusions \n"),
    "apostrophe-variants": ("don't jump to conclusions", "don’t jump to conclusions"),
    "unicode-composition": ("café au lait", "café au lait"),
    "all-together": ("Don't jump to conclusions.", " ¿DON’T  jump to conclusions? "),
}


@pytest.mark.p0
@pytest.mark.parametrize(
    ("stored", "asked"), SAME_ONCE_NORMALIZED.values(), ids=SAME_ONCE_NORMALIZED.keys()
)
def test_duplicates_returns_the_item_whose_normalized_target_matches(
    settings_factory: SettingsFactory, stored: str, asked: str
) -> None:
    """AC-6: GET duplicates returns the English Vocabulary Item whose Target equals the asked
    one once both are normalized, as `{matches: [{itemId, ...ItemContent}]}`.
    """
    item_id = str(uuid.uuid4())
    other = str(uuid.uuid4())
    store = store_with_items(
        (other, "en", vocabulary("notwithstanding")), (item_id, "en", vocabulary(stored))
    )
    client = client_over(settings_factory, store)

    response = client.get(duplicates_path(), params=ask(target=asked))

    assert [m["itemId"] for m in response.json().get("matches", [])] == [item_id]
    assert response.status_code == 200
    assert response.json() == {"matches": [on_wire(item_id, vocabulary(stored))]}


def _stored_with_diacritics() -> tuple[tuple[str, str, dict[str, Any]], str]:
    return (str(uuid.uuid4()), "en", vocabulary("café au lait")), "cafe au lait"


def _differs_inside() -> tuple[tuple[str, str, dict[str, Any]], str]:
    return (str(uuid.uuid4()), "en", vocabulary("jump to a conclusion")), TARGET


def _in_the_other_language() -> tuple[tuple[str, str, dict[str, Any]], str]:
    return (str(uuid.uuid4()), "fr", vocabulary(TARGET)), TARGET


def _in_the_other_category() -> tuple[tuple[str, str, dict[str, Any]], str]:
    return (str(uuid.uuid4()), "en", sentence(TARGET)), TARGET


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [_stored_with_diacritics, _differs_inside, _in_the_other_language, _in_the_other_category],
    ids=["diacritics", "differs-inside", "other-language", "other-category"],
)
def test_a_target_that_differs_or_another_language_or_category_is_no_match(
    settings_factory: SettingsFactory, arrange: Any
) -> None:
    """AC-7: diacritics stay significant, a Target that differs inside the text doesn't match,
    and an equal Target in French or in the Sentence Category isn't reported (FR-19).
    """
    stored, asked = arrange()
    client = client_over(settings_factory, store_with_items(stored))

    response = client.get(duplicates_path(), params=ask(target=asked))

    assert response.json().get("matches") == []
    assert response.status_code == 200


@pytest.mark.p0
def test_the_drafts_own_item_id_is_left_out_of_the_matches(
    settings_factory: SettingsFactory,
) -> None:
    """AC-8: `itemId=` leaves out the Item with that ItemId (a Draft already saved once), and
    another Item with the same Target is still a match (AD-12).
    """
    own, other = str(uuid.uuid4()), str(uuid.uuid4())
    store = store_with_items((own, "en", vocabulary()), (other, "en", vocabulary(TARGET.upper())))
    client = client_over(settings_factory, store)

    response = client.get(duplicates_path(), params=ask(item_id=own))

    assert [m["itemId"] for m in response.json().get("matches", [])] == [other]


INVALID: dict[str, tuple[str, dict[str, str]]] = {
    "no-target": ("en", {"category": "vocabulary"}),
    "blank-target": ("en", ask(target="  ")),
    "no-category": ("en", {"target": TARGET}),
    "unknown-category": ("en", ask(category="idiom")),
    "unknown-language": ("de", ask()),
    "item-id-not-a-uuid": ("en", ask(item_id="item-1")),
    "uppercase-item-id": ("en", ask(item_id=str(uuid.uuid4()).upper())),
    "item-id-uuid-version-1": ("en", ask(item_id=str(uuid.uuid1()))),
}


@pytest.mark.p0
@pytest.mark.parametrize(("language", "params"), INVALID.values(), ids=INVALID.keys())
def test_an_invalid_duplicate_read_is_validation_failed_and_anki_is_not_read(
    settings_factory: SettingsFactory, language: str, params: dict[str, str]
) -> None:
    """AC-9: an invalid duplicate read is 422 `validation_failed` in the AD-15 envelope; Anki
    is unavailable here, so reading it would have answered 503.
    """
    from tests.fakes.anki_store import FakeAnkiStore

    client = client_over(settings_factory, FakeAnkiStore(available=False))

    response = client.get(duplicates_path(language), params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


@pytest.mark.p1
def test_the_duplicate_reads_target_is_in_no_log_line(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """AC-6: the Target and the query string never reach a log line (AD-15)."""
    target = "a very particular phrase"
    client = client_over(
        settings_factory, store_with_items((str(uuid.uuid4()), "en", vocabulary(target)))
    )

    response = client.get(duplicates_path(), params=ask(target=target))

    assert response.status_code == 200
    assert target not in log_capture.all_text
    assert "particular" not in log_capture.all_text


ONE_ITEM = {
    "en-vocabulary": ("en", vocabulary()),
    "fr-sentence": ("fr", sentence(FRENCH_TARGET)),
}


@pytest.mark.p0
@pytest.mark.parametrize(("language", "wire"), ONE_ITEM.values(), ids=ONE_ITEM.keys())
def test_get_item_returns_the_item_flat_with_its_item_id(
    settings_factory: SettingsFactory, language: str, wire: dict[str, Any]
) -> None:
    """AC-10: GET /api/items/<lang>/<itemId> is 200 `{itemId, ...ItemContent}`, every field as
    stored, flat like the Draft and the Save (AD-11).
    """
    item_id = str(uuid.uuid4())
    store = store_with_items((str(uuid.uuid4()), language, wire), (item_id, language, wire))
    client = client_over(settings_factory, store)

    response = client.get(item_path(language, item_id))

    assert response.status_code == 200
    assert response.json() == on_wire(item_id, wire)


NOT_FOUND = {
    "absent": lambda item_id: str(uuid.uuid4()),
    "in-the-other-language": lambda item_id: item_id,
    "not-a-uuid": lambda item_id: "item-1",
}


@pytest.mark.p0
@pytest.mark.parametrize("asked", NOT_FOUND.values(), ids=NOT_FOUND.keys())
def test_get_item_of_an_item_id_no_item_of_the_language_holds_is_not_found(
    settings_factory: SettingsFactory, log_capture: LogCapture, asked: Any
) -> None:
    """AC-11: an ItemId no English Item holds (absent, a French Item's, or not a UUIDv4) is 404
    `not_found` in the AD-15 envelope, answered by the Item read's route: a path no route
    matches is a 404 `not_found` too, so the request log's route template tells them apart.
    """
    french = str(uuid.uuid4())
    client = client_over(settings_factory, store_with_items((french, "fr", vocabulary())))

    response = client.get(item_path("en", asked(french)))

    (line,) = log_capture.request_lines
    assert (line["route"] or "").startswith("/api/items/{lang}/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.p1
@pytest.mark.parametrize(
    "path",
    [duplicates_path(), item_path("en", str(uuid.uuid4()))],
    ids=["duplicates", "one-item"],
)
def test_anki_down_is_anki_unavailable_for_both_reads(
    settings_factory: SettingsFactory, path: str
) -> None:
    """AC-10: with Anki unreachable, both reads are 503 `anki_unavailable`."""
    from tests.fakes.anki_store import FakeAnkiStore

    client = client_over(settings_factory, FakeAnkiStore(available=False))

    response = client.get(path, params=ask() if path.endswith("duplicates") else None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "anki_unavailable"

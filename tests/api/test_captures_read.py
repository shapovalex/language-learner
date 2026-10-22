"""Story 3.2: GET /api/captures and GET /api/captures/{captureId} (AD-15, Consistency Conventions).

- **The list.** 200 with `{captures: [{captureId, text, createdAt}, ...]}`, newest first by
  CreatedAt, as the AnkiStore returns them. `createdAt` is `YYYY-MM-DDTHH:MM:SSZ`, as POST
  answers it.
- **One Capture.** 200 with `{captureId, text, createdAt}`. A CaptureId that names no Capture,
  well-formed or not, is 404 `not_found`.

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/, whose `captures`
holds each Capture by CaptureId. Its `list_captures()` is newest first, as the adapter's is.
The adapter itself is in tests/integration/test_anki_capture_reads.py.
"""

import re
import uuid
from datetime import UTC, datetime

import pytest

from language_lab.app import create_app
from language_lab.domain.captures import Capture
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client, client_over
from tests.support.live_server import closed_port

CAPTURES = "/api/captures"
# The one-Capture route's template, whatever its parameter is called
CAPTURE_ROUTE = re.compile(r"/api/captures/\{\w+\}")

NEWEST = Capture(
    str(uuid.uuid4()),
    "I'd rather not jump to conclusions.",
    datetime(2026, 10, 22, 21, 14, 5, tzinfo=UTC),
)
MIDDLE = Capture(
    str(uuid.uuid4()), "Il fait un temps de chien.", datetime(2026, 10, 22, 8, 2, tzinfo=UTC)
)
OLDEST = Capture(str(uuid.uuid4()), "un rendez-vous", datetime(2025, 10, 5, 12, 31, tzinfo=UTC))


def body_of(capture: Capture) -> dict[str, str]:
    return {
        "captureId": capture.capture_id,
        "text": capture.text,
        "createdAt": capture.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def store_with(*captures: Capture) -> FakeAnkiStore:
    store = FakeAnkiStore()
    for capture in captures:
        store.captures[capture.capture_id] = capture
    return store


@pytest.mark.p0
def test_get_lists_the_captures_newest_first(settings_factory: SettingsFactory) -> None:
    """AC-5: GET /api/captures is 200 with every Capture as `{captureId, text, createdAt}`,
    newest first by CreatedAt.
    """
    client = client_over(settings_factory, store_with(MIDDLE, OLDEST, NEWEST))

    response = client.get(CAPTURES)

    assert response.status_code == 200
    assert response.json() == {"captures": [body_of(c) for c in (NEWEST, MIDDLE, OLDEST)]}


@pytest.mark.p0
def test_get_one_capture_by_its_capture_id(settings_factory: SettingsFactory) -> None:
    """AC-6: GET /api/captures/{captureId} is 200 with that Capture."""
    client = client_over(settings_factory, store_with(NEWEST, MIDDLE, OLDEST))

    response = client.get(f"{CAPTURES}/{MIDDLE.capture_id}")

    assert response.status_code == 200
    assert response.json() == body_of(MIDDLE)


@pytest.mark.p0
@pytest.mark.parametrize(
    "capture_id",
    [str(uuid.uuid4()), "capture-1"],
    ids=["unknown-uuid4", "not-a-uuid"],
)
def test_an_unknown_capture_id_is_404_not_found(
    settings_factory: SettingsFactory, log_capture: LogCapture, capture_id: str
) -> None:
    """AC-7: GET /api/captures/{captureId} for a CaptureId no Capture holds is 404 `not_found`,
    answered by the Capture route (its template in the request log), not by a missing route.
    """
    client = client_over(settings_factory, store_with(NEWEST))

    response = client.get(f"{CAPTURES}/{capture_id}")

    (line,) = log_capture.request_lines
    assert (line["status"], CAPTURE_ROUTE.fullmatch(line["route"] or "") is not None) == (404, True)
    assert response.json()["error"]["code"] == "not_found"


# Secondary cases (green phase)


@pytest.mark.p1
@pytest.mark.parametrize("path", [CAPTURES, f"{CAPTURES}/{NEWEST.capture_id}"], ids=["list", "one"])
def test_an_unreachable_anki_is_503_on_both_reads(
    settings_factory: SettingsFactory, path: str
) -> None:
    """AC-5 / AC-6: with Anki unreachable both reads are 503 `anki_unavailable`."""
    store = store_with(NEWEST)
    store.available = False
    client = client_over(settings_factory, store)

    response = client.get(path)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "anki_unavailable"


@pytest.mark.p1
def test_a_malformed_capture_id_never_reaches_the_store(
    settings_factory: SettingsFactory,
) -> None:
    """AC-7: `capture-1` is 404 `not_found` before the store is asked (an unreachable store
    would answer 503).
    """
    store = store_with(NEWEST)
    store.available = False
    client = client_over(settings_factory, store)

    response = client.get(f"{CAPTURES}/capture-1")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.p1
@pytest.mark.parametrize("path", [CAPTURES, f"{CAPTURES}/{NEWEST.capture_id}"], ids=["list", "one"])
def test_the_app_built_without_an_injected_store_has_both_read_routes(
    settings_factory: SettingsFactory, path: str
) -> None:
    """AC-5 / AC-6: `create_app(settings)` wires both GET routes over the AnkiConnect store:
    with no Anki listening, each reaches the store and is 503 `anki_unavailable`.
    """
    settings = settings_factory(env={"ANKI_CONNECT_URL": f"http://127.0.0.1:{closed_port()}"})
    client = app_client(create_app(settings), settings)

    response = client.get(path)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "anki_unavailable"

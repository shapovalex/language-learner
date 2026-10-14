"""Story 2.1: the AnkiConnect adapter's client and lock (AD-5), against recorded replies.

The client speaks AnkiConnect API v6 through one httpx.AsyncClient, with a 10 s timeout by
default and 120 s for `sync`, and turns every failure into `anki_unavailable`. One
asyncio.Lock wraps every AnkiStore call, and waiting longer than 15 s for it is `anki_busy`.

Nothing reaches a real Anki: the client takes an httpx transport, and these tests pass a
MockTransport that replays tests/fixtures/anki/ (see tests/support/anki_connect.py).
"""

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.errors import ErrorCode
from tests.support.aio import settle, settled
from tests.support.anki_connect import (
    ANKI_CONNECT_VERSION,
    ANKI_URL,
    SYNC_OK,
    AnkiConnectReplay,
    anki_fixture,
    error_reply,
    not_json,
    refused,
    server_error,
    timed_out,
)

DEFAULT_TIMEOUT_S = 10.0
SYNC_TIMEOUT_S = 120.0
LOCK_WAIT_S = 15.0
SHORT_LOCK_WAIT_S = 0.05  # stands in for the 15 s limit, so the test doesn't wait it out


@pytest.mark.p1
@pytest.mark.parametrize(
    ("method", "action", "timeout_s", "expected"),
    [
        ("reachable", "version", DEFAULT_TIMEOUT_S, True),
        ("sync", "sync", SYNC_TIMEOUT_S, None),
    ],
    ids=["reachable", "sync"],
)
def test_store_sends_ankiconnect_v6_with_the_action_timeout(
    method: str, action: str, timeout_s: float, expected: object
) -> None:
    """AC-2: each AnkiStore call is one v6 request, with 10 s by default and 120 s for sync."""
    anki = AnkiConnectReplay({"version": anki_fixture("version")["response"], "sync": SYNC_OK})
    store = AnkiConnectStore(AnkiConnectClient(ANKI_URL, transport=anki.transport), AnkiLock())

    result = settle(getattr(store, method)())

    assert [sent.body for sent in anki.sent] == [
        {"action": action, "version": ANKI_CONNECT_VERSION}
    ]
    assert anki.sent[0].read_timeout == timeout_s
    assert anki.sent[0].url.rstrip("/") == ANKI_URL
    assert result == expected


@pytest.mark.p0
@pytest.mark.parametrize(
    "failure",
    [refused, timed_out, server_error, error_reply, not_json],
    ids=["refused", "timed-out", "http-500", "error-reply", "not-json"],
)
def test_every_ankiconnect_failure_is_anki_unavailable(failure) -> None:
    """AC-3: unreachable, slow, erroring, or unreadable, AnkiConnect is `anki_unavailable`."""
    anki = AnkiConnectReplay(failure=failure)
    client = AnkiConnectClient(ANKI_URL, transport=anki.transport)

    outcome = settle(client.invoke("version"))

    assert getattr(outcome, "code", outcome) == ErrorCode.ANKI_UNAVAILABLE
    assert isinstance(outcome, Exception)
    # The envelope's message is fixed per code (AD-15); AnkiConnect's text never reaches it
    assert "collection is not available" not in str(outcome)


@pytest.mark.p0
def test_a_call_waiting_past_the_lock_limit_is_anki_busy() -> None:
    """AC-4: while the lock is held, an AnkiStore call gives up after the wait as `anki_busy`."""
    anki = AnkiConnectReplay({"version": anki_fixture("version")["response"]})
    lock = AnkiLock(wait_seconds=SHORT_LOCK_WAIT_S)
    store = AnkiConnectStore(AnkiConnectClient(ANKI_URL, transport=anki.transport), lock)

    async def reachable_while_held() -> object:
        async with lock.hold():
            return await settled(store.reachable())

    outcome = settle(reachable_while_held())

    assert getattr(outcome, "code", outcome) == ErrorCode.ANKI_BUSY
    assert anki.sent == []  # it never reached AnkiConnect
    assert AnkiLock().wait_seconds == LOCK_WAIT_S


@pytest.mark.p1
@pytest.mark.parametrize(
    "failure",
    [refused, timed_out, server_error, error_reply, not_json],
    ids=["refused", "timed-out", "http-500", "error-reply", "not-json"],
)
def test_reachable_is_false_for_every_ankiconnect_failure(failure) -> None:
    """AC-3: readiness relies on `reachable()` answering False, not raising, when Anki is down."""
    anki = AnkiConnectReplay(failure=failure)
    store = AnkiConnectStore(AnkiConnectClient(ANKI_URL, transport=anki.transport), AnkiLock())

    outcome = settle(store.reachable())

    assert outcome is False
    assert len(anki.sent) == 1

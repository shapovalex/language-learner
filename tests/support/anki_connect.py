"""AnkiConnect as the tests see it: the recorded fixtures, a replaying httpx transport for the
adapter, and a stub HTTP server for the fixture recorder. Nothing here reaches a real Anki.
"""

import json
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx

ANKI_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "anki"
ANKI_URL = "http://127.0.0.1:8765"  # AnkiConnect's default; only ever a MockTransport here
ANKI_CONNECT_VERSION = 6  # the API version every request carries (architecture Stack)

# What AnkiConnect answers for an action it doesn't know
UNSUPPORTED: dict[str, Any] = {"result": None, "error": "unsupported action"}

type Failure = Callable[[httpx.Request], httpx.Response]
# A reply: the JSON to send, or a function of the parsed request body returning it
type StubReply = Any | Callable[[Any], Any]


def anki_fixture(name: str) -> dict[str, Any]:
    """A recorded exchange from tests/fixtures/anki/: `{"request": ..., "response": ...}`."""
    return json.loads((ANKI_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


# How AnkiConnect can fail, as seen from the adapter (AC-3 of story 2.1)
def refused(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 61] Connection refused", request=request)


def timed_out(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timed out", request=request)


def server_error(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="Internal Server Error")


def error_reply(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"result": None, "error": "collection is not available"})


def not_json(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="<html><body>AnkiConnect</body></html>")


@dataclass(frozen=True)
class SentRequest:
    url: str
    body: Any  # the parsed JSON body
    read_timeout: float | None  # httpx's per-request read timeout, in seconds


class AnkiConnectReplay:
    """An httpx transport that answers each AnkiConnect action from `replies` (or fails every
    request with `failure`) and records what the adapter sent.

    A reply is keyed by the v6 `action`, or by the JSON-RPC `method` of an API v1 request. A
    callable reply is called with the parsed request body, which lets successive polls of one
    method answer differently (see `v1_sync_replies`).

    Pass `.transport` to the client under test; read `.sent` afterwards.
    """

    def __init__(
        self, replies: Mapping[str, StubReply] | None = None, *, failure: Failure | None = None
    ) -> None:
        self.sent: list[SentRequest] = []
        self._replies = dict(replies or {})
        self._failure = failure
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        timeout = request.extensions.get("timeout", {})
        self.sent.append(SentRequest(str(request.url), body, timeout.get("read")))
        if self._failure is not None:
            return self._failure(request)
        key = body.get("action", body.get("method")) if isinstance(body, dict) else None
        reply = self._replies.get(key, UNSUPPORTED)
        return httpx.Response(200, json=reply(body) if callable(reply) else reply)


# API v1 (JSON-RPC) lives beside v6 on the same port (spike 2.2, Q7)
API_V1_PATH = "/api/v1"
# A v1 failure whose `data.type` spike 2.2 didn't record (Q4: offline was never captured)
UNRECORDED_FAILURE_TYPE = "networkError"


def _with_id(response: dict[str, Any], body: Any) -> dict[str, Any]:
    """A recorded JSON-RPC reply carrying the request's own `id`, as a live server answers."""
    return {**response, "id": body.get("id") if isinstance(body, dict) else None}


def v1_sync_replies(polls: list[dict[str, Any]], started: dict[str, Any]) -> dict[str, StubReply]:
    """Replies for v1 `collection.sync` then `operations.get`, polls answered in order.

    The last poll repeats once the list runs out, so a poll that never ends keeps saying so.
    """
    remaining = list(polls)

    def next_poll(body: Any) -> dict[str, Any]:
        reply = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return _with_id(reply, body)

    return {"collection.sync": lambda body: _with_id(started, body), "operations.get": next_poll}


def recorded_v1_sync(label: str) -> dict[str, StubReply]:
    """`v1_sync_replies` replaying tests/fixtures/anki/sync-<label>.json."""
    v1 = anki_fixture(f"sync-{label}")["v1"]
    polls = [exchange["response"] for exchange in v1["operations.get"]]
    return v1_sync_replies(polls, v1["collection.sync"]["response"])


def _poll_in_state(state: str, **extra: Any) -> dict[str, Any]:
    """The recorded normal run's last poll, moved to `state` (with `extra` result keys)."""
    last = anki_fixture("sync-normal")["v1"]["operations.get"][-1]["response"]
    result = {k: v for k, v in last["result"].items() if k not in ("result", "error")}
    return {**last, "result": {**result, "state": state, **extra}}


def synthetic_v1_sync(kind: str) -> dict[str, StubReply]:
    """v1 Sync runs the spike didn't record: `"unrecorded-failure"`, `"never-ends"`, or one that
    stops in `"waitingForUser"` or `"cancelled"`.
    """
    started = anki_fixture("sync-normal")["v1"]["collection.sync"]["response"]
    if kind == "unrecorded-failure":
        error = {"code": 1, "message": "Network error.", "data": {"type": UNRECORDED_FAILURE_TYPE}}
        return v1_sync_replies([_poll_in_state("failed", error=error)], started)
    if kind == "never-ends":
        return v1_sync_replies([_poll_in_state("running")], started)
    if kind in ("waitingForUser", "cancelled"):
        return v1_sync_replies([_poll_in_state(kind)], started)
    raise ValueError(f"unknown synthetic v1 sync: {kind}")


@dataclass(frozen=True)
class StubAnkiConnect:
    url: str  # http://127.0.0.1:<port>
    received: list[Any] = field(default_factory=list)  # parsed JSON bodies, in order


@contextmanager
def run_stub_ankiconnect(replies: Mapping[str, StubReply]) -> Iterator[StubAnkiConnect]:
    """A loopback HTTP server answering AnkiConnect actions from `replies`, for subprocesses
    (the fixture recorder) that can't take a MockTransport. Stops when the block exits.

    A reply is keyed by the v6 `action`, or by the JSON-RPC `method` of an API v1 request. A
    callable reply is called with the parsed request body, which lets one answer `multi` or
    answer successive calls of one action differently.
    """
    stub_replies = dict(replies)
    received: list[Any] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 -- http.server's naming
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
            received.append(body)
            key = body.get("action", body.get("method")) if isinstance(body, dict) else None
            reply = stub_replies.get(key, UNSUPPORTED)
            payload = json.dumps(reply(body) if callable(reply) else reply).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield StubAnkiConnect(f"http://127.0.0.1:{server.server_port}", received)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

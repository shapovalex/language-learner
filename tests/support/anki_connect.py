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

# AnkiConnect's documented reply to a successful `sync`, until spike 2 records one
SYNC_OK: dict[str, Any] = {"result": None, "error": None}
# What AnkiConnect answers for an action it doesn't know
UNSUPPORTED: dict[str, Any] = {"result": None, "error": "unsupported action"}

type Failure = Callable[[httpx.Request], httpx.Response]


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

    Pass `.transport` to the client under test; read `.sent` afterwards.
    """

    def __init__(
        self, replies: Mapping[str, Any] | None = None, *, failure: Failure | None = None
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
        action = body.get("action") if isinstance(body, dict) else None
        return httpx.Response(200, json=self._replies.get(action, UNSUPPORTED))


@dataclass(frozen=True)
class StubAnkiConnect:
    url: str  # http://127.0.0.1:<port>
    received: list[Any] = field(default_factory=list)  # parsed JSON bodies, in order


# A stub reply: the JSON to send, or a function of the request body returning it
type StubReply = Any | Callable[[Any], Any]


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

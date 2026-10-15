"""Record the test fixtures on the host machine, private values replaced (R-05).

Installed with the app as `language-lab-record-fixtures`, so the host machine runs it from the
same wheel:

  language-lab-record-fixtures serve [--port 8787] [--out FILE]
  tailscale status --json | language-lab-record-fixtures status > FILE
  language-lab-record-fixtures anki [--url http://127.0.0.1:8765] > FILE
  language-lab-record-fixtures anki probe --profile PROFILE [--out DIR] [--yes]
  language-lab-record-fixtures anki sync --profile PROFILE --label LABEL [--out DIR] [--yes]

`serve` stands in for the app on its port while the app is stopped, behind `tailscale serve`.
Every page shows whether the browser treats the origin as a secure context, and its button
sends the POST whose forwarded headers are written to FILE (default
tailscale-serve-headers.json in the current folder). It binds 127.0.0.1 only; stop it with
Ctrl-C.

`status` reads `tailscale status --json` on stdin and prints the fixture on stdout.

`anki` sends AnkiConnect one API v6 `version` request and prints the exchange,
`{"request": ..., "response": ...}`, on stdout (tests/fixtures/anki/version.json). Anki must be
open with the AnkiConnect add-on.

`anki probe` and `anki sync` are spike 2.2's recordings, run in a throwaway Anki profile only.
Both first read `getProfiles`, `getActiveProfile` and `modelNames`, and refuse (exit 1, one
stderr line, nothing sent to Anki beyond those reads) when the active profile is not
`--profile` or holds a note type whose name starts with `LanguageLab`. They then touch only
`LLProbe`-prefixed note types, decks, presets and media, and reuse those on a re-run. `probe`
writes one `<action>.json` `{"request", "response"}` per action into `--out` (a repeated action
gets a `-after` or `-initial` suffix) and pauses before `modelFieldAdd` so a dialog in Anki
Desktop can be watched for (`--yes` skips the pause). `sync` writes `sync-<label>.json`: v6
`sync` alone and inside `multi`, and v1 `collection.sync` at `/api/v1` polled with
`operations.get` until it ends or waits for the user, capped at 120 s. It pauses for Enter after
each of the three, so Anki's sync can finish and any dialog be noted before the next starts
(`--yes` skips the pauses). An AnkiConnect error reply, or a v1 endpoint that refuses or doesn't
answer, is recorded, not raised.

`serve` and `status` never write a value as received unless it is known to be harmless: the
tailnet name, logins, display names, addresses, keys and ids become the placeholders the tests
use, and any other header value or status string becomes "redacted". Header names and status
keys are kept, since they are what the recording is for. `anki` prints AnkiConnect's version
reply unchanged: it carries no private values. `probe` and `sync` replace every string that is
exactly a profile name with "LLProbeProfile" (never a part of a longer string), and email
addresses with "redacted@example.com" and the home folder with "/Users/redacted" wherever they
occur, in requests and replies alike. Read the output before committing it. Stdlib only.
"""

import argparse
import base64
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

HEADERS_FILE = Path("tailscale-serve-headers.json")
DEFAULT_PORT = 8787
ECHO_PATH = "/api/_echo"
ANKI_CONNECT_URL = "http://127.0.0.1:8765"  # AnkiConnect's default
ANKI_CONNECT_VERSION = 6
ANKI_TIMEOUT_S = 10.0

# The placeholders the test suite and its fixtures agree on
TAILNET_SUFFIX = "tail1234.ts.net"
TAILNET_HOST = f"mac-mini.{TAILNET_SUFFIX}"
PEER_IP = "100.64.0.2"
SELF_IPS = ["100.101.102.103", "fd7a:115c:a1e0::1234:5678"]
LOGIN = "user@example.com"
DISPLAY_NAME = "Example User"
USER_ID = 1234567890
REDACTED = "redacted"

_TS_NET_NAME = re.compile(r"(?:[a-z0-9-]+\.)+ts\.net", re.IGNORECASE)
# Tailscale's address ranges: CGNAT 100.64.0.0/10 and its ULA prefix
_TAILNET_IPV4 = re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_TAILNET_IPV6 = re.compile(r"\bfd7a:115c:a1e0:[0-9a-f:]*", re.IGNORECASE)

# Headers whose value says how Serve and the browser address the app: kept, minus private parts
_KEPT_VALUES = frozenset(
    {
        "host",
        "x-forwarded-host",
        "x-forwarded-proto",
        "origin",
        "referer",
        "sec-fetch-site",
        "sec-fetch-mode",
        "sec-fetch-dest",
        "content-type",
        "content-length",
    }
)
_HEADER_PLACEHOLDERS = {
    "x-forwarded-for": PEER_IP,
    "x-real-ip": PEER_IP,
    "tailscale-user-login": LOGIN,
    "tailscale-user-name": DISPLAY_NAME,
}


def _scrub_addresses(value: str) -> str:
    value = _TS_NET_NAME.sub(TAILNET_HOST, value)
    value = _TAILNET_IPV4.sub(PEER_IP, value)
    return _TAILNET_IPV6.sub(SELF_IPS[1], value)


def sanitise_headers(headers: dict[str, str]) -> dict[str, str]:
    """Every header name, lowercased, with only the values that are safe to publish."""
    clean = {}
    for raw_name, value in headers.items():
        name = raw_name.lower()
        if name in _HEADER_PLACEHOLDERS:
            clean[name] = _HEADER_PLACEHOLDERS[name]
        elif name in _KEPT_VALUES:
            clean[name] = _scrub_addresses(value)
        else:
            clean[name] = REDACTED
    return clean


def headers_fixture(method: str, path: str, port: int, headers: dict[str, str]) -> dict[str, Any]:
    """The serve-headers fixture for one forwarded request."""
    return {
        "request": {"method": method, "url": f"https://{TAILNET_HOST}{path}"},
        "upstream": f"http://127.0.0.1:{port}",
        "headers": sanitise_headers(headers),
    }


# Status strings that describe the software or its state, not the user
_KEPT_STATUS_STRINGS = frozenset({"Version", "BackendState", "OS"})
_PEER_KEY = "nodekey:0000000000000000000000000000000000000000000000000000000000000002"
_PLACEHOLDER_PEER = {
    "ID": "nGhIjKl2CNTRL",
    "HostName": "iPhone",
    "DNSName": f"iphone.{TAILNET_SUFFIX}.",
    "OS": "iOS",
    "TailscaleIPs": [PEER_IP],
    "Online": True,
}
_PLACEHOLDER_USER = {"ID": USER_ID, "LoginName": LOGIN, "DisplayName": DISPLAY_NAME}


def _dns_name(value: Any) -> Any:
    """The placeholder name, keeping the real value's trailing dot (discovery strips it)."""
    if not isinstance(value, str) or not value:
        return value
    return TAILNET_HOST + ("." if value.endswith(".") else "")


def _scrub_status(key: str, value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if key == "DNSName":
        return _dns_name(value)
    if key == "TailscaleIPs":
        return SELF_IPS if value else value
    if key == "CertDomains":
        return [TAILNET_HOST] if value else value
    if key == "Peer":
        return {_PEER_KEY: _PLACEHOLDER_PEER} if value else value
    if key == "User":
        return {str(USER_ID): _PLACEHOLDER_USER} if value else value
    if isinstance(value, dict):
        return {_scrub_addresses(k): _scrub_status(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_status(key, item) for item in value]
    if isinstance(value, (int, float)):
        return USER_ID if key == "UserID" else 0
    if not value or key in _KEPT_STATUS_STRINGS:
        return value
    return {
        "HostName": "mac-mini",
        "MagicDNSSuffix": TAILNET_SUFFIX,
        "Name": LOGIN,
        "ID": "nAbCdEf1CNTRL",
        "PublicKey": "nodekey:" + "0" * 63 + "1",
    }.get(key, REDACTED)


def sanitise_status(status: dict[str, Any]) -> dict[str, Any]:
    """`tailscale status --json` with its keys and state kept and everything private replaced."""
    return {_scrub_addresses(key): _scrub_status(key, value) for key, value in status.items()}


_PAGE = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tailscale fixture recorder</title>
<style>
  body {{ font: 18px/1.5 system-ui, sans-serif; margin: 2rem; }}
  button {{ font: inherit; padding: 0.75rem 1.25rem; }}
  dt {{ font-weight: 600; margin-top: 1rem; }}
  dd {{ margin: 0; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>Tailscale fixture recorder</h1>
<p>This is not LanguageLab. It stands in for it while the headers are recorded.</p>
<dl>
  <dt>Secure context</dt><dd id="secure"></dd>
  <dt>Origin</dt><dd id="origin"></dd>
  <dt>Recording</dt><dd id="result">Not recorded yet.</dd>
</dl>
<button id="record" type="button">Record headers</button>
<script>
  document.getElementById("secure").textContent = window.isSecureContext ? "yes" : "no";
  document.getElementById("origin").textContent = location.origin;
  document.getElementById("record").addEventListener("click", async () => {{
    const result = document.getElementById("result");
    try {{
      const response = await fetch("{ECHO_PATH}", {{
        method: "POST",
        headers: {{ "content-type": "application/json" }},
        body: "{{}}",
      }});
      const body = await response.json();
      result.textContent = response.ok
        ? "Recorded " + body.headerNames.length + " headers: " + body.headerNames.join(", ")
        : "Failed: HTTP " + response.status;
    }} catch (error) {{
      result.textContent = "Failed: " + error;
    }}
  }});
</script>
</body>
</html>
"""


def _make_handler(out: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content_type: str, body: str) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 -- http.server's naming
            self._send(200, "text/html; charset=utf-8", _PAGE)

        def do_POST(self) -> None:  # noqa: N802 -- http.server's naming
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if self.path != ECHO_PATH:
                self._send(404, "application/json", json.dumps({"recorded": False}))
                return
            # A repeated header is joined, as a proxy would fold it
            received: dict[str, str] = {}
            for name, value in self.headers.items():
                key = name.lower()
                received[key] = f"{received[key]}, {value}" if key in received else value
            fixture = headers_fixture("POST", ECHO_PATH, self.server.server_port, received)
            text = json.dumps(fixture, indent=2) + "\n"
            out.write_text(text, encoding="utf-8")
            print(f"Wrote {out}:\n{text}", flush=True)
            reply = {"recorded": True, "headerNames": list(fixture["headers"])}
            self._send(200, "application/json", json.dumps(reply))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass  # the request line would print the caller's address

    return Handler


def _serve(port: int, out: Path) -> int:
    try:
        server = HTTPServer(("127.0.0.1", port), _make_handler(out))
    except OSError as exc:
        print(
            f"cannot listen on 127.0.0.1:{port} ({exc}); stop language-lab first",
            file=sys.stderr,
        )
        return 1
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Recorder listening on {url} (Ctrl-C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


def _status() -> int:
    try:
        status = json.load(sys.stdin)
    except ValueError as exc:
        print(f"stdin is not JSON ({exc}); pipe `tailscale status --json` in", file=sys.stderr)
        return 1
    if not isinstance(status, dict):
        print("stdin is not a JSON object; pipe `tailscale status --json` in", file=sys.stderr)
        return 1
    print(json.dumps(sanitise_status(status), indent=2))
    return 0


def _anki(url: str) -> int:
    request = {"action": "version", "version": ANKI_CONNECT_VERSION}
    http_request = urllib.request.Request(
        url,
        data=json.dumps(request).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=ANKI_TIMEOUT_S) as reply:
            response = json.loads(reply.read())
    except OSError, ValueError, http.client.HTTPException:
        # OSError: refused, timed out, HTTP errors; ValueError: not JSON; HTTPException: not HTTP
        print(f"cannot reach AnkiConnect at {url}; open Anki with AnkiConnect", file=sys.stderr)
        return 1
    print(json.dumps({"request": request, "response": response}, indent=2))
    return 0


# Spike 2.2: the guarded probe and the sync probe. They touch only LLProbe-prefixed resources.
PROBE_PREFIX = "LLProbe"
PROBE_MODEL = f"{PROBE_PREFIX} Probe"
PROBE_DECK = f"{PROBE_PREFIX}::Study"
PROBE_PRESET = PROBE_PREFIX
PROBE_MEDIA = f"{PROBE_PREFIX}_probe.mp3"
PROBE_MEDIA_BYTES = b"ID3LLProbe"  # Anki stores media without checking it is audio
PROBE_EXTRA_FIELD = f"{PROBE_PREFIX}Extra"
MANAGED_PREFIX = "LanguageLab"  # matches LanguageLab and LanguageLabDev note types (AD-4)
PROFILE_PLACEHOLDER = f"{PROBE_PREFIX}Profile"
EMAIL_PLACEHOLDER = "redacted@example.com"
HOME_PLACEHOLDER = "/Users/redacted"
SYNC_TIMEOUT_S = 120.0  # AD-5's cap for `sync`; also the v1 polling cap
FIELD_ADD_TIMEOUT_S = 120.0  # long enough to answer a dialog Anki may raise
POLL_INTERVAL_S = 1.0
API_V1_PATH = "/api/v1"
V1_TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled", "waitingForUser"})
GUARD_ACTIONS = ("getProfiles", "getActiveProfile", "modelNames")
_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class _NoReply(Exception):
    """AnkiConnect did not answer: refused, timed out, not HTTP or not JSON."""


def _post_json(url: str, body: Any, timeout: float) -> Any:
    http_request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=timeout) as reply:
            return json.loads(reply.read())
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise _NoReply(str(exc) or type(exc).__name__) from exc


class _Redactor:
    """Profile names, email addresses and the home folder replaced with placeholders.

    A profile name is replaced only where a string is exactly that name: a short name such as
    `Probe` also occurs inside `LLProbe Probe`, which must stay as it is. Email addresses and the
    home folder are replaced wherever they occur.
    """

    def __init__(self, profile_names: list[str]) -> None:
        self._names = {n for n in profile_names if n}
        self._home = str(Path.home())

    def text(self, value: str) -> str:
        if value in self._names:
            return PROFILE_PLACEHOLDER
        value = _EMAIL.sub(EMAIL_PLACEHOLDER, value)
        if len(self._home) > 1:
            value = value.replace(self._home, HOME_PLACEHOLDER)
        return value

    def __call__(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, dict):
            return {self.text(k) if isinstance(k, str) else k: self(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self(item) for item in value]
        return value


def _result(exchange: dict) -> Any:
    response = exchange["response"]
    return response.get("result") if isinstance(response, dict) else None


class _Probe:
    """One AnkiConnect conversation: v6 requests, the guard, and the fixtures it writes."""

    def __init__(self, url: str, profile: str, out: Path) -> None:
        self.url = url
        self.v1_url = url.rstrip("/") + API_V1_PATH
        self.profile = profile
        self.out = out
        self.redact = _Redactor([profile])
        self._v1_id = 0

    def v6(self, action: str, params: dict[str, Any] | None = None, timeout: float = 0) -> dict:
        request: dict[str, Any] = {"action": action, "version": ANKI_CONNECT_VERSION}
        if params is not None:
            request["params"] = params
        response = _post_json(self.url, request, timeout or ANKI_TIMEOUT_S)
        return {"request": request, "response": response}

    def v1(self, method: str, params: dict[str, Any]) -> dict:
        """A JSON-RPC exchange on /api/v1. Whatever comes back, or doesn't, is the reply."""
        self._v1_id += 1
        request = {"jsonrpc": "2.0", "id": self._v1_id, "method": method, "params": params}
        http_request = urllib.request.Request(
            self.v1_url,
            data=json.dumps(request).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=ANKI_TIMEOUT_S) as reply:
                raw = reply.read()
                status = reply.status
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        except (OSError, http.client.HTTPException) as exc:
            _warn_no_reply(f"v1 {method}")
            return {"request": request, "response": {"noReply": str(exc) or type(exc).__name__}}
        try:
            body: Any = json.loads(raw)
        except ValueError:
            body = raw.decode("utf-8", "replace")
        if status != 200:
            body = {"httpStatus": status, "body": body}
        return {"request": request, "response": body}

    def guard(self) -> tuple[list[dict], str | None]:
        """The read-only exchanges, and why writing must not go ahead (None when it may)."""
        exchanges = [self.v6(action) for action in GUARD_ACTIONS]
        profiles, active, models = (_result(ex) for ex in exchanges)
        names = [p for p in profiles if isinstance(p, str)] if isinstance(profiles, list) else []
        if isinstance(active, str):
            names.append(active)
        self.redact = _Redactor([self.profile, *names])
        if not isinstance(models, list):
            return exchanges, "cannot read the note types (modelNames); nothing written"
        managed = sorted(m for m in models if isinstance(m, str) and m.startswith(MANAGED_PREFIX))
        if managed:
            return exchanges, (
                f"refusing: this profile holds the managed note type {managed[0]!r}; "
                "use a throwaway profile. Nothing written"
            )
        if active != self.profile:
            return exchanges, (
                f"refusing: the active profile is {active!r}, not --profile {self.profile!r}; "
                "nothing written"
            )
        return exchanges, None

    def write(self, name: str, fixture: Any) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        path = self.out / f"{name}.json"
        path.write_text(json.dumps(self.redact(fixture), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path}", flush=True)

    def record(self, name: str, action: str, params: dict | None = None, timeout: float = 0):
        """Send one v6 action, write its fixture, and return its result (None on an error)."""
        exchange = self.v6(action, params, timeout)
        self.write(name, exchange)
        response = exchange["response"]
        if isinstance(response, dict) and response.get("error") is not None:
            print(f"{action}: AnkiConnect error recorded: {self.redact(response['error'])}")
        return _result(exchange)


def _pause(prompt: str, yes: bool) -> None:
    if yes:
        return
    try:
        input(prompt)
    except EOFError:
        print()


def _probe_model(probe: _Probe, models: list[str], yes: bool) -> None:
    if PROBE_MODEL in models:
        print(f"{PROBE_MODEL!r} exists; reusing it (createModel not sent)")
    else:
        probe.record(
            "createModel",
            "createModel",
            {
                "modelName": PROBE_MODEL,
                "inOrderFields": ["Front", "Back"],
                "css": ".card { font-family: sans-serif; }",
                "isCloze": False,
                "cardTemplates": [
                    {
                        "Name": "Card 1",
                        "Front": "{{Front}}",
                        "Back": "{{FrontSide}}<hr id=answer>{{Back}}",
                    }
                ],
            },
        )
    fields = probe.record("modelFieldNames", "modelFieldNames", {"modelName": PROBE_MODEL})
    taken = set(fields) if isinstance(fields, list) else set()
    # A new field on every run, so a re-run shows the dialog (if any) again
    number = 1
    while f"{PROBE_EXTRA_FIELD}{number}" in taken:
        number += 1
    _pause(
        "Next: modelFieldAdd. Watch Anki Desktop for a dialog (answer it and note its wording), "
        "then press Enter to send it... ",
        yes,
    )
    started = time.monotonic()
    probe.record(
        "modelFieldAdd",
        "modelFieldAdd",
        {"modelName": PROBE_MODEL, "fieldName": f"{PROBE_EXTRA_FIELD}{number}", "index": 2},
        timeout=FIELD_ADD_TIMEOUT_S,
    )
    print(f"modelFieldAdd answered after {time.monotonic() - started:.1f} s")
    probe.record("modelFieldNames-after", "modelFieldNames", {"modelName": PROBE_MODEL})
    probe.record("modelTemplates", "modelTemplates", {"modelName": PROBE_MODEL})
    probe.record("modelStyling", "modelStyling", {"modelName": PROBE_MODEL})
    probe.record(
        "updateModelTemplates",
        "updateModelTemplates",
        {
            "model": {
                "name": PROBE_MODEL,
                "templates": {
                    "Card 1": {
                        "Front": "<div class=probe>{{Front}}</div>",
                        "Back": "{{FrontSide}}<hr id=answer>{{Back}}",
                    }
                },
            }
        },
    )
    probe.record(
        "updateModelStyling",
        "updateModelStyling",
        {"model": {"name": PROBE_MODEL, "css": ".card { font-family: serif; }"}},
    )


def _probe_preset(probe: _Probe) -> None:
    current = probe.record("getDeckConfig-initial", "getDeckConfig", {"deck": PROBE_DECK})
    if isinstance(current, dict) and current.get("name") == PROBE_PRESET:
        print(f"{PROBE_DECK!r} already uses preset {PROBE_PRESET!r}; reusing it")
        preset_id = current.get("id")
    else:
        preset_id = probe.record(
            "cloneDeckConfigId", "cloneDeckConfigId", {"name": PROBE_PRESET, "cloneFrom": 1}
        )
    if not isinstance(preset_id, int) or isinstance(preset_id, bool):
        print(f"no {PROBE_PRESET!r} preset id; skipping setDeckConfigId and saveDeckConfig")
        return
    probe.record(
        "setDeckConfigId", "setDeckConfigId", {"decks": [PROBE_DECK], "configId": preset_id}
    )
    before = probe.record("getDeckConfig", "getDeckConfig", {"deck": PROBE_DECK})
    if not isinstance(before, dict) or before.get("name") != PROBE_PRESET:
        # Never save a preset the probe didn't create
        print(f"{PROBE_DECK!r} is not on preset {PROBE_PRESET!r}; saveDeckConfig not sent")
        return
    config = json.loads(json.dumps(before))
    for section in ("new", "rev"):
        if isinstance(config.get(section), dict):
            config[section]["bury"] = False
    config["buryInterdayLearning"] = False
    probe.record("saveDeckConfig", "saveDeckConfig", {"config": config})
    probe.record("getDeckConfig-after", "getDeckConfig", {"deck": PROBE_DECK})


def _probe_actions(probe: _Probe, models: list[str], yes: bool) -> None:
    _probe_model(probe, models, yes)
    probe.record("createDeck", "createDeck", {"deck": PROBE_DECK})
    probe.record("deckNames", "deckNames")
    _probe_preset(probe)
    probe.record(
        "addNote",
        "addNote",
        {
            "note": {
                "deckName": PROBE_DECK,
                "modelName": PROBE_MODEL,
                "fields": {"Front": "LLProbe front", "Back": "LLProbe back"},
                # No allowDuplicate: a re-run records how Anki answers a duplicate (Q6)
                "tags": [PROBE_PREFIX],
            }
        },
    )
    notes = probe.record("findNotes", "findNotes", {"query": f'note:"{PROBE_MODEL}"'})
    probe.record("notesInfo", "notesInfo", {"notes": notes if isinstance(notes, list) else []})
    probe.record(
        "storeMediaFile",
        "storeMediaFile",
        {"filename": PROBE_MEDIA, "data": base64.b64encode(PROBE_MEDIA_BYTES).decode("ascii")},
    )
    probe.record("getMediaFilesNames", "getMediaFilesNames", {"pattern": f"{PROBE_PREFIX}_*"})


def _guarded(probe: _Probe, *, record: bool) -> list[str] | None:
    """Run the guard; the note type names if writing may go ahead, else None (message printed).
    With `record`, the guard's read exchanges are written as fixtures once it passes.
    """
    exchanges, refusal = probe.guard()
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return None
    if record:
        for exchange in exchanges:
            probe.write(exchange["request"]["action"], exchange)
    return [m for m in _result(exchanges[2]) if isinstance(m, str)]


def _anki_probe(url: str, profile: str, out: Path, yes: bool) -> int:
    probe = _Probe(url, profile, out)
    try:
        models = _guarded(probe, record=True)
    except _NoReply:
        print(f"cannot reach AnkiConnect at {url}; open Anki with AnkiConnect", file=sys.stderr)
        return 1
    if models is None:
        return 1
    try:
        _probe_actions(probe, models, yes)
    except _NoReply:
        print(
            f"no reply from AnkiConnect at {url}; answer any open Anki dialog, "
            "then run the probe again",
            file=sys.stderr,
        )
        return 1
    return 0


def _warn_no_reply(exchange: str) -> None:
    print(
        f"{exchange}: no reply, recorded as noReply; answer any open Anki dialog",
        file=sys.stderr,
        flush=True,
    )


def _v6_sync(probe: _Probe, action: str, params: dict | None) -> dict:
    """A v6 exchange whose failure to answer is itself the recording."""
    try:
        return probe.v6(action, params, SYNC_TIMEOUT_S)
    except _NoReply as exc:
        request = {"action": action, "version": ANKI_CONNECT_VERSION}
        if params is not None:
            request["params"] = params
        _warn_no_reply(f"v6 {action}")
        return {"request": request, "response": {"noReply": str(exc)}}


def _v1_state(exchange: dict) -> str | None:
    response = exchange["response"]
    result = response.get("result") if isinstance(response, dict) else None
    if isinstance(result, dict):
        state = result.get("state", result.get("status"))
        return state if isinstance(state, str) else None
    return None


def _sans_id(response: Any) -> Any:
    """A JSON-RPC reply without its `id`, which differs on every poll."""
    return (
        {k: v for k, v in response.items() if k != "id"} if isinstance(response, dict) else response
    )


def _v1_sync(probe: _Probe) -> dict:
    started = probe.v1("collection.sync", {})
    polls: list[dict] = []
    record: dict[str, Any] = {"collection.sync": started, "operations.get": polls}
    response = started["response"]
    result = response.get("result") if isinstance(response, dict) else None
    operation_id = result.get("operationId") if isinstance(result, dict) else None
    if operation_id is None:
        return record  # refused, unanswered or an error: the reply above is the finding
    deadline = time.monotonic() + SYNC_TIMEOUT_S
    count = 0
    while True:
        poll = probe.v1("operations.get", {"operationId": operation_id})
        count += 1
        # Only the polls whose reply changed: a queued/running stretch is one entry
        if not polls or _sans_id(poll["response"]) != _sans_id(polls[-1]["response"]):
            polls.append(poll)
        # A reply without a recognised state is not an end: keep polling until the cap
        if _v1_state(poll) in V1_TERMINAL_STATES:
            break
        if time.monotonic() >= deadline:
            record["timedOutAfterSeconds"] = SYNC_TIMEOUT_S
            break
        time.sleep(POLL_INTERVAL_S)
    record["pollCount"] = count
    return record


_SYNC_PAUSE = (
    "Sent {sent}. Let Anki Desktop's sync finish and note any dialog (answer it), "
    "then press Enter{then}... "
)


def _anki_sync(url: str, profile: str, label: str, out: Path, yes: bool) -> int:
    if not _LABEL.match(label):
        print(f"--label {label!r} must be letters, digits and dashes", file=sys.stderr)
        return 1
    probe = _Probe(url, profile, out)
    try:
        if _guarded(probe, record=False) is None:
            return 1
    except _NoReply:
        print(f"cannot reach AnkiConnect at {url}; open Anki with AnkiConnect", file=sys.stderr)
        return 1
    # One exchange at a time, with a pause after each, so one sync can't confound the next
    print("Sending v6 sync...", flush=True)
    standalone = _v6_sync(probe, "sync", None)
    _pause(_SYNC_PAUSE.format(sent="v6 sync", then=" to send v6 sync inside multi"), yes)
    multi = _v6_sync(
        probe, "multi", {"actions": [{"action": "sync", "version": ANKI_CONNECT_VERSION}]}
    )
    _pause(_SYNC_PAUSE.format(sent="v6 multi[sync]", then=" to send v1 collection.sync"), yes)
    print("Sending v1 collection.sync and polling operations.get (up to 120 s)...", flush=True)
    v1 = _v1_sync(probe)
    probe.write(
        f"sync-{label}", {"label": label, "v6": {"sync": standalone, "multi": multi}, "v1": v1}
    )
    _pause(_SYNC_PAUSE.format(sent="v1 collection.sync", then=" to finish"), yes)
    return 0


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Record the test fixtures (R-05).")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="record the headers Tailscale Serve forwards")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--out", type=Path, default=HEADERS_FILE)
    commands.add_parser("status", help="sanitise `tailscale status --json` from stdin")
    anki = commands.add_parser(
        "anki",
        help="record AnkiConnect's reply to a version request (or, with probe/sync, spike 2.2)",
    )
    anki.add_argument("--url", default=ANKI_CONNECT_URL)
    anki_commands = anki.add_subparsers(dest="anki_command")
    probe = anki_commands.add_parser(
        "probe", help="record every action Setup uses, in a throwaway profile (writes to Anki)"
    )
    sync = anki_commands.add_parser(
        "sync", help="record v6 sync and v1 collection.sync, in a throwaway profile"
    )
    for sub in (probe, sync):
        sub.add_argument("--url", default=argparse.SUPPRESS)  # also accepted after the verb
        sub.add_argument("--profile", required=True, help="the throwaway profile; must be active")
        sub.add_argument("--out", type=Path, default=Path("."), help="fixture folder")
    probe.add_argument("--yes", action="store_true", help="don't pause before modelFieldAdd")
    sync.add_argument("--yes", action="store_true", help="don't pause between the exchanges")
    sync.add_argument("--label", required=True, help="names the fixture: sync-<label>.json")
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.port, args.out)
    if args.command == "anki":
        if args.anki_command == "probe":
            return _anki_probe(args.url, args.profile, args.out, args.yes)
        if args.anki_command == "sync":
            return _anki_sync(args.url, args.profile, args.label, args.out, args.yes)
        return _anki(args.url)
    return _status()


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()

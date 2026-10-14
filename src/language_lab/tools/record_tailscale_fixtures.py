"""Record the two Tailscale test fixtures on the host machine, private values replaced (R-05).

Installed with the app as `language-lab-record-fixtures`, so the host machine runs it from the
same wheel:

  language-lab-record-fixtures serve [--port 8787] [--out FILE]
  tailscale status --json | language-lab-record-fixtures status > FILE

`serve` stands in for the app on its port while the app is stopped, behind `tailscale serve`.
Every page shows whether the browser treats the origin as a secure context, and its button
sends the POST whose forwarded headers are written to FILE (default
tailscale-serve-headers.json in the current folder). It binds 127.0.0.1 only; stop it with
Ctrl-C.

`status` reads `tailscale status --json` on stdin and prints the fixture on stdout.

Neither writes a value as received unless it is known to be harmless: the tailnet name, logins,
display names, addresses, keys and ids become the placeholders the tests use, and any other
header value or status string becomes "redacted". Header names and status keys are kept, since
they are what the recording is for. Read the output before committing it. Stdlib only.
"""

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

HEADERS_FILE = Path("tailscale-serve-headers.json")
DEFAULT_PORT = 8787
ECHO_PATH = "/api/_echo"

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


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Record the Tailscale fixtures (R-05).")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="record the headers Tailscale Serve forwards")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--out", type=Path, default=HEADERS_FILE)
    commands.add_parser("status", help="sanitise `tailscale status --json` from stdin")
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.port, args.out)
    return _status()


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()

# Recorded fixtures

Inputs captured from real externals, replayed by tests so nothing reaches them (architecture Testing convention).

| File | What it is | Used by |
| --- | --- | --- |
| `tailscale-status.json` | `tailscale status --json` on the Mac Mini | `tests/unit/test_tailscale_discovery.py` |
| `tailscale-serve-headers.json` | The request headers Tailscale Serve forwards to `127.0.0.1:8787` for a browser `POST` | `tests/api/test_host_origin_allow_list.py` |

## Synthetic until recorded (R-05)

Both Tailscale files are **synthetic**. They were written from Tailscale's documented formats on 2026-10-11, because the Mac Mini recordings weren't available yet.
Replace them with real recordings before entry 10 (device acceptance), keeping the tailnet name `mac-mini.tail1234.ts.net` or updating `TAILNET_HOST` in `tests/support/hosts.py` to match.

Recording, on the Mac Mini:

```bash
tailscale status --json > tests/fixtures/tailscale-status.json
# Headers: start the app, run `tailscale serve --bg 8787`, then POST from a tailnet browser and
# copy the request headers the app received (a temporary echo route or a debug log line).
```

Strip anything you don't want committed (peer names, login) before saving.
Under the Q1 rule (both `Host` and `X-Forwarded-Host` must be allowed), the tests pass whether Serve keeps the public `Host` or rewrites it to loopback.

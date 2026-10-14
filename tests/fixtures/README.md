# Recorded fixtures

Inputs captured from real externals, replayed by tests so nothing reaches them (architecture Testing convention).

| File | What it is | Used by |
| --- | --- | --- |
| `tailscale-status.json` | `tailscale status --json` on the Mac Mini | `tests/unit/test_tailscale_discovery.py` |
| `tailscale-serve-headers.json` | The request headers Tailscale Serve forwards to `127.0.0.1:8787` for a browser `POST` | `tests/api/test_host_origin_allow_list.py` |

## Recorded on the Mac Mini (R-05)

Both Tailscale files were recorded on the Mac Mini on 2026-10-14 during story 1.10 (device acceptance), with Tailscale 1.104.1 and LanguageLab 0.2.1. They replaced synthetic files written from Tailscale's documented formats.

They come from the `language-lab-record-fixtures` command in the wheel, which replaces the tailnet name, logins, display names, addresses, keys and ids with the placeholders the tests use (`mac-mini.tail1234.ts.net`, `user@example.com`, ...). Every other header value and status string is `redacted`. Header names and status keys are as Tailscale sent them.

What the recording showed: Tailscale Serve keeps the tailnet name in `Host` and sends the same name in `X-Forwarded-Host`, with `X-Forwarded-Proto: https` and the browser's `https://` Origin. It also adds `Tailscale-User-Login`, `Tailscale-User-Name`, `Tailscale-User-Profile-Pic` and `Tailscale-Headers-Info`.

To record them again, on the host machine, with `WHEEL` set to the release asset URL:

```bash
# Stop language-lab, then:
uvx --from "$WHEEL" language-lab-record-fixtures serve
# open https://<tailnet>/ in a tailnet browser and press "Record headers"; Ctrl-C to stop
tailscale status --json | uvx --from "$WHEEL" language-lab-record-fixtures status > tailscale-status.json
```

Read both files before committing them.

# Remote access

The server binds to `127.0.0.1` only, so nothing on your network can reach it directly. To use
it from an iPhone, iPad or another computer, put it behind
[Tailscale Serve](https://tailscale.com/kb/1312/serve). Serve gives it a private HTTPS address on
your tailnet, and browsers only allow microphone access over HTTPS.

Tailscale must be installed and logged in on the host machine and on every device you want to
use.

## Tailscale Serve command

Run this once on the host machine:

```sh
tailscale serve --bg 8787
```

It proxies HTTPS on the machine's tailnet name to the local server, and keeps doing so in the
background, including after a restart. You do not run it again.

Then open the tailnet address on any device logged in to the same tailnet, e.g.
`https://mac-mini.tailnet-name.ts.net/`. The app prints its own address at startup (see
[Install](install.md#what-it-prints)).

## Check or turn off

```sh
tailscale serve status   # show what is being served
tailscale serve reset    # stop serving
```

## macOS CLI path

On macOS, if `tailscale` is not on your `PATH`, use the CLI inside the app:

```sh
/Applications/Tailscale.app/Contents/MacOS/Tailscale serve --bg 8787
```

## Allowed hosts

The app only accepts requests addressed to `127.0.0.1:<port>`, `localhost:<port>`, or its tailnet
name. Any other host gets `403 Forbidden`.

It finds its tailnet name at startup from `tailscale status --json`, looking for `tailscale` on
your `PATH` and then at the macOS path above. If that fails (Tailscale not running, logged out,
or a CLI somewhere else), the "On your tailnet" line is missing from the startup output and the
tailnet address answers `403 Forbidden`. Set the name yourself and restart: add this line to the
[configuration file](configuration.md). It is a line for that file, not a command.
`mac-mini.tailnet-name.ts.net` is a placeholder; replace it with your machine's own tailnet name.

```dotenv
LANGUAGE_LAB_PUBLIC_HOST=mac-mini.tailnet-name.ts.net
```

## Changing the port

`tailscale serve` must point at the port the app listens on. If you set `LANGUAGE_LAB_PORT` to
something other than `8787`, run `tailscale serve reset` and then `tailscale serve --bg` with
the new port.

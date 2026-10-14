"""Story 2.1: `language-lab-record-fixtures anki` records AnkiConnect's version exchange.

The recorder ships in the wheel because the Mac Mini runs wheels only. There, with Anki open,
`language-lab-record-fixtures anki > tests/fixtures/anki/version.json` replaces the synthetic
fixture the adapter tests replay. Spike 2.2 extends the same subcommand to every action the
epic uses.

Decided 2026-10-14: it prints `{"request": ..., "response": ...}` on stdout, the way `status`
does, against `--url` (default http://127.0.0.1:8765). The `serve` and `status` subcommands
keep their Tailscale behavior (tests/integration/test_record_tailscale_fixtures.py, unchanged).
"""

import json
import subprocess

import pytest

from tests.support.anki_connect import anki_fixture, run_stub_ankiconnect
from tests.support.live_server import closed_port
from tests.support.recorder import RECORDER_COMMAND, run_recorder_anki


@pytest.mark.p2
def test_record_fixtures_anki_prints_the_version_exchange() -> None:
    """AC-7: the output is the fixture the adapter tests replay, from one v6 version call."""
    recorded = anki_fixture("version")

    with run_stub_ankiconnect({"version": recorded["response"]}) as anki:
        run = run_recorder_anki(anki.url)

    assert run.returncode == 0
    assert json.loads(run.stdout) == recorded
    assert anki.received == [recorded["request"]]
    assert "Traceback" not in run.stderr


@pytest.mark.p2
def test_record_fixtures_anki_with_anki_closed_exits_1_naming_the_url() -> None:
    """AC-7: with nothing listening, one stderr line names the URL; no traceback, no stdout."""
    url = f"http://127.0.0.1:{closed_port()}"

    run = run_recorder_anki(url)

    assert run.returncode == 1
    assert run.stdout == ""
    lines = run.stderr.strip().splitlines()
    assert len(lines) == 1
    assert url in lines[0]
    assert "Traceback" not in run.stderr


@pytest.mark.p2
def test_record_fixtures_help_lists_anki() -> None:
    """AC-7: `--help` lists `anki` next to `serve` and `status`."""
    proc = subprocess.run([*RECORDER_COMMAND, "--help"], capture_output=True, text=True, timeout=30)

    assert proc.returncode == 0
    for command in ("serve", "status", "anki"):
        assert command in proc.stdout

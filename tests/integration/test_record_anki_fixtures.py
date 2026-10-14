"""Story 2.1: `language-lab-record-fixtures anki` records AnkiConnect's version exchange.

The recorder ships in the wheel because the Mac Mini runs wheels only. There, with Anki open,
`language-lab-record-fixtures anki > tests/fixtures/anki/version.json` replaces the synthetic
fixture the adapter tests replay. Spike 2.2 extends the same subcommand to every action the
epic uses.

Decided 2026-10-14: it prints `{"request": ..., "response": ...}` on stdout, the way `status`
does, against `--url` (default http://127.0.0.1:8765). The `serve` and `status` subcommands
keep their Tailscale behavior (tests/integration/test_record_tailscale_fixtures.py, unchanged).

Skipped until the subcommand exists. Un-skip it, watch it fail, then implement.
"""

import json

import pytest

from tests.support.anki_connect import anki_fixture, run_stub_ankiconnect
from tests.support.recorder import run_recorder_anki

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.1: un-skip with the recorder's anki subcommand"
)


@RED_PHASE
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

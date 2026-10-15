"""Spike 2.2: `language-lab-record-fixtures anki probe` and `anki sync` against a stub AnkiConnect.

One test per row of the spike's I/O matrix. The real recordings come from the Mac Mini, in a
throwaway profile (runbook: _bmad-output/test-artifacts/spikes/spike-2-2-ankiconnect-findings.md).
Nothing here reaches a real Anki.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from tests.support.anki_connect import run_stub_ankiconnect
from tests.support.live_server import closed_port
from tests.support.recorder import run_recorder_anki_args

PROFILE = "Throwaway Probe"  # the --profile the user names
PRIVATE_PROFILE = "Oleksii Personal"  # another profile on the machine: never reaches a file
PRIVATE_EMAIL = "someone.real@mail.example.org"
PRIVATE_HOME = str(Path.home())
READ_ACTIONS = {"getProfiles", "getActiveProfile", "modelNames"}

# Every action the probe sends, in order, and the fixture each writes
PROBE_FIXTURES = [
    "getProfiles",
    "getActiveProfile",
    "modelNames",
    "createModel",
    "modelFieldNames",
    "modelFieldAdd",
    "modelFieldNames-after",
    "modelTemplates",
    "modelStyling",
    "updateModelTemplates",
    "updateModelStyling",
    "createDeck",
    "deckNames",
    "getDeckConfig-initial",
    "cloneDeckConfigId",
    "setDeckConfigId",
    "getDeckConfig",
    "saveDeckConfig",
    "getDeckConfig-after",
    "addNote",
    "findNotes",
    "notesInfo",
    "storeMediaFile",
    "getMediaFilesNames",
]


def ok(result: Any) -> dict[str, Any]:
    return {"result": result, "error": None}


def _deck_config(name: str, bury: bool) -> dict[str, Any]:
    return {
        "id": 1 if name == "Default" else 1700000000001,
        "name": name,
        "new": {"bury": bury, "perDay": 20},
        "rev": {"bury": bury, "perDay": 200},
        "buryInterdayLearning": bury,
    }


def anki_replies(
    *, models: list[str] | None = None, active: str = PROFILE, **overrides: Any
) -> dict[str, Any]:
    """A throwaway profile as AnkiConnect would show it, one reply per action the probe sends."""
    deck_configs = iter(
        [
            _deck_config("Default", True),  # initial: the deck is on Default
            _deck_config("LLProbe", True),  # before saving
            _deck_config("LLProbe", False),  # after saving
        ]
    )
    replies: dict[str, Any] = {
        "getProfiles": ok([PRIVATE_PROFILE, PROFILE]),
        "getActiveProfile": ok(active),
        "modelNames": ok(models if models is not None else ["Basic", "Cloze"]),
        "createModel": ok({"id": 1700000000100, "name": "LLProbe Probe"}),
        "modelFieldNames": ok(["Front", "Back"]),
        "modelFieldAdd": ok(None),
        "modelTemplates": ok({"Card 1": {"Front": "{{Front}}", "Back": "{{Back}}"}}),
        "modelStyling": ok({"css": ".card {}"}),
        "updateModelTemplates": ok(None),
        "updateModelStyling": ok(None),
        "createDeck": ok(1700000000200),
        "deckNames": ok(["Default", "LLProbe", "LLProbe::Study"]),
        "getDeckConfig": lambda body: ok(next(deck_configs)),
        "cloneDeckConfigId": ok(1700000000001),
        "setDeckConfigId": ok(True),
        "saveDeckConfig": ok(True),
        "addNote": ok(1700000000300),
        "findNotes": ok([1700000000300]),
        "notesInfo": ok(
            [
                {
                    "noteId": 1700000000300,
                    "modelName": "LLProbe Probe",
                    # An email or home path echoed back by Anki must not reach the fixture
                    "fields": {
                        "Front": {"value": f"mail {PRIVATE_EMAIL} at {PRIVATE_HOME}/x"},
                        "Back": {"value": PRIVATE_PROFILE},
                    },
                }
            ]
        ),
        "storeMediaFile": ok("LLProbe_probe.mp3"),
        "getMediaFilesNames": ok(["LLProbe_probe.mp3"]),
    }
    replies.update(overrides)
    return replies


def _written(out: Path) -> dict[str, Any]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("*.json"))}


def _sent_actions(received: list[Any]) -> list[str]:
    return [body.get("action", body.get("method")) for body in received]


def _assert_one_line(stderr: str, *needles: str) -> None:
    lines = stderr.strip().splitlines()
    assert len(lines) == 1, stderr
    for needle in needles:
        assert needle in lines[0]
    assert "Traceback" not in stderr


@pytest.mark.p1
def test_probe_in_a_clean_throwaway_profile_writes_one_redacted_fixture_per_action(
    tmp_path: Path,
) -> None:
    """Matrix row 1: one `{request, response}` file per probed action, redacted; exit 0."""
    with run_stub_ankiconnect(anki_replies()) as anki:
        run = run_recorder_anki_args(
            anki.url, "probe", "--profile", PROFILE, "--out", str(tmp_path), "--yes"
        )

    assert run.returncode == 0, run.stderr
    assert "Traceback" not in run.stderr
    written = _written(tmp_path)
    assert sorted(written) == sorted(PROBE_FIXTURES)
    for name, fixture in written.items():
        assert set(fixture) == {"request", "response"}, name
        assert fixture["request"]["version"] == 6
    assert _sent_actions(anki.received) == [
        written[name]["request"]["action"] for name in PROBE_FIXTURES
    ]

    text = "".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.json"))
    assert PROFILE not in text
    assert PRIVATE_PROFILE not in text
    assert PRIVATE_EMAIL not in text
    assert PRIVATE_HOME not in text
    assert written["getActiveProfile"]["response"]["result"] == "LLProbeProfile"
    assert written["getProfiles"]["response"]["result"] == ["LLProbeProfile", "LLProbeProfile"]
    notes_info = json.dumps(written["notesInfo"])
    assert "redacted@example.com" in notes_info
    assert "/Users/redacted/x" in notes_info
    # No allowDuplicate: a re-run records how Anki answers a duplicate note
    assert "options" not in written["addNote"]["request"]["params"]["note"]

    # Only LLProbe resources, and the three bury flags off on the LLProbe preset
    assert written["createModel"]["request"]["params"]["modelName"] == "LLProbe Probe"
    assert written["createDeck"]["request"]["params"]["deck"] == "LLProbe::Study"
    assert written["cloneDeckConfigId"]["request"]["params"]["name"] == "LLProbe"
    saved = written["saveDeckConfig"]["request"]["params"]["config"]
    assert saved["name"] == "LLProbe"
    assert (saved["new"]["bury"], saved["rev"]["bury"], saved["buryInterdayLearning"]) == (
        False,
        False,
        False,
    )
    assert written["storeMediaFile"]["request"]["params"]["filename"] == "LLProbe_probe.mp3"


@pytest.mark.p1
def test_probe_reuses_llprobe_resources_on_a_rerun(tmp_path: Path) -> None:
    """Re-runnable: an existing LLProbe note type and preset are reused, not created again."""
    configs = iter([_deck_config("LLProbe", False)] * 3)
    replies = anki_replies(
        models=["Basic", "LLProbe Probe"],
        modelFieldNames=ok(["Front", "Back", "LLProbeExtra1"]),
        getDeckConfig=lambda body: ok(next(configs)),
    )
    with run_stub_ankiconnect(replies) as anki:
        run = run_recorder_anki_args(
            anki.url, "probe", "--profile", PROFILE, "--out", str(tmp_path), "--yes"
        )

    assert run.returncode == 0, run.stderr
    sent = _sent_actions(anki.received)
    assert "createModel" not in sent
    assert "cloneDeckConfigId" not in sent
    added = _written(tmp_path)["modelFieldAdd"]["request"]["params"]["fieldName"]
    assert added == "LLProbeExtra2"


@pytest.mark.p0
def test_redaction_replaces_only_whole_profile_names(tmp_path: Path) -> None:
    """Loop 1: with the runbook's `--profile Probe`, `LLProbe Probe` must survive unchanged."""
    replies = anki_replies(
        active="Probe",
        getProfiles=ok(["Probe", PRIVATE_PROFILE]),
        notesInfo=ok([{"modelName": "LLProbe Probe", "fields": {"Front": {"value": "Probe"}}}]),
    )
    with run_stub_ankiconnect(replies) as anki:
        run = run_recorder_anki_args(
            anki.url, "probe", "--profile", "Probe", "--out", str(tmp_path), "--yes"
        )

    assert run.returncode == 0, run.stderr
    written = _written(tmp_path)
    assert written["getActiveProfile"]["response"]["result"] == "LLProbeProfile"
    assert written["getProfiles"]["response"]["result"] == ["LLProbeProfile", "LLProbeProfile"]
    assert written["createModel"]["request"]["params"]["modelName"] == "LLProbe Probe"
    assert written["createDeck"]["request"]["params"]["deck"] == "LLProbe::Study"
    info = written["notesInfo"]["response"]["result"][0]
    assert info["modelName"] == "LLProbe Probe"
    assert info["fields"]["Front"]["value"] == "LLProbeProfile"
    assert "LLLLProbe" not in "".join(p.read_text(encoding="utf-8") for p in tmp_path.iterdir())


@pytest.mark.p1
def test_probe_no_reply_after_the_guard_says_to_answer_a_dialog(tmp_path: Path) -> None:
    """Loop 1: a request left unanswered after the guard names the URL and any open dialog."""

    def hang_up(body: Any) -> Any:
        raise ConnectionAbortedError("the stub closes the connection without a reply")

    with run_stub_ankiconnect(anki_replies(modelFieldAdd=hang_up)) as anki:
        run = run_recorder_anki_args(
            anki.url, "probe", "--profile", PROFILE, "--out", str(tmp_path), "--yes"
        )

    assert run.returncode == 1
    _assert_one_line(run.stderr, anki.url, "dialog", "again")
    assert "modelFieldAdd" not in _written(tmp_path)


@pytest.mark.p0
@pytest.mark.parametrize("managed", ["LanguageLab Capture", "LanguageLabDev English Vocabulary"])
@pytest.mark.parametrize("command", [["probe", "--yes"], ["sync", "--label", "normal", "--yes"]])
def test_guard_refuses_a_profile_holding_managed_note_types(
    tmp_path: Path, managed: str, command: list[str]
) -> None:
    """Matrix row 2: exit 1, one stderr line naming the note type, only read actions sent."""
    with run_stub_ankiconnect(anki_replies(models=["Basic", managed])) as anki:
        run = run_recorder_anki_args(
            anki.url, *command[:1], "--profile", PROFILE, "--out", str(tmp_path), *command[1:]
        )

    assert run.returncode == 1
    _assert_one_line(run.stderr, managed)
    assert set(_sent_actions(anki.received)) <= READ_ACTIONS
    assert list(tmp_path.iterdir()) == []


@pytest.mark.p0
@pytest.mark.parametrize("command", [["probe", "--yes"], ["sync", "--label", "normal", "--yes"]])
def test_guard_refuses_when_the_active_profile_is_not_the_named_one(
    tmp_path: Path, command: list[str]
) -> None:
    """Matrix row 3: exit 1, one stderr line naming both profiles, only read actions sent."""
    with run_stub_ankiconnect(anki_replies(active=PRIVATE_PROFILE)) as anki:
        run = run_recorder_anki_args(
            anki.url, *command[:1], "--profile", PROFILE, "--out", str(tmp_path), *command[1:]
        )

    assert run.returncode == 1
    _assert_one_line(run.stderr, PROFILE, PRIVATE_PROFILE)
    assert set(_sent_actions(anki.received)) <= READ_ACTIONS
    assert list(tmp_path.iterdir()) == []


@pytest.mark.p1
def test_probe_records_an_action_error_and_carries_on(tmp_path: Path) -> None:
    """Matrix row 4: the error reply is the fixture; the probe continues and exits 0."""
    error = {"result": None, "error": "unsupported action"}
    with run_stub_ankiconnect(anki_replies(modelFieldAdd=error)) as anki:
        run = run_recorder_anki_args(
            anki.url, "probe", "--profile", PROFILE, "--out", str(tmp_path), "--yes"
        )

    assert run.returncode == 0, run.stderr
    written = _written(tmp_path)
    assert written["modelFieldAdd"]["response"] == error
    assert "getMediaFilesNames" in written


@pytest.mark.p1
def test_sync_records_v6_and_v1_exchanges(tmp_path: Path) -> None:
    """Matrix row 5: sync-L.json holds v6 sync alone and in multi, and v1 sync plus polls."""
    states = iter(["running", "running", "succeeded"])

    def operation(body: dict[str, Any]) -> dict[str, Any]:
        state = next(states)
        result: dict[str, Any] = {"operationId": "op-1", "state": state}
        if state == "succeeded":
            result["result"] = {"required": "noChanges", "hostNumber": 3}
        return {"jsonrpc": "2.0", "id": body["id"], "result": result}

    replies = anki_replies(
        sync=ok(None),
        multi=lambda body: ok([{"result": None, "error": f"login for {PRIVATE_EMAIL}"}]),
        **{
            "collection.sync": lambda body: {
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {"operationId": "op-1", "method": "collection.sync", "session": "s"},
            },
            "operations.get": operation,
        },
    )
    with run_stub_ankiconnect(replies) as anki:
        run = run_recorder_anki_args(
            anki.url,
            *("sync", "--profile", PROFILE, "--label", "normal", "--out", str(tmp_path), "--yes"),
        )

    assert run.returncode == 0, run.stderr
    assert [p.name for p in tmp_path.iterdir()] == ["sync-normal.json"]
    fixture = json.loads((tmp_path / "sync-normal.json").read_text(encoding="utf-8"))
    assert fixture["label"] == "normal"
    assert fixture["v6"]["sync"] == {
        "request": {"action": "sync", "version": 6},
        "response": ok(None),
    }
    assert fixture["v6"]["multi"]["request"]["params"] == {
        "actions": [{"action": "sync", "version": 6}]
    }
    assert PRIVATE_EMAIL not in json.dumps(fixture)
    assert fixture["v1"]["collection.sync"]["request"]["method"] == "collection.sync"
    polls = fixture["v1"]["operations.get"]
    # The repeated `running` reply is kept once; polling stops at the terminal state
    assert [p["response"]["result"]["state"] for p in polls] == ["running", "succeeded"]
    assert fixture["v1"]["pollCount"] == 3
    assert _sent_actions(anki.received)[3:] == [
        "sync",
        "multi",
        "collection.sync",
        "operations.get",
        "operations.get",
        "operations.get",
    ]


@pytest.mark.p2
def test_sync_records_a_v1_endpoint_that_refuses(tmp_path: Path) -> None:
    """Decision 2026-10-14: a v1 refusal (e.g. permission) is recorded as the fixture."""
    refusal = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": 1011, "message": "denied", "data": {"type": "authenticationRequired"}},
    }
    replies = anki_replies(sync=ok(None), multi=ok([ok(None)]), **{"collection.sync": refusal})
    with run_stub_ankiconnect(replies) as anki:
        run = run_recorder_anki_args(
            anki.url,
            *("sync", "--profile", PROFILE, "--label", "logged-out", "--out", str(tmp_path)),
            "--yes",
        )

    assert run.returncode == 0, run.stderr
    fixture = json.loads((tmp_path / "sync-logged-out.json").read_text(encoding="utf-8"))
    assert fixture["v1"]["collection.sync"]["response"] == refusal
    assert fixture["v1"]["operations.get"] == []
    assert "operations.get" not in _sent_actions(anki.received)


@pytest.mark.p1
@pytest.mark.parametrize("command", [["probe", "--yes"], ["sync", "--label", "offline", "--yes"]])
def test_anki_down_exits_1_naming_the_url(tmp_path: Path, command: list[str]) -> None:
    """Matrix row 6: nothing on --url gives one stderr line naming it; no traceback."""
    url = f"http://127.0.0.1:{closed_port()}"

    run = run_recorder_anki_args(
        url, *command[:1], "--profile", PROFILE, "--out", str(tmp_path), *command[1:]
    )

    assert run.returncode == 1
    _assert_one_line(run.stderr, url)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.p1
def test_sync_keeps_polling_past_an_unrecognised_reply(tmp_path: Path) -> None:
    """Loop 1: a reply without a known state is not terminal; polling goes on to the end."""
    replies_seen = iter(
        [
            {"jsonrpc": "2.0", "result": {"operationId": "op-1"}},  # no state: unrecognised
            {"jsonrpc": "2.0", "result": "pending"},  # not even an object
            {"jsonrpc": "2.0", "result": {"operationId": "op-1", "state": "waitingForUser"}},
        ]
    )
    replies = anki_replies(
        sync=ok(None),
        multi=ok([ok(None)]),
        **{
            "collection.sync": {"jsonrpc": "2.0", "id": 1, "result": {"operationId": "op-1"}},
            "operations.get": lambda body: {**next(replies_seen), "id": body["id"]},
        },
    )
    with run_stub_ankiconnect(replies) as anki:
        run = run_recorder_anki_args(
            anki.url,
            *("sync", "--profile", PROFILE, "--label", "normal", "--out", str(tmp_path), "--yes"),
        )

    assert run.returncode == 0, run.stderr
    fixture = json.loads((tmp_path / "sync-normal.json").read_text(encoding="utf-8"))
    assert fixture["v1"]["pollCount"] == 3
    assert fixture["v1"]["operations.get"][-1]["response"]["result"]["state"] == "waitingForUser"
    assert "timedOutAfterSeconds" not in fixture["v1"]

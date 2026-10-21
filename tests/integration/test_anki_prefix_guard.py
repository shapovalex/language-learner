"""Story 2.6: the AD-4 Prefix guard inside adapters/anki (NFR-1).

Every request the AnkiConnect client sends passes `PrefixGuard(manifest)` first. A write,
delete, move, preset or media action is sent only when its target is a manifest resource, a
note of a manifest note type, the `<Prefix>` preset, or an AD-7 media name. Anything else raises
`PrefixViolation` before a request leaves the client. An action the guard doesn't know is
treated as a write and rejected (it fails closed), and `multi` is checked action by action.

Targets given by note or card id are looked up first (decided with the user, 2026-10-21): the
guard reads `notesInfo` or `cardsInfo` and lets the write through only when every note belongs
to a manifest note type. A preset given by id must be the config a managed deck already uses.

Nothing reaches a real Anki: the client takes an httpx transport, and these tests replay
through `AnkiConnectReplay` (tests/support/anki_connect.py).
"""

import uuid
from typing import Any

import pytest

from language_lab import app as app_module
from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard, PrefixViolation
from language_lab.adapters.anki.manifest import build_manifest
from language_lab.domain.errors import AppError
from tests.support.aio import settle
from tests.support.anki_connect import (
    ANKI_URL,
    AnkiConnectReplay,
    anki_fixture,
    run_stub_ankiconnect,
)
from tests.support.fixtures.settings import SettingsFactory

RELEASE = "LanguageLab"
DEV = "LanguageLabDev"
OK_NULL = {"result": None, "error": None}

STUDY_LEAF = f"{RELEASE}::Study::English::Vocabulary::Understand"
CAPTURES = f"{RELEASE}::Captures"
VOCABULARY = f"{RELEASE} English Vocabulary"


def media_name(prefix: str = RELEASE) -> str:
    """An AD-7 managed media name: `<Prefix>_<ItemId>_<sha256[:12]>.mp3`."""
    return f"{prefix}_{uuid.uuid4()}_{uuid.uuid4().hex[:12]}.mp3"


# (action, params) the guard must let through for the LanguageLab Prefix
ALLOWED: list[tuple[str, dict[str, Any]]] = [
    ("deckNames", {}),
    ("createDeck", {"deck": STUDY_LEAF}),
    ("createDeck", {"deck": RELEASE}),
    ("createModel", {"modelName": f"{RELEASE} Capture", "inOrderFields": ["Text"]}),
    ("modelFieldAdd", {"modelName": VOCABULARY, "fieldName": "Extra"}),
    ("updateModelTemplates", {"model": {"name": VOCABULARY, "templates": {}}}),
    ("updateModelStyling", {"model": {"name": f"{RELEASE} French Sentence", "css": ""}}),
    ("cloneDeckConfigId", {"name": RELEASE, "cloneFrom": 1}),
    ("setDeckConfigId", {"decks": [f"{RELEASE}::Study", STUDY_LEAF], "configId": 1}),
    ("addNote", {"note": {"modelName": VOCABULARY, "deckName": STUDY_LEAF, "fields": {}}}),
    ("storeMediaFile", {"filename": media_name(), "data": ""}),
    ("deleteMediaFile", {"filename": media_name()}),
    ("multi", {"actions": [{"action": "createDeck", "params": {"deck": CAPTURES}}]}),
]

# (action, params) the guard must reject for the LanguageLab Prefix, with nothing sent
REJECTED: list[tuple[str, dict[str, Any]]] = [
    ("createDeck", {"deck": "Default"}),
    ("createDeck", {"deck": f"{DEV}::Study"}),  # the dev Prefix is not under LanguageLab
    ("createDeck", {"deck": f"{RELEASE}::Study::Spanish"}),  # under the Prefix, not managed
    ("createDeck", {"deck": f"{RELEASE}X"}),
    ("deleteDecks", {"decks": [STUDY_LEAF, "Default"], "cardsToo": True}),
    ("deleteDecks", {"decks": [RELEASE], "cardsToo": True}),  # takes unmanaged subdecks too
    ("createModel", {"modelName": "Basic", "inOrderFields": ["Front"]}),
    ("createModel", {"modelName": f"{DEV} Capture", "inOrderFields": ["Text"]}),
    ("modelFieldAdd", {"modelName": "Basic", "fieldName": "Extra"}),
    ("updateModelTemplates", {"model": {"name": "Basic", "templates": {}}}),
    ("updateModelStyling", {"model": {"name": f"{DEV} English Vocabulary", "css": ""}}),
    ("cloneDeckConfigId", {"name": "My options", "cloneFrom": 1}),
    ("setDeckConfigId", {"decks": [STUDY_LEAF, "Default"], "configId": 1}),
    ("addNote", {"note": {"modelName": "Basic", "deckName": CAPTURES, "fields": {}}}),
    ("addNote", {"note": {"modelName": VOCABULARY, "deckName": "Default", "fields": {}}}),
    (
        "addNote",
        {
            "note": {
                "modelName": VOCABULARY,
                "deckName": STUDY_LEAF,
                "fields": {},
                "audio": [{"url": "https://example.com/a.mp3", "filename": "evil.mp3"}],
            }
        },
    ),
    ("storeMediaFile", {"filename": "pronunciation.mp3", "data": ""}),
    ("storeMediaFile", {"filename": media_name(DEV), "data": ""}),
    ("deleteMediaFile", {"filename": f"{RELEASE}_not-an-item-id_0123456789ab.mp3"}),
    ("multi", {"actions": [{"action": "createDeck", "params": {"deck": "Default"}}]}),
    ("importPackage", {"path": "/tmp/deck.apkg"}),  # a write the guard doesn't know
]


def guarded_client(replay: AnkiConnectReplay, prefix: str = RELEASE) -> Any:
    guard = PrefixGuard(build_manifest(prefix))
    return AnkiConnectClient(ANKI_URL, transport=replay.transport, guard=guard)


def accept_everything(actions: list[str]) -> dict[str, Any]:
    """Replies of `null` for each action, so an allowed write comes back without an error."""
    return {action: OK_NULL for action in actions}


@pytest.mark.p0
def test_guard_rejects_writes_outside_the_prefix_before_sending_anything() -> None:
    """AC-1: only writes to manifest resources, the preset and AD-7 media names are sent."""
    rejected_sent: dict[str, list[Any]] = {}
    for action, params in REJECTED:
        replay = AnkiConnectReplay(accept_everything([action, "createDeck"]))
        outcome = settle(guarded_client(replay).invoke(action, **params))
        assert isinstance(outcome, PrefixViolation), (action, params, outcome)
        rejected_sent[f"{action} {params}"] = replay.sent

    assert {key: sent for key, sent in rejected_sent.items() if sent} == {}
    multi_reply = {"result": [OK_NULL], "error": None}
    for action, params in ALLOWED:
        replay = AnkiConnectReplay(
            {**accept_everything([action]), "multi": multi_reply, "deckNames": OK_NULL}
        )
        outcome = settle(guarded_client(replay).invoke(action, **params))
        assert not isinstance(outcome, Exception), (action, params, outcome)
        assert [sent.body.get("action") for sent in replay.sent] == [action]
    # The same LanguageLabDev write is fine for a LanguageLabDev Prefix: the guard is per Prefix
    replay = AnkiConnectReplay(accept_everything(["createDeck"]))
    dev_write = settle(guarded_client(replay, DEV).invoke("createDeck", deck=f"{DEV}::Study"))
    assert not isinstance(dev_write, Exception)
    rogue = settle(guarded_client(replay, DEV).invoke("createDeck", deck=STUDY_LEAF))
    assert isinstance(rogue, PrefixViolation)


def note_info(note_id: int, model_name: str) -> dict[str, Any]:
    """The recorded `notesInfo` entry, as a note `note_id` of `model_name`."""
    recorded = anki_fixture("notesInfo")["response"]["result"][0]
    return {**recorded, "noteId": note_id, "modelName": model_name, "cards": [note_id + 1]}


def card_info(card_id: int, model_name: str, deck_name: str) -> dict[str, Any]:
    """A `cardsInfo` entry (synthetic: the spike recorded no `cardsInfo`)."""
    return {
        "cardId": card_id,
        "note": card_id - 1,
        "modelName": model_name,
        "deckName": deck_name,
        "ord": 0,
        "fields": {},
    }


MANAGED_NOTE, BASIC_NOTE = 1792093018310, 1792093018320
NOTES = {MANAGED_NOTE: VOCABULARY, BASIC_NOTE: "Basic"}
CARDS = {MANAGED_NOTE + 1: (VOCABULARY, STUDY_LEAF), BASIC_NOTE + 1: ("Basic", "Default")}
MANAGED_CARD, BASIC_CARD = MANAGED_NOTE + 1, BASIC_NOTE + 1
UNKNOWN_NOTE = 1792093018999


def lookup_replies(write: str, preset_id: int) -> dict[str, Any]:
    """`notesInfo`/`cardsInfo` answering from NOTES and CARDS, `getDeckConfig` answering the
    managed preset with `preset_id`, and `null` for the write itself.
    """

    def notes_info(body: Any) -> dict[str, Any]:
        ids = body["params"]["notes"]
        notes = [note_info(i, NOTES[i]) if i in NOTES else {} for i in ids]
        return {"result": notes, "error": None}

    def cards_info(body: Any) -> dict[str, Any]:
        ids = body["params"]["cards"]
        return {"result": [card_info(i, *CARDS[i]) for i in ids], "error": None}

    preset = {**anki_fixture("getDeckConfig")["response"]["result"], "id": preset_id}
    return {
        "notesInfo": notes_info,
        "cardsInfo": cards_info,
        "getDeckConfig": {"result": {**preset, "name": RELEASE}, "error": None},
        write: OK_NULL,
    }


LOOKUPS = frozenset({"notesInfo", "cardsInfo", "getDeckConfig"})
PRESET_ID = 1792093018049

# (action, params, allowed): writes whose target is an id the guard has to look up
BY_ID: list[tuple[str, dict[str, Any], bool]] = [
    ("updateNoteFields", {"note": {"id": MANAGED_NOTE, "fields": {"Hint": "h"}}}, True),
    ("updateNoteFields", {"note": {"id": BASIC_NOTE, "fields": {"Front": "f"}}}, False),
    ("updateNoteFields", {"note": {"id": UNKNOWN_NOTE, "fields": {}}}, False),
    ("deleteNotes", {"notes": [MANAGED_NOTE]}, True),
    ("deleteNotes", {"notes": [MANAGED_NOTE, BASIC_NOTE]}, False),
    ("changeDeck", {"cards": [MANAGED_CARD], "deck": CAPTURES}, True),
    ("changeDeck", {"cards": [BASIC_CARD], "deck": CAPTURES}, False),
    ("changeDeck", {"cards": [MANAGED_CARD], "deck": "Default"}, False),
    ("suspend", {"cards": [MANAGED_CARD]}, True),
    ("suspend", {"cards": [MANAGED_CARD, BASIC_CARD]}, False),
    ("saveDeckConfig", {"config": {"id": PRESET_ID, "name": RELEASE}}, True),
    ("saveDeckConfig", {"config": {"id": PRESET_ID + 1, "name": RELEASE}}, False),  # Default's id
    ("saveDeckConfig", {"config": {"id": PRESET_ID, "name": "Default"}}, False),
]


@pytest.mark.p0
def test_guard_looks_up_id_targets_and_sends_the_write_only_for_managed_notes() -> None:
    """AC-2: a write by note, card or preset id is sent only after a lookup shows it managed."""
    writes_sent: dict[str, bool] = {}
    for action, params, _ in BY_ID:
        replay = AnkiConnectReplay(lookup_replies(action, PRESET_ID))
        settle(guarded_client(replay).invoke(action, **params))
        writes_sent[f"{action} {params}"] = action in [s.body["action"] for s in replay.sent]

    assert writes_sent == {f"{action} {params}": allowed for action, params, allowed in BY_ID}
    for action, params, allowed in BY_ID:
        replay = AnkiConnectReplay(lookup_replies(action, PRESET_ID))
        outcome = settle(guarded_client(replay).invoke(action, **params))
        before_write = [s.body["action"] for s in replay.sent][:-1] if allowed else None
        if allowed:
            assert not isinstance(outcome, Exception), (action, params, outcome)
            assert set(before_write) <= LOOKUPS, (action, before_write)
        else:
            assert isinstance(outcome, PrefixViolation), (action, params, outcome)
            assert {s.body["action"] for s in replay.sent} <= LOOKUPS, (action, params)


@pytest.mark.p1
def test_composed_app_client_rejects_an_out_of_prefix_write(
    settings_factory: SettingsFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-1: `create_app` wires the guard, so its client refuses a write outside the Prefix."""
    built: list[AnkiConnectClient] = []

    class Recording(AnkiConnectClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built.append(self)

    monkeypatch.setattr(app_module, "AnkiConnectClient", Recording)
    with run_stub_ankiconnect({"createDeck": OK_NULL}) as anki:
        settings = settings_factory(anki_connect_url=anki.url, anki_prefix=RELEASE)
        app_module.create_app(settings)
        [client] = built

        rogue = settle(client.invoke("createDeck", deck=f"{DEV}::Study"))
        sent_after_rogue = list(anki.received)
        # A managed write goes through Setup's path, so the guard is wired, not the client's
        # read-only default
        managed = settle(client.invoke_setup("createDeck", deck=f"{RELEASE}::Study"))
        sent_after_managed = list(anki.received)
        # Story 2.8: the SetupState gate is wired too, so a feature write isn't sent while the
        # state can't be read as `ready` (this stub answers no reads)
        gated = settle(client.invoke("createDeck", deck=f"{RELEASE}::Study"))
        sent_after_gated = list(anki.received)
        settle(client.aclose())

    assert isinstance(rogue, PrefixViolation)
    assert sent_after_rogue == []
    assert str(rogue).find(DEV) == -1  # no target name (AD-15)
    assert not isinstance(managed, Exception), managed
    assert [body["action"] for body in sent_after_managed] == ["createDeck"]
    assert sent_after_managed[0]["params"] == {"deck": f"{RELEASE}::Study"}
    assert isinstance(gated, AppError)
    assert [body["action"] for body in sent_after_gated].count("createDeck") == 1

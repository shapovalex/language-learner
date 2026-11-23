"""Example audio through the Items API (plan example-audio-card-and-pronunciation-mix).

- **Save.** The `item` part may carry `exampleVoice`, the Draft's Voice. A Vocabulary Save
  whose Example and ExampleRussian both hold text makes the example audio in that Voice when
  the stored Item has none or held another Example; speech runs before the Save, outside the
  Anki lock. A failed synthesis saves the Item without it and answers
  `exampleAudioFailed: true`. A Sentence never asks for example audio.
- **Backfill.** POST /api/items/<lang>/example-audio `{voice, skip}` gives one batch of the
  Language's Vocabulary Items with an Example and its Russian but no example audio that audio,
  answering `{done, failed, remaining}`; a failed Item is counted and skipped (the caller's
  `skip`), and a rerun picks it up.

The app takes the fake AnkiStore and FakeSpeech (tests/fakes/).
"""

import json
import uuid
from typing import Any

import pytest

from language_lab.domain.catalog import Language
from language_lab.domain.errors import ErrorCode
from language_lab.domain.setup import SetupPreview, SetupState
from tests.fakes.anki_store import FakeAnkiStore
from tests.fakes.speech import FakeSpeech
from tests.support.audio import AZURE_KEY, AZURE_REGION, EN_VOICE, MP3, audio_client
from tests.support.fixtures.settings import SettingsFactory
from tests.support.items import SENTENCE, VOCABULARY, content

BACKFILL = "/api/items/{lang}/example-audio"


def save_part(wire: dict[str, Any], item_id: str, voice: str | None = EN_VOICE) -> dict[str, Any]:
    payload = {**wire, "itemId": item_id, "audio": "keep"}
    if voice is not None:
        payload["exampleVoice"] = voice
    return {"item": (None, json.dumps(payload), "application/json")}


def client_for(settings_factory: SettingsFactory, store: FakeAnkiStore, speech: FakeSpeech) -> Any:
    settings = settings_factory(azure_speech_key=AZURE_KEY, azure_speech_region=AZURE_REGION)
    return audio_client(settings, store, speech)


def example_requests(speech: FakeSpeech) -> list[str]:
    return [text for _, _, text in speech.requests]


# ---- Save ---------------------------------------------------------------------------------


@pytest.mark.p0
def test_a_vocabulary_save_with_a_voice_makes_its_example_audio(
    settings_factory: SettingsFactory,
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech()
    client = client_for(settings_factory, store, speech)
    item_id = str(uuid.uuid4())

    response = client.post("/api/items/en", files=save_part(VOCABULARY, item_id))

    assert response.status_code == 200
    assert response.json() == {"itemId": item_id}
    assert speech.requests == [("en-US", EN_VOICE, VOCABULARY["example"])]
    assert store.media[store.example_audio[item_id]] == MP3


@pytest.mark.p0
def test_a_failed_synthesis_saves_the_item_without_example_audio_and_warns(
    settings_factory: SettingsFactory,
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech(error=ErrorCode.TTS_FAILED)
    client = client_for(settings_factory, store, speech)
    item_id = str(uuid.uuid4())

    response = client.post("/api/items/en", files=save_part(VOCABULARY, item_id))

    assert response.status_code == 200
    assert response.json() == {"itemId": item_id, "exampleAudioFailed": True}
    assert store.items[item_id] == (Language.EN, content(VOCABULARY))
    assert item_id not in store.example_audio


@pytest.mark.p0
def test_an_unchanged_example_with_audio_is_not_made_again_and_an_edit_remakes_it(
    settings_factory: SettingsFactory,
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech()
    client = client_for(settings_factory, store, speech)
    item_id = str(uuid.uuid4())
    client.post("/api/items/en", files=save_part(VOCABULARY, item_id))

    client.post("/api/items/en", files=save_part({**VOCABULARY, "hint": "new hint"}, item_id))
    edited = {**VOCABULARY, "example": "Never jump to conclusions."}
    client.post("/api/items/en", files=save_part(edited, item_id))

    assert example_requests(speech) == [VOCABULARY["example"], edited["example"]]


@pytest.mark.p1
def test_an_item_without_example_audio_gets_it_on_its_next_save(
    settings_factory: SettingsFactory,
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech()
    client = client_for(settings_factory, store, speech)
    item_id = str(uuid.uuid4())
    client.post("/api/items/en", files=save_part(VOCABULARY, item_id, voice=None))
    assert speech.requests == []

    client.post("/api/items/en", files=save_part(VOCABULARY, item_id))

    assert example_requests(speech) == [VOCABULARY["example"]]
    assert item_id in store.example_audio


@pytest.mark.p0
@pytest.mark.parametrize(
    "wire",
    [SENTENCE, {**VOCABULARY, "exampleRussian": ""}, {**VOCABULARY, "example": " "}],
    ids=["sentence", "no-example-russian", "blank-example"],
)
def test_no_example_audio_is_requested_without_an_example_card_to_make(
    settings_factory: SettingsFactory, wire: dict[str, Any]
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech()
    client = client_for(settings_factory, store, speech)
    item_id = str(uuid.uuid4())

    response = client.post("/api/items/en", files=save_part(wire, item_id))

    assert response.status_code == 200
    assert response.json() == {"itemId": item_id}
    assert speech.requests == []
    assert item_id not in store.example_audio


# ---- Backfill -----------------------------------------------------------------------------


def seed(store: FakeAnkiStore, count: int, **changes: Any) -> list[str]:
    ids = [str(uuid.uuid4()) for _ in range(count)]
    for n, item_id in enumerate(ids):
        wire = {**VOCABULARY, "example": f"Example {n}.", **changes}
        store.items[item_id] = (Language.EN, content(wire))
    return ids


@pytest.mark.p0
def test_the_backfill_runs_in_batches_until_none_remains(
    settings_factory: SettingsFactory,
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech()
    ids = seed(store, 7)
    seed(store, 1, exampleRussian="")  # no Example card to make: never pending
    store.items[str(uuid.uuid4())] = (Language.EN, content(SENTENCE))
    client = client_for(settings_factory, store, speech)

    first = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE})
    second = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE})
    third = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE})

    assert first.status_code == 200
    assert first.json() == {"done": 5, "failed": 0, "remaining": 2}
    assert second.json() == {"done": 2, "failed": 0, "remaining": 0}
    assert third.json() == {"done": 0, "failed": 0, "remaining": 0}
    assert set(store.example_audio) == set(ids)
    assert len(speech.requests) == 7


@pytest.mark.p0
def test_a_failed_item_is_counted_skipped_and_picked_up_by_a_rerun(
    settings_factory: SettingsFactory,
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech(error=ErrorCode.TTS_FAILED)
    ids = seed(store, 2)
    client = client_for(settings_factory, store, speech)

    failed = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE})
    skipped = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE, "skip": 2})
    speech.error = None
    rerun = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE})

    assert failed.json() == {"done": 0, "failed": 2, "remaining": 0}
    assert skipped.json() == {"done": 0, "failed": 0, "remaining": 0}
    assert rerun.json() == {"done": 2, "failed": 0, "remaining": 0}
    assert set(store.example_audio) == set(ids)


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [{"voice": "xx-XX-NobodyNeural"}, {"voice": ""}, {}, {"voice": EN_VOICE, "skip": -1}],
    ids=["unknown-voice", "blank-voice", "no-voice", "negative-skip"],
)
def test_a_bad_backfill_request_is_refused_before_any_write(
    settings_factory: SettingsFactory, body: dict[str, Any]
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech()
    seed(store, 1)
    client = client_for(settings_factory, store, speech)

    response = client.post(BACKFILL.format(lang="en"), json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert store.example_audio == {}
    assert speech.requests == []


@pytest.mark.p1
def test_the_backfill_is_refused_while_setup_is_not_ready(
    settings_factory: SettingsFactory,
) -> None:
    store, speech = FakeAnkiStore(), FakeSpeech()
    store.preview = SetupPreview(state=SetupState.NEEDS_MIGRATION)
    seed(store, 1)
    client = client_for(settings_factory, store, speech)

    response = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "setup_required"
    assert store.example_audio == {}


@pytest.mark.p0
def test_an_item_not_written_counts_as_neither_done_nor_failed(
    settings_factory: SettingsFactory,
) -> None:
    """An Item gone or edited between the read and its write isn't `failed`: counting it would
    grow the caller's `skip` past a really pending Item.
    """
    store, speech = FakeAnkiStore(), FakeSpeech()
    gone, pending = seed(store, 2)
    client = client_for(settings_factory, store, speech)
    real_store = store.store_example_audio

    async def vanish_first(language: Any, item_id: str, example: str, data: bytes) -> bool:
        if item_id == gone:
            store.items.pop(gone)
        return await real_store(language, item_id, example, data)

    store.store_example_audio = vanish_first  # type: ignore[method-assign]

    response = client.post(BACKFILL.format(lang="en"), json={"voice": EN_VOICE})

    assert response.json() == {"done": 1, "failed": 0, "remaining": 0}
    assert set(store.example_audio) == {pending}

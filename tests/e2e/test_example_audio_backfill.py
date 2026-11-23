"""Example audio backfill on the Items screen, through the running app (plan
example-audio-card-and-pronunciation-mix).

The real app runs on its own live server over a FakeAnkiStore seeded with English Vocabulary
Items that have an Example and its Russian but no example audio, and a FakeSpeech. "Add example
audio" posts batches to /api/items/en/example-audio in the saved Voice (the first listed when
none is saved) and shows the progress until nothing is left. The adapter's half (the Example
card in its deck) is tests/integration/test_anki_example_audio.py.
"""

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from playwright.sync_api import Page, Request, expect

from language_lab.domain.catalog import Language
from language_lab.domain.errors import ErrorCode
from language_lab.settings import Settings
from tests.fakes.anki_store import FakeAnkiStore
from tests.fakes.speech import FakeSpeech
from tests.support import viewports
from tests.support.audio import EN_VOICE
from tests.support.captures_screen import main
from tests.support.items import SENTENCE, VOCABULARY, content
from tests.support.live_server import LiveServer, bind_free_port, run_live_server

PENDING = 7  # more than one batch of five
BACKFILL = "Add example audio"


@dataclass(frozen=True)
class Seeded:
    server: LiveServer
    store: FakeAnkiStore
    speech: FakeSpeech
    pending: list[str]


@pytest.fixture
def seeded() -> Iterator[Seeded]:
    store, speech = FakeAnkiStore(), FakeSpeech()
    pending = [str(uuid.uuid4()) for _ in range(PENDING)]
    for n, item_id in enumerate(pending):
        wire = {**VOCABULARY, "target": f"word {n}", "example": f"Example {n}."}
        store.items[item_id] = (Language.EN, content(wire))
    store.items[str(uuid.uuid4())] = (Language.EN, content(SENTENCE))
    sock = bind_free_port()
    host, port = sock.getsockname()
    settings = Settings(
        host=host,
        port=port,
        azure_speech_key="e2e-azure-key",
        azure_speech_region="e2e-region",
        openrouter_api_key="e2e-openrouter-key",
    )
    with run_live_server(settings, sock, anki_store=store, speech=speech) as server:
        yield Seeded(server, store, speech, pending)


def is_backfill(request: Request) -> bool:
    return request.method == "POST" and request.url.endswith("/api/items/en/example-audio")


def progress(page: Page):
    return main(page).get_by_role("status")


@pytest.mark.p0
@pytest.mark.parametrize("width", ["phone", "desktop"])
def test_the_backfill_adds_example_audio_until_none_is_left(
    page: Page, seeded: Seeded, width: str
) -> None:
    page.set_viewport_size(viewports.ALL[width])
    page.goto(f"{seeded.server.url}/en/items")
    sent: list[dict] = []
    page.on("request", lambda r: sent.append(json.loads(r.post_data)) if is_backfill(r) else None)

    main(page).get_by_role("button", name=BACKFILL, exact=True).click()

    expect(progress(page)).to_have_text(f"Example audio added to {PENDING} Items · 0 left")
    assert set(seeded.store.example_audio) == set(seeded.pending)
    assert {voice for _, voice, _ in seeded.speech.requests} == {EN_VOICE}
    assert sent == [{"voice": EN_VOICE, "skip": 0}] * 2


@pytest.mark.p1
def test_a_failed_item_is_counted_and_a_rerun_picks_it_up(page: Page, seeded: Seeded) -> None:
    page.set_viewport_size(viewports.DESKTOP)
    seeded.speech.error = ErrorCode.TTS_FAILED
    page.goto(f"{seeded.server.url}/en/items")
    button = main(page).get_by_role("button", name=BACKFILL, exact=True)

    button.click()

    expect(progress(page)).to_have_text(
        f"Example audio added to 0 Items · 0 left · {PENDING} couldn't be made"
    )
    seeded.speech.error = None
    button.click()
    expect(progress(page)).to_have_text(f"Example audio added to {PENDING} Items · 0 left")
    assert set(seeded.store.example_audio) == set(seeded.pending)

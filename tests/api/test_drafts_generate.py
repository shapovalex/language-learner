"""Story 4.2: POST /api/drafts/generate, the generated Draft (AD-8, AD-11, AD-13, AD-15; FR-14
to FR-18).

The Make an Item pane sends JSON `{language, category, target, generationContext}`. The drafts
service asks the Llm port for the Category's generated fields and answers **201** with a fresh
ItemId, issued like the blank Draft's (AD-8), and the Draft's ItemContent, flat like the Save's
`item` part: the Target as given (decided 2026-10-22: the model can't change it), nulls as
empty, and an empty mnemonic. Nothing reaches Anki until Save (FR-18).

Invalid input is 422 `validation_failed` before the model is asked. The model's `llm_failed`
and `llm_invalid_output` are 502: an upstream failure, not the server's. The Generation context
is used once: it goes to the model and nowhere else, not the response, not the Save, not Anki,
and not the logs (AD-15).

The model is `FakeLlm` (tests/fakes/llm.py) and Anki the `FakeAnkiStore`.
"""

import json
import re
from typing import Any

import pytest

from tests.fakes.anki_store import FakeAnkiStore
from tests.support.drafts import (
    CONTEXT,
    GENERATE_API,
    GENERATED,
    SENTENCE_TARGET,
    VOCABULARY_TARGET,
    drafted,
    drafts_client,
    fake_llm,
    generate_body,
)
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory

pytestmark = pytest.mark.skip(
    reason="red phase (story 4.2): un-skip with the generated Draft in features/drafts"
)

UUID4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")

DRAFTS = {
    "en-vocabulary": ("en", "vocabulary", VOCABULARY_TARGET),
    "fr-sentence": ("fr", "sentence", SENTENCE_TARGET),
}


@pytest.mark.p0
@pytest.mark.parametrize(("language", "category", "target"), DRAFTS.values(), ids=DRAFTS.keys())
def test_generate_returns_a_draft_with_a_fresh_item_id_and_the_given_target(
    settings_factory: SettingsFactory, language: str, category: str, target: str
) -> None:
    """AC-10: 201 with a fresh lowercase UUIDv4 `itemId` and the generated ItemContent, flat,
    with the given Target; the model was asked once for that Language and Category, and Anki
    (unreachable here) isn't needed.
    """
    llm = fake_llm(GENERATED[category])
    client = drafts_client(settings_factory, FakeAnkiStore(available=False), llm)

    first = client.post(GENERATE_API, json=generate_body(category, language=language))

    assert first.status_code == 201
    second = client.post(GENERATE_API, json=generate_body(category, language=language))
    body = first.json()
    assert UUID4.fullmatch(body.pop("itemId"))
    assert body == drafted(category, target)
    assert second.json()["itemId"] != first.json()["itemId"]
    assert [(str(r[0]), str(r[1]), r[2]) for r in llm.requests] == [
        (language, category, target)
    ] * 2


INVALID: dict[str, Any] = {
    "blank-target": generate_body("vocabulary", target="   "),
    "missing-target": {k: v for k, v in generate_body("vocabulary").items() if k != "target"},
    "unknown-language": generate_body("vocabulary", language="de"),
    "unknown-category": generate_body("vocabulary", category="idiom"),
    "context-not-a-string": generate_body("vocabulary", generationContext=["a", "b"]),
    "not-an-object": [generate_body("vocabulary")],
}


@pytest.mark.p0
@pytest.mark.parametrize("body", INVALID.values(), ids=INVALID.keys())
def test_an_invalid_request_is_validation_failed_and_the_model_is_not_asked(
    settings_factory: SettingsFactory, body: Any
) -> None:
    """AC-11: a blank or missing Target, an unknown Language or Category, a non-string
    Generation context or a body that isn't an object is 422 `validation_failed`, and the model
    is not called.
    """
    llm = fake_llm(GENERATED["vocabulary"])
    client = drafts_client(settings_factory, FakeAnkiStore(), llm)

    response = client.post(GENERATE_API, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert llm.requests == []


@pytest.mark.p1
def test_a_body_that_isnt_json_is_validation_failed(settings_factory: SettingsFactory) -> None:
    """AC-11: a form or text body instead of JSON is 422 `validation_failed`."""
    llm = fake_llm(GENERATED["vocabulary"])
    client = drafts_client(settings_factory, FakeAnkiStore(), llm)

    response = client.post(
        GENERATE_API, content=b"target=jump", headers={"content-type": "text/plain"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert llm.requests == []


@pytest.mark.p1
def test_an_empty_or_absent_generation_context_is_allowed(
    settings_factory: SettingsFactory,
) -> None:
    """AC-10: the Generation context is optional: left out, it reaches the model as ""."""
    llm = fake_llm(GENERATED["vocabulary"])
    client = drafts_client(settings_factory, FakeAnkiStore(), llm)
    body = {k: v for k, v in generate_body("vocabulary").items() if k != "generationContext"}

    response = client.post(GENERATE_API, json=body)

    assert response.status_code == 201
    assert llm.requests[0][3] == ""


@pytest.mark.p0
@pytest.mark.parametrize("code", ["llm_failed", "llm_invalid_output"])
def test_a_failed_generation_is_502_with_its_code(
    settings_factory: SettingsFactory, code: str
) -> None:
    """AC-12: the model's `llm_failed` and `llm_invalid_output` are 502 with their code in the
    AD-15 envelope, and no ItemId.
    """
    client = drafts_client(settings_factory, FakeAnkiStore(), fake_llm(error=code))

    response = client.post(GENERATE_API, json=generate_body("vocabulary"))

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == code
    assert set(error) >= {"code", "message", "requestId"}
    assert "itemId" not in response.json()


@pytest.mark.p0
def test_the_generation_context_reaches_the_model_and_nothing_else(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """AC-13: the Generation context goes to the model, but not into the response, the Save of
    the Draft that follows, the Item in Anki, or any log line (FR-16, AD-15).
    """
    llm = fake_llm(GENERATED["vocabulary"])
    store = FakeAnkiStore()
    client = drafts_client(settings_factory, store, llm)

    generated = client.post(GENERATE_API, json=generate_body("vocabulary"))

    assert llm.requests[0][3] == CONTEXT

    draft = generated.json()
    item = json.dumps({**draft, "audio": "keep"}, ensure_ascii=False)
    saved = client.post("/api/items/en", files={"item": (None, item)})
    assert saved.status_code == 200
    assert CONTEXT not in str(draft)
    assert CONTEXT not in repr(store.items)
    assert CONTEXT not in log_capture.all_text
    assert VOCABULARY_TARGET not in log_capture.all_text

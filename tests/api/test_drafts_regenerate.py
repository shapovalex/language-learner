"""Story 5.2: regeneration through the drafts generation (AD-11; FR-24).

Proposed wire contract: POST /api/drafts/regenerate with JSON {language, category, target}
answers 200 with the Category's full generated model as flat ItemContent, the Target as given,
and no ItemId: the Item keeps its own. Anki is never needed, and model failures are the 502s of
/api/drafts/generate.

The model is `FakeLlm` (tests/fakes/llm.py) and Anki an unreachable `FakeAnkiStore`.
"""

import pytest

from tests.fakes.anki_store import FakeAnkiStore
from tests.support.drafts import (
    CONTEXT,
    GENERATED,
    SENTENCE_TARGET,
    VOCABULARY_TARGET,
    drafted,
    drafts_client,
    fake_llm,
)
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.regenerate_screen import REGENERATE_API


def regenerate_body(category: str = "vocabulary", **overrides: str) -> dict[str, str]:
    return {"language": "en", "category": category, "target": VOCABULARY_TARGET, **overrides}


@pytest.mark.p0
def test_regenerate_returns_the_full_generated_model_without_an_item_id(
    settings_factory: SettingsFactory,
) -> None:
    """[P0] AC-1 the full generated Vocabulary model for the given Target, no ItemId, no Anki."""
    llm = fake_llm(GENERATED["vocabulary"])
    client = drafts_client(settings_factory, FakeAnkiStore(available=False), llm)

    response = client.post(REGENERATE_API, json=regenerate_body())

    assert response.status_code == 200
    body = response.json()
    assert "itemId" not in body
    assert body == drafted("vocabulary", VOCABULARY_TARGET)
    assert [(str(r[0]), str(r[1]), r[2]) for r in llm.requests] == [
        ("en", "vocabulary", VOCABULARY_TARGET)
    ]


@pytest.mark.p1
def test_a_failed_regeneration_is_502_with_the_generation_error_code(
    settings_factory: SettingsFactory,
) -> None:
    """[P1] AC-2 the model's llm_invalid_output (after its one retry) is 502 in the envelope."""
    llm = fake_llm(error="llm_invalid_output")
    client = drafts_client(settings_factory, FakeAnkiStore(available=False), llm)

    response = client.post(REGENERATE_API, json=regenerate_body())

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == "llm_invalid_output"
    assert set(error) >= {"code", "message", "requestId"}
    assert "itemId" not in response.json()
    assert len(llm.requests) == 1


@pytest.mark.p1
def test_a_french_sentence_regenerates_its_full_model(settings_factory: SettingsFactory) -> None:
    """[P1] AC-1 a French Sentence: the Note and Russian meaning, the Target as given."""
    llm = fake_llm(GENERATED["sentence"])
    client = drafts_client(settings_factory, FakeAnkiStore(available=False), llm)

    response = client.post(
        REGENERATE_API,
        json=regenerate_body("sentence", language="fr", target=SENTENCE_TARGET),
    )

    assert response.status_code == 200
    assert response.json() == drafted("sentence", SENTENCE_TARGET)
    assert [(str(r[0]), str(r[1]), r[2]) for r in llm.requests] == [
        ("fr", "sentence", SENTENCE_TARGET)
    ]


@pytest.mark.p1
def test_the_model_unreachable_is_502_llm_failed(settings_factory: SettingsFactory) -> None:
    """[P1] AC-2 the model's llm_failed is 502 in the envelope, no itemId."""
    client = drafts_client(
        settings_factory, FakeAnkiStore(available=False), fake_llm(error="llm_failed")
    )

    response = client.post(REGENERATE_API, json=regenerate_body())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_failed"
    assert "itemId" not in response.json()


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [
        regenerate_body(target="   "),
        regenerate_body(category="phrase"),
        regenerate_body(language="xx"),
    ],
    ids=["blank-target", "unknown-category", "unknown-language"],
)
def test_an_invalid_request_is_422_and_the_model_is_not_asked(
    settings_factory: SettingsFactory, body: dict[str, str]
) -> None:
    """[P1] AC-1 invalid input is 422 validation_failed before the model is asked."""
    llm = fake_llm(GENERATED["vocabulary"])
    client = drafts_client(settings_factory, FakeAnkiStore(available=False), llm)

    response = client.post(REGENERATE_API, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert llm.requests == []


@pytest.mark.p1
def test_the_target_and_generation_context_are_not_logged(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """[P1] AC-1 the Generation context reaches the model; neither it nor the Target is logged."""
    llm = fake_llm(GENERATED["vocabulary"])
    client = drafts_client(settings_factory, FakeAnkiStore(available=False), llm)

    response = client.post(REGENERATE_API, json=regenerate_body(generationContext=CONTEXT))

    assert response.status_code == 200
    assert llm.requests[0][3] == CONTEXT
    assert CONTEXT not in str(response.json())
    assert CONTEXT not in log_capture.all_text
    assert VOCABULARY_TARGET not in log_capture.all_text

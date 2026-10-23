"""Story 5.2: regeneration through the drafts generation (AD-11; FR-24).

Proposed wire contract: POST /api/drafts/regenerate with JSON {language, category, target}
answers 200 with the Category's full generated model as flat ItemContent, the Target as given,
and no ItemId: the Item keeps its own. Anki is never needed, and model failures are the 502s of
/api/drafts/generate.

Activate only the current task's skip marker to observe RED before implementation. The model is
`FakeLlm` (tests/fakes/llm.py) and Anki an unreachable `FakeAnkiStore`.
"""

import pytest

from tests.fakes.anki_store import FakeAnkiStore
from tests.support.drafts import (
    GENERATED,
    VOCABULARY_TARGET,
    drafted,
    drafts_client,
    fake_llm,
)
from tests.support.fixtures.settings import SettingsFactory
from tests.support.regenerate_screen import REGENERATE_API

pytestmark = pytest.mark.skip(reason="ATDD 5.2: regeneration is not implemented")


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

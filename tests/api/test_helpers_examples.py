"""Target helpers RED: the CEFR example sentences route (plan
target-grammar-check-and-cefr-examples; I/O matrix M-3..M-6).

Provider endpoint: NEW POST /api/helpers/examples with JSON {language, target, context?}
answers 200 `{levels: [{level, sentences: [{sentence, russian}] × 5}] × 6}`, A1 to C2 in order.
Invalid input is 422 `validation_failed` before the model is asked; the model's `llm_failed` /
`llm_invalid_output` (a malformed set after its one retry) is 502 in the error envelope. The
context is used once: passed to the model, never echoed, stored or logged. Anki is never needed.

The model is `FakeLlm` (tests/fakes/llm.py) and Anki an unreachable `FakeAnkiStore`.
"""

import pytest

from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.helpers import (
    EXAMPLE_SENTENCES,
    EXAMPLES,
    EXAMPLES_API,
    EXAMPLES_CONTEXT,
    EXAMPLES_TARGET,
    LEVELS,
    examples_body,
    helpers_client,
    helpers_llm,
)


@pytest.mark.p0
def test_examples_are_six_levels_a1_to_c2_of_five_sentences(
    settings_factory: SettingsFactory,
) -> None:
    """[P0] M-3 a French Target: 200 with the six CEFR levels in order, five sentences each,
    every one with its Russian; the model asked once with the Language, Target and context.
    """
    llm = helpers_llm(examples=EXAMPLES)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLES_API, json=examples_body(context=EXAMPLES_CONTEXT))

    assert response.status_code == 200
    body = response.json()
    assert [group["level"] for group in body["levels"]] == LEVELS
    assert [len(group["sentences"]) for group in body["levels"]] == [5] * 6
    assert body == EXAMPLES
    assert [(str(r[0]), r[1], r[2]) for r in llm.example_requests] == [
        ("fr", EXAMPLES_TARGET, EXAMPLES_CONTEXT)
    ]
    assert llm.requests == []


@pytest.mark.p1
def test_the_context_is_optional(settings_factory: SettingsFactory) -> None:
    """[P1] M-3 a request with no context answers the same six levels; the model gets no
    context.
    """
    llm = helpers_llm(examples=EXAMPLES)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLES_API, json=examples_body())

    assert response.status_code == 200
    assert response.json() == EXAMPLES
    assert len(llm.example_requests) == 1
    assert not llm.example_requests[0][2].strip()


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [
        examples_body(target="   "),
        examples_body(language="xx"),
        {"language": "fr"},
    ],
    ids=["blank-target", "unknown-language", "target-missing"],
)
def test_an_invalid_request_is_422_and_the_model_is_not_asked(
    settings_factory: SettingsFactory, body: dict[str, str]
) -> None:
    """[P1] M-5 invalid input is 422 validation_failed before the model is asked."""
    llm = helpers_llm(examples=EXAMPLES)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLES_API, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert llm.example_requests == []


@pytest.mark.p1
@pytest.mark.parametrize("code", ["llm_failed", "llm_invalid_output"])
def test_a_model_failure_is_502_in_the_error_envelope(
    settings_factory: SettingsFactory, code: str
) -> None:
    """[P1] M-4, M-6 the model unreachable (`llm_failed`) or a malformed set after its retry
    (`llm_invalid_output`) is 502 in the error envelope, with no levels.
    """
    llm = helpers_llm(error=code)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLES_API, json=examples_body(context=EXAMPLES_CONTEXT))

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == code
    assert set(error) >= {"code", "message", "requestId"}
    assert "levels" not in response.json()
    assert len(llm.example_requests) == 1


@pytest.mark.p1
def test_the_target_context_and_sentences_are_not_logged(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """[P1] M-3 the context reaches the model but is not echoed; neither it, the Target nor a
    sentence is logged (AD-15, NFR-7).
    """
    llm = helpers_llm(examples=EXAMPLES)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLES_API, json=examples_body(context=EXAMPLES_CONTEXT))

    assert response.status_code == 200
    assert llm.example_requests[0][2] == EXAMPLES_CONTEXT
    assert EXAMPLES_CONTEXT not in str(response.json())
    logged = log_capture.all_text
    assert EXAMPLES_CONTEXT not in logged
    assert EXAMPLES_TARGET not in logged
    assert not [sentence for sentence in EXAMPLE_SENTENCES if sentence in logged]

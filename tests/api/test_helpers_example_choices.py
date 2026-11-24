"""Regenerate example: the example-choices route (plan regenerate-example-choices).

POST /api/helpers/example-choices with JSON {language, target, context?, meaning?} answers 200
`{sentences: [{sentence, russian}] × 10}`. Invalid input is 422 `validation_failed` before the
model is asked; the model's `llm_failed` / `llm_invalid_output` is 502 in the error envelope.
The context is used once: passed to the model, never echoed, stored or logged. Anki is never
needed.

The model is `FakeLlm` (tests/fakes/llm.py) and Anki an unreachable `FakeAnkiStore`.
"""

import pytest

from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.helpers import (
    CHOICE_SENTENCES,
    CHOICES_CONTEXT,
    CHOICES_MEANING,
    EXAMPLE_CHOICES,
    EXAMPLE_CHOICES_API,
    EXAMPLES_TARGET,
    choices_body,
    helpers_client,
    helpers_llm,
)


@pytest.mark.p0
def test_example_choices_are_ten_pairs_asked_with_the_context_and_meaning(
    settings_factory: SettingsFactory,
) -> None:
    """[P0] 200 with ten sentence/Russian pairs; the model asked once with the Language,
    Target, context and the Item's Russian meaning.
    """
    llm = helpers_llm(choices=EXAMPLE_CHOICES)
    client = helpers_client(settings_factory, llm)

    response = client.post(
        EXAMPLE_CHOICES_API,
        json=choices_body(context=CHOICES_CONTEXT, meaning=CHOICES_MEANING),
    )

    assert response.status_code == 200
    assert response.json() == EXAMPLE_CHOICES
    assert len(response.json()["sentences"]) == 10
    assert [(str(r[0]), r[1], r[2], r[3]) for r in llm.choice_requests] == [
        ("fr", EXAMPLES_TARGET, CHOICES_CONTEXT, CHOICES_MEANING)
    ]
    assert llm.requests == []
    assert llm.example_requests == []


@pytest.mark.p1
def test_the_context_and_meaning_are_optional(settings_factory: SettingsFactory) -> None:
    """[P1] a request with no context or meaning answers the same; the model gets neither."""
    llm = helpers_llm(choices=EXAMPLE_CHOICES)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLE_CHOICES_API, json=choices_body())

    assert response.status_code == 200
    assert response.json() == EXAMPLE_CHOICES
    [(_, _, context, meaning)] = llm.choice_requests
    assert (context, meaning) == ("", "")


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [
        choices_body(target="   "),
        choices_body(language="xx"),
        {"language": "fr"},
    ],
    ids=["blank-target", "unknown-language", "target-missing"],
)
def test_an_invalid_request_is_422_and_the_model_is_not_asked(
    settings_factory: SettingsFactory, body: dict[str, str]
) -> None:
    """[P1] invalid input is 422 validation_failed before the model is asked."""
    llm = helpers_llm(choices=EXAMPLE_CHOICES)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLE_CHOICES_API, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert llm.choice_requests == []


@pytest.mark.p1
@pytest.mark.parametrize("code", ["llm_failed", "llm_invalid_output"])
def test_a_model_failure_is_502_in_the_error_envelope(
    settings_factory: SettingsFactory, code: str
) -> None:
    """[P1] the model unreachable or invalid twice is 502 in the error envelope."""
    llm = helpers_llm(error=code)
    client = helpers_client(settings_factory, llm)

    response = client.post(EXAMPLE_CHOICES_API, json=choices_body(context=CHOICES_CONTEXT))

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == code
    assert set(error) >= {"code", "message", "requestId"}
    assert "sentences" not in response.json()
    assert len(llm.choice_requests) == 1


@pytest.mark.p1
def test_the_target_context_and_sentences_are_not_logged(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """[P1] the context reaches the model but is not echoed; neither it, the Target, the
    meaning nor a sentence is logged (AD-15, NFR-7).
    """
    llm = helpers_llm(choices=EXAMPLE_CHOICES)
    client = helpers_client(settings_factory, llm)

    response = client.post(
        EXAMPLE_CHOICES_API,
        json=choices_body(context=CHOICES_CONTEXT, meaning=CHOICES_MEANING),
    )

    assert response.status_code == 200
    assert llm.choice_requests[0][2] == CHOICES_CONTEXT
    assert CHOICES_CONTEXT not in str(response.json())
    logged = log_capture.all_text
    assert CHOICES_CONTEXT not in logged
    assert CHOICES_MEANING not in logged
    assert EXAMPLES_TARGET not in logged
    assert not [sentence for sentence, _ in CHOICE_SENTENCES if sentence in logged]

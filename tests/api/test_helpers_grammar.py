"""Target helpers RED: the grammar check route (plan target-grammar-check-and-cefr-examples;
I/O matrix M-1, M-2, M-5, M-6).

Provider endpoint: NEW POST /api/helpers/grammar with JSON {language, category, target}
answers 200 `{correct, corrected, explanation}` (the explanation in Russian, `corrected` null
when the Target is correct). Invalid input is 422 `validation_failed` before the model is
asked; the model's `llm_failed` / `llm_invalid_output` is 502 in the error envelope. Anki is
never needed, nothing is stored, and the Target is not logged.

The model is `FakeLlm` (tests/fakes/llm.py) and Anki an unreachable `FakeAnkiStore`.
"""

import pytest

from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.helpers import (
    CORRECT_TARGET,
    GRAMMAR_API,
    GRAMMAR_CORRECT,
    GRAMMAR_INCORRECT,
    INCORRECT_TARGET,
    grammar_body,
    helpers_client,
    helpers_llm,
)

pytestmark = pytest.mark.skip(
    reason="Target helpers RED scaffold: activate when implementing the plan"
)


@pytest.mark.p0
def test_a_correct_target_is_correct_with_no_correction(settings_factory: SettingsFactory) -> None:
    """[P0] M-1 a correct English Vocabulary Target: 200 `{correct: true, corrected: null,
    explanation}`, the model asked once with the request's Language, Category and Target.
    """
    llm = helpers_llm(grammar=GRAMMAR_CORRECT)
    client = helpers_client(settings_factory, llm)

    response = client.post(GRAMMAR_API, json=grammar_body())

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body == GRAMMAR_CORRECT
    assert [(str(r[0]), str(r[1]), r[2]) for r in llm.grammar_requests] == [
        ("en", "vocabulary", CORRECT_TARGET)
    ]
    assert llm.requests == []


@pytest.mark.p0
def test_an_incorrect_target_carries_its_correction_and_explanation(
    settings_factory: SettingsFactory,
) -> None:
    """[P0] M-2 a wrong English Sentence: 200 with `corrected` "He goes to school." and the
    Russian explanation.
    """
    llm = helpers_llm(grammar=GRAMMAR_INCORRECT)
    client = helpers_client(settings_factory, llm)

    response = client.post(
        GRAMMAR_API, json=grammar_body(category="sentence", target=INCORRECT_TARGET)
    )

    assert response.status_code == 200
    assert response.json()["corrected"] == "He goes to school."
    assert response.json() == GRAMMAR_INCORRECT
    assert [(str(r[0]), str(r[1]), r[2]) for r in llm.grammar_requests] == [
        ("en", "sentence", INCORRECT_TARGET)
    ]


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [
        grammar_body(target="   "),
        grammar_body(language="xx"),
        grammar_body(category="phrase"),
        {"language": "en", "category": "vocabulary"},
    ],
    ids=["blank-target", "unknown-language", "unknown-category", "target-missing"],
)
def test_an_invalid_request_is_422_and_the_model_is_not_asked(
    settings_factory: SettingsFactory, body: dict[str, str]
) -> None:
    """[P1] M-5 invalid input is 422 validation_failed before the model is asked."""
    llm = helpers_llm(grammar=GRAMMAR_CORRECT)
    client = helpers_client(settings_factory, llm)

    response = client.post(GRAMMAR_API, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert llm.grammar_requests == []


@pytest.mark.p1
@pytest.mark.parametrize("code", ["llm_failed", "llm_invalid_output"])
def test_a_model_failure_is_502_in_the_error_envelope(
    settings_factory: SettingsFactory, code: str
) -> None:
    """[P1] M-6 the model's `llm_failed` (or `llm_invalid_output` after its retry) is 502 in
    the error envelope, after one call to the port.
    """
    llm = helpers_llm(error=code)
    client = helpers_client(settings_factory, llm)

    response = client.post(GRAMMAR_API, json=grammar_body())

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == code
    assert set(error) >= {"code", "message", "requestId"}
    assert len(llm.grammar_requests) == 1


@pytest.mark.p1
def test_the_target_and_the_verdict_are_not_logged(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """[P1] M-2 neither the Target nor the correction or explanation is logged (AD-15, NFR-7)."""
    client = helpers_client(settings_factory, helpers_llm(grammar=GRAMMAR_INCORRECT))

    response = client.post(
        GRAMMAR_API, json=grammar_body(category="sentence", target=INCORRECT_TARGET)
    )

    assert response.status_code == 200
    logged = log_capture.all_text
    assert INCORRECT_TARGET not in logged
    assert GRAMMAR_INCORRECT["corrected"] not in logged
    assert GRAMMAR_INCORRECT["explanation"] not in logged

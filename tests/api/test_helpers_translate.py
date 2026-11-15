"""Capture and translate: the translation route (plan capture-and-translate; I/O matrix
HAPPY_PATH, BAD_INPUT, TRANSLATE_FAILS).

POST /api/helpers/translate with JSON {language, target} answers 200 `{russian}`. Invalid input
is 422 `validation_failed` before the model is asked; the model's `llm_failed` /
`llm_invalid_output` is 502 in the error envelope. Nothing is stored or logged; Anki is never
needed.
"""

import pytest

from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.helpers import (
    TRANSLATE_API,
    TRANSLATE_TARGET,
    TRANSLATION,
    helpers_client,
    helpers_llm,
    translate_body,
)


@pytest.mark.p0
def test_the_translation_is_the_russian_of_the_text(settings_factory: SettingsFactory) -> None:
    """[P0] HAPPY_PATH: 200 with the Russian; the model asked once with the Language and text."""
    llm = helpers_llm(translation=TRANSLATION)
    client = helpers_client(settings_factory, llm)

    response = client.post(TRANSLATE_API, json=translate_body())

    assert response.status_code == 200
    assert response.json() == TRANSLATION
    assert [(str(lang), text) for lang, text in llm.translate_requests] == [
        ("fr", TRANSLATE_TARGET)
    ]
    assert llm.requests == []


@pytest.mark.p1
def test_english_is_passed_through(settings_factory: SettingsFactory) -> None:
    """[P1] an English request reaches the model as English."""
    llm = helpers_llm(translation=TRANSLATION)
    client = helpers_client(settings_factory, llm)

    response = client.post(TRANSLATE_API, json=translate_body(language="en"))

    assert response.status_code == 200
    assert str(llm.translate_requests[0][0]) == "en"


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [
        translate_body(target="   "),
        translate_body(language="de"),
        {"language": "fr"},
    ],
    ids=["blank-target", "unknown-language", "target-missing"],
)
def test_an_invalid_request_is_422_and_the_model_is_not_asked(
    settings_factory: SettingsFactory, body: dict[str, str]
) -> None:
    """[P1] BAD_INPUT: 422 validation_failed before the model is asked."""
    llm = helpers_llm(translation=TRANSLATION)
    client = helpers_client(settings_factory, llm)

    response = client.post(TRANSLATE_API, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert llm.translate_requests == []


@pytest.mark.p1
@pytest.mark.parametrize("code", ["llm_failed", "llm_invalid_output"])
def test_a_model_failure_is_502_in_the_error_envelope(
    settings_factory: SettingsFactory, code: str
) -> None:
    """[P1] TRANSLATE_FAILS: the model unreachable or invalid twice is 502, with no Russian."""
    llm = helpers_llm(error=code)
    client = helpers_client(settings_factory, llm)

    response = client.post(TRANSLATE_API, json=translate_body())

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == code
    assert set(error) >= {"code", "message", "requestId"}
    assert "russian" not in response.json()


@pytest.mark.p1
def test_the_text_and_translation_are_not_logged(
    settings_factory: SettingsFactory, log_capture: LogCapture
) -> None:
    """[P1] neither the text nor its translation is logged (AD-15)."""
    llm = helpers_llm(translation=TRANSLATION)
    client = helpers_client(settings_factory, llm)

    response = client.post(TRANSLATE_API, json=translate_body())

    assert response.status_code == 200
    logged = log_capture.all_text
    assert TRANSLATE_TARGET not in logged
    assert TRANSLATION["russian"] not in logged

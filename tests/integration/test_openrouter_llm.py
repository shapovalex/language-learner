"""Story 4.2: the OpenRouter adapter behind the Llm port (AD-1, AD-11, AD-18; addendum A4;
FR-16, FR-17, NFR-8).

`OpenRouterLlm(api_key, models, transport=...)` makes one Chat Completions call per attempt:

- **Request (A4).** POST https://openrouter.ai/api/v1/chat/completions with the key as a Bearer
  token, `models` = OPENROUTER_MODELS in the configured order (OpenRouter's model fallbacks, so
  reordering the list changes the model called, FR-17), a strict `json_schema` response format
  holding the Category's `strict_json_schema()`, and `provider: {require_parameters: true}` so
  only providers honouring the schema are reached. Nothing else in `provider`, and no privacy
  or routing keys: OpenRouter's defaults apply (NFR-8). The messages carry the Target, the
  Language, the Category and the Generation context.
- **Validation (AD-11).** The reply's message content is validated with the Category's
  generated-fields model. Invalid (not JSON, failing the model, a refusal, no choices) is
  retried once with the same request, then `llm_invalid_output`.
- **Failure.** A refused or timed-out connection, an HTTP error status or a non-JSON body is
  `llm_failed` at once: only invalid output is retried (architecture, Deferred).

OpenRouter is `OpenRouterReplay` in tests/support/openrouter.py, with hand-built replies;
story 4.4's acceptance run checks them against a real one.
"""

from typing import Any

import pytest

from language_lab.domain.catalog import Category, Language
from tests.support.aio import settle
from tests.support.captures import code_of
from tests.support.drafts import (
    CONTEXT,
    GENERATED,
    GENERATED_VOCABULARY,
    SENTENCE_TARGET,
    VOCABULARY_TARGET,
)
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.openrouter import (
    API_KEY,
    CHAT_COMPLETIONS,
    OpenRouterReplay,
    Reply,
    answer,
    completion,
    no_choices,
    not_json,
    prompt_text,
    refused,
    status,
    timed_out,
)

MODELS = ["openai/gpt-5.6-luna", "google/gemini-3.5-flash-lite"]
TARGETS = {"vocabulary": VOCABULARY_TARGET, "sentence": SENTENCE_TARGET}
LANGUAGE_NAMES = {"en": "English", "fr": "French"}
CATEGORY_NAMES = {"vocabulary": "Vocabulary", "sentence": "Sentence"}


def openrouter(replay: OpenRouterReplay, models: list[str] = MODELS) -> Any:
    from language_lab.adapters.openrouter import OpenRouterLlm

    return OpenRouterLlm(API_KEY, models, transport=replay.transport)


def generate(llm: Any, category: str = "vocabulary", language: str = "en") -> Any:
    """The outcome of one `generate()`: the generated model, or the exception raised."""
    return settle(llm.generate(Language(language), Category(category), TARGETS[category], CONTEXT))


def strict_schema(category: str) -> dict[str, Any]:
    from language_lab.domain.items import strict_json_schema

    return strict_json_schema(Category(category))


ORDERS = {
    "en-vocabulary": ("openai/gpt-5.6-luna,google/gemini-3.5-flash-lite", "en", "vocabulary"),
    "fr-sentence-reordered": (
        "anthropic/claude-sonnet-4.6, openai/gpt-5.6-luna",
        "fr",
        "sentence",
    ),
}


@pytest.mark.p0
@pytest.mark.parametrize(("configured", "language", "category"), ORDERS.values(), ids=ORDERS.keys())
def test_generate_asks_openrouter_with_the_configured_models_and_a_strict_schema(
    settings_factory: SettingsFactory, configured: str, language: str, category: str
) -> None:
    """AC-5: `models` is OPENROUTER_MODELS in the configured order; the response format is the
    Category's strict JSON Schema; `provider` is only `require_parameters: true` (NFR-8); the
    messages carry the Target, Language, Category and Generation context; the key is Bearer.
    """
    settings = settings_factory(env={"OPENROUTER_MODELS": configured})
    replay = OpenRouterReplay([answer(GENERATED[category])])

    generate(openrouter(replay, settings.openrouter_models), category, language)

    assert replay.sent[0].body["models"] == [m.strip() for m in configured.split(",")]

    sent = replay.sent[0]
    assert sent.url == CHAT_COMPLETIONS
    assert sent.headers["authorization"] == f"Bearer {API_KEY}"
    response_format = sent.body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"] == strict_schema(category)
    assert sent.body["provider"] == {"require_parameters": True}
    assert not {"data_collection", "zdr", "order", "only", "ignore"} & set(sent.body)
    prompt = prompt_text(sent.body)
    assert TARGETS[category] in prompt
    assert CONTEXT in prompt
    assert LANGUAGE_NAMES[language] in prompt
    assert CATEGORY_NAMES[category] in prompt


@pytest.mark.p0
@pytest.mark.parametrize("category", GENERATED)
def test_a_valid_reply_is_the_generated_draft(category: str) -> None:
    """AC-6: a reply that validates is returned as the Category's generated model, after one
    request.
    """
    replay = OpenRouterReplay([answer(GENERATED[category])])

    outcome = generate(openrouter(replay), category)

    assert outcome.model_dump(by_alias=True) == GENERATED[category]

    assert len(replay.sent) == 1


INVALID: dict[str, Reply] = {
    "not-json": completion("Sure! Here is your Draft: {russian: ..."),
    "mnemonic": answer({**GENERATED_VOCABULARY, "mnemonic": "a leap over the facts"}),
    "missing-russian": answer({k: v for k, v in GENERATED_VOCABULARY.items() if k != "russian"}),
    "comma-alternative": answer(
        {**GENERATED_VOCABULARY, "russianAlternatives": ["стекло, которое исчезает"]}
    ),
    "refusal": completion(None),
    "no-choices": no_choices,
}


@pytest.mark.p0
@pytest.mark.parametrize("invalid", INVALID.values(), ids=INVALID.keys())
def test_an_invalid_reply_is_retried_once_then_llm_invalid_output(invalid: Reply) -> None:
    """AC-7: an invalid reply is retried once with the same request, and a second invalid one
    is `llm_invalid_output` after exactly two requests (FR-16).
    """
    replay = OpenRouterReplay([invalid, invalid])

    outcome = generate(openrouter(replay))

    assert code_of(outcome) == "llm_invalid_output"

    assert len(replay.sent) == 2
    assert replay.sent[1].body == replay.sent[0].body


@pytest.mark.p1
def test_a_valid_retry_is_the_generated_draft() -> None:
    """AC-7: an invalid reply followed by a valid one returns the valid one."""
    replay = OpenRouterReplay([INVALID["mnemonic"], answer(GENERATED_VOCABULARY)])

    outcome = generate(openrouter(replay))

    assert outcome.model_dump(by_alias=True) == GENERATED_VOCABULARY
    assert len(replay.sent) == 2


FAILED: dict[str, Reply] = {
    "refused": refused,
    "timed-out": timed_out,
    "unauthorized": status(401),
    "rate-limited": status(429),
    "server-error": status(500),
    "not-json": not_json,
}


@pytest.mark.p0
@pytest.mark.parametrize("failure", FAILED.values(), ids=FAILED.keys())
def test_a_failed_request_is_llm_failed_with_no_retry(failure: Reply) -> None:
    """AC-8: a refused or timed-out connection, an HTTP error status or a non-JSON body is
    `llm_failed` after one request: only invalid output is retried.
    """
    replay = OpenRouterReplay([failure, answer(GENERATED_VOCABULARY)])

    outcome = generate(openrouter(replay))

    assert code_of(outcome) == "llm_failed"

    assert len(replay.sent) == 1


@pytest.mark.p1
@pytest.mark.parametrize(
    "replies",
    [[answer(GENERATED_VOCABULARY)], [INVALID["mnemonic"]] * 2, [status(500)]],
    ids=["answered", "invalid", "failed"],
)
def test_the_adapter_logs_no_prompt_or_reply(log_capture: LogCapture, replies: list[Reply]) -> None:
    """AC-13: whatever the outcome, no log line carries the Target, the Generation context,
    the key or the model's output (AD-15).
    """
    generate(openrouter(OpenRouterReplay(replies)))

    logged = log_capture.all_text
    assert CONTEXT not in logged
    assert VOCABULARY_TARGET not in logged
    assert API_KEY not in logged
    assert GENERATED_VOCABULARY["russian"] not in logged
    assert "a leap over the facts" not in logged


@pytest.mark.p1
def test_no_configured_model_is_llm_failed_with_no_request() -> None:
    """AC-8: an empty OPENROUTER_MODELS has no model to ask: `llm_failed`, and nothing is sent."""
    replay = OpenRouterReplay([])

    outcome = generate(openrouter(replay, []))

    assert code_of(outcome) == "llm_failed"
    assert replay.sent == []

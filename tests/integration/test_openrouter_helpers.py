"""Target helpers RED: the grammar check and the CEFR examples on the OpenRouter adapter
(plan target-grammar-check-and-cefr-examples; I/O matrix M-1..M-4, M-6).

`OpenRouterLlm.check_grammar(language, category, target)` and `.examples(language, target,
context)` share `generate`'s request path:

- **Request.** The same POST, Bearer key, `models` = OPENROUTER_MODELS in order,
  `provider: {require_parameters: true}` and a strict `json_schema` response format, holding the
  helper's own closed schema. The messages carry the Target, the Language, and the Category
  (grammar) or the context (examples).
- **Validation.** The reply is validated with `GrammarCheck` / `ExampleSet`. Invalid output
  (an examples answer that isn't 6 levels A1→C2 × 5 sentences included) is retried once with
  the same body, then `llm_invalid_output`.
- **Failure.** A transport failure, an HTTP error status or a non-JSON body is `llm_failed` at
  once, with no retry. Nothing is logged.
"""

from typing import Any

import pytest

from language_lab.domain.catalog import Category, Language
from tests.support.aio import settle
from tests.support.captures import code_of
from tests.support.fixtures.logs import LogCapture
from tests.support.helpers import (
    CORRECT_TARGET,
    EXAMPLES,
    EXAMPLES_CONTEXT,
    EXAMPLES_TARGET,
    GRAMMAR_CORRECT,
    GRAMMAR_INCORRECT,
    INCORRECT_TARGET,
    LEVELS,
    MALFORMED_EXAMPLES,
)
from tests.support.openrouter import (
    API_KEY,
    CHAT_COMPLETIONS,
    OpenRouterReplay,
    Reply,
    answer,
    completion,
    not_json,
    prompt_text,
    refused,
    status,
    timed_out,
)

pytestmark = pytest.mark.skip(
    reason="Target helpers RED scaffold: activate when implementing the plan"
)

MODELS = ["openai/gpt-5.6-luna", "google/gemini-3.5-flash-lite"]


def openrouter(replay: OpenRouterReplay, models: list[str] = MODELS) -> Any:
    from language_lab.adapters.openrouter import OpenRouterLlm

    return OpenRouterLlm(API_KEY, models, transport=replay.transport)


def check_grammar(
    llm: Any, target: str = INCORRECT_TARGET, category: str = "sentence", language: str = "en"
) -> Any:
    """The outcome of one `check_grammar()`: the verdict, or the exception raised."""
    return settle(llm.check_grammar(Language(language), Category(category), target))


def examples(llm: Any, context: str = EXAMPLES_CONTEXT, language: str = "fr") -> Any:
    """The outcome of one `examples()`: the example set, or the exception raised."""
    return settle(llm.examples(Language(language), EXAMPLES_TARGET, context))


def closed(schema: dict[str, Any]) -> bool:
    """`schema` is a strict object: closed, with every property required."""
    return (
        schema.get("type") == "object"
        and schema.get("additionalProperties") is False
        and set(schema.get("required", [])) == set(schema.get("properties", {}))
    )


def assert_shared_request(sent: Any) -> dict[str, Any]:
    """The request is `generate`'s: URL, Bearer key, `models`, `require_parameters` only and a
    strict JSON Schema response format. Returns that schema.
    """
    assert sent.url == CHAT_COMPLETIONS
    assert sent.headers["authorization"] == f"Bearer {API_KEY}"
    assert sent.body["models"] == MODELS
    assert sent.body["provider"] == {"require_parameters": True}
    response_format = sent.body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    return response_format["json_schema"]["schema"]


@pytest.mark.p0
def test_check_grammar_returns_the_verdict_from_the_shared_request() -> None:
    """[P0] M-2 a wrong Target's verdict comes back with its correction, after one request on
    the same models, provider and strict-schema path as `generate`.
    """
    replay = OpenRouterReplay([answer(GRAMMAR_INCORRECT)])

    outcome = check_grammar(openrouter(replay))

    assert outcome.corrected == "He goes to school."
    assert outcome.correct is False
    assert len(replay.sent) == 1
    schema = assert_shared_request(replay.sent[0])
    assert closed(schema)
    assert set(schema["properties"]) == {"correct", "corrected", "explanation"}
    prompt = prompt_text(replay.sent[0].body)
    assert INCORRECT_TARGET in prompt
    assert "English" in prompt
    assert "Sentence" in prompt
    assert "Russian" in prompt


@pytest.mark.p1
def test_check_grammar_of_a_correct_vocabulary_target() -> None:
    """[P1] M-1 a correct French Vocabulary Target: `correct` true, no correction."""
    replay = OpenRouterReplay([answer(GRAMMAR_CORRECT)])

    outcome = check_grammar(openrouter(replay), CORRECT_TARGET, "vocabulary", "fr")

    assert outcome.correct is True
    assert outcome.corrected is None
    prompt = prompt_text(replay.sent[0].body)
    assert CORRECT_TARGET in prompt
    assert "French" in prompt
    assert "Vocabulary" in prompt


@pytest.mark.p0
def test_examples_returns_six_levels_from_the_shared_request() -> None:
    """[P0] M-3 the example set comes back A1..C2 × 5, after one request on the shared path;
    the Target, the Language and the context reach the model.
    """
    replay = OpenRouterReplay([answer(EXAMPLES)])

    outcome = examples(openrouter(replay))

    assert [str(group.level) for group in outcome.levels] == LEVELS
    assert outcome.model_dump(by_alias=True, mode="json") == EXAMPLES
    assert len(replay.sent) == 1
    schema = assert_shared_request(replay.sent[0])
    assert closed(schema)
    assert "levels" in schema["properties"]
    prompt = prompt_text(replay.sent[0].body)
    assert EXAMPLES_TARGET in prompt
    assert EXAMPLES_CONTEXT in prompt
    assert "French" in prompt


@pytest.mark.p1
def test_examples_without_context_leave_it_out_of_the_prompt() -> None:
    """[P1] M-3 a blank context is optional: the request still goes, without it."""
    replay = OpenRouterReplay([answer(EXAMPLES)])

    outcome = examples(openrouter(replay), context="")

    assert [str(group.level) for group in outcome.levels] == LEVELS
    assert EXAMPLES_CONTEXT not in prompt_text(replay.sent[0].body)


@pytest.mark.p0
@pytest.mark.parametrize("malformed", MALFORMED_EXAMPLES.values(), ids=MALFORMED_EXAMPLES.keys())
def test_a_malformed_example_set_is_retried_once_then_llm_invalid_output(
    malformed: dict[str, Any],
) -> None:
    """[P0] M-4 a set that isn't 6 levels A1→C2 × 5 sentences is retried once with the same
    body, then `llm_invalid_output` after exactly two requests.
    """
    replay = OpenRouterReplay([answer(malformed), answer(malformed)])

    outcome = examples(openrouter(replay))

    assert code_of(outcome) == "llm_invalid_output"
    assert len(replay.sent) == 2
    assert replay.sent[1].body == replay.sent[0].body


@pytest.mark.p1
def test_a_valid_retry_is_the_example_set() -> None:
    """[P1] M-4 a malformed set followed by a valid one returns the valid one."""
    replay = OpenRouterReplay([answer(MALFORMED_EXAMPLES["four-in-b1"]), answer(EXAMPLES)])

    outcome = examples(openrouter(replay))

    assert [len(group.sentences) for group in outcome.levels] == [5] * 6
    assert len(replay.sent) == 2


INVALID_GRAMMAR: dict[str, Reply] = {
    "not-json": completion("The sentence is wrong: use goes."),
    "explanation-missing": answer({"correct": False, "corrected": "He goes to school."}),
    "refusal": completion(None),
}


@pytest.mark.p1
@pytest.mark.parametrize("invalid", INVALID_GRAMMAR.values(), ids=INVALID_GRAMMAR.keys())
def test_an_invalid_verdict_is_retried_once_then_llm_invalid_output(invalid: Reply) -> None:
    """[P1] M-4 the grammar check shares the one retry on invalid output."""
    replay = OpenRouterReplay([invalid, invalid])

    outcome = check_grammar(openrouter(replay))

    assert code_of(outcome) == "llm_invalid_output"
    assert len(replay.sent) == 2
    assert replay.sent[1].body == replay.sent[0].body


FAILED: dict[str, Reply] = {
    "refused": refused,
    "timed-out": timed_out,
    "server-error": status(500),
    "not-json": not_json,
}


@pytest.mark.p0
@pytest.mark.parametrize("failure", FAILED.values(), ids=FAILED.keys())
@pytest.mark.parametrize("helper", ["grammar", "examples"])
def test_a_failed_request_is_llm_failed_with_no_retry(helper: str, failure: Reply) -> None:
    """[P0] M-6 a transport failure, an error status or a non-JSON body is `llm_failed` after
    one request, for either helper: only invalid output is retried.
    """
    valid = GRAMMAR_INCORRECT if helper == "grammar" else EXAMPLES
    replay = OpenRouterReplay([failure, answer(valid)])
    llm = openrouter(replay)

    outcome = check_grammar(llm) if helper == "grammar" else examples(llm)

    assert code_of(outcome) == "llm_failed"
    assert len(replay.sent) == 1


@pytest.mark.p1
@pytest.mark.parametrize("helper", ["grammar", "examples"])
def test_no_configured_model_is_llm_failed_with_no_request(helper: str) -> None:
    """[P1] M-6 an empty OPENROUTER_MODELS sends nothing: `llm_failed`."""
    replay = OpenRouterReplay([])
    llm = openrouter(replay, [])

    outcome = check_grammar(llm) if helper == "grammar" else examples(llm)

    assert code_of(outcome) == "llm_failed"
    assert replay.sent == []


@pytest.mark.p1
def test_the_helpers_log_no_target_context_or_reply(log_capture: LogCapture) -> None:
    """[P1] M-1..M-4 neither helper logs the Target, the context, the key or the answer
    (AD-15, NFR-7).
    """
    check_grammar(openrouter(OpenRouterReplay([answer(GRAMMAR_INCORRECT)])))
    examples(openrouter(OpenRouterReplay([answer(MALFORMED_EXAMPLES["c2-missing"])] * 2)))

    logged = log_capture.all_text
    assert INCORRECT_TARGET not in logged
    assert GRAMMAR_INCORRECT["corrected"] not in logged
    assert GRAMMAR_INCORRECT["explanation"] not in logged
    assert EXAMPLES_TARGET not in logged
    assert EXAMPLES_CONTEXT not in logged
    assert EXAMPLES["levels"][0]["sentences"][0]["sentence"] not in logged
    assert API_KEY not in logged

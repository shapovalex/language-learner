"""OpenRouter Chat Completions behind the Llm port (AD-1, AD-11; addendum A4; FR-16, FR-17, NFR-8).

One POST per attempt, with `models` = OPENROUTER_MODELS in order (OpenRouter's model fallbacks),
the Category's strict JSON Schema as the response format, and `provider.require_parameters` so
only providers honouring the schema are reached. No other routing or privacy keys: OpenRouter's
defaults apply (NFR-8).

The Target helpers (grammar check, CEFR example sentences) go down the same request path with
their own system prompt and strict schema, so they use the same key, models and provider rule.

An answer that fails validation (not JSON, outside the schema, a refusal, no choices) is asked
for once more with the same body, then `llm_invalid_output`. A failed request (no connection, a
timeout, an error status, a body that isn't JSON) is `llm_failed` at once: only invalid output
retries (architecture, Deferred). Nothing here is logged: the prompt, the Target, the Generation
context, the examples context and the answer are content (AD-15).
"""

import json
from collections.abc import Sequence
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.helpers import (
    ExampleSet,
    GrammarCheck,
    examples_json_schema,
    grammar_json_schema,
)
from language_lab.domain.items import GeneratedFields, generated_model, strict_json_schema

CHAT_COMPLETIONS = "https://openrouter.ai/api/v1/chat/completions"
# Generation is the slowest call the app makes; fallbacks across models add to it
TIMEOUT_S = 60.0

_LANGUAGES = {Language.EN: "English", Language.FR: "French"}
_CATEGORIES = {Category.VOCABULARY: "Vocabulary", Category.SENTENCE: "Sentence"}

_SYSTEM_PROMPT = """\
You write flashcard Drafts for a Russian speaker learning English and French.
Given a Target text, its Language and its Category, answer with the fields of the JSON Schema.
- russian: the one Russian meaning that fits the Target in this context, not a dictionary list.
- russianAlternatives: other Russian meanings a learner might give, one per entry, no commas;
  an empty list when there are none.
- hint: a short clue in the Target language that points to the Target without giving it away,
  or null.
- Vocabulary only: partOfSpeech and grammar (usage pattern), or null; example: one natural
  sentence in the Target language that uses the Target; exampleRussian: its Russian translation.
- Sentence only: note: a short remark on grammar or usage worth knowing, or null.
The Generation context, when given, says where the Target was met: use it to pick the meaning.
"""

_GRAMMAR_PROMPT = """\
You check the grammar of a Target text for a Russian speaker learning English and French.
Given a Target, its Language and its Category, answer with the fields of the JSON Schema.
- correct: true when the Target is grammatical and natural in the Language, else false.
  A Vocabulary Target is a word or phrase, not a full sentence: judge it as one.
- corrected: the corrected Target when it is wrong, changing as little as possible;
  null when it is correct.
- explanation: one or two short sentences in Russian saying what is wrong and why,
  or confirming that it is correct.
"""

_EXAMPLES_PROMPT = """\
You write example sentences for a Russian speaker learning English and French.
Given a Target word or phrase and its Language, answer with the fields of the JSON Schema:
levels, exactly six entries in this order: A1, A2, B1, B2, C1, C2. Each has exactly five
sentences in the Language that use the Target naturally, with vocabulary and grammar fitting
that CEFR level, and each sentence's Russian translation in russian.
The context, when given, says where the Target was met: use it to pick the meaning.
"""


def _user_prompt(language: Language, category: Category, target: str, context: str) -> str:
    lines = [
        f"Language: {_LANGUAGES[language]}",
        f"Category: {_CATEGORIES[category]}",
        f"Target: {target}",
    ]
    if context.strip():
        lines.append(f"Generation context: {context}")
    return "\n".join(lines)


def _grammar_prompt(language: Language, category: Category, target: str) -> str:
    return "\n".join(
        [
            f"Language: {_LANGUAGES[language]}",
            f"Category: {_CATEGORIES[category]}",
            f"Target: {target}",
        ]
    )


def _examples_prompt(language: Language, target: str, context: str) -> str:
    lines = [f"Language: {_LANGUAGES[language]}", f"Target: {target}"]
    if context.strip():
        lines.append(f"Context: {context}")
    return "\n".join(lines)


class _InvalidOutput(Exception):
    """The model answered, but not with the generated fields."""


class OpenRouterLlm:
    def __init__(
        self,
        api_key: str,
        models: Sequence[str],
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._models = list(models)
        self._http = httpx.AsyncClient(
            transport=transport,
            timeout=TIMEOUT_S,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def generate(
        self, language: Language, category: Category, target: str, generation_context: str
    ) -> GeneratedFields:
        return await self._complete(
            _SYSTEM_PROMPT,
            _user_prompt(language, category, target, generation_context),
            f"{category.value}_draft",
            strict_json_schema(category),
            generated_model(category),
        )

    async def check_grammar(
        self, language: Language, category: Category, target: str
    ) -> GrammarCheck:
        return await self._complete(
            _GRAMMAR_PROMPT,
            _grammar_prompt(language, category, target),
            "grammar_check",
            grammar_json_schema(),
            GrammarCheck,
        )

    async def examples(self, language: Language, target: str, context: str) -> ExampleSet:
        return await self._complete(
            _EXAMPLES_PROMPT,
            _examples_prompt(language, target, context),
            "example_sentences",
            examples_json_schema(),
            ExampleSet,
        )

    async def _complete[M: BaseModel](
        self, system: str, user: str, name: str, schema: dict[str, Any], model: type[M]
    ) -> M:
        """`model` validated from the answer to one strict-schema request, retried once on
        invalid output only (AD-11).
        """
        if not self._models:
            raise AppError(ErrorCode.LLM_FAILED)  # nothing to ask
        body = {
            "models": self._models,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": schema},
            },
            "provider": {"require_parameters": True},
        }
        for _ in range(2):  # one retry, on invalid output only (AD-11)
            reply = await self._post(body)
            try:
                return self._validate(model, reply)
            except _InvalidOutput:
                continue
        raise AppError(ErrorCode.LLM_INVALID_OUTPUT)

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        """The reply body. Raises `AppError(LLM_FAILED)`, carrying no upstream text (AD-15)."""
        try:
            response = await self._http.post(CHAT_COMPLETIONS, json=body)
            response.raise_for_status()
            reply = response.json()
        except httpx.HTTPError, ValueError:
            raise AppError(ErrorCode.LLM_FAILED) from None
        if not isinstance(reply, dict):
            raise AppError(ErrorCode.LLM_FAILED)
        return reply

    @staticmethod
    def _validate[M: BaseModel](model: type[M], reply: dict[str, Any]) -> M:
        try:
            content = reply["choices"][0]["message"]["content"]
        except KeyError, IndexError, TypeError:
            raise _InvalidOutput from None
        if not isinstance(content, str):  # null: the model refused
            raise _InvalidOutput
        try:
            return model.model_validate(json.loads(content))
        except ValueError, ValidationError:
            raise _InvalidOutput from None

    async def aclose(self) -> None:
        await self._http.aclose()

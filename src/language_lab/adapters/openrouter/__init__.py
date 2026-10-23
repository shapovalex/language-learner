"""OpenRouter Chat Completions behind the Llm port (AD-1, AD-11; addendum A4; FR-16, FR-17, NFR-8).

One POST per attempt, with `models` = OPENROUTER_MODELS in order (OpenRouter's model fallbacks),
the Category's strict JSON Schema as the response format, and `provider.require_parameters` so
only providers honouring the schema are reached. No other routing or privacy keys: OpenRouter's
defaults apply (NFR-8).

An answer that fails validation (not JSON, outside the schema, a refusal, no choices) is asked
for once more with the same body, then `llm_invalid_output`. A failed request (no connection, a
timeout, an error status, a body that isn't JSON) is `llm_failed` at once: only generation's
invalid output retries (architecture, Deferred). Nothing here is logged: the prompt, the Target,
the Generation context and the answer are content (AD-15).
"""

import json
from collections.abc import Sequence
from typing import Any

import httpx
from pydantic import ValidationError

from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
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


def _user_prompt(language: Language, category: Category, target: str, context: str) -> str:
    lines = [
        f"Language: {_LANGUAGES[language]}",
        f"Category: {_CATEGORIES[category]}",
        f"Target: {target}",
    ]
    if context.strip():
        lines.append(f"Generation context: {context}")
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
        if not self._models:
            raise AppError(ErrorCode.LLM_FAILED)  # nothing to ask
        body = {
            "models": self._models,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _user_prompt(language, category, target, generation_context),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{category.value}_draft",
                    "strict": True,
                    "schema": strict_json_schema(category),
                },
            },
            "provider": {"require_parameters": True},
        }
        for _ in range(2):  # one retry, on invalid output only (AD-11)
            reply = await self._post(body)
            try:
                return self._validate(category, reply)
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
    def _validate(category: Category, reply: dict[str, Any]) -> GeneratedFields:
        try:
            content = reply["choices"][0]["message"]["content"]
        except KeyError, IndexError, TypeError:
            raise _InvalidOutput from None
        if not isinstance(content, str):  # null: the model refused
            raise _InvalidOutput
        try:
            return generated_model(category).model_validate(json.loads(content))
        except ValueError, ValidationError:
            raise _InvalidOutput from None

    async def aclose(self) -> None:
        await self._http.aclose()

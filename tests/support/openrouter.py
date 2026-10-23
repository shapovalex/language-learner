"""OpenRouter as the tests see it: hand-built Chat Completions replies and a replaying httpx
transport for the adapter. Nothing here reaches the real OpenRouter.

The reply shape follows OpenRouter's documented Chat Completions response
(https://openrouter.ai/docs/api-reference/chat-completion); story 4.4's acceptance run checks
it against a real one.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

CHAT_COMPLETIONS = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = "test-openrouter-key"

type Failure = Callable[[httpx.Request], httpx.Response]
# A reply: a 200 JSON body, or a failure answering (or raising for) the request
type Reply = dict[str, Any] | Failure


def completion(content: str | None, *, model: str = "openai/gpt-5.6-luna") -> dict[str, Any]:
    """A 200 Chat Completions body whose one choice's message is `content` (None: a refusal)."""
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if content is None:
        message["refusal"] = "I can't help with that."
    return {
        "id": "gen-1761170000-abc",
        "provider": "OpenAI",
        "model": model,
        "object": "chat.completion",
        "created": 1761170000,
        "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
        "usage": {"prompt_tokens": 412, "completion_tokens": 96, "total_tokens": 508},
    }


def answer(reply: dict[str, Any]) -> dict[str, Any]:
    """A completion whose content is `reply` as JSON: the model's structured output."""
    return completion(json.dumps(reply, ensure_ascii=False))


def no_choices(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={**completion("{}"), "choices": []})


# How OpenRouter can fail before answering, as seen from the adapter
def refused(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 61] Connection refused", request=request)


def timed_out(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timed out", request=request)


def status(code: int) -> Failure:
    def reply(request: httpx.Request) -> httpx.Response:
        return httpx.Response(code, json={"error": {"code": code, "message": "upstream said no"}})

    return reply


def not_json(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="<html><body>Bad gateway</body></html>")


@dataclass(frozen=True)
class SentRequest:
    url: str
    headers: httpx.Headers
    body: Any  # the parsed JSON body


class OpenRouterReplay:
    """An httpx transport answering each request with the next of `replies`, in order, and
    recording what the adapter sent. A request past the last reply fails the test.

    Pass `.transport` to the adapter under test; read `.sent` afterwards.
    """

    def __init__(self, replies: Sequence[Reply]) -> None:
        self.sent: list[SentRequest] = []
        self._replies = list(replies)
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.sent.append(
            SentRequest(str(request.url), request.headers, json.loads(request.content))
        )
        if len(self.sent) > len(self._replies):
            raise AssertionError(f"unexpected request {len(self.sent)} to OpenRouter")
        reply = self._replies[len(self.sent) - 1]
        return reply(request) if callable(reply) else httpx.Response(200, json=reply)


def prompt_text(body: Any) -> str:
    """Every message's content in a sent body, joined, to look for the prompt's inputs."""
    return "\n".join(str(message.get("content", "")) for message in body["messages"])

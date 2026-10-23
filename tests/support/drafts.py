"""Generated Draft test data, shared by the domain, OpenRouter adapter and drafts API tests
(tests/unit/test_draft_generation_domain.py, tests/integration/test_openrouter_llm.py,
tests/api/test_drafts_generate.py).

`GENERATED_VOCABULARY` and `GENERATED_SENTENCE` are the generated-fields models on the wire
(camelCase, AD-11): what the model answers, with no `target`, `category` or `mnemonic`, and a
null optional field. `drafted(reply, target)` is the ItemContent the Draft carries for it.
`language_lab.domain.items`' generation models and `tests/fakes/llm.py` don't exist yet, so they
are imported inside the functions and collection passes before them.
"""

from typing import Any

from fastapi.testclient import TestClient

from language_lab.app import create_app
from language_lab.ports.anki_store import AnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client

GENERATE_API = "/api/drafts/generate"

VOCABULARY_TARGET = "jump to conclusions"
SENTENCE_TARGET = "Ne tirons pas de conclusions hâtives."
CONTEXT = "Heard in a team meeting about an outage, said about a hasty post-mortem."

GENERATED_VOCABULARY: dict[str, Any] = {
    "russian": "делать поспешные выводы",
    "russianAlternatives": ["торопиться с выводами"],
    "hint": None,
    "partOfSpeech": "phrase",
    "grammar": "jump to conclusions about sth",
    "example": "Let's not jump to conclusions before the post-mortem.",
    "exampleRussian": "Давай не будем делать поспешных выводов до разбора.",
}

GENERATED_SENTENCE: dict[str, Any] = {
    "russian": "Не будем делать поспешных выводов.",
    "russianAlternatives": [],
    "hint": "tirer des conclusions",
    "note": None,
}

GENERATED = {"vocabulary": GENERATED_VOCABULARY, "sentence": GENERATED_SENTENCE}


def drafted(category: str, target: str) -> dict[str, Any]:
    """The ItemContent on the wire a Draft carries for `GENERATED[category]` and `target`:
    the given Target and the Category, nulls as empty, and an empty mnemonic for Vocabulary.
    """
    fields = {key: "" if value is None else value for key, value in GENERATED[category].items()}
    extra = {"mnemonic": ""} if category == "vocabulary" else {}
    return {"category": category, "target": target, **fields, **extra}


def generated(category: str, reply: dict[str, Any]) -> Any:
    """`reply` validated with the Category's generated-fields model (AD-11)."""
    from language_lab.domain.catalog import Category
    from language_lab.domain.items import generated_model

    return generated_model(Category(category)).model_validate(reply)


def fake_llm(reply: dict[str, Any] | None = None, *, error: str | None = None) -> Any:
    """A `FakeLlm` answering `reply`, or raising `AppError(error)`."""
    from language_lab.domain.errors import ErrorCode
    from tests.fakes.llm import FakeLlm

    return FakeLlm(reply, error=None if error is None else ErrorCode(error))


def drafts_client(settings_factory: SettingsFactory, store: AnkiStore, llm: Any) -> TestClient:
    """`app_client` for the app over `store` and `llm`."""
    built = settings_factory()
    return app_client(create_app(built, anki_store=store, llm=llm), built)


def generate_body(kind: str, **overrides: Any) -> dict[str, Any]:
    """An English generate request for the Category `kind`, its Target and `CONTEXT`, with
    `overrides` replacing keys (`language`, even `category`).
    """
    target = VOCABULARY_TARGET if kind == "vocabulary" else SENTENCE_TARGET
    body = {
        "language": "en",
        "category": kind,
        "target": target,
        "generationContext": CONTEXT,
    }
    return {**body, **overrides}

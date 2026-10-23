"""Story 4.2: the generated-fields models and their one strict JSON Schema (AD-11; FR-14, FR-15).

Per Category, `domain/items.py` derives the model the LLM answers with, a subset of
`ItemContent`:

- No `mnemonic` (never generated, FR-14), and for Sentence no `example` (FR-15).
- No `target` or `category` either. Decided with the user (2026-10-22): the Target is input, so
  the model can't change what the user captured, and the Category is the model chosen.

`strict_json_schema(category)` is what OpenRouter gets: `additionalProperties: false`, every
property required, optional fields nullable, and no defaults. The same model validates the
reply, and `to_content(target)` turns a valid one into the Draft's `ItemContent`.

Defaults pinned here: `russian` and `russianAlternatives` are never null, nor is a Vocabulary
`example` or `exampleRussian` (one example by default, FR-14); every other field is nullable.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from tests.support.drafts import (
    GENERATED,
    GENERATED_SENTENCE,
    GENERATED_VOCABULARY,
    drafted,
    generated,
)

FIELDS = {
    "vocabulary": {
        "russian",
        "russianAlternatives",
        "hint",
        "partOfSpeech",
        "grammar",
        "example",
        "exampleRussian",
    },
    "sentence": {"russian", "russianAlternatives", "hint", "note"},
}
NEVER_NULL = {
    "vocabulary": {"russian", "russianAlternatives", "example", "exampleRussian"},
    "sentence": {"russian", "russianAlternatives"},
}


def schema_of(category: str) -> dict[str, Any]:
    from language_lab.domain.catalog import Category
    from language_lab.domain.items import strict_json_schema

    return strict_json_schema(Category(category))


def objects(node: Any) -> list[dict[str, Any]]:
    """Every object schema in `node`, at any depth, `$defs` included."""
    found = []
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            found.append(node)
        for value in node.values():
            found.extend(objects(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(objects(value))
    return found


def keys(node: Any) -> set[str]:
    """Every key at any depth of `node`."""
    if isinstance(node, dict):
        return set(node).union(*(keys(value) for value in node.values()))
    if isinstance(node, list):
        return set().union(*(keys(value) for value in node))
    return set()


def is_nullable(prop: dict[str, Any]) -> bool:
    types = prop.get("type")
    if isinstance(types, list):
        return "null" in types
    return any(option.get("type") == "null" for option in prop.get("anyOf", []))


@pytest.mark.p0
@pytest.mark.parametrize("category", FIELDS)
def test_each_category_generates_its_item_fields_less_target_and_mnemonic(category: str) -> None:
    """AC-1: the schema's properties are exactly the Category's generated fields: ItemContent
    less `target`, `category` and `mnemonic`, and for Sentence less `example`.
    """
    schema = schema_of(category)

    assert set(schema["properties"]) == FIELDS[category]

    assert schema["type"] == "object"


@pytest.mark.p0
@pytest.mark.parametrize("category", FIELDS)
def test_strict_json_schema_follows_the_strict_rules(category: str) -> None:
    """AC-2: every object forbids extra properties and requires all of them; the optional
    fields are nullable and the rest are not; no default appears anywhere (AD-11).
    """
    schema = schema_of(category)

    assert all(obj.get("additionalProperties") is False for obj in objects(schema))

    assert all(set(obj["required"]) == set(obj["properties"]) for obj in objects(schema))
    props = schema["properties"]
    assert {name for name, prop in props.items() if not is_nullable(prop)} == NEVER_NULL[category]
    assert "default" not in keys(schema)


REFUSED = {
    "vocabulary-mnemonic": ("vocabulary", {**GENERATED_VOCABULARY, "mnemonic": "a leap"}),
    "vocabulary-target": ("vocabulary", {**GENERATED_VOCABULARY, "target": "jumped"}),
    "sentence-example": ("sentence", {**GENERATED_SENTENCE, "example": "On y va."}),
    "missing-key": ("sentence", {k: v for k, v in GENERATED_SENTENCE.items() if k != "hint"}),
    "null-russian": ("sentence", {**GENERATED_SENTENCE, "russian": None}),
    "null-example": ("vocabulary", {**GENERATED_VOCABULARY, "example": None}),
    "blank-russian": ("vocabulary", {**GENERATED_VOCABULARY, "russian": "  "}),
    "comma-alternative": (
        "vocabulary",
        {**GENERATED_VOCABULARY, "russianAlternatives": ["спешить, торопиться"]},
    ),
    "not-a-list": ("sentence", {**GENERATED_SENTENCE, "russianAlternatives": "спешить"}),
}


@pytest.mark.p0
@pytest.mark.parametrize(("category", "reply"), REFUSED.values(), ids=REFUSED.keys())
def test_the_generated_model_refuses_a_reply_outside_the_schema(
    category: str, reply: dict[str, Any]
) -> None:
    """AC-3: an extra key (a mnemonic, a Target, a Sentence example), a missing key, a null
    required field, a blank Russian meaning or a comma alternative is refused.
    """
    with pytest.raises(ValidationError):
        generated(category, reply)


@pytest.mark.p0
@pytest.mark.parametrize("category", GENERATED)
def test_a_valid_reply_becomes_the_drafts_item_content(category: str) -> None:
    """AC-4: `to_content(target)` is the Draft's ItemContent: the given Target, the Category,
    null optional fields empty, and an empty mnemonic for Vocabulary.
    """
    target = f"target {category}"

    content = generated(category, GENERATED[category]).to_content(target)

    assert content.model_dump(by_alias=True) == drafted(category, target)

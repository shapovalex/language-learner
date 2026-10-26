---
title: 'Fix Draft generation failing on comma alternatives'
type: 'bugfix'
ticket: ''
created: '2026-10-26'
status: 'built'
baseline_revision: 'e9ab646c343cc64c719339cc947ba59aec09ae48'
route: 'oneshot'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Generating a Draft from a Capture often ends in "The model's answer failed the checks twice" (`llm_invalid_output`, see `bugs/model_error.png`, Capture "Vanishing glass", English Vocabulary). The cause, reproduced against OpenRouter with the configured models (0/6 valid): the model writes Russian alternatives with a comma, such as "стекло, которое исчезает". Russian grammar needs that comma, but AD-10 forbids commas in an alternative. The rule lives only in a pydantic validator and not in the strict JSON Schema sent to the model, so the retry fails the same way (the schema drifts from the validator, which AD-11 is meant to prevent).

**Approach:** Express the alternative rule (not blank, no comma) as a string `pattern` on the alternatives' items in the domain type. `strict_json_schema()` then carries it to the model, and the same model still validates the reply. With the pattern added, 12/12 calls across `openai/gpt-5.6-luna`, `google/gemini-3.5-flash-lite` and `anthropic/claude-sonnet-4.6` returned valid answers, and no provider rejected the keyword. Save keeps refusing a comma alternative.

</frozen-after-approval>

## Implementation Notes

Oneshot: a one-type change in `src/language_lab/domain/items.py` (`_Alternatives` items gain a `StringConstraints` pattern, `^[^,]*[^,\s][^,]*$`, which emits `pattern` into the schema; keep or drop the AfterValidator as the pattern makes it redundant), plus unit tests in `tests/unit/test_draft_generation_domain.py` (schema carries the pattern on `russianAlternatives.items` for both Categories) and an adapter-level test that a reply with a comma alternative is still `llm_invalid_output`. Existing Save tests (`tests/api/test_items_save.py`, `tests/unit/test_items_domain.py`) must still refuse comma and blank alternatives; check whether any assert the pydantic error type or message.

## Verification

**Commands:**
- `uv run pytest tests/unit tests/api -q` -- expected: all pass
- `uv run ruff check src tests && uv run ruff format --check src tests` -- expected: clean

Changed `src/language_lab/domain/items.py` (the `_alternatives` AfterValidator became a `StringConstraints` pattern), `tests/unit/test_draft_generation_domain.py` (the schema carries the pattern; a blank alternative is refused), `tests/integration/test_openrouter_llm.py` (a comma alternative is `llm_invalid_output` after one retry) and `tests/unit/test_items_domain.py` (Save content refuses a blank alternative). Live check after the fix: 5/5 `OpenRouterLlm.generate` calls for "Vanishing glass" passed validation.

## Review Triage Log

- low, patched: Save-side `ItemContent` had no blank-alternative case. Added `blank-alternative` to `tests/unit/test_items_domain.py` REFUSED.
- low, rejected: Rust `\s` excludes `\x1c`–`\x1f`, which `str.strip()` treated as whitespace. An alternative made only of those characters is unreachable in practice, and fixing it would complicate the pattern.
- false: the new schema test uses Python `re`, not Rust regex. For the strings it tests the two engines agree, and the `REFUSED` and adapter `comma-alternative` cases cover real enforcement through pydantic.

"""Story 4.2: the Llm port and its fake keep step (AD-1).

`ports/llm.py` declares `Llm.generate(language, category, target, generation_context)`, which
returns the Category's generated-fields model (AD-11) and raises `llm_failed` or
`llm_invalid_output`. Only `adapters/openrouter` calls OpenRouter; `tests/fakes/llm.py` is the
in-memory fake. Epic-maintain-items reuses the same port for per-field regeneration.
"""

import inspect

import pytest

from tests.support.ports import public_methods


@pytest.mark.p1
def test_the_llm_port_the_fake_and_the_openrouter_adapter_declare_generate() -> None:
    """AC-9: the port has one async `generate(language, category, target,
    generation_context)`; the fake and the OpenRouter adapter match it.
    """
    from language_lab.adapters.openrouter import OpenRouterLlm
    from language_lab.domain.catalog import Category, Language
    from language_lab.ports.llm import Llm
    from tests.fakes.llm import FakeLlm

    port = public_methods(Llm)

    assert {name: public_methods(FakeLlm).get(name) for name in port} == port

    assert {name: public_methods(OpenRouterLlm).get(name) for name in port} == port
    assert set(port) == {"generate"}
    assert inspect.iscoroutinefunction(Llm.generate)
    hints = inspect.get_annotations(Llm.generate, eval_str=True)
    assert {k: v for k, v in hints.items() if k != "return"} == {
        "language": Language,
        "category": Category,
        "target": str,
        "generation_context": str,
    }

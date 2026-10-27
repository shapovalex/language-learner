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
    """AC-9: the port has async `generate(language, category, target, generation_context)`
    beside the Target helpers; the fake and the OpenRouter adapter match it.
    """
    from language_lab.adapters.openrouter import OpenRouterLlm
    from language_lab.domain.catalog import Category, Language
    from language_lab.ports.llm import Llm
    from tests.fakes.llm import FakeLlm

    port = public_methods(Llm)

    assert {name: public_methods(FakeLlm).get(name) for name in port} == port

    assert {name: public_methods(OpenRouterLlm).get(name) for name in port} == port
    assert set(port) == {"generate", "check_grammar", "examples"}
    assert inspect.iscoroutinefunction(Llm.generate)
    hints = inspect.get_annotations(Llm.generate, eval_str=True)
    assert {k: v for k, v in hints.items() if k != "return"} == {
        "language": Language,
        "category": Category,
        "target": str,
        "generation_context": str,
    }


@pytest.mark.p1
def test_the_llm_port_declares_the_target_helpers() -> None:
    """The Target helpers share the port: async `check_grammar(language, category, target)`
    and `examples(language, target, context)`, answering the helpers' domain models.
    """
    from language_lab.domain.catalog import Category, Language
    from language_lab.domain.helpers import ExampleSet, GrammarCheck
    from language_lab.ports.llm import Llm

    assert inspect.iscoroutinefunction(Llm.check_grammar)
    assert inspect.iscoroutinefunction(Llm.examples)
    assert inspect.get_annotations(Llm.check_grammar, eval_str=True) == {
        "language": Language,
        "category": Category,
        "target": str,
        "return": GrammarCheck,
    }
    assert inspect.get_annotations(Llm.examples, eval_str=True) == {
        "language": Language,
        "target": str,
        "context": str,
        "return": ExampleSet,
    }

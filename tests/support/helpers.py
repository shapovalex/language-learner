"""Target helpers test data, shared by the domain, OpenRouter adapter and helpers API tests
(tests/unit/test_helpers_domain.py, tests/integration/test_openrouter_helpers.py,
tests/api/test_helpers_grammar.py, tests/api/test_helpers_examples.py).

`GRAMMAR_CORRECT` and `GRAMMAR_INCORRECT` are grammar verdicts on the wire, explained in
Russian. `EXAMPLES` is an examples answer on the wire: five French sentences with their Russian
for each CEFR level, A1 to C2, in order. `examples_with(...)` derives a malformed one from it.
`language_lab.domain.helpers` doesn't exist yet, so `FakeLlm`'s helper methods import it inside
the methods and collection passes before it.
"""

import copy
from typing import Any

from fastapi.testclient import TestClient

from language_lab.app import create_app
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import app_client

GRAMMAR_API = "/api/helpers/grammar"
EXAMPLES_API = "/api/helpers/examples"

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

CORRECT_TARGET = "jump to conclusions"
INCORRECT_TARGET = "He go to school."
CORRECTED_TARGET = "He goes to school."
EXAMPLES_TARGET = "tirer des conclusions"
EXAMPLES_CONTEXT = "Entendu dans une réunion d'équipe à propos d'une panne."

GRAMMAR_CORRECT: dict[str, Any] = {
    "correct": True,
    "corrected": None,
    "explanation": "Ошибок нет: устойчивое выражение употреблено правильно.",
}

GRAMMAR_INCORRECT: dict[str, Any] = {
    "correct": False,
    "corrected": CORRECTED_TARGET,
    "explanation": "После he глагол в Present Simple получает окончание -s: goes, а не go.",
}

_SENTENCES: dict[str, list[tuple[str, str]]] = {
    "A1": [
        ("Je tire des conclusions.", "Я делаю выводы."),
        ("Tu tires des conclusions.", "Ты делаешь выводы."),
        ("Il ne tire pas de conclusions.", "Он не делает выводов."),
        ("Nous tirons des conclusions.", "Мы делаем выводы."),
        ("Elles tirent des conclusions vite.", "Они быстро делают выводы."),
    ],
    "A2": [
        ("Hier, j'ai tiré des conclusions.", "Вчера я сделал выводы."),
        ("Ne tire pas de conclusions trop vite.", "Не делай выводов слишком быстро."),
        ("Le prof tire des conclusions du test.", "Учитель делает выводы из теста."),
        ("On a tiré des conclusions ensemble.", "Мы сделали выводы вместе."),
        ("Pourquoi tires-tu des conclusions ?", "Почему ты делаешь выводы?"),
    ],
    "B1": [
        (
            "Il ne faut pas tirer de conclusions hâtives.",
            "Не нужно делать поспешных выводов.",
        ),
        (
            "Après la réunion, elle a tiré ses propres conclusions.",
            "После собрания она сделала собственные выводы.",
        ),
        (
            "Nous tirerons des conclusions quand nous aurons les résultats.",
            "Мы сделаем выводы, когда получим результаты.",
        ),
        (
            "J'ai tiré des conclusions de mes erreurs.",
            "Я сделал выводы из своих ошибок.",
        ),
        (
            "Avant de tirer des conclusions, écoute-le.",
            "Прежде чем делать выводы, выслушай его.",
        ),
    ],
    "B2": [
        (
            "Les enquêteurs refusent de tirer des conclusions prématurées.",
            "Следователи отказываются делать преждевременные выводы.",
        ),
        (
            "On peut tirer plusieurs conclusions de cette étude.",
            "Из этого исследования можно сделать несколько выводов.",
        ),
        (
            "Il est trop tôt pour tirer des conclusions sur la panne.",
            "Слишком рано делать выводы о сбое.",
        ),
        (
            "Elle a tiré les conclusions qui s'imposaient et a démissionné.",
            "Она сделала напрашивающиеся выводы и уволилась.",
        ),
        (
            "Les médias ont tiré des conclusions sans preuves.",
            "СМИ сделали выводы без доказательств.",
        ),
    ],
    "C1": [
        (
            "Le rapport se garde bien de tirer des conclusions définitives.",
            "Отчёт благоразумно избегает окончательных выводов.",
        ),
        (
            "Tirer des conclusions d'un échantillon aussi restreint serait imprudent.",
            "Делать выводы по столь малой выборке было бы неосмотрительно.",
        ),
        (
            "Le gouvernement n'a pas encore tiré les conclusions de la crise.",
            "Правительство ещё не извлекло уроков из кризиса.",
        ),
        (
            "Quelles conclusions faut-il tirer de ce revirement inattendu ?",
            "Какие выводы следует сделать из этого неожиданного поворота?",
        ),
        (
            "Elle s'est empressée de tirer des conclusions qui l'arrangeaient.",
            "Она поспешила сделать удобные для себя выводы.",
        ),
    ],
    "C2": [
        (
            "Il serait spécieux d'en tirer des conclusions d'ordre général.",
            "Было бы лукавством делать из этого общие выводы.",
        ),
        (
            "L'auteur se refuse à tirer la moindre conclusion de ces données lacunaires.",
            "Автор отказывается делать какие-либо выводы из этих неполных данных.",
        ),
        (
            "Encore faut-il savoir tirer les conclusions qui s'imposent.",
            "Ещё нужно уметь сделать напрашивающиеся выводы.",
        ),
        (
            "Loin de tirer des conclusions hâtives, la commission a temporisé.",
            "Комиссия не спешила с выводами и выжидала.",
        ),
        (
            "Les historiens ont tiré de ces archives des conclusions iconoclastes.",
            "Историки сделали из этих архивов ниспровергающие выводы.",
        ),
    ],
}

EXAMPLES: dict[str, Any] = {
    "levels": [
        {
            "level": level,
            "sentences": [{"sentence": s, "russian": r} for s, r in sentences],
        }
        for level, sentences in _SENTENCES.items()
    ]
}

EXAMPLE_SENTENCES = [s for sentences in _SENTENCES.values() for s, _ in sentences]


def examples_with(*, levels: list[str] | None = None, sentences: dict[str, int] | None = None):
    """`EXAMPLES` with its levels picked in the order of `levels` (missing, repeated or out of
    order), then each level in `sentences` cut or padded to that many sentences.
    """
    by_level = {group["level"]: group for group in EXAMPLES["levels"]}
    groups = [copy.deepcopy(by_level[level]) for level in (levels or LEVELS)]
    for group in groups:
        count = (sentences or {}).get(group["level"])
        if count is not None:
            pool = group["sentences"] * 2
            group["sentences"] = pool[:count]
    return {"levels": groups}


MALFORMED_EXAMPLES: dict[str, dict[str, Any]] = {
    "four-in-b1": examples_with(sentences={"B1": 4}),
    "six-in-c2": examples_with(sentences={"C2": 6}),
    "c2-missing": examples_with(levels=LEVELS[:5]),
    "out-of-order": examples_with(levels=["A1", "A2", "B2", "B1", "C1", "C2"]),
    "level-repeated": examples_with(levels=["A1", "A1", "B1", "B2", "C1", "C2"]),
}


def helpers_llm(
    *,
    grammar: dict[str, Any] | None = None,
    examples: dict[str, Any] | None = None,
    error: str | None = None,
) -> Any:
    """A `FakeLlm` answering the helpers with `grammar` and `examples`, or raising
    `AppError(error)`.
    """
    from language_lab.domain.errors import ErrorCode
    from tests.fakes.llm import FakeLlm

    return FakeLlm(
        error=None if error is None else ErrorCode(error),
        grammar_reply=grammar,
        examples_reply=examples,
    )


def helpers_client(settings_factory: SettingsFactory, llm: Any) -> TestClient:
    """`app_client` for the app over `llm`, with Anki unreachable: the helpers never need it."""
    built = settings_factory()
    return app_client(create_app(built, anki_store=FakeAnkiStore(available=False), llm=llm), built)


def grammar_body(**overrides: str) -> dict[str, str]:
    """An English Vocabulary grammar request for `CORRECT_TARGET`, `overrides` replacing keys."""
    return {"language": "en", "category": "vocabulary", "target": CORRECT_TARGET, **overrides}


def examples_body(**overrides: str) -> dict[str, str]:
    """A French examples request for `EXAMPLES_TARGET`, no context; `overrides` add or replace."""
    return {"language": "fr", "target": EXAMPLES_TARGET, **overrides}

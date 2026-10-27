"""Fake Llm: the port in memory, kept in step with `ports/llm.py` (AD-1)."""

from typing import Any

from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.helpers import ExampleSet, GrammarCheck
from language_lab.domain.items import GeneratedFields, generated_model

# A valid answer per Category, on the wire, when no `reply` is given
_REPLIES: dict[Category, dict[str, Any]] = {
    Category.VOCABULARY: {
        "russian": "делать поспешные выводы",
        "russianAlternatives": [],
        "hint": None,
        "partOfSpeech": "phrase",
        "grammar": None,
        "example": "Let's not jump to conclusions.",
        "exampleRussian": "Давай не будем делать поспешных выводов.",
    },
    Category.SENTENCE: {
        "russian": "Не будем делать поспешных выводов.",
        "russianAlternatives": [],
        "hint": None,
        "note": None,
    },
}

# The grammar verdict on the wire when no `grammar_reply` is given: a Target listed here is
# wrong and gets its correction, any other is correct
_GRAMMAR_CORRECTIONS: dict[str, dict[str, Any]] = {
    "He go to school.": {
        "correct": False,
        "corrected": "He goes to school.",
        "explanation": "После he глагол в Present Simple получает окончание -s: goes.",
    },
}
_GRAMMAR_CORRECT: dict[str, Any] = {
    "correct": True,
    "corrected": None,
    "explanation": "Ошибок нет: фраза построена правильно.",
}

# Five English sentences per CEFR level, A1 to C2, when no `examples_reply` is given
_EXAMPLE_SENTENCES: dict[str, list[tuple[str, str]]] = {
    "A1": [
        ("Do not jump to conclusions.", "Не делай поспешных выводов."),
        ("I jump to conclusions.", "Я делаю поспешные выводы."),
        ("She does not jump to conclusions.", "Она не делает поспешных выводов."),
        ("Please don't jump to conclusions.", "Пожалуйста, не делай поспешных выводов."),
        ("We jump to conclusions too fast.", "Мы слишком быстро делаем выводы."),
    ],
    "A2": [
        ("He always jumps to conclusions.", "Он всегда делает поспешные выводы."),
        ("Don't jump to conclusions about her.", "Не делай поспешных выводов о ней."),
        ("I jumped to conclusions yesterday.", "Вчера я поторопился с выводами."),
        ("They jumped to conclusions at work.", "На работе они поспешили с выводами."),
        ("Why do you jump to conclusions?", "Почему ты делаешь поспешные выводы?"),
    ],
    "B1": [
        (
            "It's easy to jump to conclusions when you're tired.",
            "Легко поспешить с выводами, когда устал.",
        ),
        (
            "Let's not jump to conclusions before we hear his side.",
            "Давай не будем спешить с выводами, пока не выслушаем его.",
        ),
        (
            "She tends to jump to conclusions about new people.",
            "Она склонна делать поспешные выводы о новых людях.",
        ),
        (
            "I jumped to conclusions and blamed the wrong person.",
            "Я поспешил с выводами и обвинил не того человека.",
        ),
        (
            "The manager jumped to conclusions about the delay.",
            "Менеджер поспешил с выводами о задержке.",
        ),
    ],
    "B2": [
        (
            "Investors jumped to conclusions after the weak report.",
            "После слабого отчёта инвесторы поспешили с выводами.",
        ),
        (
            "Try not to jump to conclusions until all the data is in.",
            "Постарайся не делать выводов, пока не будут все данные.",
        ),
        (
            "Jumping to conclusions cost us a good client.",
            "Поспешные выводы стоили нам хорошего клиента.",
        ),
        (
            "He has a habit of jumping to conclusions under pressure.",
            "Под давлением у него привычка торопиться с выводами.",
        ),
        (
            "The press jumped to conclusions about the outage.",
            "Пресса поспешила с выводами о сбое.",
        ),
    ],
    "C1": [
        (
            "The committee was careful not to jump to conclusions.",
            "Комитет старался не делать поспешных выводов.",
        ),
        (
            "Jumping to conclusions undermined the whole investigation.",
            "Поспешные выводы подорвали всё расследование.",
        ),
        (
            "Critics jumped to conclusions without reading the study.",
            "Критики поспешили с выводами, не прочитав исследование.",
        ),
        (
            "Had we not jumped to conclusions, the deal would have closed.",
            "Если бы мы не поспешили с выводами, сделка бы состоялась.",
        ),
        (
            "Her instinct to jump to conclusions rarely serves her well.",
            "Привычка торопиться с выводами редко идёт ей на пользу.",
        ),
    ],
    "C2": [
        (
            "Jumping to conclusions is the occupational hazard of pundits.",
            "Поспешные выводы — профессиональный риск комментаторов.",
        ),
        (
            "Far from jumping to conclusions, the auditors weighed every caveat.",
            "Аудиторы не спешили с выводами и взвесили каждую оговорку.",
        ),
        (
            "One would be forgiven for jumping to conclusions on this evidence.",
            "При таких данных поспешные выводы были бы простительны.",
        ),
        (
            "The post-mortem warned against jumping to conclusions about root causes.",
            "Разбор предостерегал от поспешных выводов о первопричинах.",
        ),
        (
            "Seasoned editors know the cost of jumping to conclusions in print.",
            "Опытные редакторы знают цену поспешных выводов в печати.",
        ),
    ],
}
_EXAMPLES: dict[str, Any] = {
    "levels": [
        {
            "level": level,
            "sentences": [{"sentence": s, "russian": r} for s, r in sentences],
        }
        for level, sentences in _EXAMPLE_SENTENCES.items()
    ]
}


class FakeLlm:
    """Records each `generate()` as `(language, category, target, generation_context)` in
    `requests`, then raises `AppError(error)` or answers `reply` (generated fields on the wire),
    validated with the Category's generated model.

    The helpers record apart: `check_grammar()` as `(language, category, target)` in
    `grammar_requests` and `examples()` as `(language, target, context)` in `example_requests`.
    Each raises `AppError(error)` too, or answers `grammar_reply` / `examples_reply` (on the
    wire), by default a verdict from `_GRAMMAR_CORRECTIONS` and the English `_EXAMPLES`.
    """

    def __init__(
        self,
        reply: dict[str, Any] | None = None,
        *,
        error: ErrorCode | None = None,
        grammar_reply: dict[str, Any] | None = None,
        examples_reply: dict[str, Any] | None = None,
    ):
        self.reply = reply
        self.error = error
        self.grammar_reply = grammar_reply
        self.examples_reply = examples_reply
        self.requests: list[tuple[Language, Category, str, str]] = []
        self.grammar_requests: list[tuple[Language, Category, str]] = []
        self.example_requests: list[tuple[Language, str, str]] = []

    async def generate(
        self, language: Language, category: Category, target: str, generation_context: str
    ) -> GeneratedFields:
        self.requests.append((language, category, target, generation_context))
        if self.error is not None:
            raise AppError(self.error)
        reply = _REPLIES[category] if self.reply is None else self.reply
        return generated_model(category).model_validate(reply)

    async def check_grammar(
        self, language: Language, category: Category, target: str
    ) -> GrammarCheck:
        self.grammar_requests.append((language, category, target))
        if self.error is not None:
            raise AppError(self.error)
        reply = self.grammar_reply
        if reply is None:
            reply = _GRAMMAR_CORRECTIONS.get(target, _GRAMMAR_CORRECT)
        return GrammarCheck.model_validate(reply)

    async def examples(self, language: Language, target: str, context: str) -> ExampleSet:
        self.example_requests.append((language, target, context))
        if self.error is not None:
            raise AppError(self.error)
        reply = _EXAMPLES if self.examples_reply is None else self.examples_reply
        return ExampleSet.model_validate(reply)

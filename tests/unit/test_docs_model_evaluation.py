"""Story 4.2: the model-evaluation fixtures section of the setup docs (FR-4, FR-17; addendum A2).

Every model in `OPENROUTER_MODELS` must support strict JSON Schema output and be evaluated
before it is configured. `docs/configuration.md` gets an "Evaluating a model" section: a fixture
set of representative Targets, English and French, Vocabulary and Sentence, with what a good
Russian Draft for each looks like, and when to run it (before adding a model to the list or
reordering it).
"""

import re

import pytest

from tests.support.release import REPO_ROOT

pytestmark = [
    pytest.mark.p2,
]

CONFIGURATION = REPO_ROOT / "docs" / "configuration.md"
HEADING = "## Evaluating a model"


def section() -> str:
    """The "Evaluating a model" section of docs/configuration.md, up to the next `## `."""
    text = CONFIGURATION.read_text(encoding="utf-8")
    start = text.find(f"\n{HEADING}\n")
    if start < 0:
        return ""
    end = text.find("\n## ", start + 1)
    return text[start : end if end >= 0 else None]


def table_rows(text: str) -> list[list[str]]:
    """The cells of each table row in `text`, divider rows dropped."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.strip().startswith("|")
    ]
    return [row for row in rows if not all(re.fullmatch(r":?-+:?", c) for c in row)]


def test_configuration_docs_say_how_to_evaluate_a_model_against_fixtures() -> None:
    """AC-18: an "Evaluating a model" section with a fixture table covering English and French,
    Vocabulary and Sentence, run before adding a model to or reordering OPENROUTER_MODELS.
    """
    text = section()

    assert text != ""

    assert "OPENROUTER_MODELS" in text
    assert re.search(r"\badd", text, re.I) and re.search(r"\breorder", text, re.I)
    assert "strict JSON Schema" in text
    covered = {
        (language, category)
        for row in table_rows(text)
        for language in ("English", "French")
        for category in ("Vocabulary", "Sentence")
        if language in row and category in row
    }
    assert covered == {
        ("English", "Vocabulary"),
        ("English", "Sentence"),
        ("French", "Vocabulary"),
        ("French", "Sentence"),
    }
    assert "Russian" in text

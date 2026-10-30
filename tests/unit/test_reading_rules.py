"""The French reading rules' package data and its loader (domain/reading_rules.py).

`reading_rules()` reads `language_lab/data/french_reading_rules/rules.json` and the bundled
`audio/<key>-<n>.mp3` once: 46 rules in deck order, each with a fixed lowercase UUIDv4 id and
three example words, every one with a complete MP3. `audio/index.json` (written by
scripts/generate_reading_rules_audio.py) maps each file to the word it says, so a changed word
without regenerated audio fails here.
"""

import json
import re
import shutil
from pathlib import Path

import pytest

from language_lab.domain.audio import validate_mp3
from language_lab.domain.reading_rules import (
    EXAMPLES_PER_RULE,
    audio_file,
    data_dir,
    load_reading_rules,
    reading_rules,
)

DATA = Path(str(data_dir()))
UUID4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


def _rows() -> list[dict]:
    return json.loads((DATA / "rules.json").read_text(encoding="utf-8"))


@pytest.mark.p0
def test_the_packaged_rules_load_in_deck_order_with_three_examples_each() -> None:
    rules = reading_rules()

    assert len(rules) == 46
    assert [r.key for r in rules[:3]] == ["ou", "ou-vowel", "oi"]
    assert rules[-1].combination == "-ent (verbs)"
    assert all(len(r.examples) == EXAMPLES_PER_RULE for r in rules)
    assert all(UUID4.fullmatch(r.id) for r in rules)
    for attribute in ("id", "key", "combination"):
        values = [getattr(r, attribute) for r in rules]
        assert len(set(values)) == len(values), attribute
    assert reading_rules() is rules  # loaded once


@pytest.mark.p1
def test_every_example_has_a_valid_mp3_and_the_index_says_its_word() -> None:
    rules = reading_rules()
    index = json.loads((DATA / "audio" / "index.json").read_text(encoding="utf-8"))
    expected = {audio_file(r.key, n): e.word for r in rules for n, e in enumerate(r.examples, 1)}

    assert index == expected
    for rule in rules:
        for example in rule.examples:
            validate_mp3(example.audio)
    assert len({e.audio for r in rules for e in r.examples}) == 138  # every word its own clip


@pytest.mark.p1
def test_the_audio_directory_holds_no_stray_file() -> None:
    files = {p.name for p in (DATA / "audio").iterdir()}
    rows = _rows()

    assert files == {"index.json"} | {
        audio_file(row["key"], n) for row in rows for n in range(1, EXAMPLES_PER_RULE + 1)
    }
    assert {p.name for p in DATA.iterdir()} == {"rules.json", "audio"}


def _copy(tmp_path: Path, change) -> Path:
    """The packaged data copied to `tmp_path`, with `change(rows)` applied to rules.json."""
    target = tmp_path / "rules"
    shutil.copytree(DATA, target)
    rows = _rows()
    change(rows)
    (target / "rules.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return target


def _two_examples(rows: list[dict]) -> None:
    rows[0]["examples"] = rows[0]["examples"][:2]


def _duplicate_id(rows: list[dict]) -> None:
    rows[1]["id"] = rows[0]["id"]


def _duplicate_combination(rows: list[dict]) -> None:
    rows[1]["combination"] = rows[0]["combination"]


def _uppercase_id(rows: list[dict]) -> None:
    rows[0]["id"] = rows[0]["id"].upper()


@pytest.mark.p2
@pytest.mark.parametrize(
    "change", [_two_examples, _duplicate_id, _duplicate_combination, _uppercase_id]
)
def test_the_loader_refuses_malformed_rules(tmp_path: Path, change) -> None:
    with pytest.raises(ValueError):
        load_reading_rules(_copy(tmp_path, change))


@pytest.mark.p2
def test_the_loader_refuses_an_audio_file_that_is_not_an_mp3(tmp_path: Path) -> None:
    target = _copy(tmp_path, lambda rows: None)
    (target / "audio" / audio_file("ou", 2)).write_bytes(b"not an mp3")

    with pytest.raises(ValueError, match="audio"):
        load_reading_rules(target)

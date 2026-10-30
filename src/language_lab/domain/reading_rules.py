"""The French reading rules Setup seeds into `<Prefix>::Study::French::Reading Rules`.

Package data, read once: `language_lab/data/french_reading_rules/rules.json` holds the rules
in deck order, each with its fixed UUIDv4 `id` (the note's `RuleId` and the AD-7 media id),
an ASCII `key`, the combination, its IPA transcription, an optional note and three example
words. `audio/<key>-<n>.mp3` is example `n`'s pre-generated fr-CA audio (Azure
`fr-CA-SylvieNeural`, by scripts/generate_reading_rules_audio.py); Setup never synthesizes.

`reading_rules()` validates what it loads: three examples each, unique ids, keys and
combinations, and every MP3 complete (`validate_mp3`). Anything else is a packaging bug and
raises `ValueError`.
"""

import functools
import json
import re
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable

from language_lab.domain.audio import validate_mp3
from language_lab.domain.errors import AppError

EXAMPLES_PER_RULE = 3
_UUID4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_KEY = re.compile(r"[a-z][a-z0-9-]*")


def data_dir() -> Traversable:
    """The package data directory of the rules and their audio."""
    return files("language_lab") / "data" / "french_reading_rules"


@dataclass(frozen=True)
class Example:
    word: str
    audio: bytes  # a complete MP3 of the word


@dataclass(frozen=True)
class ReadingRule:
    id: str  # lowercase UUIDv4: the note's RuleId
    key: str  # the ASCII stem of its audio files
    combination: str  # the card's front
    transcription: str
    note: str  # "" when none
    examples: tuple[Example, ...]


def audio_file(key: str, n: int) -> str:
    """The file name of example `n` (1-based) of the rule keyed `key`, under `audio/`."""
    return f"{key}-{n}.mp3"


def _text(row: dict[str, object], name: str, *, empty: bool = False) -> str:
    value = row.get(name)
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"reading rule {row.get('key')!r}: bad {name}")
    return value


def _rule(row: object, audio: Traversable) -> ReadingRule:
    if not isinstance(row, dict):
        raise ValueError("reading rule: not an object")
    rule_id, key = _text(row, "id"), _text(row, "key")
    if not _UUID4.fullmatch(rule_id):
        raise ValueError(f"reading rule {key!r}: id is not a lowercase UUIDv4")
    if not _KEY.fullmatch(key):
        raise ValueError(f"reading rule {key!r}: key is not ASCII")
    words = row.get("examples")
    if not isinstance(words, list) or len(words) != EXAMPLES_PER_RULE:
        raise ValueError(f"reading rule {key!r}: needs {EXAMPLES_PER_RULE} examples")
    examples = []
    for n, word in enumerate(words, 1):
        if not isinstance(word, str) or not word.strip():
            raise ValueError(f"reading rule {key!r}: bad example {n}")
        data = (audio / audio_file(key, n)).read_bytes()
        try:
            validate_mp3(data)
        except AppError:
            raise ValueError(f"reading rule {key!r}: example {n} audio is not an MP3") from None
        examples.append(Example(word, data))
    return ReadingRule(
        id=rule_id,
        key=key,
        combination=_text(row, "combination"),
        transcription=_text(row, "transcription"),
        note=_text(row, "note", empty=True),
        examples=tuple(examples),
    )


def load_reading_rules(directory: Traversable) -> tuple[ReadingRule, ...]:
    """The rules in `directory` (`rules.json` and `audio/`), in data order, validated."""
    rows = json.loads((directory / "rules.json").read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("rules.json: not a list of rules")
    rules = tuple(_rule(row, directory / "audio") for row in rows)
    for attribute in ("id", "key", "combination"):
        values = [getattr(rule, attribute) for rule in rules]
        if len(set(values)) != len(values):
            raise ValueError(f"rules.json: duplicate {attribute}")
    return rules


@functools.cache
def reading_rules() -> tuple[ReadingRule, ...]:
    """The packaged French reading rules, loaded and validated once."""
    return load_reading_rules(data_dir())

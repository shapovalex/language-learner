"""Story 2.6: one query builder for every Anki search the adapter sends (AD-4, NFR-1).

`deck_query(manifest, deck)` and `note_query(manifest, note_type)` in adapters/anki/query.py
are the only way the adapter builds a search. They emit exact scopes only, `deck:"<Prefix>"`,
`deck:"<Prefix>::<path>"` and `note:"<note type>"`, for names the manifest declares, and they
raise `ValueError` for anything else. User text never reaches them: a name that isn't in the
manifest, a wildcard, or a quote that would widen the scope is refused.
"""

import re

import pytest

from language_lab.adapters.anki.manifest import build_manifest
from language_lab.adapters.anki.query import deck_query, note_query

RELEASE = "LanguageLab"
DEV = "LanguageLabDev"

# Inputs that must never become a search: outside the Prefix, another Prefix, a wildcard, or
# text that would close the quote and add a scope of its own
REFUSED_DECKS = (
    "Default",
    f"{DEV}::Study",
    f"{RELEASE}*",
    f"{RELEASE}::Study::*",
    f"{RELEASE}::Study::Spanish",
    f'{RELEASE}::Study" or deck:*',
    f"{RELEASE}::Captures ",
    "",
)
REFUSED_NOTE_TYPES = (
    "Basic",
    f"{DEV} Capture",
    f"{RELEASE} *",
    f'{RELEASE} Capture" or note:*',
    "jump to conclusions",
    "",
)

EXACT_DECK = re.compile(rf'deck:"{RELEASE}(::[^"*:\\][^"*\\]*)?"')
EXACT_NOTE = re.compile(rf'note:"{RELEASE} [^"*\\]+"')


@pytest.mark.p0
def test_query_builder_emits_only_exact_scopes_for_manifest_names() -> None:
    """AC-3: every built search is an exact deck or note scope; any other name is refused."""
    manifest = build_manifest(RELEASE)

    assert [deck_query(manifest, deck) for deck in manifest.decks] == [
        f'deck:"{deck}"' for deck in manifest.decks
    ]
    assert [note_query(manifest, nt.name) for nt in manifest.note_types] == [
        f'note:"{nt.name}"' for nt in manifest.note_types
    ]
    built = [deck_query(manifest, d) for d in manifest.decks] + [
        note_query(manifest, nt.name) for nt in manifest.note_types
    ]
    assert [q for q in built if not (EXACT_DECK.fullmatch(q) or EXACT_NOTE.fullmatch(q))] == []
    for deck in REFUSED_DECKS:
        with pytest.raises(ValueError):
            deck_query(manifest, deck)
    for note_type in REFUSED_NOTE_TYPES:
        with pytest.raises(ValueError):
            note_query(manifest, note_type)
    # A LanguageLabDev manifest refuses the release names in turn
    dev = build_manifest(DEV)
    with pytest.raises(ValueError):
        deck_query(dev, f"{RELEASE}::Study")
    with pytest.raises(ValueError):
        note_query(dev, f"{RELEASE} Capture")

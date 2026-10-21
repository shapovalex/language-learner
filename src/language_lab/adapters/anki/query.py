"""The one query builder for every Anki search the adapter sends (AD-4, NFR-1).

Only exact scopes for names the manifest declares: `deck:"<deck>"` and `note:"<note type>"`.
Any other name raises `ValueError`, so user text, wildcards or quotes never widen a search.
"""

from language_lab.adapters.anki.manifest import Manifest


def deck_query(manifest: Manifest, deck: str) -> str:
    if deck not in manifest.decks:
        raise ValueError("not a manifest deck")
    return f'deck:"{deck}"'


def note_query(manifest: Manifest, note_type: str) -> str:
    if note_type not in {nt.name for nt in manifest.note_types}:
        raise ValueError("not a manifest note type")
    return f'note:"{note_type}"'

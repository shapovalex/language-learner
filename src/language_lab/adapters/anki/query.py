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


def pronounce_queue_query(manifest: Manifest, deck: str, note_type: str, card: int) -> str:
    """The Pronounce queue of one Language/Category (FR-30, AD-6): the exact deck and note type
    scopes, template `card` (1-based), new or due, and not suspended.
    """
    if not 1 <= card <= 4:
        raise ValueError("not a card template")
    scope = f"{deck_query(manifest, deck)} {note_query(manifest, note_type)}"
    return f"{scope} card:{card} (is:due OR is:new) -is:suspended"

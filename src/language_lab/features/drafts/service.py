"""Drafts: the blank Draft, which only issues the ItemId the Draft carries until Save (AD-8).

Entry 2 adds the generated Draft beside it.
"""

import uuid


class DraftService:
    def blank(self) -> str:
        """A fresh ItemId, a UUIDv4 in lowercase canonical form. Touches no Anki."""
        return str(uuid.uuid4())
